import os
import json
import re
from google import genai
from google.genai import types

from schemas import AnalysisStepResponse
from tools.r_tool import execute_r_code_internal
from vertex import converse_r_docs

# Initialize GenAI Client
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "us-central1"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

MODEL_ID = "gemini-2.5-flash" # Verified stable version for April 2026
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
    base_instr = """You are aiR, a professional Analysis Coach.
Your goal is to guide the user through a structured data analysis.
You have access to the `execute_r_code` tool. Use it to perform analysis, verify assumptions, generate data, and create plots BEFORE providing your final analysis step.

Grounding Note: You will be provided with 'Grounded Context' from a search engine. Use this for R package documentation, syntax, and statistical advice.

Hard rules:
- NEVER claim to have generated data or performed analysis unless you have successfully called `execute_r_code`.
- ALWAYS include the exact R code you executed in the `code` field of your final JSON response.
- COMBINE related operations into a single `execute_r_code` call (e.g., fit model, generate results, and plot in one go) to save time.
- If generating data, always assign it to a named object (e.g. `df <- data.frame(...)`).
- Follow-up steps must reuse the correct object name from the environment.
- If an error occurs, cautiously correct your code and retry.
- Do NOT return a code block without calling the tool if the user asks you to execute/analyze something.
- Return your final answer in the required structured JSON format.
"""
    instructions = f"{base_instr}\n\n{policy.get('system_prompt_extension', '')}\n\n"
    
    session_ctx = f"CURRENT SESSION CONTEXT:\n"
    session_ctx += f"Objective: {context_data.get('objective')}\n"
    
    if context_data.get("analysis_plan"):
        session_ctx += f"\nUPLOADED ANALYSIS PLAN:\n{context_data.get('analysis_plan')}\n"

    if context_data.get("env_summary"):
        env_str = "\n".join([f"- {obj.get('name')} ({obj.get('type')}): {obj.get('details')}" for obj in context_data.get('env_summary')[:15]])
        session_ctx += f"\nEnvironment (Existing Objects):\n{env_str}\n"
    else:
        session_ctx += "\nEnvironment is currently empty.\n"
    
    if context_data.get("recent_history"):
        hist_str = "\n".join(context_data.get('recent_history')[-5:])
        session_ctx += f"\nRecent R Commands:\n{hist_str}\n"
        
    if context_data.get("last_error"):
        session_ctx += f"\nLast Execution Error: {context_data.get('last_error')}\n"

    instructions += session_ctx
    return instructions

def call_agent_stream(session_uuid: str, user_message: str, policy: dict, context_data: dict):
    """
    Generator that yields chunks of the response process.
    """
    system_instruction = build_system_instruction(policy, context_data)
    
    yield {"type": "status", "message": "Grounding query..."}
    
    is_simple_task = len(user_message.split()) < 10 and any(k in user_message.lower() for k in ["fit", "plot", "sum", "mean", "df"])
    
    grounded_context = ""
    if not is_simple_task or context_data.get("grounding_context") == "":
        grounded_context = converse_r_docs(user_message, session_uuid, preamble="You are an R documentation helper.")
    
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"User Message: {user_message}\n\nGrounded Context: {grounded_context}")])
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_r_code_tool],
        temperature=0.1,
    )

    last_executed_code = ""
    round_count = 0
    while round_count < MAX_TOOL_ROUNDS:
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
                last_executed_code = code # Track for final output
                yield {"type": "status", "message": "Executing R..."}
                result = execute_r_code_internal(code, session_uuid)
                
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
    
    # Ensure alternating roles: if the last message was 'user' (from a tool response), 
    # we need to get a model response before we can send another 'user' prompt.
    if contents and contents[-1].role == "user":
        yield {"type": "status", "message": "Finalizing analysis..."}
        mid_response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        if mid_response.candidates and mid_response.candidates[0].content:
            contents.append(mid_response.candidates[0].content)

    # Explicitly ask for the code to be included in the structured format
    final_prompt = "Please provide your final summary in the required structured JSON format now."
    if last_executed_code:
        final_prompt += f" Ensure the 'code' field contains the R code that was just executed: {last_executed_code}"

    contents.append(types.Content(
        role="user", 
        parts=[types.Part.from_text(text=final_prompt)]
    ))
    
    yield {"type": "status", "message": "Formatting result..."}
    
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
            
    yield {"type": "done", "full_content": full_text}

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
