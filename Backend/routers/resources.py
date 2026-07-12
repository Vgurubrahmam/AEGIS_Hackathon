"""
AEGIS — Resources Router
REST endpoints for resource data.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.engine import get_db
from db.models import Resource
from schemas.resource import ResourceResponse

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=list[ResourceResponse])
async def list_resources(
    status: Optional[str] = Query(None, description="Filter by status (available/reserved/deployed)"),
    type: Optional[str] = Query(None, description="Filter by type (medical/rescue/food/shelter)"),
    db: AsyncSession = Depends(get_db),
):
    """List all resources, optionally filtered by status or type."""
    stmt = select(Resource).order_by(Resource.name)

    if status:
        stmt = stmt.where(Resource.status == status)
    if type:
        stmt = stmt.where(Resource.type == type)

    result = await db.execute(stmt)
    resources = result.scalars().all()
    return [ResourceResponse.model_validate(r) for r in resources]
