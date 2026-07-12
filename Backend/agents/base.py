"""
AEGIS — Base Agent
Common execution wrapper providing timing, error handling, and uniform output format.
All agents inherit from this.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger("aegis.agent")


@dataclass
class AgentResult:
    """Uniform result from any agent execution."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


class BaseAgent(ABC):
    """
    Base class for all AEGIS agents.
    Provides:
    - Timed execution wrapper
    - Error catching and uniform error result
    - Logging
    """

    name: str = "base_agent"

    async def execute(self, **kwargs) -> AgentResult:
        """
        Execute the agent with timing and error handling.
        Subclasses implement _run() with their specific logic.
        """
        start = time.perf_counter()
        try:
            result = await self._run(**kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result.duration_ms = elapsed_ms
            logger.info(f"[{self.name}] completed in {elapsed_ms}ms — {'SUCCESS' if result.success else 'FAILED'}")
            return result
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.error(f"[{self.name}] failed in {elapsed_ms}ms: {e}")
            return AgentResult(
                success=False,
                error=str(e),
                reasoning=f"Agent {self.name} encountered an error: {e}",
                duration_ms=elapsed_ms,
            )

    @abstractmethod
    async def _run(self, **kwargs) -> AgentResult:
        """Subclass-specific agent logic. Must return AgentResult."""
        raise NotImplementedError
