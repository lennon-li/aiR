import os
import json
from google import genai
from google.genai import types

from schemas import AnalysisStepResponse
from tools.r_tool import execute_r_code_internal

# Initialize GenAI Client
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "air-mvp-lennon-li-2026")
LOCATION = "us-central1"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

MODEL_ID = "gemini-2.5-flash"
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
When asked to perform a task:
1. Think about what needs to be done.
2. If R code is needed to inspect data or generate a result, call `execute_r_code` with the necessary code.
3. Review the output from the tool.
4. If an error occurs, cautiously correct your code and retry.
5. If the request is simple, be concise. If it's deeper, be more explanatory.
6. Do NOT just return a code block without calling the tool if the user asks you to analyze something.
7. Return your final answer matching the required structured JSON format.

Hard rules:
- If generating data, always assign it to a named object (e.g. `df <- data.frame(...)`).
- Follow-up steps must reuse the correct object name from the environment.
- If ambiguity exists, ask one short clarification question.
- Do not emit undefined object names like `data` unless that object actually exists.
- Never send narrative text as executable code to the tool.
- Avoid documentation fallback chatter for simple R tasks.
"""
    instructions = f"{base_instr}\n\n{policy.get('system_prompt_extension', '')}\n\n"
    
    session_ctx = f"CURRENT SESSION CONTEXT:\n"
    session_ctx += f"Objective: {context_data.get('objective')}\n"
    
    if context_data.get("analysis_plan"):
        session_ctx += f"\nUPLOADED ANALYSIS PLAN:\n{context_data.get('analysis_plan')}\n"
        session_ctx += "NOTE: Since a plan was uploaded, prioritize its steps. If this is the start of the session, restate the plan, identify ambiguities, and ask for confirmation before executing.\n"

    if context_data.get("env_summary"):
        env_str = "\n".join([f"- {obj.get('name')} ({obj.get('type')}): {obj.get('details')}" for obj in context_data.get('env_summary')[:20]])
        session_ctx += f"\nEnvironment (Existing Objects):\n{env_str}\n"
    
    if context_data.get("recent_history"):
        hist_str = "\n".join(context_data.get('recent_history')[-15:]) # Keep recent
        session_ctx += f"\nRecent R Commands:\n{hist_str}\n"
        
    if context_data.get("last_error"):
        session_ctx += f"\nLast Execution Error: {context_data.get('last_error')}\n"

    if context_data.get("grounding_context"):
        session_ctx += f"\nCONTEXT FOR GROUNDING:\n{context_data.get('grounding_context')}\n"

    instructions += session_ctx
    return instructions

from vertex import search_r_docs, converse_r_docs

def call_agent_stream(session_uuid: str, user_message: str, policy: dict, context_data: dict):
    """
    Generator that yields chunks of the response process.
    Every step of reasoning now performs a grounded lookup via Discovery Engine
    to maximize credit consumption.
    """
    system_instruction = build_system_instruction(policy, context_data)
    
    # 1. Primary Grounding Call (Credit Consumer)
    # We ask the Discovery Engine for the grounded strategy/answer
    yield {"type": "status", "message": "Querying knowledge base..."}
    grounded_context = converse_r_docs(user_message, session_uuid, preamble=system_instruction)
    
    # Add the grounded information to our context
    context_data["grounding_context"] = grounded_context

    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=f"User Message: {user_message}\n\nGrounded Context from Search Engine: {grounded_context}")])
    ]
    
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_r_code_tool],
        temperature=0.2,
    )

    round_count = 0
    while round_count < MAX_TOOL_ROUNDS:
        yield {"type": "status", "message": f"Analyzing (Round {round_count + 1})..."}
        
        # We still use Flash for the tool-handling logic, 
        # but the 'Knowledge' is now coming from the Search Engine (Credits)
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
            contents.append(candidate.content)
            
        if not tool_calls:
            break
            
        for call in tool_calls:
            if call.name == "execute_r_code":
                code = call.args.get("code", "")
                yield {"type": "status", "message": "Executing R code..."}
                result = execute_r_code_internal(code, session_uuid)
                
                stdout = result.get("stdout", "")
                if len(stdout) > 2000:
                    stdout = stdout[:2000] + "\n...[truncated]"
                result["stdout"] = stdout
                
                contents.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(
                        name="execute_r_code",
                        response={"result": result}
                    )
                ]))
        
        round_count += 1
        
    final_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=AnalysisStepResponse
    )
    
    contents.append(types.Content(
        role="user", 
        parts=[types.Part.from_text(text="Please provide your final answer using the required structured format. Summarize what was done, why, the code used, and suggest next steps.")]
    ))
    
    yield {"type": "status", "message": "Finalizing summary..."}
    
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
    system_instruction = build_system_instruction(policy, context_data)
    
    # Configure the tool config and schema for final response
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[execute_r_code_tool],
        temperature=0.2, # Lower temp for tool calling reliability
    )

    # Initialize conversation history with the user message
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    ]
    
    round_count = 0
    while round_count < MAX_TOOL_ROUNDS:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=config
        )
        
        if not response.candidates:
            raise Exception("Model returned no candidates.")
            
        candidate = response.candidates[0]
        
        # Determine if there are tool calls
        tool_calls = []
        if candidate.content and candidate.content.parts:
            for part in candidate.content.parts:
                if part.function_call:
                    tool_calls.append(part.function_call)
                    
        # Append assistant's message (which includes the function calls) to the contents
        if candidate.content:
            contents.append(candidate.content)
            
        if not tool_calls:
            # No tool calls, this is the final response.
            # But we want the final response to be structured.
            # We will perform one final call enforcing the JSON schema.
            break
            
        # Execute tools
        tool_responses = []
        for call in tool_calls:
            if call.name == "execute_r_code":
                args = call.args
                code = args.get("code", "")
                print(f"Executing R Code:\n{code}")
                result = execute_r_code_internal(code, session_uuid)
                # Cap the output size to prevent blowing up context
                stdout = result.get("stdout", "")
                if len(stdout) > 2000:
                    stdout = stdout[:2000] + "\n...[truncated]"
                result["stdout"] = stdout
                
                tool_responses.append(types.Part.from_function_response(
                    name="execute_r_code",
                    response={"result": result}
                ))
            else:
                tool_responses.append(types.Part.from_function_response(
                    name=call.name,
                    response={"error": "Unknown function"}
                ))
                
        # Append tool responses as user role
        contents.append(types.Content(role="user", parts=tool_responses))
        round_count += 1
        
    # We reached the end of tool rounds or the model stopped using tools.
    # Now generate the final structured response.
    # We enforce the JSON schema.
    final_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=AnalysisStepResponse
    )
    
    # We just ask the model to summarize the outcome in the final structured format.
    # Add a prompt asking for the structured response.
    contents.append(types.Content(
        role="user", 
        parts=[types.Part.from_text(text="Please provide your final answer using the required structured format. Summarize what was done, why, the code used, and suggest next steps.")]
    ))
    
    final_response = client.models.generate_content(
        model=MODEL_ID,
        contents=contents,
        config=final_config
    )
    
    try:
        if final_response.text:
            data = json.loads(final_response.text)
            return AnalysisStepResponse(**data)
        else:
            raise Exception("Empty final response")
    except Exception as e:
        print(f"Error parsing final response: {e}\nResponse text: {final_response.text}")
        # Fallback to a default response if parsing fails
        return AnalysisStepResponse(
            summary="I encountered an error generating the final summary.",
            what="Generating response",
            why="The previous execution did not return a valid structured format.",
            code="",
            interpretation=str(e),
            next_step="Try again.",
            options=[],
            uses_objects=[],
            should_autorun=False
        )
