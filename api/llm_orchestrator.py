import os
import json
import re
import time
from google import genai
from google.genai import types

from schemas import AnalysisStepResponse
from tools.r_tool import execute_r_code_internal
from vertex import converse_r_docs

# Initialize GenAI Client
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "us-central1"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# --- PHASE 0: PRESERVE MODEL ---
MODEL_ID = "gemini-2.5-flash" 
# -------------------------------

MAX_TOOL_ROUNDS = 2 # Reduced from 4 for speed

# Thinking config for faster reasoning in Gemini 2.5
thinking_config = types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)

execute_r_code_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="execute_r_code",
            description="Executes R code in the current aiR session. Used for analysis, plotting, modeling, and calculations. Returns stdout, error (if any), generated plots, and environment summary.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "code": {
                        "type": "STRING",
                        "description": "Complete, valid R code to execute in the current session environment. Must not include markdown fences."
                    }
                },
                "required": ["code"]
            }
        )
    ]
)

def build_system_instruction(policy: dict, context_data: dict) -> str:
    """
    PHASE 4: Explicitly handle Coaching Depth and Mode.
    """
    mode = policy.get("label", "Guided").lower()
    depth = context_data.get("coaching_depth", 50)
    
    # Tiered Coaching Logic
    if depth > 66:
        coach_type = "SENIOR STATISTICIAN: Explain assumptions, interpret results deeply, and suggest 2-3 options."
        option_instr = "You MUST provide 2-3 'options' for the next step as buttons."
    elif depth < 34:
        coach_type = "DIRECT ASSISTANT: Just provide code and results. No filler. No options."
        option_instr = "Leave the 'options' list empty."
    else:
        coach_type = "BALANCED COPILOT: Concise explanation and 1 recommendation."
        option_instr = "Provide 1-2 'options' for the next step."

    base_instr = f"""You are aiR, an R copilot acting as a {coach_type}.

CORE RULES:
1. MODES ({mode.upper()}):
   - GUIDED: Propose next step + code. 'should_autorun' MUST be FALSE.
   - AUTONOMOUS: Provide code for direct execution. 'should_autorun' MUST be TRUE.
2. COACHING: {option_instr}
3. GROUNDING: Use 'Grounded Context' for R syntax and package docs.
4. JSON: You MUST output valid JSON following the schema.
"""
    return f"{base_instr}\n\n--- CONTEXT ---\nObj: {context_data.get('objective')}\nEnv: {context_data.get('env_summary')[:5] if context_data.get('env_summary') else 'Empty'}"

def call_agent_stream(session_uuid: str, user_message: str, policy: dict, context_data: dict):
    """
    Generator that yields chunks of the response process with instrumentation.
    """
    start_time = time.time()
    system_instruction = build_system_instruction(policy, context_data)
    
    # FAST PATH: Skip grounding for short, simple messages
    is_simple_task = len(user_message.split()) < 8 and not any(k in user_message.lower() for k in ["how", "explain", "why", "documentation", "::"])
    
    grounded_context = ""
    if not is_simple_task:
        yield {"type": "status", "message": "Grounding..."}
        grounded_context = converse_r_docs(user_message, session_uuid, preamble="You are an R documentation helper.")
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"User Message: {user_message}\n\nGrounded Context: {grounded_context}")])
    ]
    
    # Reasoning Config
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_r_code_tool],
        temperature=0.0,
        thinking=thinking_config
    )

    last_executed_code = ""
    round_count = 0
    total_r_time = 0
    
    while round_count < MAX_TOOL_ROUNDS:
        round_start = time.time()
        yield {"type": "status", "message": "Reasoning..."}
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        
        if not response.candidates:
            break
            
        candidate = response.candidates[0]
        tool_calls = []
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.function_call:
                    tool_calls.append(part.function_call)
        
        if candidate.content:
            if not candidate.content.role:
                candidate.content.role = "model"
            contents.append(candidate.content)
            
        if not tool_calls:
            break
            
        function_responses = []
        for call in tool_calls:
            if call.name == "execute_r_code":
                code = call.args.get("code", "")
                last_executed_code = code
                
                yield {"type": "status", "message": "Running R..."}
                r_start = time.time()
                result = execute_r_code_internal(code, session_uuid)
                total_r_time += int((time.time() - r_start) * 1000)
                
                result["stdout"] = (result.get("stdout", "") or "")[:800]
                
                function_responses.append(types.Part.from_function_response(
                    name="execute_r_code",
                    response={"result": result}
                ))
        
        if function_responses:
            contents.append(types.Content(role="user", parts=function_responses))
        round_count += 1
        
    # Final Structured Response
    final_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=AnalysisStepResponse,
        thinking=thinking_config
    )
    
    # Finalization
    if contents and contents[-1].role == "user":
        yield {"type": "status", "message": "Finalizing..."}
        mid_response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        if mid_response.candidates and mid_response.candidates[0].content:
            contents.append(mid_response.candidates[0].content)

    final_prompt = "Provide final JSON summary."
    if last_executed_code:
        final_prompt += f" code: {last_executed_code}"

    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=final_prompt)]))
    
    yield {"type": "status", "message": "Formatting..."}
    
    stream = client.models.generate_content_stream(
        model=MODEL_ID,
        contents=contents,
        config=final_config
    )
    
    full_text = ""
    for chunk in stream:
        if chunk.text:
            full_text += chunk.text
            yield {"type": "chunk", "content": chunk.text}
            
    total_latency = int((time.time() - start_time) * 1000)
    yield {"type": "done", "full_content": full_text, "instrumentation": {
        "total_latency_ms": total_latency,
        "r_latency_ms": total_r_time,
        "tool_rounds": round_count
    }}

def call_agent(session_uuid: str, user_message: str, policy: dict, context_data: dict) -> AnalysisStepResponse:
    gen = call_agent_stream(session_uuid, user_message, policy, context_data)
    final_json_text = ""
    for event in gen:
        if event.get("type") == "done":
            final_json_text = event.get("full_content", "")
    
    try:
        return AnalysisStepResponse(**json.loads(final_json_text))
    except:
        return AnalysisStepResponse(
            summary="Error parsing response.",
            what="Parsing", why="Malformed JSON", code="", interpretation="", next_step="", options=[], uses_objects=[], should_autorun=False
        )
