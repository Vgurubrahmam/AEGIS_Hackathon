"""
AEGIS — Geolocation Agent
Extracts landmark/location from SMS text via LLM, then geocodes via hybrid service.
Uses Groq llama-3.1-8b-instant for fast extraction + gazetteer/Google Maps for coordinates.
"""

from agents.base import BaseAgent, AgentResult
from services.llm_service import llm_service
from services.geocoding_service import geocoding_service
from config import get_settings

settings = get_settings()

GEOLOCATION_SYSTEM_PROMPT = """You are AEGIS Geolocation Agent. Your job is to extract the most specific location or landmark name from an emergency SMS message.

You MUST respond with a JSON object containing:
- "landmark_name": the most specific location/landmark mentioned (or null if none found)
- "reasoning": brief explanation of what location info you found

Extraction rules:
- Extract the most specific location reference: building name, landmark, area name, bridge, hospital, station, etc.
- If multiple locations are mentioned, pick the one where the emergency is happening.
- Clean up the text: fix obvious typos, normalize to standard spelling.
- If the message has no location info at all, return {"landmark_name": null, "reasoning": "No location information found in message"}.
- Do NOT invent or guess locations. Only extract what is explicitly mentioned.
- Return just the landmark/area name, not a full address.

Examples:
SMS: "Help we are stuck near charminar water rising"
→ {"landmark_name": "charminar", "reasoning": "Explicit mention of Charminar landmark"}

SMS: "old man fell down near secbad station entrance"
→ {"landmark_name": "secunderabad station", "reasoning": "Reference to Secunderabad Railway Station (corrected abbreviation)"}

SMS: "flooding in our area families need rescue boats"
→ {"landmark_name": null, "reasoning": "No specific location mentioned, only generic 'our area'"}

SMS: "building collapsed near musi river bridge chaderghat"
→ {"landmark_name": "chaderghat bridge", "reasoning": "Specific bridge name mentioned near Musi River"}

SMS: "need ambulance near NIMS hospital someone injured badly"
→ {"landmark_name": "nims hospital", "reasoning": "Specific hospital name mentioned"}

Respond ONLY with the JSON object."""


class GeolocationAgent(BaseAgent):
    """Extracts landmark from SMS text and resolves to coordinates."""

    name = "geolocation"

    async def _run(self, raw_text: str, **kwargs) -> AgentResult:
        """
        Extract location and geocode from SMS text.

        Args:
            raw_text: The raw SMS body text.

        Returns:
            AgentResult with data: {landmark_name, latitude, longitude, source}
        """
        # Step 1: LLM extracts landmark name
        result = await llm_service.chat_completion_json(
            system_prompt=GEOLOCATION_SYSTEM_PROMPT,
            user_prompt=f'SMS: "{raw_text}"',
            model=settings.llm_model_fast,
            temperature=0.1,
        )

        landmark_name = result.get("landmark_name")
        reasoning = result.get("reasoning", "No reasoning provided")

        if not landmark_name:
            return AgentResult(
                success=True,  # Not a failure — just no location found
                data={
                    "landmark_name": None,
                    "latitude": None,
                    "longitude": None,
                    "source": "not_found",
                },
                reasoning=f"No location extracted from SMS. {reasoning}",
            )

        # Step 2: Geocode via hybrid service (gazetteer + Google Maps fallback)
        geocode_result = await geocoding_service.geocode(landmark_name)

        if geocode_result:
            resolved_name, lat, lng = geocode_result
            source = "gazetteer" if resolved_name in landmark_name.lower() or landmark_name.lower() in resolved_name else "google_maps"
            return AgentResult(
                success=True,
                data={
                    "landmark_name": resolved_name,
                    "latitude": lat,
                    "longitude": lng,
                    "source": source,
                },
                reasoning=f"Extracted '{landmark_name}' → resolved to '{resolved_name}' ({lat}, {lng}) via {source}. {reasoning}",
            )
        else:
            return AgentResult(
                success=True,  # Partial success — extracted name but couldn't geocode
                data={
                    "landmark_name": landmark_name,
                    "latitude": None,
                    "longitude": None,
                    "source": "not_found",
                },
                reasoning=f"Extracted '{landmark_name}' but could not geocode to coordinates. {reasoning}",
            )


# Singleton instance
geolocation_agent = GeolocationAgent()
