"""
AEGIS — Twilio Webhook Router
Receives inbound SMS from Twilio, kicks off the Orchestrator pipeline.
"""

import asyncio
import logging
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from db.engine import get_db, AsyncSessionLocal
from orchestrator.pipeline import process_incident

logger = logging.getLogger("aegis.router.twilio")
router = APIRouter(prefix="/api/twilio", tags=["twilio"])


@router.post("/webhook")
async def twilio_inbound_sms(request: Request):
    """
    Receive inbound SMS from Twilio webhook.
    Twilio sends form-encoded data with 'Body' and 'From' fields.
    If the body is a confirmation (e.g. 'ok', 'yes'), acknowledges the active dispatch.
    Otherwise, treats it as a new emergency report and runs the multi-agent pipeline.
    """
    form_data = await request.form()
    body = (form_data.get("Body", "")).strip()
    sender = form_data.get("From", "+0000000000")

    if not body:
        logger.warning("Received empty SMS body from Twilio webhook.")
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )

    logger.info(f"Twilio webhook received SMS from {sender}: {body[:100]}...")

    # Check if the message is a volunteer acknowledgment (e.g. "ok", "yes", "ack")
    clean_body = body.lower().strip(" .!*")
    if clean_body in ("ok", "yes", "ack", "confirm"):
        async with AsyncSessionLocal() as db:
            from datetime import datetime, timezone
            from sqlalchemy import select
            from db.models import Dispatch, Resource
            from services.websocket_manager import ws_manager
            from schemas.websocket import WSEvent

            # Find the latest pending dispatch sent to this phone number
            stmt = (
                select(Dispatch)
                .join(Resource)
                .where(Resource.contact_phone == sender)
                .where(Dispatch.status == "sent")
                .order_by(Dispatch.created_at.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            dispatch = res.scalar_one_or_none()

            if dispatch:
                # Update statuses
                dispatch.status = "acknowledged"
                
                # Fetch and update resource status to deployed
                stmt_res = select(Resource).where(Resource.id == dispatch.resource_id)
                res_resource = await db.execute(stmt_res)
                resource = res_resource.scalar_one_or_none()
                if resource:
                    resource.status = "deployed"

                await db.commit()

                # Broadcast live update to the dashboard
                event = WSEvent(
                    event_type="dispatch_ack",
                    incident_id=dispatch.incident_id,
                    data={
                        "dispatch_id": dispatch.id,
                        "status": "acknowledged",
                        "resource_id": dispatch.resource_id,
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                await ws_manager.broadcast(event)

                logger.info(f"Dispatch {dispatch.id[:8]} acknowledged via SMS from volunteer ({sender})")

                # Reply to the volunteer
                reply_twiml = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Response>'
                    '<Message>AEGIS: Acknowledgment received. Dispatch confirmed. Proceed to location.</Message>'
                    '</Response>'
                )
                return Response(content=reply_twiml, media_type="application/xml")

    # Regular flow: Run emergency pipeline as background task
    asyncio.create_task(_run_pipeline(body, sender))

    # Return empty TwiML response immediately to prevent timeout
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )


async def _run_pipeline(raw_text: str, sender_phone: str):
    """Background task: run the orchestrator pipeline with its own DB session."""
    async with AsyncSessionLocal() as db:
        try:
            incident_id = await process_incident(raw_text, sender_phone, db)
            logger.info(f"Pipeline completed for incident {incident_id[:8]}...")
        except Exception as e:
            logger.error(f"Pipeline failed for SMS from {sender_phone}: {e}", exc_info=True)
