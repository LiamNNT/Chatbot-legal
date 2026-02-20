"""
RAGServicePort — interface for RAG retrieval.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..domain.entities import RAGContext


class RAGServicePort(ABC):
    """Port for retrieving context from the RAG system."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        search_mode: str = "hybrid",
        use_rerank: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RAGContext:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...
