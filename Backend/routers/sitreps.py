"""
AEGIS — SitReps Router
REST endpoints for situation reports.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.engine import get_db
from db.models import SitRep
from schemas.sitrep import SitRepResponse

router = APIRouter(prefix="/api/sitreps", tags=["sitreps"])


@router.get("", response_model=list[SitRepResponse])
async def list_sitreps(
    db: AsyncSession = Depends(get_db),
):
    """List all sitreps, most recent first."""
    stmt = select(SitRep).order_by(SitRep.created_at.desc()).limit(20)
    result = await db.execute(stmt)
    sitreps = result.scalars().all()
    return [SitRepResponse.model_validate(s) for s in sitreps]


@router.get("/latest", response_model=SitRepResponse)
async def get_latest_sitrep(
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent sitrep."""
    stmt = select(SitRep).order_by(SitRep.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    sitrep = result.scalar_one_or_none()

    if not sitrep:
        raise HTTPException(status_code=404, detail="No sitreps generated yet")

    return SitRepResponse.model_validate(sitrep)
