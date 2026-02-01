# app/api/schemas/retrieval.py
#
# Description:
# Pydantic schemas for the Legal Retrieval API endpoints.
# These schemas provide the request/response models for the unified retrieval layer.

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class QueryIntentType(str, Enum):
    """Query intent types for legal search."""
    LOOKUP_EXACT = "LOOKUP_EXACT"        # Exact reference: Điều 5, Khoản 2
    LOOKUP_ARTICLE = "LOOKUP_ARTICLE"    # Article-level: Điều 5
    SEMANTIC_QUESTION = "SEMANTIC_QUESTION"  # General question
    DEFINITION = "DEFINITION"            # Asking for definition
    COMPARISON = "COMPARISON"            # Comparing laws/articles


class LegalReferenceDTO(BaseModel):
    """A parsed legal reference from the query."""
    law_id: Optional[str] = Field(None, description="Law identifier, e.g., '20/2023/QH15'")
    article_id: Optional[int] = Field(None, description="Article number (Điều)")
    clause_no: Optional[int] = Field(None, description="Clause number (Khoản)")
    point_no: Optional[str] = Field(None, description="Point identifier (Điểm), e.g., 'a', 'b'")
    chapter: Optional[str] = Field(None, description="Chapter number (Chương)")
    section: Optional[str] = Field(None, description="Section number (Mục)")


class ParsedQueryDTO(BaseModel):
    """The parsed query information."""
    original_query: str = Field(..., description="The original query text")
    normalized_query: str = Field(..., description="Cleaned/normalized query")
    intent: QueryIntentType = Field(..., description="Detected query intent")
    references: List[LegalReferenceDTO] = Field(default_factory=list, description="Extracted legal references")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Parse confidence score")


class RetrievedChunkDTO(BaseModel):
    """A retrieved document chunk with metadata."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="The chunk text content")
    score: float = Field(..., description="Retrieval score")
    source_type: str = Field("hybrid", description="Source: 'vector', 'bm25', 'hybrid'")
    
    # Legal metadata
    law_id: Optional[str] = None
    article_id: Optional[int] = None
    clause_no: Optional[int] = None
    point_no: Optional[str] = None
    chapter: Optional[str] = None
    section: Optional[str] = None
    
    # Neighbor relationships
    parent_id: Optional[str] = None
    prev_sibling_id: Optional[str] = None
    next_sibling_id: Optional[str] = None
    
    # Additional metadata
    extra_metadata: Optional[Dict[str, Any]] = None
    
    # Expansion info
    is_expanded: bool = Field(False, description="Whether this was added via neighbor expansion")
    expansion_type: Optional[str] = Field(None, description="'parent', 'prev', 'next' if expanded")


class CitationDTO(BaseModel):
    """A citation for a retrieved chunk."""
    chunk_id: str = Field(..., description="Referenced chunk ID")
    citation_text: str = Field(..., description="Human-readable citation, e.g., 'Điều 5, Khoản 2, Luật 20/2023/QH15'")
    law_id: Optional[str] = None
    article_id: Optional[int] = None
    clause_no: Optional[int] = None
    point_no: Optional[str] = None


class RetrievalMetricsDTO(BaseModel):
    """Metrics from the retrieval process."""
    parse_time_ms: float = Field(0.0, description="Query parsing time")
    retrieval_time_ms: float = Field(0.0, description="Core retrieval time")
    expansion_time_ms: float = Field(0.0, description="Neighbor expansion time")
    total_time_ms: float = Field(0.0, description="Total processing time")
    
    vector_hits: int = Field(0, description="Number of vector search results")
    bm25_hits: int = Field(0, description="Number of BM25 results")
    fused_hits: int = Field(0, description="Number of results after fusion")
    expanded_hits: int = Field(0, description="Number of expanded neighbors added")


# ============================================================================
# Request/Response Models
# ============================================================================

class LegalRetrievalRequest(BaseModel):
    """Request body for the legal retrieval endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="The search query")
    top_k: int = Field(8, ge=1, le=50, description="Number of top results to return")
    
    # Search modes
    search_mode: str = Field("hybrid", pattern="^(vector|bm25|hybrid)$", description="Search mode")
    
    # Hybrid search weights (for RRF)
    vector_weight: float = Field(0.6, ge=0.0, le=1.0, description="Weight for vector search in fusion")
    bm25_weight: float = Field(0.4, ge=0.0, le=1.0, description="Weight for BM25 in fusion")
    
    # Neighbor expansion
    expand_neighbors: bool = Field(True, description="Whether to expand with neighbor chunks")
    max_neighbor_tokens: int = Field(1500, ge=0, le=8000, description="Max tokens for neighbor expansion")
    
    # Filtering
    law_ids: Optional[List[str]] = Field(None, description="Filter by specific law IDs")
    filter_mode: str = Field("fuzzy", pattern="^(strict|fuzzy)$", description="Filter matching mode")
    
    # Additional options
    include_parse_details: bool = Field(False, description="Include parsed query details in response")
    include_metrics: bool = Field(False, description="Include timing metrics in response")


class LegalRetrievalResponse(BaseModel):
    """Response from the legal retrieval endpoint."""
    success: bool = Field(True, description="Whether the request succeeded")
    
    # Main results
    chunks: List[RetrievedChunkDTO] = Field(default_factory=list, description="Retrieved chunks")
    citations: List[CitationDTO] = Field(default_factory=list, description="Generated citations")
    
    # Combined context for LLM
    combined_context: str = Field("", description="All chunk texts combined, ready for LLM")
    
    # Summary
    total_chunks: int = Field(0, description="Total number of chunks returned")
    
    # Optional details
    parsed_query: Optional[ParsedQueryDTO] = Field(None, description="Parsed query details (if requested)")
    metrics: Optional[RetrievalMetricsDTO] = Field(None, description="Timing metrics (if requested)")
    
    # Error info
    error_message: Optional[str] = Field(None, description="Error message if success=False")


class QueryParseRequest(BaseModel):
    """Request to parse a query without retrieval."""
    query: str = Field(..., min_length=1, max_length=2000, description="The query to parse")


class QueryParseResponse(BaseModel):
    """Response with parsed query information."""
    success: bool = True
    parsed_query: ParsedQueryDTO


class BatchRetrievalRequest(BaseModel):
    """Batch retrieval request for multiple queries."""
    queries: List[str] = Field(..., min_items=1, max_items=10, description="List of queries")
    top_k: int = Field(5, ge=1, le=20, description="Results per query")
    search_mode: str = Field("hybrid", pattern="^(vector|bm25|hybrid)$")
    expand_neighbors: bool = Field(True)


class BatchRetrievalResponse(BaseModel):
    """Response for batch retrieval."""
    success: bool = True
    results: List[LegalRetrievalResponse] = Field(default_factory=list)
    total_time_ms: float = 0.0
