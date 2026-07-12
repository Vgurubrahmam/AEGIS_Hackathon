"""
AEGIS — Dispatches Router
REST endpoints for dispatch records.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.engine import get_db
from db.models import Dispatch
from schemas.dispatch import DispatchResponse

router = APIRouter(prefix="/api/dispatches", tags=["dispatches"])


@router.get("", response_model=list[DispatchResponse])
async def list_dispatches(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all dispatch records, most recent first."""
    stmt = select(Dispatch).order_by(Dispatch.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    dispatches = result.scalars().all()
    return [DispatchResponse.model_validate(d) for d in dispatches]
