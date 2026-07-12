"""
AEGIS — Groq LLM Service
Wraps the Groq API (OpenAI-compatible) for all agent LLM calls.
Uses llama-3.1-8b-instant for fast tasks, llama-3.3-70b-versatile for quality tasks.
"""

import json
import logging
import asyncio
from typing import Any, Optional
from groq import AsyncGroq
from config import get_settings

logger = logging.getLogger("aegis.llm")
settings = get_settings()


class LLMService:
    """Groq LLM API wrapper with retry logic."""

    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key) if settings.groq_configured else None
        self.model_fast = settings.llm_model_fast
        self.model_strong = settings.llm_model_strong

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        """
        Make a chat completion call to Groq.

        Args:
            system_prompt: System message defining the agent's role
            user_prompt: The user's input text
            model: Override model selection (defaults to fast model)
            temperature: LLM temperature (low for consistency)
            max_tokens: Max response tokens
            json_mode: If True, request JSON response format

        Returns:
            The LLM's response text.

        Raises:
            RuntimeError: If Groq API is not configured or all retries fail.
        """
        if not self.client:
            raise RuntimeError("Groq API key not configured. Set GROQ_API_KEY in .env")

        model = model or self.model_fast

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        # Retry logic: 3 attempts with exponential backoff
        last_error = None
        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                logger.debug(f"LLM response ({model}): {content[:200]}...")
                return content
            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt
                logger.warning(f"LLM call attempt {attempt + 1}/3 failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        raise RuntimeError(f"LLM call failed after 3 attempts: {last_error}")

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> dict:
        """
        Make a chat completion call and parse the response as JSON.
        Uses json_mode for reliable structured output.
        """
        response = await self.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            json_mode=True,
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            raise RuntimeError(f"Failed to parse LLM response as JSON: {response[:200]}")


# Singleton instance
llm_service = LLMService()
