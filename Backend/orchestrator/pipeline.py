"""
AEGIS — Orchestrator Pipeline
Central controller that sequences all agents, logs every step, applies decision logic,
and broadcasts live updates via WebSocket.

This is a simple sequential function chain — no framework (LangGraph, CrewAI),
no event bus (Kafka/Redis). Just async functions called in order.
"""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Incident, AgentLog, Dispatch, SitRep, generate_uuid, utc_now
from agents.triage import triage_agent
from agents.verification import verification_agent
from agents.geolocation import geolocation_agent
from agents.resource_matching import resource_matching_agent
from agents.dispatch import dispatch_agent
from agents.sitrep import sitrep_agent
from agents.base import AgentResult
from services.websocket_manager import ws_manager
from services.vector_store import vector_store
from schemas.websocket import WSEvent
from config import get_settings

logger = logging.getLogger("aegis.orchestrator")
settings = get_settings()


async def _log_step(
    db: AsyncSession,
    incident_id: str,
    agent_name: str,
    result: AgentResult,
    input_summary: str = "",
) -> None:
    """Write an agent step to the agent_logs table."""
    log_entry = AgentLog(
        id=generate_uuid(),
        incident_id=incident_id,
        agent_name=agent_name,
        step_status="success" if result.success else "failed",
        input_summary=input_summary[:500],
        output_summary=result.reasoning[:500],
        duration_ms=result.duration_ms,
    )
    db.add(log_entry)
    await db.commit()


async def _broadcast_step(
    incident_id: str,
    agent_name: str,
    result: AgentResult,
    extra_data: dict = None,
) -> None:
    """Broadcast an agent step event via WebSocket."""
    event = WSEvent(
        event_type="agent_step",
        incident_id=incident_id,
        agent_name=agent_name,
        step_status="success" if result.success else "failed",
        data={
            "reasoning": result.reasoning[:300],
            "duration_ms": result.duration_ms,
            **(result.data or {}),
            **(extra_data or {}),
        },
        timestamp=datetime.now(timezone.utc),
    )
    await ws_manager.broadcast(event)


async def _broadcast_incident_update(incident: Incident) -> None:
    """Broadcast incident state change via WebSocket."""
    event = WSEvent(
        event_type="incident_updated",
        incident_id=incident.id,
        data={
            "status": incident.status,
            "severity": incident.severity,
            "need_type": incident.need_type,
            "confidence_score": incident.confidence_score,
            "landmark_name": incident.landmark_name,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "matched_resource_id": incident.matched_resource_id,
            "raw_text": incident.raw_text[:200],
        },
        timestamp=datetime.now(timezone.utc),
    )
    await ws_manager.broadcast(event)


async def process_incident(
    raw_text: str,
    sender_phone: str,
    db: AsyncSession,
) -> str:
    """
    Main orchestrator pipeline — processes a single incident through all agents.

    Pipeline:
    1. Create incident (status: new)
    2. Triage Agent → severity + need_type (status: triaged)
    3. Verification Agent → confidence score (status: verified / needs_review)
    4. Geolocation Agent → coordinates (status: located)
    5. Resource Matching Agent → matched resource (status: matched)
    6. Dispatch Agent → SMS sent (status: dispatched)
    7. SitRep Agent → summary regenerated

    Args:
        raw_text: SMS body text
        sender_phone: Sender's phone number
        db: Async database session

    Returns:
        Incident ID
    """
    # ── Step 1: Create Incident ──────────────────────────────────────────
    incident_id = generate_uuid()
    incident = Incident(
        id=incident_id,
        raw_text=raw_text,
        sender_phone=sender_phone,
        status="new",
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    logger.info(f"[Pipeline] Created incident {incident_id[:8]}... from {sender_phone}")

    # Broadcast: new incident created
    event = WSEvent(
        event_type="incident_created",
        incident_id=incident_id,
        data={"raw_text": raw_text[:200], "sender_phone": sender_phone, "status": "new"},
        timestamp=datetime.now(timezone.utc),
    )
    await ws_manager.broadcast(event)

    # ── Step 2: Triage Agent ─────────────────────────────────────────────
    logger.info(f"[Pipeline] Step 2: Triage Agent for {incident_id[:8]}...")
    triage_result = await triage_agent.execute(raw_text=raw_text)

    await _log_step(db, incident_id, "triage", triage_result, input_summary=raw_text[:200])
    await _broadcast_step(incident_id, "triage", triage_result)

    if not triage_result.success:
        incident.status = "needs_review"
        await db.commit()
        await _broadcast_incident_update(incident)
        logger.warning(f"[Pipeline] Triage failed for {incident_id[:8]}. Marking needs_review.")
        return incident_id

    # Update incident with triage results
    incident.severity = triage_result.data["severity"]
    incident.need_type = triage_result.data["need_type"]
    incident.status = "triaged"
    await db.commit()
    await _broadcast_incident_update(incident)

    # ── Step 3: Verification Agent ───────────────────────────────────────
    logger.info(f"[Pipeline] Step 3: Verification Agent for {incident_id[:8]}...")
    verification_result = await verification_agent.execute(
        raw_text=raw_text,
        severity=incident.severity,
        need_type=incident.need_type,
    )

    await _log_step(db, incident_id, "verification", verification_result, input_summary=raw_text[:200])
    await _broadcast_step(incident_id, "verification", verification_result)

    if not verification_result.success:
        incident.status = "needs_review"
        await db.commit()
        await _broadcast_incident_update(incident)
        logger.warning(f"[Pipeline] Verification failed for {incident_id[:8]}. Marking needs_review.")
        return incident_id

    # Update incident with verification results
    confidence = verification_result.data.get("confidence_score", 0.5)
    flags = verification_result.data.get("flags", [])
    incident.confidence_score = confidence
    incident.confidence_flags = json.dumps(flags)

    # Decision gate: confidence threshold
    if confidence < settings.confidence_threshold:
        incident.status = "needs_review"
        await db.commit()
        await _broadcast_incident_update(incident)
        logger.info(
            f"[Pipeline] Confidence {confidence:.2f} < threshold {settings.confidence_threshold} "
            f"for {incident_id[:8]}. Flags: {flags}. Marking needs_review."
        )
        return incident_id

    incident.status = "verified"
    await db.commit()
    await _broadcast_incident_update(incident)

    # ── Step 4: Geolocation Agent ────────────────────────────────────────
    logger.info(f"[Pipeline] Step 4: Geolocation Agent for {incident_id[:8]}...")
    geo_result = await geolocation_agent.execute(raw_text=raw_text)

    await _log_step(db, incident_id, "geolocation", geo_result, input_summary=raw_text[:200])
    await _broadcast_step(incident_id, "geolocation", geo_result)

    # Geolocation is non-critical — use fallback coordinates if it fails
    lat = geo_result.data.get("latitude") if geo_result.success else None
    lng = geo_result.data.get("longitude") if geo_result.success else None
    landmark = geo_result.data.get("landmark_name") if geo_result.success else None

    if lat is None or lng is None:
        # Fallback: use a default central location for the demo city
        lat = 17.3850  # Hyderabad center
        lng = 78.4867
        landmark = landmark or "unknown location"
        logger.warning(f"[Pipeline] Geolocation incomplete for {incident_id[:8]}. Using default coords.")

    incident.landmark_name = landmark
    incident.latitude = lat
    incident.longitude = lng
    incident.status = "located"
    await db.commit()
    await _broadcast_incident_update(incident)

    # ── Step 5: Resource Matching Agent ──────────────────────────────────
    logger.info(f"[Pipeline] Step 5: Resource Matching Agent for {incident_id[:8]}...")
    matching_result = await resource_matching_agent.execute(
        latitude=lat,
        longitude=lng,
        need_type=incident.need_type,
        db=db,
    )

    await _log_step(db, incident_id, "resource_matching", matching_result, input_summary=f"lat={lat}, lng={lng}, type={incident.need_type}")
    await _broadcast_step(incident_id, "resource_matching", matching_result)

    if not matching_result.success:
        incident.status = "needs_review"
        await db.commit()
        await _broadcast_incident_update(incident)
        logger.warning(f"[Pipeline] Resource matching failed for {incident_id[:8]}. No resources available.")
        return incident_id

    incident.matched_resource_id = matching_result.data["resource_id"]
    incident.status = "matched"
    await db.commit()
    await _broadcast_incident_update(incident)

    # ── Step 6: Dispatch Agent ───────────────────────────────────────────
    logger.info(f"[Pipeline] Step 6: Dispatch Agent for {incident_id[:8]}...")
    dispatch_result = await dispatch_agent.execute(
        incident_id=incident_id,
        raw_text=raw_text,
        severity=incident.severity,
        need_type=incident.need_type,
        landmark_name=incident.landmark_name,
        latitude=incident.latitude,
        longitude=incident.longitude,
        resource_name=matching_result.data["resource_name"],
        resource_id=matching_result.data["resource_id"],
        contact_phone=matching_result.data["contact_phone"],
    )

    await _log_step(db, incident_id, "dispatch", dispatch_result, input_summary=f"resource={matching_result.data['resource_name']}")
    await _broadcast_step(incident_id, "dispatch", dispatch_result)

    if dispatch_result.success:
        # Create dispatch record
        dispatch_record = Dispatch(
            id=generate_uuid(),
            incident_id=incident_id,
            resource_id=matching_result.data["resource_id"],
            status="sent",
            sms_sid=dispatch_result.data.get("sms_sid"),
            dispatch_message=dispatch_result.data.get("dispatch_message"),
        )
        db.add(dispatch_record)
        incident.status = "dispatched"
        await db.commit()

        # Broadcast dispatch created
        dispatch_event = WSEvent(
            event_type="dispatch_created",
            incident_id=incident_id,
            data={
                "dispatch_id": dispatch_record.id,
                "resource_name": matching_result.data["resource_name"],
                "contact_phone": matching_result.data["contact_phone"],
                "status": "sent",
            },
            timestamp=datetime.now(timezone.utc),
        )
        await ws_manager.broadcast(dispatch_event)
    else:
        # Dispatch failed but pipeline continues (non-critical for incident tracking)
        incident.status = "matched"  # Stay as matched, not dispatched
        await db.commit()
        logger.warning(f"[Pipeline] Dispatch SMS failed for {incident_id[:8]}, but incident is tracked.")

    await _broadcast_incident_update(incident)

    # ── Step 7: SitRep Agent ─────────────────────────────────────────────
    logger.info(f"[Pipeline] Step 7: SitRep Agent for {incident_id[:8]}...")
    sitrep_result = await sitrep_agent.execute(db=db)

    await _log_step(db, incident_id, "sitrep", sitrep_result, input_summary="Regenerate SitRep after dispatch")
    await _broadcast_step(incident_id, "sitrep", sitrep_result)

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

        # Broadcast SitRep update
        sitrep_event = WSEvent(
            event_type="sitrep_updated",
            incident_id=incident_id,
            data={
                "sitrep_id": sitrep_record.id,
                "summary_text": sitrep_result.data["summary_text"][:500],
                "incident_count": sitrep_result.data["incident_count"],
                "critical_count": sitrep_result.data["critical_count"],
            },
            timestamp=datetime.now(timezone.utc),
        )
        await ws_manager.broadcast(sitrep_event)

    logger.info(f"[Pipeline] ✅ Completed full pipeline for incident {incident_id[:8]}...")
    return incident_id
