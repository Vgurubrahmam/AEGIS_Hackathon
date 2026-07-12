"""
AEGIS — Pydantic Schemas for Agent Activity Logs
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AgentLogResponse(BaseModel):
    """Agent log response for API endpoints and dashboard trace panel."""
    id: str
    incident_id: str
    agent_name: str
    step_status: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
