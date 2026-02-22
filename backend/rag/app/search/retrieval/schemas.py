# app/core/retrieval/schemas.py
"""
Data models for the unified retrieval layer.

These schemas define the contracts between components:
- LegalQuery: Parsed legal query with extracted metadata
- RetrievalResult: Final retrieval output with chunks and citations
- Citation: Standardized citation format for UI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """Intent classification for legal queries."""
    
    LOOKUP_EXACT = "lookup_exact"  # User wants specific Điều/Khoản/Điểm
    LOOKUP_ARTICLE = "lookup_article"  # User wants full article context
    SEMANTIC_QUESTION = "semantic_question"  # General question requiring semantic search
    COMPARISON = "comparison"  # Compare multiple articles/laws
    DEFINITION = "definition"  # Looking for term definitions


@dataclass
class LegalQuery:
    """
    Parsed legal query with extracted metadata.
    
    This is the output of LegalQueryParser.parse().
    
    Attributes:
        raw: Original query string
        law_id: Extracted law identifier (e.g., "20/2023/QH15")
        article_id: Article identifier (e.g., "11", "11a")
        clause_no: Clause number (e.g., "2")
        point_no: Point letter (e.g., "a", "đ")
        intent: Classified query intent
        keywords: Remaining keywords for semantic search
        normalized_query: Query with legal refs normalized
        confidence: Parser confidence score (0-1)
    """
    raw: str
    law_id: Optional[str] = None
    article_id: Optional[str] = None
    clause_no: Optional[str] = None
    point_no: Optional[str] = None
    intent: QueryIntent = QueryIntent.SEMANTIC_QUESTION
    keywords: List[str] = field(default_factory=list)
    normalized_query: str = ""
    confidence: float = 1.0
    
    def has_legal_reference(self) -> bool:
        """Check if query contains any legal reference."""
        return any([self.law_id, self.article_id, self.clause_no, self.point_no])
    
    def get_filter_dict(self) -> Dict[str, str]:
        """Get metadata filter dictionary for VectorDB queries."""
        filters = {}
        if self.law_id:
            filters["law_id"] = self.law_id
        if self.article_id:
            filters["article_id"] = f"Điều {self.article_id}"
        if self.clause_no:
            filters["clause_no"] = self.clause_no
        if self.point_no:
            filters["point_no"] = self.point_no
        return filters
    
    def to_citation_prefix(self) -> str:
        """Generate citation prefix from parsed references."""
        parts = []
        if self.point_no:
            parts.append(f"Điểm {self.point_no}")
        if self.clause_no:
            parts.append(f"Khoản {self.clause_no}")
        if self.article_id:
            parts.append(f"Điều {self.article_id}")
        if self.law_id:
            parts.append(f"Luật {self.law_id}")
        return " ".join(parts) if parts else ""


class Citation(BaseModel):
    """
    Standardized citation for UI display.
    
    Follows Vietnamese legal citation conventions:
    "Điểm a Khoản 2 Điều 11 Luật 20/2023/QH15"
    """
    
    law_id: Optional[str] = Field(None, description="Law identifier")
    law_name: Optional[str] = Field(None, description="Full law name")
    chapter: Optional[str] = Field(None, description="Chapter (Chương)")
    section: Optional[str] = Field(None, description="Section (Mục)")
    article_id: Optional[str] = Field(None, description="Article ID (Điều)")
    article_title: Optional[str] = Field(None, description="Article title")
    clause_no: Optional[str] = Field(None, description="Clause number (Khoản)")
    point_no: Optional[str] = Field(None, description="Point letter (Điểm)")
    
    # Source tracking
    chunk_id: str = Field(..., description="Source chunk ID")
    source_file: Optional[str] = Field(None, description="Source filename")
    
    def to_short_form(self) -> str:
        """Generate short citation string."""
        parts = []
        if self.point_no:
            parts.append(f"Điểm {self.point_no}")
        if self.clause_no:
            parts.append(f"Khoản {self.clause_no}")
        if self.article_id:
            parts.append(self.article_id if self.article_id.startswith("Điều") else f"Điều {self.article_id}")
        if self.law_id:
            parts.append(f"Luật {self.law_id}")
        return " ".join(parts) if parts else self.chunk_id
    
    def to_long_form(self) -> str:
        """Generate long citation with law name."""
        short = self.to_short_form()
        if self.law_name and self.law_id:
            return f"{short} ({self.law_name})"
        return short
    
    @classmethod
    def from_chunk_metadata(cls, chunk_id: str, metadata: Dict[str, Any]) -> "Citation":
        """Create Citation from chunk metadata."""
        return cls(
            law_id=metadata.get("law_id"),
            law_name=metadata.get("law_name"),
            chapter=metadata.get("chapter"),
            section=metadata.get("section"),
            article_id=metadata.get("article_id"),
            article_title=metadata.get("article_title"),
            clause_no=metadata.get("clause_no"),
            point_no=metadata.get("point_no"),
            chunk_id=chunk_id,
            source_file=metadata.get("source_file") or metadata.get("filename"),
        )


class NeighborContext(BaseModel):
    """Context from neighboring chunks (siblings/parent)."""
    
    parent_chunk: Optional["RetrievedChunk"] = Field(None, description="Parent chunk (e.g., Điều for Khoản)")
    prev_sibling: Optional["RetrievedChunk"] = Field(None, description="Previous sibling chunk")
    next_sibling: Optional["RetrievedChunk"] = Field(None, description="Next sibling chunk")
    
    def get_all_chunks(self) -> List["RetrievedChunk"]:
        """Get all neighbor chunks as list."""
        chunks = []
        if self.parent_chunk:
            chunks.append(self.parent_chunk)
        if self.prev_sibling:
            chunks.append(self.prev_sibling)
        if self.next_sibling:
            chunks.append(self.next_sibling)
        return chunks


class RetrievedChunk(BaseModel):
    """
    A single retrieved chunk with metadata and citation.
    
    This is the unified chunk format used throughout the retrieval layer.
    """
    
    # Core content
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    embedding_prefix: Optional[str] = Field(None, description="Embedding prefix for context")
    
    # Scoring
    score: float = Field(0.0, description="Retrieval score (0-1)")
    rerank_score: Optional[float] = Field(None, description="Reranker score if applied")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Full chunk metadata")
    
    # Citation
    citation: Optional[Citation] = Field(None, description="Standardized citation")
    
    # Relationships for expansion
    parent_id: Optional[str] = Field(None, description="Parent chunk ID")
    prev_sibling_id: Optional[str] = Field(None, description="Previous sibling chunk ID")
    next_sibling_id: Optional[str] = Field(None, description="Next sibling chunk ID")
    
    # Neighbor context (populated by NeighborExpander)
    neighbors: Optional[NeighborContext] = Field(None, description="Expanded neighbor context")
    
    # Source tracking
    retrieval_source: Literal["vector", "bm25", "hybrid", "filter", "neighbor"] = Field(
        "hybrid", description="How this chunk was retrieved"
    )
    
    def get_full_context(self, include_neighbors: bool = True) -> str:
        """
        Get full context including neighbors if available.
        
        Args:
            include_neighbors: Whether to include neighbor text
            
        Returns:
            Combined context string
        """
        parts = []
        
        if include_neighbors and self.neighbors:
            if self.neighbors.parent_chunk:
                parts.append(f"[Context từ {self.neighbors.parent_chunk.citation.to_short_form() if self.neighbors.parent_chunk.citation else 'parent'}]\n{self.neighbors.parent_chunk.content}")
            if self.neighbors.prev_sibling:
                parts.append(f"[Trước đó]\n{self.neighbors.prev_sibling.content}")
        
        # Main content
        parts.append(self.content)
        
        if include_neighbors and self.neighbors:
            if self.neighbors.next_sibling:
                parts.append(f"[Tiếp theo]\n{self.neighbors.next_sibling.content}")
        
        return "\n\n".join(parts)
    
    @classmethod
    def from_llama_node(cls, node, score: float = 0.0) -> "RetrievedChunk":
        """Create from LlamaIndex TextNode."""
        metadata = node.metadata if hasattr(node, 'metadata') else {}
        chunk_id = metadata.get("chunk_id") or node.node_id if hasattr(node, 'node_id') else str(id(node))
        
        return cls(
            chunk_id=chunk_id,
            content=node.text if hasattr(node, 'text') else str(node),
            embedding_prefix=metadata.get("embedding_prefix"),
            score=score,
            metadata=metadata,
            citation=Citation.from_chunk_metadata(chunk_id, metadata),
            parent_id=metadata.get("parent_id"),
            prev_sibling_id=metadata.get("prev_sibling_id"),
            next_sibling_id=metadata.get("next_sibling_id"),
        )


class RetrievalConfig(BaseModel):
    """Configuration for the unified retriever."""
    
    # Search parameters
    top_k: int = Field(5, description="Number of chunks to retrieve")
    vector_top_k: int = Field(20, description="Vector search pre-filter count")
    bm25_top_k: int = Field(20, description="BM25 search pre-filter count")
    
    # Fusion
    fusion_mode: Literal["rrf", "weighted", "simple"] = Field("rrf", description="Fusion algorithm")
    vector_weight: float = Field(0.5, description="Vector search weight (0-1)")
    bm25_weight: float = Field(0.5, description="BM25 search weight (0-1)")
    rrf_k: int = Field(60, description="RRF constant")
    
    # Reranking
    enable_rerank: bool = Field(True, description="Enable cross-encoder reranking")
    rerank_top_n: int = Field(10, description="Number of chunks to rerank")
    
    # Neighbor expansion
    enable_neighbor_expansion: bool = Field(True, description="Expand context with neighbors")
    include_parent: bool = Field(True, description="Include parent chunk")
    include_siblings: bool = Field(True, description="Include prev/next siblings")
    max_neighbor_tokens: int = Field(500, description="Max tokens from neighbors")
    
    # Filtering
    enable_metadata_filter: bool = Field(True, description="Use metadata filters from query")
    strict_filter: bool = Field(False, description="Require exact match for filters")
    
    # Citation
    generate_citations: bool = Field(True, description="Generate citations for chunks")
    
    @classmethod
    def for_exact_lookup(cls) -> "RetrievalConfig":
        """Config optimized for exact legal reference lookup."""
        return cls(
            top_k=3,
            enable_metadata_filter=True,
            strict_filter=True,
            enable_neighbor_expansion=True,
            enable_rerank=False,  # Exact match doesn't need reranking
        )
    
    @classmethod
    def for_semantic_search(cls) -> "RetrievalConfig":
        """Config optimized for semantic question answering."""
        return cls(
            top_k=5,
            vector_top_k=30,
            bm25_top_k=20,
            enable_metadata_filter=True,
            strict_filter=False,
            enable_neighbor_expansion=True,
            enable_rerank=True,
        )


class RetrievalResult(BaseModel):
    """
    Final result from the unified retriever.
    
    Contains:
    - Retrieved chunks with scores and citations
    - Combined context for LLM
    - All citations for UI
    - Debug/metrics info
    """
    
    # Retrieved chunks
    chunks: List[RetrievedChunk] = Field(default_factory=list, description="Retrieved chunks sorted by relevance")
    
    # Combined context
    final_context: str = Field("", description="Combined context string for LLM")
    
    # Citations
    citations: List[Citation] = Field(default_factory=list, description="All unique citations")
    
    # Query info
    parsed_query: Optional[LegalQuery] = Field(None, description="Parsed query details")
    
    # Metrics
    retrieval_time_ms: float = Field(0.0, description="Total retrieval time in milliseconds")
    chunks_before_rerank: int = Field(0, description="Chunks before reranking")
    chunks_after_filter: int = Field(0, description="Chunks after metadata filtering")
    neighbor_chunks_added: int = Field(0, description="Neighbor chunks added")
    
    # Debug info
    debug_info: Dict[str, Any] = Field(default_factory=dict, description="Debug information")
    
    def get_citation_list(self) -> List[str]:
        """Get list of citation strings for UI."""
        return [c.to_short_form() for c in self.citations]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "chunks": [chunk.model_dump() for chunk in self.chunks],
            "final_context": self.final_context,
            "citations": [c.model_dump() for c in self.citations],
            "citation_strings": self.get_citation_list(),
            "metrics": {
                "retrieval_time_ms": self.retrieval_time_ms,
                "chunks_retrieved": len(self.chunks),
                "chunks_before_rerank": self.chunks_before_rerank,
                "neighbor_chunks_added": self.neighbor_chunks_added,
            },
        }


# Update forward references
NeighborContext.model_rebuild()
RetrievedChunk.model_rebuild()
