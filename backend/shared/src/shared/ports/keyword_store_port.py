"""KeywordStorePort — interface for keyword/BM25 search operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..domain.rag_models import DocumentChunk, SearchQuery, SearchResult


class KeywordStorePort(ABC):
    @abstractmethod
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        ...

    @abstractmethod
    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        ...

    @abstractmethod
    async def delete_by_doc_id(self, doc_id: str) -> bool:
        ...

    @abstractmethod
    async def get_facets(self, query: SearchQuery) -> Dict[str, Any]:
        ...
