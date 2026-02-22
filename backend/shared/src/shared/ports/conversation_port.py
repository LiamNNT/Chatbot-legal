"""
ConversationManagerPort — interface for conversation state management.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..domain.entities import ConversationContext


class ConversationManagerPort(ABC):
    """Manages conversation sessions and message history."""

    @abstractmethod
    async def create_context(
        self, session_id: str, system_prompt: Optional[str] = None
    ) -> ConversationContext:
        ...

    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        ...

    @abstractmethod
    async def save_context(self, context: ConversationContext) -> None:
        ...

    @abstractmethod
    async def delete_context(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def add_message(self, session_id: str, role: str, content: str) -> bool:
        ...

    @abstractmethod
    async def get_history(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        ...
