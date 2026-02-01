# app/core/retrieval/unified_retriever.py
"""
Unified Retriever for Vietnamese Legal RAG.

This is the main orchestration module that combines:
1. Query parsing (extract legal references)
2. Metadata filtering (build VectorDB filters)
3. Hybrid retrieval (vector + BM25)
4. Neighbor expansion (siblings/parent context)
5. Reranking (cross-encoder)
6. Context packing with citations

Usage:
    from app.core.retrieval import UnifiedRetriever
    
    retriever = UnifiedRetriever.from_settings(settings)
    result = await retriever.retrieve(
        query="Khoản 2 Điều 11 quy định gì về học phí?",
        top_k=5
    )
    
    # Access results
    context = result.final_context
    citations = result.citations
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from app.core.retrieval.schemas import (
    Citation,
    LegalQuery,
    NeighborContext,
    QueryIntent,
    RetrievalConfig,
    RetrievalResult,
    RetrievedChunk,
)
from app.core.retrieval.legal_query_parser import LegalQueryParser
from app.core.retrieval.metadata_filter_builder import (
    MetadataFilterBuilder,
    WeaviateFilterBuilder,
    OpenSearchFilterBuilder,
    get_filter_builder,
)
from app.core.retrieval.neighbor_expander import NeighborExpander

logger = logging.getLogger(__name__)


class UnifiedRetriever:
    """
    Unified retriever combining all retrieval components.
    
    This class orchestrates the full retrieval pipeline:
    1. Parse query → LegalQuery
    2. Build metadata filters
    3. Execute hybrid search (vector + BM25)
    4. Apply metadata filters
    5. Expand with neighbor context
    6. Rerank results
    7. Pack context with citations
    
    The retriever is designed to be:
    - Configurable (via RetrievalConfig)
    - Extensible (via dependency injection)
    - Async-first (all operations are async)
    - Observable (detailed metrics and logging)
    """
    
    def __init__(
        self,
        vector_search_fn: Callable[..., Any],
        bm25_search_fn: Optional[Callable[..., Any]] = None,
        fetch_chunk_fn: Optional[Callable[[str], Any]] = None,
        fetch_chunks_fn: Optional[Callable[[List[str]], List[Any]]] = None,
        rerank_fn: Optional[Callable[[str, List[Any]], List[Any]]] = None,
        config: Optional[RetrievalConfig] = None,
        parser: Optional[LegalQueryParser] = None,
        filter_builder: Optional[MetadataFilterBuilder] = None,
        neighbor_expander: Optional[NeighborExpander] = None,
    ):
        """
        Initialize the unified retriever.
        
        Args:
            vector_search_fn: Async function for vector search
                Signature: (query: str, top_k: int, filters: Optional[dict]) -> List[chunks]
            bm25_search_fn: Optional async function for BM25/keyword search
                Signature: (query: str, top_k: int, filters: Optional[dict]) -> List[chunks]
            fetch_chunk_fn: Optional async function to fetch chunk by ID
            fetch_chunks_fn: Optional async function to fetch multiple chunks by IDs
            rerank_fn: Optional async function for reranking
                Signature: (query: str, chunks: List) -> List[chunks]
            config: Retrieval configuration
            parser: Query parser instance
            filter_builder: Metadata filter builder instance
            neighbor_expander: Neighbor expander instance
        """
        self.vector_search_fn = vector_search_fn
        self.bm25_search_fn = bm25_search_fn
        self.fetch_chunk_fn = fetch_chunk_fn
        self.fetch_chunks_fn = fetch_chunks_fn
        self.rerank_fn = rerank_fn
        
        self.config = config or RetrievalConfig()
        self.parser = parser or LegalQueryParser()
        self.filter_builder = filter_builder or WeaviateFilterBuilder()
        
        # Initialize neighbor expander with fetch functions
        self.neighbor_expander = neighbor_expander or NeighborExpander(
            fetch_chunk_fn=fetch_chunk_fn,
            fetch_chunks_fn=fetch_chunks_fn,
            max_total_neighbor_tokens=self.config.max_neighbor_tokens,
            include_parent=self.config.include_parent,
            include_prev_sibling=self.config.include_siblings,
            include_next_sibling=self.config.include_siblings,
        )
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
        config_override: Optional[RetrievalConfig] = None,
    ) -> RetrievalResult:
        """
        Execute the full retrieval pipeline.
        
        Args:
            query: User query string
            top_k: Number of chunks to retrieve (overrides config)
            filters: Additional filters to apply
            config_override: Override config for this request
            
        Returns:
            RetrievalResult with chunks, context, and citations
        """
        start_time = time.time()
        config = config_override or self.config
        top_k = top_k or config.top_k
        
        # 1. Parse query
        parsed_query = self.parser.parse(query)
        logger.info(
            f"Parsed query: intent={parsed_query.intent.value}, "
            f"law_id={parsed_query.law_id}, article={parsed_query.article_id}, "
            f"clause={parsed_query.clause_no}, point={parsed_query.point_no}"
        )
        
        # 2. Select retrieval strategy based on intent
        if parsed_query.intent == QueryIntent.LOOKUP_EXACT:
            # For exact lookups, use config optimized for precision
            config = RetrievalConfig.for_exact_lookup()
        
        # 3. Build metadata filters
        query_filters = None
        if config.enable_metadata_filter and parsed_query.has_legal_reference():
            query_filters = self.filter_builder.build_filter(
                parsed_query,
                strict=config.strict_filter,
                additional_filters=filters,
            )
            logger.debug(f"Built query filters: {query_filters}")
        elif filters:
            query_filters = self.filter_builder.build_filter_from_dict(filters, strict=config.strict_filter)
        
        # 4. Execute search
        chunks = await self._execute_search(
            query=parsed_query.normalized_query or query,
            top_k=max(config.vector_top_k, config.bm25_top_k),
            filters=query_filters,
            config=config,
        )
        
        chunks_before_rerank = len(chunks)
        logger.info(f"Retrieved {chunks_before_rerank} chunks from search")
        
        # 5. Rerank if enabled
        if config.enable_rerank and self.rerank_fn and len(chunks) > 1:
            chunks = await self._rerank_chunks(query, chunks, config.rerank_top_n)
            logger.info(f"Reranked to {len(chunks)} chunks")
        
        # 6. Take top_k after reranking
        chunks = chunks[:top_k]
        
        # 7. Expand with neighbor context
        neighbor_chunks_added = 0
        if config.enable_neighbor_expansion and self.neighbor_expander:
            existing_ids = {c.chunk_id for c in chunks}
            chunks = await self.neighbor_expander.expand(chunks, existing_ids)
            
            # Count neighbor chunks added
            for chunk in chunks:
                if chunk.neighbors:
                    neighbor_chunks_added += len(chunk.neighbors.get_all_chunks())
            
            logger.info(f"Added {neighbor_chunks_added} neighbor chunks")
        
        # 8. Generate citations
        citations = self._generate_citations(chunks) if config.generate_citations else []
        
        # 9. Pack final context
        final_context = self._pack_context(chunks, parsed_query)
        
        # 10. Build result
        elapsed_ms = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            chunks=chunks,
            final_context=final_context,
            citations=citations,
            parsed_query=parsed_query,
            retrieval_time_ms=elapsed_ms,
            chunks_before_rerank=chunks_before_rerank,
            chunks_after_filter=len(chunks),
            neighbor_chunks_added=neighbor_chunks_added,
            debug_info={
                "query_intent": parsed_query.intent.value,
                "filters_applied": query_filters is not None,
                "rerank_applied": config.enable_rerank and self.rerank_fn is not None,
            },
        )
    
    async def retrieve_by_ids(
        self,
        chunk_ids: List[str],
    ) -> List[RetrievedChunk]:
        """
        Retrieve specific chunks by their IDs.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve
            
        Returns:
            List of retrieved chunks
        """
        if not chunk_ids:
            return []
        
        if self.fetch_chunks_fn:
            raw_chunks = await self.fetch_chunks_fn(chunk_ids)
            return [self._convert_to_chunk(c) for c in raw_chunks if c]
        
        elif self.fetch_chunk_fn:
            chunks = []
            for chunk_id in chunk_ids:
                try:
                    raw = await self.fetch_chunk_fn(chunk_id)
                    if raw:
                        chunks.append(self._convert_to_chunk(raw))
                except Exception as e:
                    logger.warning(f"Failed to fetch chunk {chunk_id}: {e}")
            return chunks
        
        else:
            logger.warning("No fetch function available for retrieve_by_ids")
            return []
    
    async def retrieve_with_query(
        self,
        legal_query: LegalQuery,
        top_k: Optional[int] = None,
        config_override: Optional[RetrievalConfig] = None,
    ) -> RetrievalResult:
        """
        Retrieve using pre-parsed LegalQuery.
        
        Args:
            legal_query: Pre-parsed legal query
            top_k: Number of chunks to retrieve
            config_override: Override config for this request
            
        Returns:
            RetrievalResult
        """
        config = config_override or self.config
        top_k = top_k or config.top_k
        
        # Build filters from legal query
        query_filters = None
        if config.enable_metadata_filter and legal_query.has_legal_reference():
            query_filters = self.filter_builder.build_filter(
                legal_query,
                strict=config.strict_filter,
            )
        
        # Execute search
        chunks = await self._execute_search(
            query=legal_query.normalized_query or legal_query.raw,
            top_k=max(config.vector_top_k, config.bm25_top_k),
            filters=query_filters,
            config=config,
        )
        
        # Continue with normal pipeline...
        # (Simplified for pre-parsed query case)
        chunks = chunks[:top_k]
        
        citations = self._generate_citations(chunks)
        final_context = self._pack_context(chunks, legal_query)
        
        return RetrievalResult(
            chunks=chunks,
            final_context=final_context,
            citations=citations,
            parsed_query=legal_query,
        )
    
    async def _execute_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Any],
        config: RetrievalConfig,
    ) -> List[RetrievedChunk]:
        """Execute the actual search (vector, BM25, or hybrid)."""
        
        # Determine search mode
        has_bm25 = self.bm25_search_fn is not None
        use_hybrid = has_bm25 and config.bm25_weight > 0
        
        if use_hybrid:
            return await self._hybrid_search(query, top_k, filters, config)
        else:
            return await self._vector_search(query, top_k, filters)
    
    async def _vector_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Any],
    ) -> List[RetrievedChunk]:
        """Execute vector-only search."""
        try:
            raw_results = await self.vector_search_fn(query, top_k, filters)
            return [self._convert_to_chunk(r, "vector") for r in raw_results]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        filters: Optional[Any],
        config: RetrievalConfig,
    ) -> List[RetrievedChunk]:
        """Execute hybrid search (vector + BM25) with fusion."""
        
        # Execute both searches in parallel
        vector_task = asyncio.create_task(
            self._safe_search(self.vector_search_fn, query, config.vector_top_k, filters, "vector")
        )
        bm25_task = asyncio.create_task(
            self._safe_search(self.bm25_search_fn, query, config.bm25_top_k, filters, "bm25")
        )
        
        vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
        
        # Fuse results using RRF
        if config.fusion_mode == "rrf":
            fused = self._rrf_fusion(vector_results, bm25_results, config.rrf_k, top_k)
        elif config.fusion_mode == "weighted":
            fused = self._weighted_fusion(
                vector_results, bm25_results,
                config.vector_weight, config.bm25_weight,
                top_k
            )
        else:
            # Simple interleaving
            fused = self._simple_fusion(vector_results, bm25_results, top_k)
        
        return fused
    
    async def _safe_search(
        self,
        search_fn: Optional[Callable],
        query: str,
        top_k: int,
        filters: Optional[Any],
        source: str,
    ) -> List[RetrievedChunk]:
        """Execute search with error handling."""
        if search_fn is None:
            return []
        
        try:
            raw_results = await search_fn(query, top_k, filters)
            return [self._convert_to_chunk(r, source) for r in raw_results]
        except Exception as e:
            logger.error(f"{source} search failed: {e}")
            return []
    
    def _rrf_fusion(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        k: int = 60,
        top_n: int = 10,
    ) -> List[RetrievedChunk]:
        """Reciprocal Rank Fusion of two result lists."""
        
        # Build RRF scores
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}
        
        for rank, chunk in enumerate(vector_results):
            score = 1.0 / (k + rank + 1)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + score
            chunk_map[chunk.chunk_id] = chunk
        
        for rank, chunk in enumerate(bm25_results):
            score = 1.0 / (k + rank + 1)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0) + score
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk
        
        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Build result list with updated scores
        results = []
        for chunk_id in sorted_ids[:top_n]:
            chunk = chunk_map[chunk_id]
            chunk.score = rrf_scores[chunk_id]
            chunk.retrieval_source = "hybrid"
            results.append(chunk)
        
        return results
    
    def _weighted_fusion(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        vector_weight: float,
        bm25_weight: float,
        top_n: int,
    ) -> List[RetrievedChunk]:
        """Weighted score fusion."""
        
        scores: Dict[str, float] = {}
        chunk_map: Dict[str, RetrievedChunk] = {}
        
        # Normalize and weight vector scores
        if vector_results:
            max_v = max(c.score for c in vector_results) or 1.0
            for chunk in vector_results:
                norm_score = (chunk.score / max_v) * vector_weight
                scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + norm_score
                chunk_map[chunk.chunk_id] = chunk
        
        # Normalize and weight BM25 scores
        if bm25_results:
            max_b = max(c.score for c in bm25_results) or 1.0
            for chunk in bm25_results:
                norm_score = (chunk.score / max_b) * bm25_weight
                scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + norm_score
                if chunk.chunk_id not in chunk_map:
                    chunk_map[chunk.chunk_id] = chunk
        
        # Sort and return
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        results = []
        for chunk_id in sorted_ids[:top_n]:
            chunk = chunk_map[chunk_id]
            chunk.score = scores[chunk_id]
            chunk.retrieval_source = "hybrid"
            results.append(chunk)
        
        return results
    
    def _simple_fusion(
        self,
        vector_results: List[RetrievedChunk],
        bm25_results: List[RetrievedChunk],
        top_n: int,
    ) -> List[RetrievedChunk]:
        """Simple interleaving fusion."""
        
        seen_ids: Set[str] = set()
        results: List[RetrievedChunk] = []
        
        # Interleave results
        max_len = max(len(vector_results), len(bm25_results))
        for i in range(max_len):
            if i < len(vector_results):
                chunk = vector_results[i]
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    chunk.retrieval_source = "hybrid"
                    results.append(chunk)
            
            if i < len(bm25_results):
                chunk = bm25_results[i]
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    chunk.retrieval_source = "hybrid"
                    results.append(chunk)
            
            if len(results) >= top_n:
                break
        
        return results[:top_n]
    
    async def _rerank_chunks(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        top_n: int,
    ) -> List[RetrievedChunk]:
        """Rerank chunks using cross-encoder."""
        if not self.rerank_fn:
            return chunks
        
        try:
            reranked = await self.rerank_fn(query, chunks)
            
            # Update rerank scores
            for i, chunk in enumerate(reranked):
                if hasattr(chunk, 'rerank_score'):
                    chunk.rerank_score = chunk.score
            
            return reranked[:top_n]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return chunks[:top_n]
    
    def _convert_to_chunk(
        self,
        raw: Any,
        source: str = "hybrid",
    ) -> RetrievedChunk:
        """Convert raw result to RetrievedChunk."""
        
        # Handle LlamaIndex NodeWithScore
        if hasattr(raw, 'node') and hasattr(raw, 'score'):
            chunk = RetrievedChunk.from_llama_node(raw.node, score=raw.score)
            chunk.retrieval_source = source
            return chunk
        
        # Handle LlamaIndex TextNode
        if hasattr(raw, 'text') and hasattr(raw, 'metadata'):
            score = raw.metadata.get('score', 0.0) if hasattr(raw, 'metadata') else 0.0
            chunk = RetrievedChunk.from_llama_node(raw, score=score)
            chunk.retrieval_source = source
            return chunk
        
        # Handle dict format
        if isinstance(raw, dict):
            chunk_id = raw.get("chunk_id", raw.get("id", str(id(raw))))
            metadata = raw.get("metadata", {})
            score = raw.get("score", raw.get("_score", 0.0))
            
            return RetrievedChunk(
                chunk_id=chunk_id,
                content=raw.get("content", raw.get("text", "")),
                embedding_prefix=raw.get("embedding_prefix") or metadata.get("embedding_prefix"),
                score=score,
                metadata=metadata,
                citation=Citation.from_chunk_metadata(chunk_id, metadata),
                parent_id=metadata.get("parent_id"),
                prev_sibling_id=metadata.get("prev_sibling_id"),
                next_sibling_id=metadata.get("next_sibling_id"),
                retrieval_source=source,
            )
        
        # Handle RetrievedChunk directly
        if isinstance(raw, RetrievedChunk):
            raw.retrieval_source = source
            return raw
        
        # Fallback
        return RetrievedChunk(
            chunk_id=str(id(raw)),
            content=str(raw),
            score=0.0,
            retrieval_source=source,
        )
    
    def _generate_citations(
        self,
        chunks: List[RetrievedChunk],
    ) -> List[Citation]:
        """Generate unique citations from chunks."""
        
        citations: List[Citation] = []
        seen: Set[str] = set()
        
        for chunk in chunks:
            if chunk.citation:
                citation_key = chunk.citation.to_short_form()
                if citation_key not in seen:
                    citations.append(chunk.citation)
                    seen.add(citation_key)
        
        return citations
    
    def _pack_context(
        self,
        chunks: List[RetrievedChunk],
        parsed_query: Optional[LegalQuery] = None,
    ) -> str:
        """Pack chunks into final context string for LLM."""
        
        if not chunks:
            return ""
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            # Citation header
            citation_str = chunk.citation.to_short_form() if chunk.citation else f"[{i}]"
            
            # Build chunk context
            content = chunk.get_full_context(include_neighbors=True)
            
            # Format with citation
            context_parts.append(f"### {citation_str}\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    @classmethod
    def from_adapters(
        cls,
        vector_adapter: Any,
        keyword_adapter: Optional[Any] = None,
        reranker: Optional[Any] = None,
        config: Optional[RetrievalConfig] = None,
    ) -> "UnifiedRetriever":
        """
        Create UnifiedRetriever from existing adapter instances.
        
        This factory method bridges with the existing adapter architecture.
        
        Args:
            vector_adapter: WeaviateVectorAdapter or similar
            keyword_adapter: OpenSearchKeywordAdapter or similar
            reranker: CrossEncoderReranker or similar
            config: Retrieval configuration
            
        Returns:
            UnifiedRetriever instance
        """
        # Wrap adapter methods
        async def vector_search(query: str, top_k: int, filters: Any = None):
            if hasattr(vector_adapter, 'search'):
                return await vector_adapter.search(query, top_k, filters)
            elif hasattr(vector_adapter, 'asearch'):
                return await vector_adapter.asearch(query, top_k, filters)
            else:
                raise NotImplementedError("Vector adapter must have search or asearch method")
        
        bm25_search = None
        if keyword_adapter:
            async def bm25_search(query: str, top_k: int, filters: Any = None):
                if hasattr(keyword_adapter, 'search'):
                    return await keyword_adapter.search(query, top_k, filters)
                elif hasattr(keyword_adapter, 'asearch'):
                    return await keyword_adapter.asearch(query, top_k, filters)
                else:
                    raise NotImplementedError("Keyword adapter must have search method")
        
        rerank_fn = None
        if reranker:
            async def rerank_fn(query: str, chunks: List):
                if hasattr(reranker, 'rerank'):
                    return await reranker.rerank(query, chunks)
                elif hasattr(reranker, 'arerank'):
                    return await reranker.arerank(query, chunks)
                else:
                    return chunks
        
        # Determine filter builder from adapter type
        filter_builder = WeaviateFilterBuilder()
        if keyword_adapter and "opensearch" in type(keyword_adapter).__name__.lower():
            filter_builder = OpenSearchFilterBuilder()
        
        return cls(
            vector_search_fn=vector_search,
            bm25_search_fn=bm25_search,
            rerank_fn=rerank_fn,
            config=config,
            filter_builder=filter_builder,
        )
