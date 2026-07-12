"""
AEGIS — Dispatch Agent
Sends dispatch SMS to assigned volunteer/resource via Twilio.
Creates dispatch record in database.
"""

from agents.base import BaseAgent, AgentResult
from services.twilio_service import twilio_service


class DispatchAgent(BaseAgent):
    """Sends outbound dispatch SMS to assigned resource contact."""

    name = "dispatch"

    async def _run(
        self,
        incident_id: str,
        raw_text: str,
        severity: str,
        need_type: str,
        landmark_name: str | None,
        latitude: float | None,
        longitude: float | None,
        resource_name: str,
        resource_id: str,
        contact_phone: str,
        **kwargs,
    ) -> AgentResult:
        """
        Send a dispatch SMS to the assigned resource.

        Returns:
            AgentResult with data: {sms_sid, dispatch_message, contact_phone}
        """
        # Compose dispatch SMS (shortened to fit 1 segment/GSM-7 for Twilio Trial)
        location_str = landmark_name[:15] if landmark_name else "Unknown"
        coords_str = f"({latitude:.2f},{longitude:.2f})" if latitude and longitude else ""
        
        # Max limit for trial message body is ~120 characters to fit 160-char GSM limit with trial prefix
        dispatch_message = (
            f"AEGIS DISPATCH\n"
            f"Need: {need_type.upper()}\n"
            f"Loc: {location_str} {coords_str}\n"
            f"Msg: {raw_text[:40]}{'...' if len(raw_text) > 40 else ''}\n"
            f"Reply OK"
        )

        # Send via Twilio (or log-only mode)
        try:
            sms_sid = twilio_service.send_sms(to=contact_phone, body=dispatch_message)
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"SMS send failed: {e}",
                reasoning=f"Failed to send dispatch SMS to {contact_phone}: {e}",
            )

        return AgentResult(
            success=True,
            data={
                "sms_sid": sms_sid,
                "dispatch_message": dispatch_message,
                "contact_phone": contact_phone,
                "resource_name": resource_name,
                "resource_id": resource_id,
            },
            reasoning=f"Dispatch SMS sent to {resource_name} at {contact_phone}. SID: {sms_sid or 'log-only'}",
        )


# Singleton instance
dispatch_agent = DispatchAgent()
