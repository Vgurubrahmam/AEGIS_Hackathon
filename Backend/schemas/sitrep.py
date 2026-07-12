"""
AEGIS — Pydantic Schemas for Situation Reports
"""

from pydantic import BaseModel
from datetime import datetime


class SitRepResponse(BaseModel):
    """SitRep response for API endpoints."""
    id: str
    summary_text: str
    incident_count: int
    critical_count: int
    dispatched_count: int
    needs_review_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
