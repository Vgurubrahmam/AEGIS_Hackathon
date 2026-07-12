"""
AEGIS Backend — Centralized Configuration
Loads from .env file, provides typed access to all settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Groq API ──────────────────────────────────────────────
    groq_api_key: str = ""

    # LLM model selection (Groq-hosted)
    llm_model_fast: str = "llama-3.1-8b-instant"       # Triage, Geolocation extraction
    llm_model_strong: str = "llama-3.3-70b-versatile"   # Verification, SitRep

    # ── Twilio ────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ── Google Maps ───────────────────────────────────────────
    google_maps_api_key: str = ""

    # ── Database ──────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./aegis.db"

    # ── Pipeline ──────────────────────────────────────────────
    confidence_threshold: float = 0.6

    # ── Demo ──────────────────────────────────────────────────
    demo_city: str = "Hyderabad"

    # ── Computed Properties ───────────────────────────────────
    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_phone_number)

    @property
    def google_maps_configured(self) -> bool:
        return bool(self.google_maps_api_key)

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
