"""
AEGIS — Verification Agent
Assigns a confidence score using RAG-based similarity to past incidents + heuristic flags.
Uses ChromaDB for similarity search, Groq llama-3.3-70b-versatile for scoring.
Honestly framed as "confidence scoring," not "misinformation detection."
"""

import json
from agents.base import BaseAgent, AgentResult
from services.llm_service import llm_service
from services.vector_store import vector_store
from config import get_settings

settings = get_settings()

VERIFICATION_SYSTEM_PROMPT = """You are AEGIS Verification Agent, a confidence scoring system for emergency reports. Your job is to assess how credible and actionable an incoming incident report is.

You receive:
1. The new incident report text
2. Similar past incidents from our database (if any)

You MUST respond with a JSON object containing:
- "confidence_score": a float between 0.0 and 1.0 (1.0 = highly credible and actionable)
- "flags": an array of string flags (empty if none apply)
- "reasoning": a brief explanation of your assessment

Scoring guidelines:
- 0.8-1.0: Clear emergency with specific details (location, number of people, specific need). Similar to verified past incidents.
- 0.5-0.7: Plausible emergency but vague or missing details. May need human review.
- 0.2-0.4: Suspicious — very vague, no location, implausible claims, or looks like spam/test message.
- 0.0-0.1: Almost certainly not a real emergency — gibberish, promotional content, test messages.

Flag types you can apply:
- "vague_location": No specific location mentioned
- "no_details": Very short or vague description
- "possible_duplicate": Very similar to a recent incident in the database
- "implausible_claim": Extraordinary claims without specifics
- "spam_pattern": Repeated text, promotional language, or non-emergency content

If similar past incidents are provided, use them to calibrate:
- If a past incident with similar text was resolved successfully → higher confidence
- If the new text is nearly identical to a very recent report → flag as possible_duplicate

Respond ONLY with the JSON object."""


class VerificationAgent(BaseAgent):
    """Confidence scoring via RAG retrieval + LLM assessment."""

    name = "verification"

    async def _run(self, raw_text: str, severity: str = "", need_type: str = "", **kwargs) -> AgentResult:
        """
        Score the credibility of an incident report.

        Args:
            raw_text: The raw SMS body text.
            severity: Triage-assigned severity.
            need_type: Triage-assigned need type.

        Returns:
            AgentResult with data: {confidence_score, flags, similar_incidents}
        """
        # Step 1: Query ChromaDB for similar past incidents
        similar_incidents = vector_store.query_similar(raw_text, n_results=3)

        # Step 2: Apply heuristic pre-flags
        heuristic_flags = self._apply_heuristics(raw_text, similar_incidents)

        # Step 3: Build context for LLM
        similar_context = ""
        if similar_incidents:
            similar_context = "\n\nSimilar past incidents in our database:\n"
            for i, inc in enumerate(similar_incidents, 1):
                similar_context += f"{i}. (distance: {inc['distance']:.3f}) \"{inc['text']}\"\n"
                if inc.get("metadata"):
                    similar_context += f"   Metadata: severity={inc['metadata'].get('severity', '?')}, type={inc['metadata'].get('need_type', '?')}\n"
        else:
            similar_context = "\n\nNo similar past incidents found in our database."

        user_prompt = f"""New incident report:
\"{raw_text}\"

Triage classification: severity={severity}, need_type={need_type}

Pre-screening flags from heuristics: {json.dumps(heuristic_flags) if heuristic_flags else "none"}
{similar_context}"""

        # Step 4: LLM confidence scoring
        result = await llm_service.chat_completion_json(
            system_prompt=VERIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=settings.llm_model_strong,
            temperature=0.1,
        )

        confidence_score = float(result.get("confidence_score", 0.5))
        flags = result.get("flags", [])
        reasoning = result.get("reasoning", "No reasoning provided")

        # Merge heuristic flags with LLM flags (dedup)
        all_flags = list(set(heuristic_flags + flags))

        # Clamp confidence score
        confidence_score = max(0.0, min(1.0, confidence_score))

        return AgentResult(
            success=True,
            data={
                "confidence_score": confidence_score,
                "flags": all_flags,
                "similar_incidents": [
                    {"text": s["text"][:100], "distance": s["distance"]}
                    for s in similar_incidents
                ],
            },
            reasoning=reasoning,
        )

    def _apply_heuristics(self, text: str, similar: list[dict]) -> list[str]:
        """Apply simple heuristic flags before LLM scoring."""
        flags = []

        # Very short message
        if len(text.strip()) < 15:
            flags.append("no_details")

        # No location-related words at all
        location_words = [
            "near", "at", "in", "road", "street", "bridge", "building",
            "area", "colony", "nagar", "galli", "chowk", "hospital",
            "station", "lake", "river", "market", "masjid", "temple",
        ]
        text_lower = text.lower()
        if not any(word in text_lower for word in location_words):
            flags.append("vague_location")

        # Check for near-duplicate (very low distance = very similar)
        for inc in similar:
            if inc["distance"] < 0.3:  # Very similar
                flags.append("possible_duplicate")
                break

        # Repeated identical text pattern (spam)
        words = text.lower().split()
        if len(words) > 3:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:  # Less than 30% unique words
                flags.append("spam_pattern")

        return flags


# Singleton instance
verification_agent = VerificationAgent()
