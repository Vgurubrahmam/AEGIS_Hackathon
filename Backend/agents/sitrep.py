"""
AEGIS — SitRep (Situation Report) Agent
Generates a live markdown summary of all active incidents.
Uses Groq llama-3.3-70b-versatile for high-quality summarization.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from agents.base import BaseAgent, AgentResult
from db.models import Incident, Dispatch
from services.llm_service import llm_service
from config import get_settings

settings = get_settings()

SITREP_SYSTEM_PROMPT = """You are AEGIS SitRep Agent, generating a concise Situation Report for Emergency Operations Center staff.

You will receive data about current active incidents. Generate a clear, professional situation report in markdown format.

Structure your report as:
1. **Summary** — one paragraph overview (total incidents, critical count, dispatched count, pending review)
2. **Critical Incidents** — bullet list of critical-severity incidents with location and status
3. **Active Dispatches** — bullet list of dispatched resources
4. **Pending Review** — any incidents flagged for human review
5. **Recommendations** — 1-2 actionable recommendations based on the current situation

Keep it concise — this is for rapid situational awareness, not a full report.
Do NOT use headers larger than h3 (###).
If there are no active incidents, say so clearly."""


class SitRepAgent(BaseAgent):
    """Generates a situation report summarizing all active incidents."""

    name = "sitrep"

    async def _run(self, db: AsyncSession, **kwargs) -> AgentResult:
        """
        Generate a SitRep from current database state.

        Args:
            db: Database session.

        Returns:
            AgentResult with data: {summary_text, incident_count, critical_count, dispatched_count, needs_review_count}
        """
        # Query active incidents (not resolved)
        stmt = select(Incident).where(Incident.status != "resolved").order_by(Incident.created_at.desc())
        result = await db.execute(stmt)
        incidents = result.scalars().all()

        # Count categories
        total = len(incidents)
        critical = sum(1 for i in incidents if i.severity == "critical")
        high = sum(1 for i in incidents if i.severity == "high")
        dispatched = sum(1 for i in incidents if i.status == "dispatched")
        needs_review = sum(1 for i in incidents if i.status == "needs_review")

        if total == 0:
            summary = "### Situation Report\n\nNo active incidents at this time. All systems nominal."
            return AgentResult(
                success=True,
                data={
                    "summary_text": summary,
                    "incident_count": 0,
                    "critical_count": 0,
                    "dispatched_count": 0,
                    "needs_review_count": 0,
                },
                reasoning="No active incidents to report.",
            )

        # Build incident data for LLM
        incident_data = []
        for inc in incidents:
            incident_data.append(
                f"- ID: {inc.id[:8]}... | Status: {inc.status} | Severity: {inc.severity or '?'} | "
                f"Type: {inc.need_type or '?'} | Location: {inc.landmark_name or 'unknown'} | "
                f"Report: \"{inc.raw_text[:100]}{'...' if len(inc.raw_text) > 100 else ''}\""
            )

        user_prompt = f"""Current active incidents ({total} total, {critical} critical, {dispatched} dispatched, {needs_review} pending review):

{chr(10).join(incident_data)}

Generate a situation report."""

        summary = await llm_service.chat_completion(
            system_prompt=SITREP_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=settings.llm_model_strong,
            temperature=0.3,
            max_tokens=1500,
        )

        return AgentResult(
            success=True,
            data={
                "summary_text": summary,
                "incident_count": total,
                "critical_count": critical,
                "dispatched_count": dispatched,
                "needs_review_count": needs_review,
            },
            reasoning=f"Generated SitRep covering {total} active incidents ({critical} critical).",
        )


# Singleton instance
sitrep_agent = SitRepAgent()
