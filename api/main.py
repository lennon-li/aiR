# api/main.py
import os
import uuid
import requests
import hmac
import hashlib
import base64
import json
import re
import time
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.cloud import storage
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
import google.auth
from google.auth import iam
import vertexai
from typing import List, Optional
from google.cloud import dialogflowcx_v3 as dialogflow
from google.api_core.client_options import ClientOptions

# Internal Modules
from policy_engine import get_session_policy
from telemetry import log_event, TelemetryTimer
from vertex import search_r_docs
from llm_orchestrator import call_agent, call_agent_stream
from tools.r_tool import execute_r_code_internal
from schemas import AgentChatResponse

app = FastAPI(title="aiR Control Plane")

# --- Constants ---
CORE_MANDATE = """[AGENT_TYPE: R_ANALYSIS_COPILOT]
[MANDATE_VERSION: 2.0]
[RULES]
1. EXECUTION_GATING: You are NOT allowed to claim that objects exist or actions have been performed unless you provide the EXACT R code in fences.
2. FORMATTING: Use only ```r ... ``` for code.
3. AUTONOMOUS_MODE_PROTOCOL: 
   - OUTPUT_STRUCTURE: [R_CODE_BLOCK]
   - CHAT_TEXT: NULL or Minimal.
   - NO_HALLUCINATION: If no real stdout is provided in context, you MUST assume the environment is empty.
4. BALANCED_MODE_PROTOCOL: Concise explanation + R code.
5. GUIDED_MODE_PROTOCOL: Educational explanation + Propose R code.
6. GOAL_SHAPING: If objective is VAGUE (e.g. 'analyze this'), ask for: Outcome, Exposure, Population, Hypotheses.
[/RULES]"""

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
SESSION_BUCKET = os.getenv("SESSION_BUCKET", f"{PROJECT_ID}-sessions")
R_RUNTIME_URL = os.getenv("R_RUNTIME_URL")
API_SECRET = os.getenv("API_SECRET")

# Fail-fast for production auth security
if PROJECT_ID == "air-mvp-lennon-li-2026": # Production project ID
    if not API_SECRET or API_SECRET == "default-dev-secret":
        print("CRITICAL: API_SECRET is missing or using default in production! Shutting down.")
        import sys
        sys.exit(1)
elif not API_SECRET:
    API_SECRET = "default-dev-secret"

# Dialogflow CX / Conversation Agent Config
AGENT_ID = os.getenv("CONVERSATION_AGENT_ID", "1e9ad1e9-30bb-45ad-98e1-16714da84164")
LANGUAGE_CODE = os.getenv("CONVERSATION_AGENT_LANGUAGE_CODE", "en")

credentials, _ = google.auth.default()
storage_client = storage.Client(credentials=credentials)
vertexai.init(project=PROJECT_ID, location="us-central1")

# --- Schemas ---
class SessionCreate(BaseModel):
    objective: str
    analysis_mode: str = "guided"
    analysis_plan: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    analysis_mode: str = "guided"
    history: Optional[List[dict]] = []
    file_names: Optional[List[str]] = []
    objective: Optional[str] = None
    env_summary: Optional[List[dict]] = []
    recent_history: Optional[List[str]] = []
    last_error: Optional[str] = None
    coaching_depth: Optional[int] = 50

class AgentChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    event: Optional[str] = None
    context: Optional[dict] = None

# --- Helpers ---
def normalize_agent_event(event: Optional[str]) -> Optional[str]:
    if event == "WELCOME":
        return "playbookStart"
    return event

def save_execution_result(session_uuid: str, result: dict):
    bucket = storage_client.bucket(SESSION_BUCKET)
    blob = bucket.blob(f"sessions/{session_uuid}/last_execution.json")
    blob.upload_from_string(json.dumps(result))

def get_last_execution_result(session_uuid: str) -> Optional[dict]:
    bucket = storage_client.bucket(SESSION_BUCKET)
    blob = bucket.blob(f"sessions/{session_uuid}/last_execution.json")
    if blob.exists():
        try:
            return json.loads(blob.download_as_string())
        except:
            return None
    return None

def extract_r_code(text: str, strict: bool = False) -> str:
    """
    Extracts R code from markdown blocks. 
    If strict=True (autonomous), only accepts code in fences.
    """
    # 1. Look for ```r ... ``` or ```R ... ```
    blocks = re.findall(r"```(?:[Rr])\n?([\s\S]*?)```", text)
    if blocks:
        return "\n\n".join([b.strip() for b in blocks])
    
    # 2. Fallback to generic fences if not strict
    if not strict:
        generic_blocks = re.findall(r"```\n?([\s\S]*?)```", text)
        if generic_blocks:
            # Filter blocks that contain R-like patterns
            r_blocks = [b.strip() for b in generic_blocks if "<-" in b or "(" in b or "library" in b]
            if r_blocks:
                return "\n\n".join(r_blocks)
    
    # 3. Heuristic fallback (Non-strict only)
    if not strict and ("<-" in text or "library(" in text):
        lines = text.split("\n")
        # Very strict heuristic: must look like code and not be too long
        code_lines = [l for l in lines if ("<-" in l or "(" in l or l.startswith("  ") or not l.strip()) and len(l) < 200]
        if len(code_lines) > len(lines) * 0.8 and len(lines) < 20:
            return text.strip()
            
    return ""

def is_low_signal_reply(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return True

    lower = cleaned.lower()
    if lower in {"...", "fdadf", "hi", "hello", "ok", "okay", "test"}:
        return True

    if len(cleaned) <= 8 and re.fullmatch(r"[a-zA-Z]+", cleaned):
        return True

    if re.fullmatch(r"```[Rr]?\s*(?:\.\.\.)?\s*```", cleaned):
        return True

    return False

def is_placeholder_code(text: str) -> bool:
    cleaned = (text or "").strip()
    return cleaned in {"", "..."} or bool(re.fullmatch(r"[.`\s]+", cleaned))

def strip_r_code_blocks(text: str) -> str:
    if not text:
        return ""

    without_r_fences = re.sub(r"```(?:[Rr])\n?[\s\S]*?```", "", text)
    without_generic_fences = re.sub(r"```\n?[\s\S]*?```", "", without_r_fences)
    collapsed = re.sub(r"\n{3,}", "\n\n", without_generic_fences)
    return collapsed.strip()

def normalize_plot_refs(raw_plots, plot_url: Optional[str] = None) -> List[str]:
    normalized = []
    candidates = list(raw_plots or [])

    if plot_url:
        candidates.append(plot_url)

    for raw_path in candidates:
        plot_path = raw_path[0] if isinstance(raw_path, list) and len(raw_path) > 0 else raw_path
        if not isinstance(plot_path, str) or not plot_path:
            continue
        if plot_path.startswith("http://") or plot_path.startswith("https://"):
            normalized.append(plot_path)
        else:
            normalized.append(f"/v1/artifacts/{plot_path.lstrip('/')}")

    # Preserve order while de-duplicating.
    return list(dict.fromkeys(normalized))

def summarize_environment(target_env: dict) -> List[dict]:
    env_summary = []
    for name, value in target_env.items():
        if name.startswith("."):
            continue

        obj_type = type(value).__name__
        details = ""
        shape = getattr(value, "shape", None)
        if isinstance(shape, tuple) and len(shape) == 2:
            details = f"{shape[0]} rows x {shape[1]} cols"
        elif isinstance(value, (list, tuple, set)):
            details = f"{len(value)} items"
        elif isinstance(value, dict):
            details = f"{len(value)} keys"

        env_summary.append({"name": name, "type": obj_type, "details": details})

    return env_summary

def normalize_r_service_result(r_result: dict) -> dict:
    normalized = dict(r_result or {})
    normalized.setdefault("status", "success")

    if "stdout" not in normalized:
        normalized["stdout"] = normalized.get("output", "")
    if "environment" not in normalized or normalized["environment"] is None:
        normalized["environment"] = []
    if "objects_changed" not in normalized or normalized["objects_changed"] is None:
        normalized["objects_changed"] = []

    normalized["plots"] = normalize_plot_refs(
        normalized.get("plots", []),
        plot_url=normalized.get("plot_url"),
    )
    return normalized

def validate_session_token(token: str) -> dict:
    try:
        token = (token or "").strip()
        print("AUTH: token_validation_called")
        if token.startswith('"') and token.endswith('"') and len(token) >= 2:
            token = token[1:-1]
        if not token:
            print("AUTH: token_present=False, failure_reason=missing_or_malformed")
            raise ValueError("Malformed token")
        if "." not in token:
            print("AUTH: token_present=True, failure_reason=missing_or_malformed")
            raise ValueError("Malformed token")
        
        payload_b64, signature = token.rsplit(".", 1)
        # Strip padding for consistent signature check
        payload_unpadded = payload_b64.rstrip('=')
        expected = hmac.new(API_SECRET.encode(), payload_unpadded.encode(), hashlib.sha256).hexdigest()[:16]
        
        if not hmac.compare_digest(signature, expected):
            print(f"AUTH: token_present=True, token_parts_count=2, signature_match=False, failure_reason=signature_mismatch")
            raise ValueError("Signature mismatch")
            
        # Re-add padding for decoding if needed
        padding_needed = (4 - len(payload_unpadded) % 4) % 4
        decoded = base64.urlsafe_b64decode(payload_unpadded + '=' * padding_needed).decode()
        return json.loads(decoded)
    except Exception as e:
        print(f"AUTH: token_present=True, payload_decode_success=False, failure_reason={type(e).__name__}")
        raise HTTPException(status_code=403, detail="Invalid token")

_bearer_scheme = HTTPBearer(auto_error=False)

async def verify_api_secret(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)):
    token = credentials.credentials if credentials else None
    if not token or not hmac.compare_digest(token, API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")

def sign_session_data(data: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip('=')
    signature = hmac.new(API_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}.{signature}"

def get_file_previews(session_uuid: str, file_names: List[str]):
    previews = []
    bucket = storage_client.bucket(SESSION_BUCKET)
    for name in file_names[:3]:
        blob = bucket.blob(f"sessions/{session_uuid}/uploads/{name}")
        try:
            content = blob.download_as_string(start=0, end=1024).decode('utf-8', errors='ignore')
            previews.append(f"File: {name}\nContent Sample:\n{content}")
        except: continue
    return "\n---\n".join(previews)

def classify_intent(message: str) -> str:
    m = message.lower()
    if any(k in m for k in ["generate", "simulate", "make a", "create", "toy", "example data", "write code", "plot a", "sum ", "mean of", "df with", "boxplot", "scatter", "summary", "cols", "subset", "calculate", "mock"]):
        return "CODE_GEN"
    if any(k in m for k in ["fail", "error", "error:", "why did", "not found", "invalid"]):
        return "DEBUG"
    if any(k in m for k in ["file", "this data", "uploaded", "summarize"]):
        return "FILE_TASK"
    if any(k in m for k in ["how do i use", "explain", "what does", "meaning of", "::"]):
        return "DOCS_EXPLAIN"
    return "CODE_GEN"

# --- Routes ---
@app.post("/v1/sessions")
async def create_session(request: SessionCreate, _: None = Depends(verify_api_secret)):
    with TelemetryTimer() as timer:
        session_uuid = str(uuid.uuid4())
        token_data = {
            "id": session_uuid,
            "analysis_mode": request.analysis_mode,
            "objective": request.objective,
            "analysis_plan": request.analysis_plan
        }
        signed_token = sign_session_data(token_data)
    log_event("session_created", session_uuid, {"duration_ms": timer.duration_ms, "mode": get_session_policy(request.analysis_mode)["label"]})
    return {"session_id": signed_token}

@app.post("/v1/sessions/{session_id}/refresh")
async def refresh_session(session_id: str, payload: dict = Body(...)):
    session_data = validate_session_token(session_id)
    session_data["analysis_mode"] = payload.get("analysis_mode", "guided")
    log_event("policy_updated", session_data["id"], {"new_mode": get_session_policy(session_data["analysis_mode"])["label"]})
    return {"session_id": sign_session_data(session_data)}

@app.post("/v1/agent/chat")
async def agent_chat(request: AgentChatRequest):
    """
    Policy-driven orchestrator that uses Dialogflow CX for dialogue 
    but handles R execution and session state in the backend.
    """
    # 1. Parse and validate session
    session_data = validate_session_token(request.session_id)
    session_uuid = session_data["id"]
    
    # Priority: context.guidance_depth > session_data.analysis_mode
    analysis_mode = session_data.get("analysis_mode", "guided")
    agent_context = request.context or {}
    if agent_context.get("guidance_depth"):
        analysis_mode = agent_context.get("guidance_depth")
    
    objective = agent_context.get("objective") or session_data.get("objective", "Exploration")
    
    # Map 'auto' to 'autonomous' for consistency
    if analysis_mode == "auto":
        analysis_mode = "autonomous"

    normalized_event = normalize_agent_event(request.event)

    # 2. Setup Dialogflow Client
    client_options = None
    if LOCATION != "global":
        client_options = ClientOptions(api_endpoint=f"{LOCATION}-dialogflow.googleapis.com")
    
    client = dialogflow.SessionsClient(credentials=credentials, client_options=client_options)
    session_path = client.session_path(PROJECT_ID, LOCATION, AGENT_ID, session_uuid)
    
    # 3. Retrieve last execution result for context
    last_result = get_last_execution_result(session_uuid)
    
    # 4. Handle Context (Parameters)
    agent_context.update({
        "analysis_mode": analysis_mode,
        "objective": objective,
        "core_mandate": CORE_MANDATE,
        "instruction": CORE_MANDATE,
        "system_instruction": CORE_MANDATE
    })
    
    if last_result:
        # Inject last execution summary into context
        env_summary = last_result.get("environment", [])
        env_str = ", ".join([obj.get("name") for obj in env_summary])
        agent_context["last_execution_ok"] = last_result.get("ok", True)
        agent_context["last_execution_output"] = last_result.get("stdout", "")[:1000] # Truncate for context
        agent_context["available_objects"] = env_str

    # 5. Prepare final message with injected instruction
    final_message = request.message
    if final_message:
        # Instruction injection with both prefix and suffix to battle recency bias
        system_prefix = f"### SYSTEM INSTRUCTION ###\n{CORE_MANDATE}\nCURRENT MODE: {analysis_mode.upper()}\n"
        if last_result:
            system_prefix += f"PREVIOUS R OUTPUT: {agent_context.get('last_execution_output')}\n"
        
        system_suffix = "\n\nCRITICAL: Provide ONLY valid R code in fences. Do not hallucinate results."
        final_message = f"{system_prefix}\nUSER: {final_message}{system_suffix}"

    query_params = dialogflow.QueryParameters(
        parameters=agent_context
    )
    
    # 6. Prepare Query Input
    query_input = None
    if normalized_event:
        query_input = dialogflow.QueryInput(
            event=dialogflow.EventInput(event=normalized_event),
            language_code=LANGUAGE_CODE
        )
    else:
        query_input = dialogflow.QueryInput(
            text=dialogflow.TextInput(text=final_message),
            language_code=LANGUAGE_CODE
        )
    
    # 7. Execute Detect Intent
    def do_detect(q_input):
        req = dialogflow.DetectIntentRequest(
            session=session_path,
            query_input=q_input,
            query_params=query_params
        )
        return client.detect_intent(request=req)

    try:
        start_time = time.time()
        response = do_detect(query_input)
        agent_latency = (time.time() - start_time) * 1000
        
        # DEBUG LOGGING
        print(f"DEBUG: Dialogflow Response: {response}")
        
        # Fallback for playbookStart
        if normalized_event == "playbookStart" and not response.query_result.response_messages:
            fallback_input = dialogflow.QueryInput(
                text=dialogflow.TextInput(text="hi"),
                language_code=LANGUAGE_CODE
            )
            response = do_detect(fallback_input)
            
        # 8. Extract response text - DEEP EXTRACTION
        # First, try to get anything from the standard text response fields
        messages = response.query_result.response_messages
        reply_text = ""
        for msg in messages:
            if hasattr(msg, "text") and msg.text and msg.text.text:
                reply_text += "\n".join(msg.text.text)
            elif hasattr(msg, "payload") and msg.payload:
                if "text" in msg.payload:
                    reply_text += str(msg.payload["text"])
        
        # Second, check for generative info (Playbooks)
        if not reply_text.strip():
            gen_info = getattr(response.query_result, "generative_info", None)
            if gen_info:
                reply_text = getattr(gen_info, "model_output", "")
        
        # Third, if we still don't have R code or text, scan the WHOLE response string representation.
        # This is a robust "catch-all" for Playbook/Proto-nested content.
        if not reply_text.strip() or "```r" not in reply_text:
            full_resp_str = str(response)
            # Find R code fences anywhere in the response dump
            code_match = re.search(r"```r\n?([\s\S]*?)```", full_resp_str)
            if code_match:
                # If we found code but didn't have reply text, use the code block as the source
                reply_text = code_match.group(0)
            elif "model_output:" in full_resp_str:
                # Pull the raw model output and unescape it
                model_match = re.search(r'model_output:\s*"([\s\S]*?)"', full_resp_str)
                if model_match:
                    reply_text = model_match.group(1).replace('\\n', '\n').replace('\\"', '"')

        reply_text = reply_text.strip()
        
        # 9. Extract R Code - Strict extraction for autonomous mode
        extracted_code = extract_r_code(reply_text, strict=(analysis_mode == "autonomous"))
        if is_placeholder_code(extracted_code):
            extracted_code = ""
        elif extracted_code:
            reply_text = strip_r_code_blocks(reply_text)

        if is_low_signal_reply(reply_text) and not extracted_code:
            if normalized_event == "playbookStart":
                reply_text = "Ready. Ask for R code or describe the analysis you want to run."
            else:
                reply_text = "I can help with that. Ask for R code or describe the analysis step you want."
        
        # 10. Apply Execution Policy
        executed = False
        execution_output = ""
        execution_error = None
        plots = []
        environment = []
        should_execute = False
        r_latency = 0
        
        # Determine if we should auto-execute
        if extracted_code and not normalized_event:
            if analysis_mode == "autonomous":
                should_execute = True
            elif analysis_mode == "balanced":
                # Balanced mode auto-executes safe inspection commands
                safe_patterns = ["summary(", "head(", "str(", "dim(", "colnames(", "nrow(", "ls()", "getwd()"]
                if any(p in extracted_code for p in safe_patterns):
                    should_execute = True

        if should_execute:
            # Check for safety
            destructive = ["rm(", "unlink(", "file.remove("]
            if not any(d in extracted_code.lower() for d in destructive):
                log_event("agent_auto_execute", session_uuid, {"code_length": len(extracted_code), "mode": analysis_mode})
                
                r_start = time.time()
                
                # Mock execution for local testing if R_RUNTIME_URL is not set or is 'MOCK'
                if not R_RUNTIME_URL or R_RUNTIME_URL == "MOCK":
                    res = {
                        "ok": True,
                        "stdout": f"Mock output for: {extracted_code[:50]}...",
                        "error": None,
                        "plots": [],
                        "environment": [{"name": "df", "type": "data.frame", "details": "10 obs. of 3 variables"}] if "df" in extracted_code else [],
                    }
                else:
                    res = execute_r_code_internal(extracted_code, session_uuid)
                
                r_latency = (time.time() - r_start) * 1000
                
                executed = res.get("ok", False)
                execution_output = res.get("stdout", "")
                execution_error = res.get("error")
                plots = res.get("plots", [])
                environment = res.get("environment", [])
                
                # Store result for follow-up
                save_execution_result(session_uuid, res)
                
                # Override reply for autonomous mode to keep it concise
                if analysis_mode == "autonomous" and executed:
                    # Heuristic for status message
                    if "<-" in extracted_code:
                        # Extract object name from assignment
                        match = re.search(r"([a-zA-Z0-9_\.]+)\s*<-", extracted_code)
                        obj_name = match.group(1) if match else "data"
                        reply_text = f"Created `{obj_name}` in the R session."
                    else:
                        reply_text = "Ran the code in R."
            else:
                execution_output = "[AUTO-EXECUTE BLOCKED: Code contains potentially destructive commands.]"
                execution_error = "Destructive command blocked."

        # Anti-Hallucination Filter
        if not executed:
            hallucination_phrases = ["i created", "i ran", "summary is back", "the result shows", "here is the summary"]
            if any(p in reply_text.lower() for p in hallucination_phrases):
                reply_text = f"[WARNING: Agent hallucinated execution results.] {reply_text}"

        # Runtime Logging
        log_event("agent_chat_performance", session_uuid, {
            "mode": analysis_mode,
            "agent_latency_ms": agent_latency,
            "r_latency_ms": r_latency,
            "should_execute": should_execute,
            "executed": executed,
            "output_stored": executed
        })

        return AgentChatResponse(
            reply=reply_text,
            code=extracted_code if extracted_code else None,
            executed=executed,
            should_execute=should_execute,
            execution_output_hidden=executed, # Captured but hidden from chat by default
            execution_summary=execution_output[:500] if executed else None,
            execution_error=execution_error,
            plots=plots,
            environment=environment,
            session_id=request.session_id,
            mode=analysis_mode,
            agent=AGENT_ID,
            intent=response.query_result.intent.display_name if response.query_result.intent else None
        )
        
    except Exception as e:
        log_event("agent_chat_error", session_uuid, {"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/sessions/{session_id}/chat")
async def chat(session_id: str, request: ChatRequest):
    # Keep old Gemini route for reference
    session_data = validate_session_token(session_id)
    session_uuid = session_data["id"]
    analysis_mode = session_data.get("analysis_mode", "guided")
    objective = session_data.get("objective", "Exploration")
    analysis_plan = session_data.get("analysis_plan")
    policy = get_session_policy(analysis_mode)

    intent = classify_intent(request.message)
    grounding_context = ""
    if intent == "FILE_TASK":
        grounding_context = get_file_previews(session_uuid, request.file_names)

    context_data = {
        "objective": request.objective or objective,
        "analysis_plan": analysis_plan,
        "env_summary": request.env_summary,
        "recent_history": request.recent_history,
        "last_error": request.last_error,
        "grounding_context": grounding_context
    }

    from schemas import AnalysisStepResponse
    final_json_text = ""
    try:
        for event in call_agent_stream(session_uuid, request.message, policy, context_data):
            if event.get("type") == "done":
                final_json_text = event.get("full_content", "")
        structured_data = json.loads(final_json_text)
        structured_response = AnalysisStepResponse(**structured_data)
    except Exception as e:
        structured_response = AnalysisStepResponse(
            summary="Error generating summary.",
            what="Error", why="Failed.", code="", interpretation=str(e), next_step="Try again.", options=[], uses_objects=[], should_autorun=False
        )

    return {
        "response": structured_response.summary,
        "structured_response": structured_response.model_dump(),
        "grounded": False,
        "intent": intent
    }

@app.post("/v1/sessions/{session_id}/chat_stream")
async def chat_stream(session_id: str, request: ChatRequest):
    session_data = validate_session_token(session_id)
    session_uuid = session_data["id"]
    analysis_mode = session_data.get("analysis_mode", "guided")
    objective = session_data.get("objective", "Exploration")
    analysis_plan = session_data.get("analysis_plan")
    policy = get_session_policy(analysis_mode)

    context_data = {
        "objective": request.objective or objective,
        "analysis_plan": analysis_plan,
        "env_summary": request.env_summary,
        "recent_history": request.recent_history,
        "last_error": request.last_error,
        "grounding_context": ""
    }

    async def event_generator():
        try:
            for event in call_agent_stream(session_uuid, request.message, policy, context_data):
                data_to_send = event
                if hasattr(event, "model_dump"):
                    data_to_send = event.model_dump()
                yield f"data: {json.dumps(data_to_send)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/v1/sessions/{session_id}/execute")
async def execute(session_id: str, payload: dict = Body(...)):
    session_data = validate_session_token(session_id)
    session_uuid = session_data["id"]
    analysis_mode = session_data.get("analysis_mode", "guided")
    policy = get_session_policy(analysis_mode)
    prov = payload.get("provenance", "You")
    is_agent = payload.get("is_agent_code", False)
    code = payload.get("code")

    status, error_msg, r_result = "success", None, None
    with TelemetryTimer() as timer:
        try:
            token = id_token.fetch_id_token(GoogleAuthRequest(), R_RUNTIME_URL)
            r_payload = {"session_id": session_uuid, "code": code, "persist_bucket": SESSION_BUCKET}
            resp = requests.post(f"{R_RUNTIME_URL}/execute", json=r_payload, headers={"Authorization": f"Bearer {token}"}, timeout=120)

            if resp.status_code != 200:
                status = "error"
                error_msg = f"R Service Failure ({resp.status_code})"
            else:
                r_result = normalize_r_service_result(resp.json())
                if r_result.get("status") == "error":
                    status = "error"
                    error_msg = r_result.get("error")
        except Exception as e:
            status = "error"
            error_msg = str(e)

    log_event("execute_request", session_uuid, {
        "mode": policy["label"],
        "provenance": prov,
        "is_agent_code": is_agent,
        "status": status,
        "error": error_msg
    })

    if status == "error":
        return {"status": "error", "error": error_msg, "stdout": "", "plots": [], "environment": []}
    return r_result

@app.get("/v1/artifacts/{path:path}")
async def get_artifact(path: str):
    try:
        bucket = storage_client.bucket(SESSION_BUCKET)
        blob = bucket.blob(path)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="Artifact not found")
        content = blob.download_as_bytes()
        return Response(content=content, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health(): return {"status": "ok"}
