"""
AEGIS — Triage Agent
Classifies incoming SMS into severity (critical/high/medium) and need_type (medical/rescue/food/shelter).
Uses Groq llama-3.1-8b-instant for fast classification with few-shot examples.
"""

from agents.base import BaseAgent, AgentResult
from services.llm_service import llm_service
from config import get_settings

settings = get_settings()

TRIAGE_SYSTEM_PROMPT = """You are AEGIS Triage Agent, an emergency classification system. Your job is to classify incoming disaster/emergency SMS messages.

You MUST respond with a JSON object containing exactly these fields:
- "severity": one of "critical", "high", "medium"
- "need_type": one of "medical", "rescue", "food", "shelter"
- "reasoning": a brief one-sentence explanation of your classification

Classification rules:
- CRITICAL: Immediate life threat — drowning, building collapse with people trapped, cardiac arrest, heavy bleeding, fire with people inside
- HIGH: Urgent but not immediately life-threatening — injuries needing medical attention, displacement, rising water threatening safety, no food/water for 24+ hours
- MEDIUM: Needs help but stable — property damage, need for supplies, minor injuries, need temporary shelter but safe for now

Need type rules:
- MEDICAL: Injuries, illness, need ambulance, someone collapsed, bleeding, difficulty breathing
- RESCUE: Trapped, stranded, floodwater, building collapse, need evacuation
- FOOD: No food, no clean water, supplies needed for displaced people
- SHELTER: Homeless, house damaged/flooded, need temporary accommodation

Here are examples:

SMS: "Help we are stuck on the terrace water is coming in fast 4 people here please send help"
→ {"severity": "critical", "need_type": "rescue", "reasoning": "People trapped by rising floodwater, immediate life threat requiring rescue"}

SMS: "Old uncle fell down near market he is not moving please send doctor"
→ {"severity": "critical", "need_type": "medical", "reasoning": "Unconscious person, potential cardiac or trauma emergency requiring immediate medical response"}

SMS: "Our house is flooded we moved to neighbor but need food and water for 5 people"
→ {"severity": "high", "need_type": "food", "reasoning": "Displaced family without food/water but currently safe at neighbor's house"}

SMS: "Road blocked due to tree falling. Some people minor cuts. Need assistance"
→ {"severity": "medium", "need_type": "medical", "reasoning": "Minor injuries from fallen tree, not immediately life-threatening"}

SMS: "pls help family stuck flood charminar area children cold no shelter"
→ {"severity": "critical", "need_type": "shelter", "reasoning": "Family with children exposed to elements during flood, urgent shelter need"}

SMS: "building wall cracked after earthquake. we are outside but house is damaged cant stay"
→ {"severity": "high", "need_type": "shelter", "reasoning": "Structural damage making home unsafe, family needs temporary shelter but not in immediate danger"}

Respond ONLY with the JSON object. No other text."""


class TriageAgent(BaseAgent):
    """Classifies severity and need type from raw SMS text."""

    name = "triage"

    async def _run(self, raw_text: str, **kwargs) -> AgentResult:
        """
        Classify an incoming SMS message.

        Args:
            raw_text: The raw SMS body text.

        Returns:
            AgentResult with data: {severity, need_type, reasoning}
        """
        result = await llm_service.chat_completion_json(
            system_prompt=TRIAGE_SYSTEM_PROMPT,
            user_prompt=f"SMS: \"{raw_text}\"",
            model=settings.llm_model_fast,
            temperature=0.1,
        )

        severity = result.get("severity", "medium")
        need_type = result.get("need_type", "rescue")
        reasoning = result.get("reasoning", "No reasoning provided")

        # Validate values
        if severity not in ("critical", "high", "medium"):
            severity = "medium"
        if need_type not in ("medical", "rescue", "food", "shelter"):
            need_type = "rescue"

        return AgentResult(
            success=True,
            data={
                "severity": severity,
                "need_type": need_type,
            },
            reasoning=reasoning,
        )


# Singleton instance
triage_agent = TriageAgent()
