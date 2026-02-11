from abc import ABC, abstractmethod
from typing import List, Optional

from ..domain.rag_models import SearchResult


class RerankerPort(ABC):
    @abstractmethod
    async def rerank(self, query: str, results: List[SearchResult], top_k: Optional[int] = None,) -> List[SearchResult]:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...
