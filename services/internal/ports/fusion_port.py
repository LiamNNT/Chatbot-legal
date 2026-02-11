from abc import ABC, abstractmethod
from typing import List

from ..domain.rag_models import SearchResult


class FusionPort(ABC):
    @abstractmethod
    async def fuse(self, vector_results: List[SearchResult], keyword_results: List[SearchResult], vector_weight: float = 0.5, keyword_weight: float = 0.5,) -> List[SearchResult]:
        ...
