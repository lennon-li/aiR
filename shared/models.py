# shared/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ObjectSummary(BaseModel):
    name: str
    type: str
    details: str = ""

class ExecutionRequest(BaseModel):
    session_id: str
    code: str
    persist_bucket: str
    options: Dict[str, bool] = {"capture_plots": True, "return_objects": True}

class ExecutionResponse(BaseModel):
    status: str
    stdout: str
    stderr: Optional[str] = None
    plots: List[str] = []
    environment: List[ObjectSummary] = []
    snapshot_uri: str

class ChatRequest(BaseModel):
    message: str
    slider_value: int
    history: List[Dict[str, str]] = []
    context_window: int = 10

class ChatResponse(BaseModel):
    response: str
    proposed_code: Optional[str] = None
    citations: List[str] = []
