# core/container.py
#
# Description:
# Dependency injection container for the RAG system.
# This container manages the creation and lifecycle of all dependencies,
# ensuring proper separation of concerns and easy testing.

import logging
from typing import Optional

from core.domain.search_service import SearchService
from core.ports.repositories import VectorSearchRepository, KeywordSearchRepository
from core.ports.services import RerankingService, FusionService

from adapters.llamaindex_vector_adapter import LlamaIndexVectorAdapter
from adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter
from adapters.service_adapters import CrossEncoderRerankingAdapter, HybridFusionAdapter

from app.config.settings import settings

logger = logging.getLogger(__name__)


class DIContainer:
    """
    Dependency Injection Container for the RAG system.
    
    This container follows the Ports & Adapters pattern by:
    1. Creating concrete implementations (adapters) for the ports
    2. Injecting dependencies into the core domain services
    3. Managing the lifecycle of all components
    """
    
    def __init__(self):
        self._vector_repository: Optional[VectorSearchRepository] = None
        self._keyword_repository: Optional[KeywordSearchRepository] = None
        self._reranking_service: Optional[RerankingService] = None
        self._fusion_service: Optional[FusionService] = None
        self._search_service: Optional[SearchService] = None
    
    def get_vector_repository(self) -> VectorSearchRepository:
        """Get or create the vector search repository."""
        if self._vector_repository is None:
            self._vector_repository = LlamaIndexVectorAdapter(
                storage_dir=settings.storage_dir,
                embedding_model=settings.emb_model,
                vector_backend=settings.vector_backend
            )
            logger.info("Created LlamaIndex vector repository")
        
        return self._vector_repository
    
    def get_keyword_repository(self) -> Optional[KeywordSearchRepository]:
        """Get or create the keyword search repository."""
        if not settings.use_hybrid_search:
            return None
        
        if self._keyword_repository is None:
            try:
                from store.opensearch.client import get_opensearch_client
                opensearch_client = get_opensearch_client()
                self._keyword_repository = OpenSearchKeywordAdapter(opensearch_client)
                logger.info("Created OpenSearch keyword repository")
            except Exception as e:
                logger.warning(f"Could not create OpenSearch keyword repository: {e}")
                return None
        
        return self._keyword_repository
    
    def get_reranking_service(self) -> Optional[RerankingService]:
        """Get or create the reranking service."""
        if not settings.rerank_model:
            return None
        
        if self._reranking_service is None:
            try:
                self._reranking_service = CrossEncoderRerankingAdapter(settings.rerank_model)
                logger.info(f"Created CrossEncoder reranking service: {settings.rerank_model}")
            except Exception as e:
                logger.warning(f"Could not create reranking service: {e}")
                return None
        
        return self._reranking_service
    
    def get_fusion_service(self) -> Optional[FusionService]:
        """Get or create the fusion service."""
        if not settings.use_hybrid_search:
            return None
        
        if self._fusion_service is None:
            self._fusion_service = HybridFusionAdapter(
                rrf_constant=settings.rrf_rank_constant
            )
            logger.info("Created hybrid fusion service")
        
        return self._fusion_service
    
    def get_search_service(self) -> SearchService:
        """Get or create the main search service."""
        if self._search_service is None:
            vector_repo = self.get_vector_repository()
            keyword_repo = self.get_keyword_repository()
            rerank_service = self.get_reranking_service()
            fusion_service = self.get_fusion_service()
            
            self._search_service = SearchService(
                vector_repository=vector_repo,
                keyword_repository=keyword_repo,
                reranking_service=rerank_service,
                fusion_service=fusion_service,
                highlighting_service=None  # Not implemented yet
            )
            
            logger.info("Created core search service with injected dependencies")
        
        return self._search_service
    
    def reset(self):
        """Reset all cached instances (useful for testing)."""
        self._vector_repository = None
        self._keyword_repository = None
        self._reranking_service = None
        self._fusion_service = None
        self._search_service = None
        logger.info("Reset DI container")


# Global container instance
_container = DIContainer()


def get_container() -> DIContainer:
    """Get the global DI container instance."""
    return _container


# Convenience functions for direct access
def get_search_service() -> SearchService:
    """Get the configured search service."""
    return _container.get_search_service()


def reset_container():
    """Reset the global container (mainly for testing)."""
    _container.reset()
