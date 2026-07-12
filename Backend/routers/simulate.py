"""
AEGIS — SMS Simulation Router
Manual injection endpoint for demo/testing without Twilio.
This is the primary demo entry point.
"""

import asyncio
import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field

from db.engine import AsyncSessionLocal
from orchestrator.pipeline import process_incident

logger = logging.getLogger("aegis.router.simulate")
router = APIRouter(prefix="/api/simulate", tags=["simulate"])


class SimulateSMSRequest(BaseModel):
    """Request body for simulated SMS."""
    body: str = Field(..., description="SMS text body", min_length=1)
    from_phone: str = Field(default="+911234567890", description="Simulated sender phone number")


class SimulateSMSResponse(BaseModel):
    """Response confirming simulation started."""
    status: str = "processing"
    message: str
    incident_id: str = ""


@router.post("/sms", response_model=SimulateSMSResponse)
async def simulate_sms(request: SimulateSMSRequest):
    """
    Simulate an inbound SMS for demo/testing.
    Identical pipeline as real Twilio webhook, but no Twilio credentials needed.
    Pipeline runs as background task and returns immediately.
    """
    logger.info(f"Simulated SMS from {request.from_phone}: {request.body[:100]}...")

    # Run pipeline as background task
    asyncio.create_task(_run_simulated_pipeline(request.body.strip(), request.from_phone))

    return SimulateSMSResponse(
        status="processing",
        message=f"Simulated SMS received. Pipeline started for message: '{request.body[:50]}...'",
    )


async def _run_simulated_pipeline(raw_text: str, sender_phone: str):
    """Background task: run the orchestrator pipeline with its own DB session."""
    async with AsyncSessionLocal() as db:
        try:
            incident_id = await process_incident(raw_text, sender_phone, db)
            logger.info(f"Simulated pipeline completed for incident {incident_id[:8]}...")
        except Exception as e:
            logger.error(f"Simulated pipeline failed: {e}", exc_info=True)
