# api/main.py
import os
import uuid
import requests
import hmac
import hashlib
import base64
import json
from datetime import timedelta
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
import google.auth
from google.auth import iam
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import List, Optional

# Internal Modules
from policy_engine import get_session_policy
from telemetry import log_event, TelemetryTimer
from vertex import search_r_docs, converse_r_docs
from llm_orchestrator import call_agent, call_agent_stream

app = FastAPI(title="aiR Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "us-central1" # Base compute location
SESSION_BUCKET = os.getenv("SESSION_BUCKET", f"{PROJECT_ID}-sessions")
R_RUNTIME_URL = os.getenv("R_RUNTIME_URL")
API_SECRET = os.getenv("API_SECRET", "default-dev-secret")

credentials, _ = google.auth.default()
SERVICE_ACCOUNT_EMAIL = None
if hasattr(credentials, 'service_account_email'):
    SERVICE_ACCOUNT_EMAIL = credentials.service_account_email
else:
    try:
        import requests
        resp = requests.get("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email", headers={"Metadata-Flavor": "Google"})
        SERVICE_ACCOUNT_EMAIL = resp.text
    except:
        pass

storage_client = storage.Client(credentials=credentials)
vertexai.init(project=PROJECT_ID, location=LOCATION)

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

# --- Helpers ---
def validate_session_token(token: str) -> dict:
    try:
        payload_b64, signature = token.rsplit(".", 1)
        expected = hmac.new(API_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(signature, expected): raise ValueError()
        return json.loads(base64.urlsafe_b64decode(payload_b64).decode())
    except: raise HTTPException(status_code=403, detail="Invalid token")

def sign_session_data(data: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
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
async def create_session(request: SessionCreate):
    session_uuid = str(uuid.uuid4())
    token_data = {
        "id": session_uuid, 
        "analysis_mode": request.analysis_mode,
        "objective": request.objective,
        "analysis_plan": request.analysis_plan
    }
    signed_token = sign_session_data(token_data)
    log_event("session_created", session_uuid, {"mode": get_session_policy(request.analysis_mode)["label"]})
    return {"session_id": signed_token}

@app.post("/v1/sessions/{session_id}/refresh")
async def refresh_session(session_id: str, payload: dict = Body(...)):
    session_data = validate_session_token(session_id)
    session_data["analysis_mode"] = payload.get("analysis_mode", "guided")
    log_event("policy_updated", session_data["id"], {"new_mode": get_session_policy(session_data["analysis_mode"])["label"]})
    return {"session_id": sign_session_data(session_data)}

@app.post("/v1/sessions/{session_id}/chat")
async def chat(session_id: str, request: ChatRequest):
    session_data = validate_session_token(session_id)
    session_uuid = session_data["id"]
    analysis_mode = session_data.get("analysis_mode", "guided")
    objective = session_data.get("objective", "Exploration")
    analysis_plan = session_data.get("analysis_plan")
    
    depth = request.coaching_depth if request.coaching_depth is not None else session_data.get("coaching_depth", 50)
    policy = get_session_policy(analysis_mode)
    
    if depth < 30:
        policy["explanation_depth"] = "minimal"
        policy["system_prompt_extension"] += " Be extremely concise. Minimize theory. Focus purely on immediate code and results."
    elif depth > 70:
        policy["explanation_depth"] = "exhaustive"
        policy["system_prompt_extension"] += " Provide detailed statistical theory and comprehensive rationale for every step."

    intent = classify_intent(request.message)
    grounding_context = ""
    g_type, g_count = "none", 0

    if intent == "FILE_TASK":
        grounding_context = get_file_previews(session_uuid, request.file_names)
        g_type, g_count = "session_files", len(request.file_names)
    elif intent in ["DOCS_EXPLAIN", "DEBUG"]:
        grounding_context, g_count, _ = search_r_docs(request.message)
        g_type = "r_docs" if g_count > 0 else "none"

    with TelemetryTimer() as timer:
        context_data = {
            "objective": request.objective or objective,
            "analysis_plan": analysis_plan,
            "env_summary": request.env_summary,
            "recent_history": request.recent_history,
            "last_error": request.last_error,
            "grounding_context": grounding_context
        }
        
        # Consolidate on the stable gemini-1.5-flash logic
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
                summary="I encountered an error generating the final summary.",
                what="Error", why="Model execution failed.", code="", interpretation=str(e), next_step="Try again.", options=[], uses_objects=[], should_autorun=False
            )

    log_event("chat_request", session_uuid, {
        "request_intent": intent,
        "is_grounded": g_count > 0,
        "g_type": g_type,
        "mode": policy["label"]
    })
    
    return {
        "response": structured_response.summary,
        "structured_response": structured_response.model_dump(),
        "grounded": g_count > 0,
        "g_type": g_type,
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
    
    intent = classify_intent(request.message)
    grounding_context = ""
    if intent == "FILE_TASK":
        grounding_context = get_file_previews(session_uuid, request.file_names)
    elif intent in ["DOCS_EXPLAIN", "DEBUG"]:
        grounding_context, _, _ = search_r_docs(request.message)

    context_data = {
        "objective": request.objective or objective,
        "analysis_plan": analysis_plan,
        "env_summary": request.env_summary,
        "recent_history": request.recent_history,
        "last_error": request.last_error,
        "grounding_context": grounding_context
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
                r_result = resp.json()
                if r_result.get("status") == "error":
                    status = "error"
                    error_msg = r_result.get("error")
                else:
                    plot_urls = []
                    raw_plots = r_result.get("plots", [])
                    for raw_path in raw_plots:
                        plot_path = raw_path[0] if isinstance(raw_path, list) and len(raw_path) > 0 else raw_path
                        if not isinstance(plot_path, str): continue
                        plot_urls.append(f"/v1/artifacts/{plot_path}")
                    r_result["plots"] = plot_urls
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
