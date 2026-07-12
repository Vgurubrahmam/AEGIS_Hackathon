"""
AEGIS — Geocoding Service
Hybrid: fixed landmark table (primary, demo-safe) + Google Maps API (fallback).
"""

import logging
from typing import Optional
import httpx
from config import get_settings
from utils.landmarks import lookup_landmark

logger = logging.getLogger("aegis.geocoding")
settings = get_settings()


class GeocodingService:
    """Geocoding with landmark gazetteer primary + Google Maps fallback."""

    async def geocode(self, landmark_name: str) -> Optional[tuple[str, float, float]]:
        """
        Resolve a landmark name to coordinates.

        Strategy:
        1. Look up in fixed landmark table (deterministic, demo-safe)
        2. If not found, try Google Maps Geocoding API (if configured)
        3. If still not found, return None

        Args:
            landmark_name: Extracted landmark/location name

        Returns:
            Tuple of (resolved_name, latitude, longitude) or None
        """
        if not landmark_name:
            return None

        # Step 1: Fixed landmark table lookup
        result = lookup_landmark(landmark_name)
        if result:
            name, lat, lng = result
            logger.info(f"Landmark '{landmark_name}' resolved via gazetteer: {name} ({lat}, {lng})")
            return (name, lat, lng)

        # Step 2: Google Maps Geocoding API (if configured)
        if settings.google_maps_configured:
            try:
                return await self._google_maps_geocode(landmark_name)
            except Exception as e:
                logger.warning(f"Google Maps geocoding failed for '{landmark_name}': {e}")

        logger.warning(f"Could not geocode landmark: '{landmark_name}'")
        return None

    async def _google_maps_geocode(self, query: str) -> Optional[tuple[str, float, float]]:
        """
        Call Google Maps Geocoding API.
        Adds demo city context for better results.
        """
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": f"{query}, {settings.demo_city}, India",
            "key": settings.google_maps_api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]
            formatted = result.get("formatted_address", query)
            lat = location["lat"]
            lng = location["lng"]
            logger.info(f"Google Maps geocoded '{query}' → {formatted} ({lat}, {lng})")
            return (formatted, lat, lng)

        logger.warning(f"Google Maps returned no results for '{query}'")
        return None


# Singleton instance
geocoding_service = GeocodingService()
