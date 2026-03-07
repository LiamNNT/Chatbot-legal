"""
LlamaIndex-based Search Service.

This service provides an alternative implementation of SearchService using
LlamaIndex retrievers and postprocessors. It can be used as a drop-in
replacement for the original SearchService.

Migration path:
    # Old approach
    search_service = SearchService(vector_repo, keyword_repo, reranker, fusion)
    
    # New approach with LlamaIndex
    search_service = LlamaIndexSearchService(vector_repo, keyword_repo, reranker)

The LlamaIndex implementation provides:
    - Cleaner code through LlamaIndex abstractions
    - Better extensibility with postprocessor pipelines
    - Access to LlamaIndex ecosystem (query transformers, etc.)
    - Same interface as original SearchService

Usage:
    from app.search.adapters.llamaindex.search_service import LlamaIndexSearchService
    
    service = LlamaIndexSearchService(
        vector_repository=qdrant_adapter,
        keyword_repository=opensearch_adapter,
        reranking_service=cross_encoder_reranker
    )
    
    response = await service.search(query)
"""

import logging
import time
from typing import List, Optional, Dict, Any

from llama_index.core.schema import QueryBundle, NodeWithScore

from shared.domain.rag_models import (
    SearchQuery, 
    SearchResponse, 
    SearchResult, 
    SearchMode, 
    DocumentChunk,
    DocumentMetadata
)
from .retriever import (
    LlamaIndexHybridRetriever,
    PortBasedVectorRetriever,
    PortBasedBM25Retriever,
    RetrievalConfig,
    FusionMode,
    create_hybrid_retriever
)
from .postprocessors import (
    PostprocessorPipeline,
    DeduplicationPostprocessor,
    CrossEncoderRerankPostprocessor,
    MetadataFilterPostprocessor,
    ScoreThresholdPostprocessor,
    CitationPostprocessor,
    TopKPostprocessor,
    create_default_pipeline
)
from app.search.ports.repositories import VectorSearchRepository, KeywordSearchRepository
from app.search.ports.services import RerankingService, HighlightingService

logger = logging.getLogger(__name__)


class LlamaIndexSearchService:
    """
    Search service implementation using LlamaIndex.
    
    This is a drop-in replacement for SearchService that uses LlamaIndex
    retrievers and postprocessors for cleaner, more maintainable code.
    
    Features:
        - Hybrid search with RRF fusion via LlamaIndexHybridRetriever
        - Configurable postprocessor pipeline
        - Async-first design
        - Same interface as original SearchService
    """
    
    def __init__(
        self,
        vector_repository: VectorSearchRepository,
        keyword_repository: Optional[KeywordSearchRepository] = None,
        reranking_service: Optional[RerankingService] = None,
        highlighting_service: Optional[HighlightingService] = None,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Initialize LlamaIndex search service.
        
        Args:
            vector_repository: Vector search repository implementation
            keyword_repository: Keyword/BM25 search repository implementation
            reranking_service: Optional reranking service for cross-encoder
            highlighting_service: Optional highlighting service
            config: Optional retrieval configuration
        """
        self.vector_repository = vector_repository
        self.keyword_repository = keyword_repository
        self.reranking_service = reranking_service
        self.highlighting_service = highlighting_service
        self.config = config or RetrievalConfig()
        
        # Initialize retrievers
        self._init_retrievers()
        
        # Initialize postprocessor pipeline
        self._postprocessor_pipeline = create_default_pipeline(
            reranking_service=reranking_service,
            enable_rerank=self.config.enable_rerank,
            top_k=self.config.final_top_k,
            dedup_method="content_prefix"
        )
        
        logger.info(
            f"LlamaIndexSearchService initialized with "
            f"config={self.config}"
        )
    
    def _init_retrievers(self):
        """Initialize LlamaIndex retrievers."""
        # Vector retriever (always available)
        self._vector_retriever = PortBasedVectorRetriever(
            vector_repository=self.vector_repository,
            top_k=self.config.vector_top_k
        )
        
        # BM25 retriever (optional)
        self._bm25_retriever = None
        if self.keyword_repository:
            self._bm25_retriever = PortBasedBM25Retriever(
                keyword_repository=self.keyword_repository,
                top_k=self.config.bm25_top_k
            )
        
        # Hybrid retriever (if both available)
        self._hybrid_retriever = None
        if self.keyword_repository:
            self._hybrid_retriever = LlamaIndexHybridRetriever(
                vector_repository=self.vector_repository,
                keyword_repository=self.keyword_repository,
                config=self.config
            )
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """
        Execute a search query using LlamaIndex retrievers.
        
        Args:
            query: The search query containing all search parameters
            
        Returns:
            SearchResponse: Complete search results with metadata
        """
        start_time = time.time()
        
        try:
            # Create query bundle for LlamaIndex
            query_bundle = QueryBundle(query_str=query.text)
            
            # Route to appropriate retriever
            if query.search_mode == SearchMode.VECTOR:
                nodes = await self._vector_search(query_bundle, query)
            elif query.search_mode == SearchMode.BM25:
                nodes = await self._keyword_search(query_bundle, query)
            elif query.search_mode == SearchMode.HYBRID:
                nodes = await self._hybrid_search(query_bundle, query)
            else:
                raise ValueError(f"Unsupported search mode: {query.search_mode}")
            
            # Apply postprocessor pipeline
            nodes = await self._apply_postprocessors(
                nodes, 
                query_bundle, 
                query
            )
            
            # Apply highlighting if requested
            if query.highlight_matches and self.highlighting_service:
                results = self._nodes_to_results(nodes)
                results = await self.highlighting_service.highlight_matches(
                    query.text, results
                )
            else:
                results = self._nodes_to_results(nodes)
            
            # Limit to requested top_k
            results = results[:query.top_k]
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            return SearchResponse(
                results=results,
                total_hits=len(results),
                latency_ms=latency_ms,
                search_metadata={
                    "search_mode": query.search_mode.value,
                    "use_rerank": query.use_rerank,
                    "filters_applied": query.filters is not None,
                    "engine": "llamaindex"
                }
            )
            
        except Exception as e:
            logger.error(f"LlamaIndex search failed: {e}", exc_info=True)
            raise SearchError(f"Search failed: {str(e)}") from e
    
    async def _vector_search(
        self, 
        query_bundle: QueryBundle,
        query: SearchQuery
    ) -> List[NodeWithScore]:
        """Execute vector-only search."""
        logger.info(f"🔍 LlamaIndex vector search: '{query.text[:50]}...'")
        
        # Update retriever top_k for this query
        self._vector_retriever._top_k = max(query.top_k * 2, 20)
        
        nodes = await self._vector_retriever._aretrieve(query_bundle)
        
        logger.info(f"   Retrieved {len(nodes)} nodes via vector search")
        return nodes
    
    async def _keyword_search(
        self, 
        query_bundle: QueryBundle,
        query: SearchQuery
    ) -> List[NodeWithScore]:
        """Execute keyword/BM25 search."""
        if not self._bm25_retriever:
            raise SearchError("Keyword repository not configured")
        
        logger.info(f"🔍 LlamaIndex BM25 search: '{query.text[:50]}...'")
        
        # Update retriever top_k for this query
        self._bm25_retriever._top_k = max(query.top_k * 2, 20)
        
        nodes = await self._bm25_retriever._aretrieve(query_bundle)
        
        logger.info(f"   Retrieved {len(nodes)} nodes via BM25 search")
        return nodes
    
    async def _hybrid_search(
        self, 
        query_bundle: QueryBundle,
        query: SearchQuery
    ) -> List[NodeWithScore]:
        """Execute hybrid search (vector + BM25 with RRF fusion)."""
        if not self._hybrid_retriever:
            # Fallback to vector-only if no keyword repository
            logger.warning("Keyword repository not available, falling back to vector search")
            return await self._vector_search(query_bundle, query)
        
        logger.info(f"🔍 LlamaIndex hybrid search: '{query.text[:50]}...'")
        
        # Update config for this query
        self._hybrid_retriever.config.vector_weight = query.vector_weight or 0.5
        self._hybrid_retriever.config.bm25_weight = query.bm25_weight or 0.5
        self._hybrid_retriever.config.final_top_k = max(query.top_k * 2, 20)
        
        nodes = await self._hybrid_retriever._aretrieve(query_bundle)
        
        logger.info(f"   Retrieved {len(nodes)} fused nodes via hybrid search")
        return nodes
    
    async def _apply_postprocessors(
        self,
        nodes: List[NodeWithScore],
        query_bundle: QueryBundle,
        query: SearchQuery
    ) -> List[NodeWithScore]:
        """Apply postprocessor pipeline with query-specific config."""
        # Build custom pipeline based on query parameters
        pipeline = PostprocessorPipeline()
        
        # 1. Deduplication (always)
        pipeline.add(DeduplicationPostprocessor(
            method="content_prefix",
            keep_highest_score=True
        ))
        
        # 2. Metadata filtering (if filters provided)
        if query.filters:
            filters_dict = query.filters if isinstance(query.filters, dict) else {}
            pipeline.add(MetadataFilterPostprocessor(
                doc_types=filters_dict.get("doc_types"),
                faculties=filters_dict.get("faculties"),
                years=filters_dict.get("years"),
                subjects=filters_dict.get("subjects")
            ))
        
        # 3. Reranking (if requested and available)
        if query.use_rerank and self.reranking_service:
            rerank_top_n = getattr(query, 'rerank_top_n', None) or min(query.top_k * 2, 20)
            pipeline.add(CrossEncoderRerankPostprocessor(
                reranking_service=self.reranking_service,
                top_n=rerank_top_n
            ))
        
        # 4. Top-K limiter
        pipeline.add(TopKPostprocessor(top_k=query.top_k))
        
        # 5. Citation enrichment (if needed)
        if getattr(query, 'need_citation', False):
            pipeline.add(CitationPostprocessor())
        
        # Execute pipeline
        return await pipeline.process_async(nodes, query_bundle)
    
    def _nodes_to_results(
        self, 
        nodes: List[NodeWithScore]
    ) -> List[SearchResult]:
        """Convert LlamaIndex nodes to SearchResult domain objects."""
        results = []
        
        for node_with_score in nodes:
            node = node_with_score.node
            meta = node.metadata or {}
            
            # Build DocumentMetadata
            doc_meta = DocumentMetadata(
                doc_id=meta.get("doc_id", ""),
                chunk_id=meta.get("chunk_id"),
                title=meta.get("title"),
                page=meta.get("page"),
                doc_type=meta.get("doc_type"),
                faculty=meta.get("faculty"),
                year=meta.get("year"),
                subject=meta.get("subject"),
                section=meta.get("section"),
                subsection=meta.get("subsection")
            )
            
            # Build SearchResult
            result = SearchResult(
                text=node.get_content(),
                metadata=doc_meta,
                score=node_with_score.score,
                source_type=meta.get("source_type", "unknown"),
                rank=meta.get("citation_index"),
                char_spans=meta.get("char_spans"),
                highlighted_text=meta.get("highlighted_text"),
                highlighted_title=meta.get("highlighted_title"),
                bm25_score=meta.get("bm25_score"),
                vector_score=meta.get("vector_score"),
                rerank_score=meta.get("rerank_score")
            )
            
            results.append(result)
        
        return results
    
    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        Index document chunks (delegates to repositories).
        
        Args:
            chunks: List of document chunks to index
            
        Returns:
            bool: True if indexing succeeded
        """
        success_count = 0
        
        # Index in vector repository
        try:
            if await self.vector_repository.index_documents(chunks):
                success_count += 1
                logger.info(f"Indexed {len(chunks)} chunks in vector repository")
        except Exception as e:
            logger.error(f"Vector indexing failed: {e}")
        
        # Index in keyword repository
        if self.keyword_repository:
            try:
                if await self.keyword_repository.index_documents(chunks):
                    success_count += 1
                    logger.info(f"Indexed {len(chunks)} chunks in keyword repository")
            except Exception as e:
                logger.error(f"Keyword indexing failed: {e}")
        
        return success_count > 0
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from all repositories.
        
        Args:
            doc_id: ID of the document to delete
            
        Returns:
            bool: True if deletion succeeded
        """
        success_count = 0
        
        try:
            if await self.vector_repository.delete_document_vectors(doc_id):
                success_count += 1
        except Exception as e:
            logger.error(f"Vector deletion failed: {e}")
        
        if self.keyword_repository:
            try:
                if await self.keyword_repository.delete_document_index(doc_id):
                    success_count += 1
            except Exception as e:
                logger.error(f"Keyword deletion failed: {e}")
        
        return success_count > 0
    
    async def highlight_results(
        self, 
        query: str, 
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Add highlighting to search results.
        
        Args:
            query: The search query for highlighting
            results: List of search results to highlight
            
        Returns:
            List of SearchResult with highlighting applied
        """
        if not self.highlighting_service:
            logger.debug("No highlighting service configured, returning results as-is")
            return results
        
        try:
            return await self.highlighting_service.highlight_matches(query, results)
        except Exception as e:
            logger.warning(f"Highlighting failed: {e}, returning results without highlighting")
            return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the search service.
        
        Returns:
            Dict with service statistics
        """
        return {
            "engine": "llamaindex",
            "has_vector_repository": self.vector_repository is not None,
            "has_keyword_repository": self.keyword_repository is not None,
            "has_reranking": self.reranking_service is not None,
            "has_highlighting": self.highlighting_service is not None,
            "config": {
                "vector_weight": self.config.vector_weight,
                "bm25_weight": self.config.bm25_weight,
                "vector_top_k": self.config.vector_top_k,
                "bm25_top_k": self.config.bm25_top_k,
                "final_top_k": self.config.final_top_k,
                "enable_rerank": self.config.enable_rerank,
                "fusion_mode": self.config.fusion_mode.value
            }
        }


class SearchError(Exception):
    """Domain exception for search-related errors."""
    pass


# =============================================================================
# Factory Function
# =============================================================================

def create_llamaindex_search_service(
    vector_repository: VectorSearchRepository,
    keyword_repository: Optional[KeywordSearchRepository] = None,
    reranking_service: Optional[RerankingService] = None,
    highlighting_service: Optional[HighlightingService] = None,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
    top_k: int = 10,
    enable_rerank: bool = True
) -> LlamaIndexSearchService:
    """
    Factory function to create a configured LlamaIndex search service.
    
    Args:
        vector_repository: Vector search repository
        keyword_repository: Optional keyword search repository
        reranking_service: Optional reranking service
        highlighting_service: Optional highlighting service
        vector_weight: Weight for vector search (default 0.5)
        bm25_weight: Weight for BM25 search (default 0.5)
        top_k: Default number of results (default 10)
        enable_rerank: Whether to enable reranking (default True)
        
    Returns:
        Configured LlamaIndexSearchService instance
    """
    config = RetrievalConfig(
        vector_top_k=max(top_k * 4, 20),
        bm25_top_k=max(top_k * 4, 20),
        final_top_k=top_k,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        enable_rerank=enable_rerank
    )
    
    return LlamaIndexSearchService(
        vector_repository=vector_repository,
        keyword_repository=keyword_repository,
        reranking_service=reranking_service,
        highlighting_service=highlighting_service,
        config=config
    )
