from pydantic import BaseModel, Field
from typing import List, Optional

class ProposedOption(BaseModel):
    id: str = Field(description="A short unique id for this option, e.g., 'opt1'")
    label: str = Field(description="A short human-readable label for the UI button")
    prompt: str = Field(description="The exact prompt to send to the assistant if this option is clicked")

class AnalysisStepResponse(BaseModel):
    response_type: str = Field(default="analysis_step", description="Must always be 'analysis_step'")
    summary: str = Field(description="A short natural language summary of the assistant's answer or the results of the executed code.")
    what: str = Field(description="What we’re doing: A one-sentence summary of the action.")
    why: str = Field(description="Why: A brief statistical or logical rationale.")
    code: str = Field(description="Raw executable R code. NO markdown fences. Leave empty if no code is provided.")
    interpretation: str = Field(description="Interpretation: How to read the results of the code, or findings from the analysis.")
    next_step: str = Field(description="Next step: A single sentence recommendation.")
    options: List[ProposedOption] = Field(description="2-3 options proposed for the user to select.")
    uses_objects: List[str] = Field(description="List of names of the dataframe(s) or objects modified or analyzed in this step.")
    should_autorun: bool = Field(default=False, description="Whether the code should be automatically run if the app is in auto mode.")
