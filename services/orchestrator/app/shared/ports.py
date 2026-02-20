"""
Orchestrator port definitions.

AgentPort is re-exported from the shared package.
ConversationManagerPort and RAGServicePort are orchestrator-specific
variants (different signatures from the shared versions) and stay here
until a future unification pass.
"""

from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Any

from shared.ports.agent_port import AgentPort  # noqa: F401 — canonical definition
from shared.domain.entities import ConversationContext


class ConversationManagerPort(ABC):
    """Orchestrator-specific conversation manager port."""

    @abstractmethod
    async def create_context(self, session_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        pass

    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        pass

    @abstractmethod
    async def update_context(self, context: ConversationContext) -> None:
        pass

    @abstractmethod
    async def delete_context(self, session_id: str) -> bool:
        pass


class RAGServicePort(ABC):
    """
    Orchestrator-specific RAG service port.

    NOTE: This differs from ``shared.ports.rag_port.RAGServicePort`` in that
    it returns a raw ``dict`` (the HTTP-level response) rather than a typed
    ``RAGContext``.  A future refactor should unify the two.
    """

    @abstractmethod
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Any] = None,
        search_mode: str = "hybrid",
        use_rerank: bool = True,
        need_citation: bool = True,
        include_char_spans: bool = True,
    ) -> dict:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass