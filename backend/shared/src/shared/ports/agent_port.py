"""
AgentPort — interface for LLM communication.

Any LLM backend (OpenRouter, OpenAI, Anthropic, local) must implement this.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from ..domain.value_objects import AgentRequest, AgentResponse


class AgentPort(ABC):
    """
    Port for LLM agent interaction.

    Responsibilities:
        - Send a prompt and get a complete response  (generate_response)
        - Send a prompt and stream tokens back       (stream_response)
        - Clean up resources                         (close)
    """

    @abstractmethod
    async def generate_response(self, request: AgentRequest) -> AgentResponse:
        """Send a request to the LLM and return the full response."""
        ...

    @abstractmethod
    async def stream_response(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        """Send a request to the LLM and yield tokens as they arrive."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any held resources (HTTP sessions, connections)."""
        ...
