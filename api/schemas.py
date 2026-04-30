from pydantic import BaseModel, Field
from typing import List, Optional

class ProposedOption(BaseModel):
    id: str = Field(description="A short unique id for this option, e.g., 'opt1'")
    label: str = Field(description="A user-friendly label for the button.")
    prompt: str = Field(description="The message that will be sent to the agent if this option is clicked.")

class AnalysisStepResponse(BaseModel):
    response_type: str = Field(default="analysis_step", description="Fixed type for the frontend renderer.")
    summary: str = Field(description="A 1-2 sentence high-level summary of the outcome.")
    what: str = Field(description="A detailed description of what analysis or step was performed.")
    why: str = Field(description="The rationale behind this specific analysis choice.")
    code: str = Field(description="The EXACT R code that was executed during this step.")
    interpretation: str = Field(description="Professional interpretation of the results, including statistical context.")
    next_step: str = Field(description="A single clear recommendation for the user's next action.")
    options: List[ProposedOption] = Field(description="2-3 specific clickable follow-up paths.")
    uses_objects: List[str] = Field(description="List of names of the dataframe(s) or objects modified or analyzed in this step.")
    should_autorun: bool = Field(default=False, description="Whether the code should be automatically run if the app is in auto mode.")

class AgentChatResponse(BaseModel):
    reply: str = Field(description="Short chat message for the user.")
    code: Optional[str] = Field(None, description="R code to show/send.")
    language: str = Field(default="r", description="Code language.")
    should_execute: bool = Field(default=False, description="Whether the code should be executed.")
    executed: bool = Field(default=False, description="Whether the code was executed in the backend.")
    execution_output_hidden: bool = Field(default=False, description="Whether the execution output is captured but hidden from chat.")
    execution_summary: Optional[str] = Field(None, description="Optional short summary for model context.")
    session_id: str = Field(description="Session ID or signed token.")
    mode: str = Field(description="Current analysis mode: guided, balanced, or autonomous.")
    agent: str = Field(description="Agent ID.")
    intent: Optional[str] = Field(None, description="Detected intent name.")
    plots: Optional[List[str]] = Field(default=[], description="List of generated plot URLs.")
    environment: Optional[List[dict]] = Field(default=[], description="Summary of the R environment.")
    execution_error: Optional[str] = Field(None, description="Any error from R execution.")
