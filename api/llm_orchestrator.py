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

MAX_TOOL_ROUNDS = 4

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
    PHASE 4: Preserve or improve explicit context assembly.
    """
    analysis_mode = policy.get("label", "Guided").lower()
    
    base_instr = f"""You are aiR, an R analysis copilot and guide. Your primary job is to generate correct, concise R code and guide the next analysis step. 

CORE RULES:
1. NO HALLUCINATION: Do not fabricate R execution results. If the backend provides real execution output, use it for follow-up interpretation. Otherwise, assume no objects exist yet.
2. CONCISENESS: Be direct. Avoid conversational filler. In autonomous mode, the primary visible artifact should be the R code.
3. MODES (Current Mode: {analysis_mode.upper()}):
   - GUIDED: Propose the next step, give concise R code, and explain why. Do not auto-execute.
   - BALANCED: Give concise R code. Keep explanation short. Suggest execution for safe tasks.
   - AUTONOMOUS: Write the R code for direct execution. Do not ask unnecessary questions. Provide a very short status message only.
4. ANALYSIS SHAPING: 
   - Code-first for clear tasks (e.g., 'simulate df', 'summarize df', 'plot X by Y').
   - Question-first for vague goals (e.g., 'analyze my data', 'find patterns'). 
   - Help users formulate: Research question, Outcome variable, Exposure/predictor, Unit of analysis, Population/subset, Time frame, and Statistical hypotheses (Null and Alternative).
5. DECISION MAKING: When the user says 'you decide' or the task is simple/safe, make a reasonable default choice and proceed.
6. OUTPUT: You MUST return your final answer in the required structured JSON format.

GROUNDING: Use provided 'Grounded Context' for R package documentation, syntax, and statistical advice.
"""
    instructions = f"{base_instr}\n\n"
    
    session_ctx = f"--- SESSION STATE ---\n"
    session_ctx += f"Objective: {context_data.get('objective')}\n"
    
    if context_data.get("analysis_plan"):
        session_ctx += f"Analysis Plan:\n{context_data.get('analysis_plan')}\n"

    # Environment Summary (Compact)
    if context_data.get("env_summary"):
        env_str = "\n".join([f"- {obj.get('name')} ({obj.get('type')}): {obj.get('details')}" for obj in context_data.get('env_summary')[:15]])
        session_ctx += f"Environment:\n{env_str}\n"
        
        # Identify active dataframe
        dfs = [obj.get('name') for obj in context_data.get('env_summary') if obj.get('type') == 'data.frame']
        if len(dfs) == 1:
            session_ctx += f"Active Dataframe: {dfs[0]}\n"
    else:
        session_ctx += "Environment: Empty\n"
    
    # Recent History (Deduplicated/Pruned)
    if context_data.get("recent_history"):
        hist_str = "\n".join(list(dict.fromkeys(context_data.get('recent_history')[-5:])))
        session_ctx += f"Recent Commands:\n{hist_str}\n"
        
    if context_data.get("last_error"):
        session_ctx += f"Last Error: {context_data.get('last_error')}\n"

    instructions += session_ctx
    return instructions

def call_agent_stream(session_uuid: str, user_message: str, policy: dict, context_data: dict):
    """
    Generator that yields chunks of the response process with instrumentation.
    """
    start_time = time.time()
    system_instruction = build_system_instruction(policy, context_data)
    
    yield {"type": "status", "message": "Grounding..."}
    
    # Simple heuristic to speed up common tasks
    is_simple_task = len(user_message.split()) < 10 and any(k in user_message.lower() for k in ["fit", "plot", "sum", "mean", "df"])
    
    grounded_context = ""
    if not is_simple_task or context_data.get("grounding_context") == "":
        grounded_context = converse_r_docs(user_message, session_uuid, preamble="You are an R documentation helper.")
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"User Message: {user_message}\n\nGrounded Context: {grounded_context}")])
    ]
    
    # PHASE 5: Optimize speed (Low temperature for tool turns)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_r_code_tool],
        temperature=0.0, # Most deterministic for tool use
    )

    last_executed_code = ""
    round_count = 0
    total_r_time = 0
    
    while round_count < MAX_TOOL_ROUNDS:
        round_start = time.time()
        yield {"type": "status", "message": f"Reasoning (Round {round_count + 1})..."}
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        
        model_latency = int((time.time() - round_start) * 1000)
        print(f"Model Round {round_count + 1} Latency: {model_latency}ms")
        
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
                
                yield {"type": "status", "message": "Executing R..."}
                r_start = time.time()
                result = execute_r_code_internal(code, session_uuid)
                r_latency = int((time.time() - r_start) * 1000)
                total_r_time += r_latency
                print(f"R Tool Latency: {r_latency}ms")
                
                stdout = result.get("stdout", "")
                if len(stdout) > 1000:
                    stdout = stdout[:1000] + "\n...[truncated]"
                result["stdout"] = stdout
                
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
        response_schema=AnalysisStepResponse
    )
    
    # Role sequence fix
    if contents and contents[-1].role == "user":
        yield {"type": "status", "message": "Finalizing..."}
        mid_response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        if mid_response.candidates and mid_response.candidates[0].content:
            contents.append(mid_response.candidates[0].content)

    final_prompt = "Please provide your final summary in the required structured JSON format now."
    if last_executed_code:
        final_prompt += f" Ensure the 'code' field contains the R code that was just executed: {last_executed_code}"

    contents.append(types.Content(
        role="user", 
        parts=[types.Part.from_text(text=final_prompt)]
    ))
    
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
    print(f"Total /chat Latency: {total_latency}ms (R: {total_r_time}ms, Rounds: {round_count})")
    
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
