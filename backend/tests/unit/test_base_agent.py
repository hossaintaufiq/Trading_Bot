"""
Unit tests — Base Agent contract.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

import pytest
from pydantic import BaseModel

from app.agents.base_agent import BaseAgent, AgentResult


class SampleInput(BaseModel):
    value: float


class SampleOutput(BaseModel):
    doubled: float
    message: str


class GoodAgent(BaseAgent[SampleInput, SampleOutput]):
    agent_id = "good_agent"
    agent_name = "Good Agent"

    async def execute(self, input_data: SampleInput) -> SampleOutput:
        return SampleOutput(doubled=input_data.value * 2, message="ok")


class FailingAgent(BaseAgent[SampleInput, SampleOutput]):
    agent_id = "failing_agent"
    agent_name = "Failing Agent"

    async def execute(self, input_data: SampleInput) -> SampleOutput:
        raise ValueError("deliberate error")


class TestBaseAgent:
    def test_successful_execution(self):
        agent = GoodAgent()
        result: AgentResult = asyncio.run(
            agent.run(SampleInput(value=5.0))
        )
        assert result.success is True
        assert result.output.doubled == 10.0
        assert result.error_message is None
        assert result.duration_ms is not None
        assert result.duration_ms >= 0

    def test_failed_execution_captured(self):
        agent = FailingAgent()
        result: AgentResult = asyncio.run(
            agent.run(SampleInput(value=5.0))
        )
        assert result.success is False
        assert "deliberate error" in result.error_message
        assert result.error_type == "ValueError"
        assert result.output is None

    def test_execution_id_is_unique(self):
        agent = GoodAgent()
        r1 = asyncio.run(agent.run(SampleInput(value=1.0)))
        r2 = asyncio.run(agent.run(SampleInput(value=2.0)))
        assert r1.execution_id != r2.execution_id

    def test_agent_id_is_set(self):
        agent = GoodAgent()
        result = asyncio.run(
            agent.run(SampleInput(value=1.0))
        )
        assert result.agent_id == "good_agent"

