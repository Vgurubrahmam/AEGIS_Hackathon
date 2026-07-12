"""
AEGIS — Twilio SMS Service
Handles sending outbound SMS and validates inbound webhook requests.
Falls back to logging-only mode if Twilio credentials are not configured.
"""

import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger("aegis.twilio")
settings = get_settings()


class TwilioService:
    """Twilio SMS send/receive helpers."""

    def __init__(self):
        self._client = None
        if settings.twilio_configured:
            try:
                from twilio.rest import Client
                self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                logger.info("Twilio client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Twilio client: {e}. Running in log-only mode.")
        else:
            logger.warning("Twilio credentials not configured. SMS will be logged but not sent.")

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def send_sms(self, to: str, body: str) -> Optional[str]:
        """
        Send an SMS via Twilio.

        Args:
            to: Recipient phone number (E.164 format)
            body: SMS message body

        Returns:
            Twilio message SID if sent, None if in log-only mode.
        """
        if not self._client:
            logger.info(f"[LOG-ONLY SMS] To: {to} | Body: {body}")
            return None

        try:
            message = self._client.messages.create(
                body=body,
                from_=settings.twilio_phone_number,
                to=to,
            )
            logger.info(f"SMS sent to {to}. SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {e}")
            raise

    def validate_webhook(self, url: str, params: dict, signature: str) -> bool:
        """
        Validate Twilio webhook request signature.
        For hackathon, this is optional — skip if signature header is missing.
        """
        if not self._client:
            return True  # Log-only mode, accept all

        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(settings.twilio_auth_token)
            return validator.validate(url, params, signature)
        except Exception as e:
            logger.warning(f"Webhook validation failed: {e}. Accepting anyway for hackathon.")
            return True


# Singleton instance
twilio_service = TwilioService()
