"""
Agent Base Class — all agents must implement this interface.

Rules:
- Agents MUST NOT call each other directly.
- Agents MUST return structured output conforming to their output_contract.
- All execution must be logged via the base class methods.
- Agent errors must be caught, logged, and surfaced — never silently swallowed.
"""
import abc
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentResult(BaseModel, Generic[OutputT]):
    """Wrapper returned by every agent execution."""
    agent_id: str
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool
    output: Optional[Any] = None         # OutputT when success=True
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: Optional[float] = None


class BaseAgent(abc.ABC, Generic[InputT, OutputT]):
    """
    Abstract base for all NEPTUNE specialist agents.

    Subclasses must implement:
      - agent_id: str class variable
      - agent_name: str class variable
      - execute(input_data: InputT) -> OutputT
    """

    agent_id: str = "base"
    agent_name: str = "Base Agent"

    async def run(self, input_data: InputT) -> AgentResult:
        """
        Execute the agent with full error handling and timing.
        This method should NOT be overridden — override execute() instead.
        """
        execution_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        try:
            output = await self.execute(input_data)
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            return AgentResult(
                agent_id=self.agent_id,
                execution_id=execution_id,
                started_at=started_at,
                completed_at=completed_at,
                success=True,
                output=output,
                duration_ms=duration_ms,
            )

        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000
            error_output = await self.on_error(exc, input_data)

            return AgentResult(
                agent_id=self.agent_id,
                execution_id=execution_id,
                started_at=started_at,
                completed_at=completed_at,
                success=False,
                output=error_output,
                error_message=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )

    @abc.abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        Core agent logic. Override this in every agent.
        Must return a Pydantic model conforming to the agent's output contract.
        """
        ...

    async def on_error(
        self, error: Exception, input_data: InputT
    ) -> Optional[Dict[str, Any]]:
        """
        Optional error recovery hook. Override to provide partial results.
        Default: returns None (no partial output on error).
        """
        return None

    def __repr__(self) -> str:
        return f"<Agent id={self.agent_id} name={self.agent_name}>"

