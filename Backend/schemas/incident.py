"""
AEGIS — Pydantic Schemas for Incidents
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class IncidentCreate(BaseModel):
    """Manual incident creation (via simulate endpoint)."""
    body: str = Field(..., description="SMS text body")
    from_phone: str = Field(default="+0000000000", description="Sender phone number")


class IncidentResponse(BaseModel):
    """Full incident response for API endpoints."""
    id: str
    raw_text: str
    sender_phone: str
    status: str
    severity: Optional[str] = None
    need_type: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_flags: Optional[str] = None
    landmark_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    matched_resource_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentBrief(BaseModel):
    """Compact incident for list views / SitRep context."""
    id: str
    raw_text: str
    status: str
    severity: Optional[str] = None
    need_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
