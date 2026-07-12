"""
AEGIS — ORM Models
All 5 database tables: incidents, resources, dispatches, sitreps, agent_logs.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, ForeignKey, Enum
)
from sqlalchemy.orm import relationship
from db.engine import Base


def generate_uuid() -> str:
    """Generate a UUID4 string for primary keys."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


# ── Incidents ────────────────────────────────────────────────────────────────

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    raw_text = Column(Text, nullable=False)
    sender_phone = Column(String(20), nullable=False, default="+0000000000")
    status = Column(
        String(20),
        nullable=False,
        default="new",
        # Values: new, triaged, verified, needs_review, located, matched, dispatched, resolved
    )
    severity = Column(String(10), nullable=True)        # critical, high, medium
    need_type = Column(String(10), nullable=True)        # medical, rescue, food, shelter
    confidence_score = Column(Float, nullable=True)
    confidence_flags = Column(Text, nullable=True)       # JSON array of flag strings
    landmark_name = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    matched_resource_id = Column(String(36), ForeignKey("resources.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    matched_resource = relationship("Resource", back_populates="incidents")
    dispatches = relationship("Dispatch", back_populates="incident")
    agent_logs = relationship("AgentLog", back_populates="incident", order_by="AgentLog.created_at")


# ── Resources ────────────────────────────────────────────────────────────────

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    type = Column(String(10), nullable=False)            # medical, rescue, food, shelter
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(15), nullable=False, default="available")  # available, reserved, deployed
    contact_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    incidents = relationship("Incident", back_populates="matched_resource")
    dispatches = relationship("Dispatch", back_populates="resource")


# ── Dispatches ───────────────────────────────────────────────────────────────

class Dispatch(Base):
    __tablename__ = "dispatches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    resource_id = Column(String(36), ForeignKey("resources.id"), nullable=False)
    status = Column(String(15), nullable=False, default="sent")  # sent, acknowledged, en_route, completed
    sms_sid = Column(String(50), nullable=True)          # Twilio message SID
    dispatch_message = Column(Text, nullable=True)       # The SMS body sent
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="dispatches")
    resource = relationship("Resource", back_populates="dispatches")


# ── SitReps ──────────────────────────────────────────────────────────────────

class SitRep(Base):
    __tablename__ = "sitreps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    summary_text = Column(Text, nullable=False)
    incident_count = Column(Integer, nullable=False, default=0)
    critical_count = Column(Integer, nullable=False, default=0)
    dispatched_count = Column(Integer, nullable=False, default=0)
    needs_review_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False)


# ── Agent Activity Logs ──────────────────────────────────────────────────────

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id"), nullable=False)
    agent_name = Column(String(30), nullable=False)
    # Values: triage, verification, geolocation, resource_matching, dispatch, sitrep
    step_status = Column(String(10), nullable=False)     # success, failed, skipped
    input_summary = Column(Text, nullable=True)          # Truncated input for display
    output_summary = Column(Text, nullable=True)         # Truncated output / decision reasoning
    duration_ms = Column(Integer, nullable=True)         # Execution time in ms
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="agent_logs")
