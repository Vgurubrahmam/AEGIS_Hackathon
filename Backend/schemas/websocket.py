"""
AEGIS — WebSocket Event Schemas
Defines the event envelope pushed to the dashboard after each pipeline step.
"""

from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class WSEvent(BaseModel):
    """
    WebSocket event envelope.
    Sent to all connected dashboard clients after every Orchestrator step.
    """
    event_type: str
    # Values:
    #   "incident_created"    — new incident entered the pipeline
    #   "agent_step"          — an agent completed a step (success or failure)
    #   "incident_updated"    — incident status/data changed
    #   "dispatch_created"    — a dispatch SMS was sent
    #   "sitrep_updated"      — new SitRep generated
    #   "dispatch_ack"        — volunteer acknowledged dispatch (via dashboard button)
    #   "incident_resolved"   — incident marked as resolved

    incident_id: Optional[str] = None
    agent_name: Optional[str] = None
    step_status: Optional[str] = None
    data: dict[str, Any] = {}
    timestamp: datetime

    def to_json(self) -> str:
        return self.model_dump_json()
