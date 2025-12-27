"""
LlamaIndex-based Hybrid Retriever for RAG Pipeline.

This module replaces the manual hybrid search implementation with LlamaIndex's
QueryFusionRetriever and custom retrievers for better maintainability
and access to LlamaIndex's ecosystem of optimizations.

Architecture:
    LlamaIndexHybridRetriever
    ├── VectorIndexRetriever (from existing Weaviate adapter)
    ├── BM25Retriever (from existing OpenSearch adapter)  
    └── QueryFusionRetriever (RRF/weighted fusion)
           └── NodePostprocessors (reranking, deduplication)

Migration from manual implementation:
    - SearchService._hybrid_search() → LlamaIndexHybridRetriever.retrieve()
    - FusionAlgorithms.reciprocal_rank_fusion() → QueryFusionRetriever
    - _deduplicate_documents() → SimilarityPostprocessor

Usage:
    from core.domain.llamaindex_retriever import LlamaIndexHybridRetriever
    
    retriever = LlamaIndexHybridRetriever(
        vector_store=weaviate_store,
        bm25_store=opensearch_store,
        embedding_model=embed_model
    )
    results = await retriever.aretrieve(query, top_k=10)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable, Sequence, Union

# LlamaIndex imports
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.schema import (
    NodeWithScore,
    TextNode,
    QueryBundle,
    BaseNode,
)
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.callbacks import CallbackManager
from llama_index.core.postprocessor.types import BaseNodePostprocessor

logger = logging.getLogger(__name__)


class FusionMode(str, Enum):
    """Fusion algorithm modes for combining retrieval results."""
    RECIPROCAL_RANK = "reciprocal_rank"  # RRF algorithm
    RELATIVE_SCORE = "relative_score"    # Score normalization and averaging
    DISTRIBUTION_BASED = "distribution_based"  # Distribution-based fusion
    SIMPLE = "simple"  # Simple weighted combination


@dataclass
class RetrievalConfig:
    """Configuration for LlamaIndex retrieval pipeline."""
    
    # Search parameters
    vector_top_k: int = 20
    bm25_top_k: int = 20
    final_top_k: int = 10
    
    # Fusion parameters  
    fusion_mode: FusionMode = FusionMode.RECIPROCAL_RANK
    vector_weight: float = 0.5
    bm25_weight: float = 0.5
    rrf_k: int = 60  # RRF constant
    
    # Query expansion
    num_query_variations: int = 3
    enable_query_expansion: bool = True
    
    # Reranking
    enable_rerank: bool = True
    rerank_top_n: int = 10
    
    # Deduplication
    enable_dedup: bool = True
    similarity_threshold: float = 0.85
    
    # Metadata
    include_metadata: bool = True
    metadata_fields: List[str] = field(default_factory=lambda: [
        "doc_id", "title", "doc_type", "faculty", "year", "subject"
    ])


class AsyncWrapperRetriever(BaseRetriever):
    """
    Wrapper to convert sync retrievers to async-compatible retrievers.
    
    LlamaIndex's base retrievers are sync, but our RAG pipeline is async.
    This wrapper enables async execution while maintaining compatibility.
    """
    
    def __init__(
        self,
        retriever: BaseRetriever,
        callback_manager: Optional[CallbackManager] = None
    ):
        """Initialize with wrapped retriever."""
        super().__init__(callback_manager=callback_manager)
        self._retriever = retriever
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync retrieve - delegates to wrapped retriever."""
        return self._retriever.retrieve(query_bundle)
    
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Async retrieve - runs sync in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._retriever.retrieve, 
            query_bundle
        )


class PortBasedVectorRetriever(BaseRetriever):
    """
    Vector retriever that uses existing VectorSearchRepository port.
    
    This adapter bridges LlamaIndex's retriever interface with our
    hexagonal architecture's port pattern.
    """
    
    def __init__(
        self,
        vector_repository,  # VectorSearchRepository port
        top_k: int = 10,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        Initialize with vector repository port.
        
        Args:
            vector_repository: VectorSearchRepository implementation
            top_k: Number of results to retrieve
        """
        super().__init__(callback_manager=callback_manager)
        self._vector_repo = vector_repository
        self._top_k = top_k
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync retrieve - not supported, use async."""
        raise NotImplementedError("Use aretrieve for async retrieval")
    
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Async retrieve using vector repository.
        
        Converts repository results to LlamaIndex NodeWithScore format.
        """
        from ..domain.models import SearchQuery, SearchMode
        
        query = SearchQuery(
            text=query_bundle.query_str,
            top_k=self._top_k,
            search_mode=SearchMode.VECTOR,
            filters=None,
            include_char_spans=True
        )
        
        try:
            results = await self._vector_repo.search(query)
            return self._convert_to_nodes(results)
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return []
    
    def _convert_to_nodes(self, results) -> List[NodeWithScore]:
        """Convert SearchResult list to NodeWithScore list."""
        nodes = []
        for result in results:
            metadata = {
                "doc_id": result.metadata.doc_id,
                "chunk_id": result.metadata.chunk_id,
                "title": result.metadata.title or "",
                "doc_type": result.metadata.doc_type or "",
                "faculty": result.metadata.faculty or "",
                "year": result.metadata.year,
                "subject": result.metadata.subject or "",
                "page": result.metadata.page,
                "source_type": "vector",
                "vector_score": result.score
            }
            
            node = TextNode(
                text=result.text,
                id_=result.metadata.chunk_id or result.metadata.doc_id,
                metadata=metadata
            )
            
            nodes.append(NodeWithScore(
                node=node,
                score=result.score
            ))
        
        return nodes


class PortBasedBM25Retriever(BaseRetriever):
    """
    BM25 retriever that uses existing KeywordSearchRepository port.
    
    This adapter bridges LlamaIndex's retriever interface with our
    hexagonal architecture's port pattern for keyword/BM25 search.
    """
    
    def __init__(
        self,
        keyword_repository,  # KeywordSearchRepository port
        top_k: int = 10,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        Initialize with keyword repository port.
        
        Args:
            keyword_repository: KeywordSearchRepository implementation
            top_k: Number of results to retrieve
        """
        super().__init__(callback_manager=callback_manager)
        self._keyword_repo = keyword_repository
        self._top_k = top_k
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync retrieve - not supported, use async."""
        raise NotImplementedError("Use aretrieve for async retrieval")
    
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Async retrieve using keyword repository.
        
        Converts repository results to LlamaIndex NodeWithScore format.
        """
        from ..domain.models import SearchQuery, SearchMode
        
        query = SearchQuery(
            text=query_bundle.query_str,
            top_k=self._top_k,
            search_mode=SearchMode.BM25,
            filters=None,
            include_char_spans=True
        )
        
        try:
            results = await self._keyword_repo.search(query)
            return self._convert_to_nodes(results)
        except Exception as e:
            logger.error(f"BM25 retrieval failed: {e}")
            return []
    
    def _convert_to_nodes(self, results) -> List[NodeWithScore]:
        """Convert SearchResult list to NodeWithScore list."""
        nodes = []
        for result in results:
            metadata = {
                "doc_id": result.metadata.doc_id,
                "chunk_id": result.metadata.chunk_id,
                "title": result.metadata.title or "",
                "doc_type": result.metadata.doc_type or "",
                "faculty": result.metadata.faculty or "",
                "year": result.metadata.year,
                "subject": result.metadata.subject or "",
                "page": result.metadata.page,
                "source_type": "bm25",
                "bm25_score": result.score
            }
            
            node = TextNode(
                text=result.text,
                id_=result.metadata.chunk_id or result.metadata.doc_id,
                metadata=metadata
            )
            
            nodes.append(NodeWithScore(
                node=node,
                score=result.score
            ))
        
        return nodes


class RecursiveRankFusion:
    """
    Reciprocal Rank Fusion (RRF) algorithm implementation.
    
    RRF is a method for combining multiple ranked lists.
    Formula: RRF(d) = Σ 1/(k + r(d)) for each ranking where d appears
    
    Reference: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
    """
    
    @staticmethod
    def fuse(
        results_lists: List[List[NodeWithScore]],
        weights: Optional[List[float]] = None,
        k: int = 60,
        top_k: Optional[int] = None
    ) -> List[NodeWithScore]:
        """
        Fuse multiple ranked result lists using RRF.
        
        Args:
            results_lists: List of ranked result lists
            weights: Optional weights for each list (default: equal weights)
            k: RRF constant (default: 60)
            top_k: Maximum results to return
            
        Returns:
            Fused and re-ranked list of results
        """
        if not results_lists:
            return []
        
        # Default to equal weights
        if weights is None:
            weights = [1.0] * len(results_lists)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Calculate RRF scores
        rrf_scores: Dict[str, float] = {}
        node_map: Dict[str, NodeWithScore] = {}
        
        for list_idx, results in enumerate(results_lists):
            weight = weights[list_idx]
            
            for rank, node_with_score in enumerate(results, start=1):
                node_id = node_with_score.node.node_id or node_with_score.node.id_
                
                # RRF score contribution
                rrf_contribution = weight / (k + rank)
                
                if node_id in rrf_scores:
                    rrf_scores[node_id] += rrf_contribution
                else:
                    rrf_scores[node_id] = rrf_contribution
                    node_map[node_id] = node_with_score
        
        # Sort by RRF score
        sorted_ids = sorted(
            rrf_scores.keys(),
            key=lambda x: rrf_scores[x],
            reverse=True
        )
        
        # Build final results
        fused_results = []
        for node_id in sorted_ids[:top_k] if top_k else sorted_ids:
            original = node_map[node_id]
            
            # Create new node with RRF score
            new_node = NodeWithScore(
                node=original.node,
                score=rrf_scores[node_id]
            )
            
            # Preserve original scores in metadata
            if hasattr(original.node, 'metadata'):
                original.node.metadata["rrf_score"] = rrf_scores[node_id]
            
            fused_results.append(new_node)
        
        return fused_results


class LlamaIndexHybridRetriever(BaseRetriever):
    """
    Hybrid retriever combining vector and BM25 search using LlamaIndex.
    
    This is the main replacement for SearchService._hybrid_search().
    It uses our existing repository ports but leverages LlamaIndex's
    retriever abstractions for cleaner code and extensibility.
    
    Features:
        - Reciprocal Rank Fusion (RRF) for combining results
        - Configurable weights for vector vs BM25
        - Async execution for parallel retrieval
        - Compatible with LlamaIndex postprocessors
    """
    
    def __init__(
        self,
        vector_repository,
        keyword_repository,
        config: Optional[RetrievalConfig] = None,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        Initialize hybrid retriever with repository ports.
        
        Args:
            vector_repository: VectorSearchRepository implementation
            keyword_repository: KeywordSearchRepository implementation
            config: Optional retrieval configuration
        """
        super().__init__(callback_manager=callback_manager)
        
        self.config = config or RetrievalConfig()
        
        # Create sub-retrievers using ports
        self._vector_retriever = PortBasedVectorRetriever(
            vector_repository=vector_repository,
            top_k=self.config.vector_top_k
        )
        
        self._bm25_retriever = PortBasedBM25Retriever(
            keyword_repository=keyword_repository,
            top_k=self.config.bm25_top_k
        )
        
        logger.info(
            f"LlamaIndexHybridRetriever initialized with "
            f"fusion_mode={self.config.fusion_mode.value}, "
            f"vector_weight={self.config.vector_weight}, "
            f"bm25_weight={self.config.bm25_weight}"
        )
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync retrieve - not supported, use async."""
        # For sync calls, run async in new event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Use aretrieve in async context")
        except RuntimeError:
            pass
        
        return asyncio.run(self._aretrieve(query_bundle))
    
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Async hybrid retrieval with parallel execution and RRF fusion.
        
        Steps:
        1. Execute vector and BM25 retrieval in parallel
        2. Fuse results using configured fusion algorithm
        3. Return top-k fused results
        """
        logger.info(f"🔍 Hybrid retrieval for: {query_bundle.query_str[:50]}...")
        
        # Execute retrievals in parallel
        vector_task = self._vector_retriever._aretrieve(query_bundle)
        bm25_task = self._bm25_retriever._aretrieve(query_bundle)
        
        vector_results, bm25_results = await asyncio.gather(
            vector_task,
            bm25_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(vector_results, Exception):
            logger.warning(f"Vector retrieval failed: {vector_results}")
            vector_results = []
        if isinstance(bm25_results, Exception):
            logger.warning(f"BM25 retrieval failed: {bm25_results}")
            bm25_results = []
        
        logger.info(
            f"   Retrieved {len(vector_results)} vector, "
            f"{len(bm25_results)} BM25 results"
        )
        
        # Fuse results
        if self.config.fusion_mode == FusionMode.RECIPROCAL_RANK:
            fused = RecursiveRankFusion.fuse(
                results_lists=[vector_results, bm25_results],
                weights=[self.config.vector_weight, self.config.bm25_weight],
                k=self.config.rrf_k,
                top_k=self.config.final_top_k
            )
        else:
            # Fallback to simple concatenation for other modes
            fused = self._simple_fusion(vector_results, bm25_results)
        
        # Mark results as fused
        for node_with_score in fused:
            if hasattr(node_with_score.node, 'metadata'):
                node_with_score.node.metadata["source_type"] = "fused"
        
        logger.info(f"   Fused into {len(fused)} final results")
        
        return fused
    
    def _simple_fusion(
        self,
        vector_results: List[NodeWithScore],
        bm25_results: List[NodeWithScore]
    ) -> List[NodeWithScore]:
        """Simple fusion by deduplication and sorting by score."""
        seen = set()
        fused = []
        
        # Combine all results
        all_results = []
        for r in vector_results:
            r.node.metadata["source_type"] = "vector"
            all_results.append(r)
        for r in bm25_results:
            r.node.metadata["source_type"] = "bm25"
            all_results.append(r)
        
        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Deduplicate
        for r in all_results:
            node_id = r.node.node_id or r.node.id_
            if node_id not in seen:
                seen.add(node_id)
                fused.append(r)
        
        return fused[:self.config.final_top_k]


class QueryExpansionRetriever(BaseRetriever):
    """
    Query expansion retriever that generates multiple query variations.
    
    This replaces the manual multi-query approach in _perform_rag_retrieval().
    Uses LLM to generate query variations, then retrieves and fuses results.
    
    Based on LlamaIndex's QueryFusionRetriever pattern.
    """
    
    def __init__(
        self,
        base_retriever: BaseRetriever,
        llm=None,  # LLM for query generation
        num_variations: int = 3,
        fusion_k: int = 60,
        callback_manager: Optional[CallbackManager] = None
    ):
        """
        Initialize query expansion retriever.
        
        Args:
            base_retriever: Base retriever to use for each query
            llm: LLM for generating query variations
            num_variations: Number of query variations to generate
            fusion_k: RRF constant for fusion
        """
        super().__init__(callback_manager=callback_manager)
        
        self._retriever = base_retriever
        self._llm = llm
        self._num_variations = num_variations
        self._fusion_k = fusion_k
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Sync retrieve."""
        raise NotImplementedError("Use aretrieve for async retrieval")
    
    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Generate query variations and retrieve for each.
        
        Steps:
        1. Generate query variations using LLM
        2. Retrieve results for each query in parallel
        3. Fuse all results using RRF
        """
        original_query = query_bundle.query_str
        
        # Generate variations
        queries = [original_query]
        if self._llm and self._num_variations > 1:
            variations = await self._generate_variations(original_query)
            queries.extend(variations[:self._num_variations - 1])
        
        logger.info(f"🔍 Query expansion: {len(queries)} queries")
        
        # Retrieve for each query in parallel
        tasks = [
            self._retriever._aretrieve(QueryBundle(query_str=q))
            for q in queries
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = [
            r for r in all_results 
            if not isinstance(r, Exception) and r
        ]
        
        if not valid_results:
            return []
        
        # Fuse all results
        fused = RecursiveRankFusion.fuse(
            results_lists=valid_results,
            k=self._fusion_k
        )
        
        return fused
    
    async def _generate_variations(self, query: str) -> List[str]:
        """Generate query variations using LLM."""
        if not self._llm:
            return []
        
        try:
            prompt = f"""Generate {self._num_variations} different ways to ask 
the following question. Return only the questions, one per line.

Original question: {query}

Requirements:
- Keep the same meaning
- Use different words/phrases
- Focus on different aspects
"""
            response = await self._llm.acomplete(prompt)
            variations = [
                line.strip() 
                for line in response.text.split('\n')
                if line.strip() and line.strip() != query
            ]
            return variations[:self._num_variations]
        except Exception as e:
            logger.warning(f"Query variation generation failed: {e}")
            return []


# =============================================================================
# Factory Functions
# =============================================================================

def create_hybrid_retriever(
    vector_repository,
    keyword_repository,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
    top_k: int = 10,
    enable_rerank: bool = True
) -> LlamaIndexHybridRetriever:
    """
    Factory function to create a configured hybrid retriever.
    
    Args:
        vector_repository: VectorSearchRepository implementation
        keyword_repository: KeywordSearchRepository implementation
        vector_weight: Weight for vector search results
        bm25_weight: Weight for BM25 results
        top_k: Number of final results
        enable_rerank: Whether to enable reranking
        
    Returns:
        Configured LlamaIndexHybridRetriever instance
    """
    config = RetrievalConfig(
        vector_top_k=max(top_k * 4, 20),
        bm25_top_k=max(top_k * 4, 20),
        final_top_k=top_k,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        enable_rerank=enable_rerank
    )
    
    return LlamaIndexHybridRetriever(
        vector_repository=vector_repository,
        keyword_repository=keyword_repository,
        config=config
    )


def create_query_expansion_retriever(
    base_retriever: BaseRetriever,
    llm=None,
    num_variations: int = 3
) -> QueryExpansionRetriever:
    """
    Factory function to create a query expansion retriever.
    
    Args:
        base_retriever: Base retriever (typically hybrid)
        llm: Optional LLM for query generation
        num_variations: Number of query variations
        
    Returns:
        Configured QueryExpansionRetriever instance
    """
    return QueryExpansionRetriever(
        base_retriever=base_retriever,
        llm=llm,
        num_variations=num_variations
    )
