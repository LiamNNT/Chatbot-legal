# core/ports/services.py
#
# Description:
# Port interfaces for external services and utilities.
# These abstractions decouple the core domain from specific service implementations.

from abc import ABC, abstractmethod
from typing import List, Tuple
from ..domain.models import SearchResult, DocumentChunk


class EmbeddingService(ABC):
    """Port for text embedding operations."""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts."""
        pass


class RerankingService(ABC):
    """Port for reranking/cross-encoder operations."""
    
    @abstractmethod
    async def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank search results based on query-result relevance."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the reranking service is available."""
        pass


class TextChunker(ABC):
    """Port for text chunking operations."""
    
    @abstractmethod
    async def chunk_text(self, text: str, metadata: dict) -> List[DocumentChunk]:
        """Split text into chunks suitable for indexing."""
        pass


class FusionService(ABC):
    """Port for search result fusion operations."""
    
    @abstractmethod
    async def fuse_results(
        self, 
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        rrf_constant: int = 60
    ) -> List[SearchResult]:
        """Fuse results from different search methods."""
        pass


class HighlightingService(ABC):
    """Port for text highlighting operations."""
    
    @abstractmethod
    async def highlight_matches(
        self, 
        query: str, 
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Add highlighting information to search results."""
        pass
