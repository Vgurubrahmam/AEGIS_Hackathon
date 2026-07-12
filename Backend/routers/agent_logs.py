"""
AEGIS — Agent Logs Router
REST endpoints for the Agent Activity Log (powers the trace panel on dashboard).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.engine import get_db
from db.models import AgentLog
from schemas.agent_log import AgentLogResponse

router = APIRouter(prefix="/api/agent-logs", tags=["agent-logs"])


@router.get("", response_model=list[AgentLogResponse])
async def list_agent_logs(
    incident_id: Optional[str] = Query(None, description="Filter by incident ID"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    List agent activity logs, optionally filtered by incident or agent.
    Used by the dashboard trace panel to show step-by-step agent decisions.
    """
    stmt = select(AgentLog).order_by(AgentLog.created_at.desc()).limit(limit)

    if incident_id:
        stmt = stmt.where(AgentLog.incident_id == incident_id)
    if agent_name:
        stmt = stmt.where(AgentLog.agent_name == agent_name)

    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [AgentLogResponse.model_validate(log) for log in logs]
