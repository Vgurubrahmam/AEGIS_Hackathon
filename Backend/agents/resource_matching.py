"""
AEGIS — Resource Matching Agent
Finds the nearest available resource for the incident's need type.
NO LLM — pure SQL + haversine math. This is a deterministic "tool call," not an AI agent.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from agents.base import BaseAgent, AgentResult
from db.models import Resource
from utils.haversine import haversine


class ResourceMatchingAgent(BaseAgent):
    """Finds nearest available resource by need_type + distance."""

    name = "resource_matching"

    async def _run(
        self,
        latitude: float,
        longitude: float,
        need_type: str,
        db: AsyncSession,
        **kwargs,
    ) -> AgentResult:
        """
        Find the nearest available resource matching the need type.

        Args:
            latitude: Incident latitude.
            longitude: Incident longitude.
            need_type: Required resource type (medical/rescue/food/shelter).
            db: Database session.

        Returns:
            AgentResult with data: {resource_id, resource_name, distance_km, contact_phone}
        """
        if latitude is None or longitude is None:
            return AgentResult(
                success=False,
                error="No coordinates available for resource matching",
                reasoning="Cannot match resources without incident coordinates.",
            )

        # Query all available resources of the matching type
        stmt = select(Resource).where(
            Resource.type == need_type,
            Resource.status == "available",
        )
        result = await db.execute(stmt)
        candidates = result.scalars().all()

        if not candidates:
            # Fallback: try ANY available resource regardless of type
            stmt_any = select(Resource).where(Resource.status == "available")
            result_any = await db.execute(stmt_any)
            candidates = result_any.scalars().all()

            if not candidates:
                return AgentResult(
                    success=False,
                    error="No available resources found",
                    reasoning=f"No resources available for type '{need_type}' or any other type.",
                )

        # Calculate distances and sort
        scored = []
        for resource in candidates:
            dist = haversine(latitude, longitude, resource.latitude, resource.longitude)
            scored.append((resource, dist))

        scored.sort(key=lambda x: x[1])
        best_resource, best_distance = scored[0]

        # Reserve the resource (atomic update)
        best_resource.status = "reserved"
        await db.commit()

        return AgentResult(
            success=True,
            data={
                "resource_id": best_resource.id,
                "resource_name": best_resource.name,
                "resource_type": best_resource.type,
                "distance_km": round(best_distance, 2),
                "contact_phone": best_resource.contact_phone,
                "latitude": best_resource.latitude,
                "longitude": best_resource.longitude,
            },
            reasoning=f"Matched '{best_resource.name}' ({best_resource.type}) at {best_distance:.2f}km distance. Resource reserved.",
        )


# Singleton instance
resource_matching_agent = ResourceMatchingAgent()
