"""
AEGIS — Dashboard Actions Router
Interactive endpoints for demo: volunteer acknowledgment, incident resolution.
These replace two-way SMS parsing (simulated via dashboard buttons).
"""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.engine import get_db
from db.models import Dispatch, Incident, generate_uuid
from services.websocket_manager import ws_manager
from services.vector_store import vector_store
from schemas.websocket import WSEvent
from orchestrator.pipeline import process_incident
from agents.sitrep import sitrep_agent
from db.models import SitRep

logger = logging.getLogger("aegis.router.actions")
router = APIRouter(prefix="/api/actions", tags=["dashboard-actions"])


@router.post("/ack-dispatch/{dispatch_id}")
async def acknowledge_dispatch(
    dispatch_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate volunteer acknowledging a dispatch.
    Called by the dashboard "Accept" button instead of parsing real SMS replies.
    """
    stmt = select(Dispatch).where(Dispatch.id == dispatch_id)
    result = await db.execute(stmt)
    dispatch = result.scalar_one_or_none()

    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    if dispatch.status != "sent":
        raise HTTPException(status_code=400, detail=f"Dispatch already in status: {dispatch.status}")

    dispatch.status = "acknowledged"
    await db.commit()

    # Broadcast update
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

    logger.info(f"Dispatch {dispatch_id[:8]} acknowledged via dashboard.")
    return {"status": "acknowledged", "dispatch_id": dispatch_id}


@router.post("/resolve-incident/{incident_id}")
async def resolve_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an incident as resolved.
    Also stores the incident in ChromaDB for future RAG retrieval.
    """
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status == "resolved":
        raise HTTPException(status_code=400, detail="Incident already resolved")

    # Mark resolved
    incident.status = "resolved"
    await db.commit()

    # Store in ChromaDB for RAG (resolved incidents become training data)
    try:
        vector_store.add_incident(
            incident_id=incident.id,
            text=incident.raw_text,
            metadata={
                "severity": incident.severity or "unknown",
                "need_type": incident.need_type or "unknown",
                "landmark": incident.landmark_name or "unknown",
            },
        )
    except Exception as e:
        logger.warning(f"Failed to store resolved incident in ChromaDB: {e}")

    # Broadcast update
    event = WSEvent(
        event_type="incident_resolved",
        incident_id=incident.id,
        data={"status": "resolved"},
        timestamp=datetime.now(timezone.utc),
    )
    await ws_manager.broadcast(event)

    # Regenerate SitRep
    try:
        sitrep_result = await sitrep_agent.execute(db=db)
        if sitrep_result.success:
            sitrep_record = SitRep(
                id=generate_uuid(),
                summary_text=sitrep_result.data["summary_text"],
                incident_count=sitrep_result.data["incident_count"],
                critical_count=sitrep_result.data["critical_count"],
                dispatched_count=sitrep_result.data["dispatched_count"],
                needs_review_count=sitrep_result.data["needs_review_count"],
            )
            db.add(sitrep_record)
            await db.commit()
    except Exception as e:
        logger.warning(f"SitRep regeneration after resolve failed: {e}")

    logger.info(f"Incident {incident_id[:8]} resolved and stored in ChromaDB.")
    return {"status": "resolved", "incident_id": incident_id}
