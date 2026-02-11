"""
ConversationUseCase - Business logic for conversation management.

Owns:
    - Message pruning (sliding window)
    - Role validation
    - History formatting
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..domain.entities import (
    ConversationContext,
    ConversationMessage,
    ConversationRole,
    MessageType,
)
from ..domain.exceptions import InvalidRoleError
from ..ports.conversation_port import ConversationManagerPort

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "user": ConversationRole.USER,
    "assistant": ConversationRole.ASSISTANT,
    "system": ConversationRole.SYSTEM,
}


class ConversationUseCase:
    """
    Application service for conversation operations.

    All business rules about conversations live here:
    - How many messages to keep (sliding window)
    - How to format history for downstream consumers
    - Role validation
    """

    def __init__(
        self,
        conversation_port: ConversationManagerPort,
        max_messages: int = 20,
        default_history_limit: int = 6,
    ):
        self._port = conversation_port
        self._max_messages = max_messages
        self._default_history_limit = default_history_limit

    # ── Public Use Case Methods ──

    async def get_or_create_context(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
    ) -> ConversationContext:
        """Retrieve existing context or create a new one."""
        context = await self._port.get_context(session_id)
        if context is None:
            context = await self._port.create_context(session_id, system_prompt)
            logger.info("Created new conversation context for session %s", session_id)
        return context

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> bool:
        """
        Add a message and apply sliding-window pruning.

        Raises InvalidRoleError if the role string is not recognized.
        """
        conv_role = _ROLE_MAP.get(role.lower())
        if conv_role is None:
            raise InvalidRoleError(role)

        # Ensure context exists
        context = await self.get_or_create_context(session_id)

        # Create domain message
        message = ConversationMessage(
            role=conv_role,
            content=content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT,
        )
        context.add_message(message)

        # Apply sliding window
        self._prune(context)

        # Update metadata
        if context.metadata is None:
            context.metadata = {}
        context.metadata["updated_at"] = datetime.now().isoformat()
        context.metadata["message_count"] = len(context.messages)

        # Persist
        await self._port.save_context(context)
        return True

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Return recent messages formatted as [{"role": ..., "content": ...}].

        System messages are always included on top.
        """
        limit = limit or self._default_history_limit

        context = await self._port.get_context(session_id)
        if not context or not context.messages:
            return []

        all_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in context.messages
        ]

        system_msgs = [m for m in all_msgs if m["role"] == "system"]
        other_msgs = [m for m in all_msgs if m["role"] != "system"]
        recent = other_msgs[-limit:] if len(other_msgs) > limit else other_msgs

        return system_msgs + recent

    async def delete_session(self, session_id: str) -> bool:
        """Delete a conversation and all its messages."""
        return await self._port.delete_context(session_id)

    # ── Private Helpers ──

    def _prune(self, context: ConversationContext) -> None:
        """Sliding-window pruning: keep system messages + last N others."""
        if len(context.messages) <= self._max_messages:
            return

        system = [m for m in context.messages if m.role == ConversationRole.SYSTEM]
        others = [m for m in context.messages if m.role != ConversationRole.SYSTEM]

        max_others = self._max_messages - len(system)
        if len(others) > max_others:
            others = others[-max_others:]

        context.messages = system + others
        logger.debug(
            "Pruned session %s to %d messages",
            context.session_id,
            len(context.messages),
        )
