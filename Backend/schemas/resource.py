"""
AEGIS — Pydantic Schemas for Resources
"""

from pydantic import BaseModel
from datetime import datetime


class ResourceResponse(BaseModel):
    """Resource response for API endpoints."""
    id: str
    name: str
    type: str
    latitude: float
    longitude: float
    status: str
    contact_phone: str
    created_at: datetime

    model_config = {"from_attributes": True}
