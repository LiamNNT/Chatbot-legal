"""
PrepareAgentRequestUseCase - Build AgentRequest from raw inputs.

Owns:
    - Selecting how many history messages to include
    - Assembling the AgentRequest value object
"""

import logging
from typing import Optional

from ..domain.entities import ConversationContext, MessageType
from ..domain.value_objects import AgentRequest

logger = logging.getLogger(__name__)


class PrepareAgentRequestUseCase:
    """
    Builds an AgentRequest from raw inputs.

    Business rules:
    - How many history messages to include (max_history)
    - Filter out non-TEXT messages
    - Default model selection
    """

    def __init__(
        self,
        max_history: int = 10,
        default_model: Optional[str] = None,
    ):
        self._max_history = max_history
        self._default_model = default_model

    def execute(
        self,
        prompt: str,
        context: Optional[ConversationContext] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
    ) -> AgentRequest:
        """
        Create an AgentRequest ready to send to an AgentPort.

        Trims history to the last ``max_history`` TEXT messages.
        """
        # Prepare context with trimmed history
        prepared_context: Optional[ConversationContext] = None

        if context is not None:
            # Keep only recent TEXT messages
            trimmed = [
                m
                for m in context.messages
                if m.message_type == MessageType.TEXT
            ][-self._max_history :]

            prepared_context = ConversationContext(
                session_id=context.session_id,
                messages=trimmed,
                system_prompt=system_prompt or context.system_prompt,
                metadata=context.metadata,
            )
        elif system_prompt:
            # No context but a system prompt was provided
            prepared_context = ConversationContext(
                session_id="__standalone__",
                messages=[],
                system_prompt=system_prompt,
            )

        return AgentRequest(
            prompt=prompt,
            context=prepared_context,
            model=self._default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )
