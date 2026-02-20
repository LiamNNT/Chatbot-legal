"""
LlamaIndex Node Postprocessors for RAG Pipeline.

This module provides postprocessors for filtering, reranking, and transforming
retrieved nodes in the RAG pipeline.

Postprocessors:
    - DeduplicationPostprocessor: Remove duplicate nodes based on content similarity
    - CrossEncoderRerankPostprocessor: Rerank using cross-encoder model
    - MetadataFilterPostprocessor: Filter nodes based on metadata
    - ScoreThresholdPostprocessor: Filter by minimum score
    - CitationPostprocessor: Add citation information to nodes

Migration from manual implementation:
    - _deduplicate_documents() → DeduplicationPostprocessor
    - RerankingService → CrossEncoderRerankPostprocessor
    - Filter logic in search_service → MetadataFilterPostprocessor

Usage:
    from app.knowledge_graph.domain.llamaindex_postprocessors import (
        DeduplicationPostprocessor,
        CrossEncoderRerankPostprocessor
    )
    
    postprocessors = [
        DeduplicationPostprocessor(similarity_threshold=0.85),
        CrossEncoderRerankPostprocessor(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    ]
    
    for pp in postprocessors:
        nodes = pp.postprocess_nodes(nodes, query_bundle)
"""

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Callable

# LlamaIndex imports
from llama_index.core.schema import (
    NodeWithScore,
    TextNode,
    QueryBundle,
)
from llama_index.core.postprocessor.types import BaseNodePostprocessor

logger = logging.getLogger(__name__)


class DeduplicationPostprocessor(BaseNodePostprocessor):
    """
    Remove duplicate nodes based on content similarity.
    
    This replaces the manual _deduplicate_documents() implementation.
    Uses content fingerprinting for efficient deduplication.
    
    Deduplication methods:
        - content_hash: MD5 hash of full content
        - content_prefix: First N characters comparison
        - node_id: Node ID comparison
    """
    
    # Pydantic fields
    similarity_threshold: float = 0.85
    method: str = "content_prefix"
    prefix_length: int = 100
    keep_highest_score: bool = True
    
    @classmethod
    def class_name(cls) -> str:
        return "DeduplicationPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """
        Remove duplicate nodes.
        
        Args:
            nodes: List of nodes to deduplicate
            query_bundle: Optional query (not used)
            
        Returns:
            Deduplicated list of nodes
        """
        if not nodes:
            return nodes
        
        seen_signatures: Dict[str, NodeWithScore] = {}
        
        for node_with_score in nodes:
            signature = self._get_signature(node_with_score)
            
            if signature not in seen_signatures:
                seen_signatures[signature] = node_with_score
            elif self.keep_highest_score:
                # Keep the one with higher score
                existing = seen_signatures[signature]
                if node_with_score.score > existing.score:
                    seen_signatures[signature] = node_with_score
        
        unique_nodes = list(seen_signatures.values())
        
        # Sort by score descending
        unique_nodes.sort(key=lambda x: x.score, reverse=True)
        
        logger.debug(
            f"Deduplication: {len(nodes)} → {len(unique_nodes)} nodes"
        )
        
        return unique_nodes
    
    def _get_signature(self, node_with_score: NodeWithScore) -> str:
        """Get unique signature for a node."""
        node = node_with_score.node
        text = node.get_content()
        
        if self.method == "content_hash":
            return hashlib.md5(text.encode()).hexdigest()
        elif self.method == "content_prefix":
            prefix = text[:self.prefix_length].strip().lower()
            return hashlib.md5(prefix.encode()).hexdigest()
        elif self.method == "node_id":
            return node.node_id or node.id_ or text[:50]
        else:
            # Default to content prefix
            prefix = text[:self.prefix_length].strip().lower()
            return hashlib.md5(prefix.encode()).hexdigest()


class CrossEncoderRerankPostprocessor(BaseNodePostprocessor):
    """
    Rerank nodes using cross-encoder model.
    
    This wraps our existing RerankingService to work as a LlamaIndex
    postprocessor, enabling seamless integration with the retrieval pipeline.
    
    Uses the existing CrossEncoderRerankingService implementation.
    """
    
    # Pydantic fields - use Any for service to avoid type issues
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n: Optional[int] = None
    min_score: float = 0.0
    batch_size: int = 32
    
    # Private attributes (not Pydantic fields)
    _reranking_service: Any = None
    _model: Any = None
    
    def __init__(self, reranking_service=None, **data):
        """Initialize with optional reranking service."""
        super().__init__(**data)
        object.__setattr__(self, '_reranking_service', reranking_service)
        object.__setattr__(self, '_model', None)
    
    @classmethod
    def class_name(cls) -> str:
        return "CrossEncoderRerankPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """
        Rerank nodes using cross-encoder (sync wrapper).
        
        For async reranking, use postprocess_nodes_async().
        """
        if not nodes or not query_bundle:
            return nodes
        
        # Try async execution if possible
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._async_rerank(nodes, query_bundle)
                    )
                    return future.result()
            else:
                return asyncio.run(self._async_rerank(nodes, query_bundle))
        except RuntimeError:
            return asyncio.run(self._async_rerank(nodes, query_bundle))
    
    async def postprocess_nodes_async(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Async reranking using cross-encoder."""
        return await self._async_rerank(nodes, query_bundle)
    
    async def _async_rerank(
        self,
        nodes: List[NodeWithScore],
        query_bundle: QueryBundle
    ) -> List[NodeWithScore]:
        """Internal async reranking implementation."""
        if not nodes:
            return nodes
        
        query = query_bundle.query_str
        
        # Use existing RerankingService if available
        if self._reranking_service:
            return await self._rerank_with_service(nodes, query)
        else:
            return await self._rerank_with_model(nodes, query)
    
    async def _rerank_with_service(
        self,
        nodes: List[NodeWithScore],
        query: str
    ) -> List[NodeWithScore]:
        """Rerank using RerankingService port."""
        from app.knowledge_graph.domain.models import SearchResult, DocumentMetadata
        
        # Convert NodeWithScore to SearchResult
        search_results = []
        node_map = {}  # Map to preserve original nodes
        
        for i, nws in enumerate(nodes):
            node = nws.node
            meta = node.metadata or {}
            
            doc_meta = DocumentMetadata(
                doc_id=meta.get("doc_id", f"doc_{i}"),
                chunk_id=meta.get("chunk_id"),
                title=meta.get("title"),
                page=meta.get("page"),
                doc_type=meta.get("doc_type"),
                faculty=meta.get("faculty"),
                year=meta.get("year"),
                subject=meta.get("subject")
            )
            
            result = SearchResult(
                text=node.get_content(),
                metadata=doc_meta,
                score=nws.score,
                source_type=meta.get("source_type", "unknown")
            )
            search_results.append(result)
            node_map[id(result)] = nws
        
        # Rerank using service
        try:
            reranked = await self._reranking_service.rerank(
                query=query,
                results=search_results,
                top_k=self.top_n
            )
            
            # Convert back to NodeWithScore
            reranked_nodes = []
            for result in reranked:
                # Create new node with rerank score
                original_nws = node_map.get(id(result))
                if original_nws:
                    new_node = NodeWithScore(
                        node=original_nws.node,
                        score=result.rerank_score or result.score
                    )
                    # Add rerank score to metadata
                    original_nws.node.metadata["rerank_score"] = result.rerank_score
                    reranked_nodes.append(new_node)
            
            return reranked_nodes
            
        except Exception as e:
            logger.warning(f"Reranking failed, returning original order: {e}")
            return nodes[:self.top_n] if self.top_n else nodes
    
    async def _rerank_with_model(
        self,
        nodes: List[NodeWithScore],
        query: str
    ) -> List[NodeWithScore]:
        """Rerank using direct cross-encoder model."""
        try:
            # Lazy load model
            if self._model is None:
                from sentence_transformers import CrossEncoder
                object.__setattr__(self, '_model', CrossEncoder(self.model_name))
            
            # Prepare pairs for scoring
            texts = [node.node.get_content() for node in nodes]
            pairs = [[query, text] for text in texts]
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(
                None,
                self._model.predict,
                pairs
            )
            
            # Update nodes with rerank scores
            reranked = []
            for node, score in zip(nodes, scores):
                if score >= self.min_score:
                    new_node = NodeWithScore(
                        node=node.node,
                        score=float(score)
                    )
                    node.node.metadata["rerank_score"] = float(score)
                    reranked.append(new_node)
            
            # Sort by rerank score
            reranked.sort(key=lambda x: x.score, reverse=True)
            
            return reranked[:self.top_n] if self.top_n else reranked
            
        except Exception as e:
            logger.warning(f"Model reranking failed: {e}")
            return nodes[:self.top_n] if self.top_n else nodes


class MetadataFilterPostprocessor(BaseNodePostprocessor):
    """
    Filter nodes based on metadata criteria.
    
    This enables filtering by doc_type, faculty, year, subject etc.
    Replaces manual filter logic in search_service.
    """
    
    # Pydantic fields
    doc_types: Optional[List[str]] = None
    faculties: Optional[List[str]] = None
    years: Optional[List[int]] = None
    subjects: Optional[List[str]] = None
    
    # Private attribute for custom filter (not a Pydantic field)
    _custom_filter: Optional[Callable[[Dict], bool]] = None
    
    def __init__(self, custom_filter: Optional[Callable[[Dict], bool]] = None, **data):
        """Initialize with optional custom filter."""
        super().__init__(**data)
        object.__setattr__(self, '_custom_filter', custom_filter)
    
    @classmethod
    def class_name(cls) -> str:
        return "MetadataFilterPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Filter nodes by metadata."""
        if not nodes:
            return nodes
        
        filtered = []
        for node_with_score in nodes:
            meta = node_with_score.node.metadata or {}
            
            if self._matches_filters(meta):
                filtered.append(node_with_score)
        
        logger.debug(f"Metadata filter: {len(nodes)} → {len(filtered)} nodes")
        
        return filtered
    
    def _matches_filters(self, metadata: Dict[str, Any]) -> bool:
        """Check if metadata matches all specified filters."""
        # Check doc_types
        if self.doc_types:
            doc_type = metadata.get("doc_type")
            if doc_type and doc_type not in self.doc_types:
                return False
        
        # Check faculties
        if self.faculties:
            faculty = metadata.get("faculty")
            if faculty and faculty not in self.faculties:
                return False
        
        # Check years
        if self.years:
            year = metadata.get("year")
            if year and year not in self.years:
                return False
        
        # Check subjects
        if self.subjects:
            subject = metadata.get("subject")
            if subject and subject not in self.subjects:
                return False
        
        # Custom filter
        if self._custom_filter and not self._custom_filter(metadata):
            return False
        
        return True


class ScoreThresholdPostprocessor(BaseNodePostprocessor):
    """
    Filter nodes by minimum relevance score.
    
    Useful for removing low-quality results after retrieval.
    """
    
    # Pydantic fields
    min_score: float = 0.0
    score_field: str = "score"
    
    @classmethod
    def class_name(cls) -> str:
        return "ScoreThresholdPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Filter nodes below score threshold."""
        if not nodes:
            return nodes
        
        filtered = [
            node for node in nodes
            if node.score >= self.min_score
        ]
        
        logger.debug(
            f"Score filter (min={self.min_score}): "
            f"{len(nodes)} → {len(filtered)} nodes"
        )
        
        return filtered


class CitationPostprocessor(BaseNodePostprocessor):
    """
    Add citation information to nodes.
    
    Enhances node metadata with citation details for
    source attribution in generated responses.
    """
    
    # Pydantic fields
    include_page: bool = True
    include_section: bool = True
    format_style: str = "apa"
    
    @classmethod
    def class_name(cls) -> str:
        return "CitationPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Add citation info to node metadata."""
        for i, node_with_score in enumerate(nodes, start=1):
            node = node_with_score.node
            meta = node.metadata or {}
            
            # Build citation
            citation = self._build_citation(meta, index=i)
            node.metadata["citation"] = citation
            node.metadata["citation_index"] = i
        
        return nodes
    
    def _build_citation(
        self,
        metadata: Dict[str, Any],
        index: int
    ) -> Dict[str, Any]:
        """Build citation object from metadata."""
        citation = {
            "index": index,
            "doc_id": metadata.get("doc_id", ""),
            "title": metadata.get("title", "Unknown"),
        }
        
        if self.include_page and metadata.get("page"):
            citation["page"] = metadata["page"]
        
        if self.include_section:
            if metadata.get("section"):
                citation["section"] = metadata["section"]
            if metadata.get("subsection"):
                citation["subsection"] = metadata["subsection"]
        
        # Add doc type and faculty if available
        if metadata.get("doc_type"):
            citation["doc_type"] = metadata["doc_type"]
        if metadata.get("faculty"):
            citation["faculty"] = metadata["faculty"]
        
        # Format citation text
        citation["formatted"] = self._format_citation(citation)
        
        return citation
    
    def _format_citation(self, citation: Dict[str, Any]) -> str:
        """Format citation as text string."""
        parts = [f"[{citation['index']}]"]
        
        if citation.get("title"):
            parts.append(citation["title"])
        
        if citation.get("page"):
            parts.append(f"(trang {citation['page']})")
        
        if citation.get("section"):
            parts.append(f"- {citation['section']}")
        
        return " ".join(parts)


class TopKPostprocessor(BaseNodePostprocessor):
    """
    Simple postprocessor to limit results to top K.
    
    Useful as the final postprocessor in a pipeline.
    """
    
    # Pydantic fields
    top_k: int = 10
    
    @classmethod
    def class_name(cls) -> str:
        return "TopKPostprocessor"
    
    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Return only top K nodes."""
        return nodes[:self.top_k]


# =============================================================================
# Pipeline Builder
# =============================================================================

class PostprocessorPipeline:
    """
    Chain multiple postprocessors together.
    
    Provides a fluent interface for building postprocessor pipelines.
    
    Example:
        pipeline = (
            PostprocessorPipeline()
            .add(DeduplicationPostprocessor())
            .add(CrossEncoderRerankPostprocessor(top_n=10))
            .add(ScoreThresholdPostprocessor(min_score=0.5))
            .build()
        )
        
        results = pipeline.process(nodes, query_bundle)
    """
    
    def __init__(self):
        """Initialize empty pipeline."""
        self._postprocessors: List[BaseNodePostprocessor] = []
    
    def add(self, postprocessor: BaseNodePostprocessor) -> "PostprocessorPipeline":
        """Add a postprocessor to the pipeline."""
        self._postprocessors.append(postprocessor)
        return self
    
    def build(self) -> "PostprocessorPipeline":
        """Finalize pipeline (returns self for chaining)."""
        return self
    
    def process(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Run all postprocessors in sequence."""
        result = nodes
        for pp in self._postprocessors:
            result = pp.postprocess_nodes(result, query_bundle)
        return result
    
    async def process_async(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        """Run all postprocessors in sequence (async where supported)."""
        result = nodes
        for pp in self._postprocessors:
            if hasattr(pp, 'postprocess_nodes_async'):
                result = await pp.postprocess_nodes_async(result, query_bundle)
            else:
                result = pp.postprocess_nodes(result, query_bundle)
        return result


# =============================================================================
# Factory Functions
# =============================================================================

def create_default_pipeline(
    reranking_service=None,
    enable_rerank: bool = True,
    top_k: int = 10,
    min_score: float = 0.0,
    dedup_method: str = "content_prefix"
) -> PostprocessorPipeline:
    """
    Create a default postprocessor pipeline.
    
    Default pipeline:
    1. Deduplication (content-based)
    2. Cross-encoder reranking (if enabled)
    3. Score threshold filter
    4. Top-K limiter
    5. Citation enrichment
    
    Args:
        reranking_service: Optional RerankingService for reranking
        enable_rerank: Whether to enable reranking
        top_k: Maximum results to return
        min_score: Minimum score threshold
        dedup_method: Deduplication method
        
    Returns:
        Configured PostprocessorPipeline
    """
    pipeline = PostprocessorPipeline()
    
    # 1. Deduplication
    pipeline.add(DeduplicationPostprocessor(
        method=dedup_method,
        keep_highest_score=True
    ))
    
    # 2. Reranking
    if enable_rerank:
        pipeline.add(CrossEncoderRerankPostprocessor(
            reranking_service=reranking_service,
            top_n=min(top_k * 2, 20)  # Rerank more than final top_k
        ))
    
    # 3. Score threshold
    if min_score > 0:
        pipeline.add(ScoreThresholdPostprocessor(min_score=min_score))
    
    # 4. Top-K limiter
    pipeline.add(TopKPostprocessor(top_k=top_k))
    
    # 5. Citation enrichment
    pipeline.add(CitationPostprocessor())
    
    return pipeline.build()


def create_metadata_filter_pipeline(
    doc_types: Optional[List[str]] = None,
    faculties: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    subjects: Optional[List[str]] = None,
    top_k: int = 10
) -> PostprocessorPipeline:
    """
    Create a pipeline with metadata filtering.
    
    Args:
        doc_types: Filter by document types
        faculties: Filter by faculties
        years: Filter by years
        subjects: Filter by subjects
        top_k: Maximum results
        
    Returns:
        Configured PostprocessorPipeline
    """
    pipeline = PostprocessorPipeline()
    
    # 1. Metadata filter
    pipeline.add(MetadataFilterPostprocessor(
        doc_types=doc_types,
        faculties=faculties,
        years=years,
        subjects=subjects
    ))
    
    # 2. Deduplication
    pipeline.add(DeduplicationPostprocessor())
    
    # 3. Top-K
    pipeline.add(TopKPostprocessor(top_k=top_k))
    
    # 4. Citations
    pipeline.add(CitationPostprocessor())
    
    return pipeline.build()
