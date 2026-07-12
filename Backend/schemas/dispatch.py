"""
AEGIS — Pydantic Schemas for Dispatches
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DispatchResponse(BaseModel):
    """Dispatch response for API endpoints."""
    id: str
    incident_id: str
    resource_id: str
    status: str
    sms_sid: Optional[str] = None
    dispatch_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
