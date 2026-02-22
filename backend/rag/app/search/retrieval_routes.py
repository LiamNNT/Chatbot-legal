# app/api/v1/routes/retrieval.py
#
# Description:
# This module implements the Legal Retrieval API endpoints.
# It provides a unified interface for querying Vietnamese legal documents
# using the LegalQueryParser with:
#   - Query parsing (Điều/Khoản/Điểm + law_id extraction)
#   - Intent classification
#
# Note: This endpoint focuses on query parsing. For full retrieval with
# vector/BM25 search, see the UnifiedRetriever class which requires
# database adapters to be injected.

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
import time

from app.search.retrieval_schemas import (
    LegalRetrievalRequest,
    LegalRetrievalResponse,
    QueryParseRequest,
    QueryParseResponse,
    BatchRetrievalRequest,
    BatchRetrievalResponse,
    ParsedQueryDTO,
    LegalReferenceDTO,
    RetrievedChunkDTO,
    CitationDTO,
    RetrievalMetricsDTO,
    QueryIntentType,
)
from app.search.retrieval import (
    LegalQueryParser,
    UnifiedRetriever,
    RetrievalConfig,
    LegalQuery,
    RetrievalResult,
    RetrievedChunk,
    Citation,
    QueryIntent,
)

# Create router
router = APIRouter(prefix="/retrieval", tags=["Legal Retrieval"])
logger = logging.getLogger(__name__)

# Singleton instances (lazy initialization)
_parser: Optional[LegalQueryParser] = None


def get_parser() -> LegalQueryParser:
    """Get or create the query parser singleton."""
    global _parser
    if _parser is None:
        _parser = LegalQueryParser()
    return _parser


# ============================================================================
# Converter Functions (Internal -> API DTOs)
# ============================================================================

def _convert_legal_query_to_dto(lq: LegalQuery) -> ParsedQueryDTO:
    """Convert internal LegalQuery to API DTO."""
    # Build a single reference from the flat LegalQuery fields
    ref = LegalReferenceDTO(
        law_id=lq.law_id,
        article_id=int(lq.article_id) if lq.article_id and lq.article_id.isdigit() else None,
        clause_no=int(lq.clause_no) if lq.clause_no and lq.clause_no.isdigit() else None,
        point_no=lq.point_no,
    )
    
    # Only include reference if it has any data
    refs = [ref] if lq.has_legal_reference() else []
    
    # Map internal intent enum to API enum
    intent_map = {
        QueryIntent.LOOKUP_EXACT: QueryIntentType.LOOKUP_EXACT,
        QueryIntent.LOOKUP_ARTICLE: QueryIntentType.LOOKUP_ARTICLE,
        QueryIntent.SEMANTIC_QUESTION: QueryIntentType.SEMANTIC_QUESTION,
        QueryIntent.DEFINITION: QueryIntentType.DEFINITION,
        QueryIntent.COMPARISON: QueryIntentType.COMPARISON,
    }
    
    return ParsedQueryDTO(
        original_query=lq.raw,
        normalized_query=lq.normalized_query,
        intent=intent_map.get(lq.intent, QueryIntentType.SEMANTIC_QUESTION),
        references=refs,
        keywords=lq.keywords,
        confidence=lq.confidence,
    )


def _convert_chunk_to_dto(chunk: RetrievedChunk) -> RetrievedChunkDTO:
    """Convert internal RetrievedChunk to API DTO."""
    metadata = chunk.metadata or {}
    
    return RetrievedChunkDTO(
        chunk_id=chunk.chunk_id,
        text=chunk.content,  # Internal uses 'content', API uses 'text'
        score=chunk.score,
        source_type=chunk.retrieval_source,  # Internal uses 'retrieval_source'
        law_id=metadata.get("law_id"),
        article_id=int(metadata.get("article_id")) if metadata.get("article_id") and str(metadata.get("article_id")).isdigit() else None,
        clause_no=int(metadata.get("clause_no")) if metadata.get("clause_no") and str(metadata.get("clause_no")).isdigit() else None,
        point_no=metadata.get("point_no"),
        chapter=metadata.get("chapter"),
        section=metadata.get("section"),
        parent_id=chunk.parent_id,
        prev_sibling_id=chunk.prev_sibling_id,
        next_sibling_id=chunk.next_sibling_id,
        extra_metadata={k: v for k, v in metadata.items() if k not in ["law_id", "article_id", "clause_no", "point_no", "chapter", "section"]},
        is_expanded=chunk.retrieval_source == "neighbor",
        expansion_type=None,  # Could be set if we track expansion type
    )


def _convert_citation_to_dto(cit: Citation) -> CitationDTO:
    """Convert internal Citation to API DTO."""
    return CitationDTO(
        chunk_id=cit.chunk_id,
        citation_text=cit.to_short_form(),
        law_id=cit.law_id,
        article_id=int(cit.article_id) if cit.article_id and str(cit.article_id).replace("Điều ", "").isdigit() else None,
        clause_no=int(cit.clause_no) if cit.clause_no and str(cit.clause_no).isdigit() else None,
        point_no=cit.point_no,
    )


def _convert_retrieval_result_to_response(
    result: RetrievalResult,
    include_parse_details: bool = False,
    include_metrics: bool = False,
) -> LegalRetrievalResponse:
    """Convert internal RetrievalResult to API response."""
    
    # Convert chunks
    chunks = [_convert_chunk_to_dto(chunk) for chunk in result.chunks]
    
    # Convert citations
    citations = [_convert_citation_to_dto(cit) for cit in result.citations]
    
    # Build response
    response = LegalRetrievalResponse(
        success=True,
        chunks=chunks,
        citations=citations,
        combined_context=result.final_context,  # Internal uses 'final_context'
        total_chunks=len(chunks),
    )
    
    # Optional: parsed query details
    if include_parse_details and result.parsed_query:
        response.parsed_query = _convert_legal_query_to_dto(result.parsed_query)
    
    # Optional: metrics
    if include_metrics:
        response.metrics = RetrievalMetricsDTO(
            parse_time_ms=0.0,  # Not tracked separately
            retrieval_time_ms=result.retrieval_time_ms,
            expansion_time_ms=0.0,  # Not tracked separately
            total_time_ms=result.retrieval_time_ms,
            vector_hits=result.chunks_before_rerank,
            bm25_hits=0,  # Not tracked separately
            fused_hits=result.chunks_after_filter,
            expanded_hits=result.neighbor_chunks_added,
        )
    
    return response


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/search", response_model=LegalRetrievalResponse)
async def legal_search(request: LegalRetrievalRequest) -> LegalRetrievalResponse:
    """
    Unified legal document retrieval endpoint.
    
    This endpoint:
    1. Parses the query to extract legal references (Điều/Khoản/Điểm, law_id)
    2. Builds metadata filters for precise matching
    3. Performs hybrid search (vector + BM25 with RRF fusion)
    4. Expands context with neighboring chunks (parent/siblings)
    5. Generates citations for each retrieved chunk
    
    **Example queries:**
    - "Điều 5 Luật 20/2023/QH15" → LOOKUP_EXACT intent, metadata filter
    - "Quy định về giờ làm việc" → SEMANTIC_QUESTION, vector search
    - "Thế nào là tai nạn lao động?" → DEFINITION intent
    
    **Response includes:**
    - `chunks`: Retrieved document chunks with metadata
    - `citations`: Human-readable citations for each chunk
    - `combined_context`: All texts combined, ready for LLM
    
    **Note:** Full retrieval requires database adapters. Without them,
    this endpoint returns an error. Use /parse for query parsing only.
    """
    try:
        # For now, we don't have adapters injected, so we need to return an error
        # In production, you would create the retriever with real adapters:
        # retriever = UnifiedRetriever.from_adapters(vector_adapter, keyword_adapter)
        
        return LegalRetrievalResponse(
            success=False,
            error_message="Retrieval service not configured. Database adapters are required. Use /parse endpoint for query parsing.",
        )
        
    except Exception as e:
        logger.exception(f"Legal search failed: {e}")
        return LegalRetrievalResponse(
            success=False,
            error_message=str(e),
        )


@router.post("/parse", response_model=QueryParseResponse)
async def parse_query(request: QueryParseRequest) -> QueryParseResponse:
    """
    Parse a legal query without performing retrieval.
    
    Useful for:
    - Understanding how the system interprets a query
    - Debugging query parsing issues
    - Pre-validating queries before search
    
    **Extracts:**
    - Legal references (law_id, Điều, Khoản, Điểm)
    - Query intent (LOOKUP_EXACT, SEMANTIC_QUESTION, DEFINITION, etc.)
    - Keywords for search
    """
    try:
        parser = get_parser()
        parsed = parser.parse(request.query)
        
        return QueryParseResponse(
            success=True,
            parsed_query=_convert_legal_query_to_dto(parsed),
        )
        
    except Exception as e:
        logger.exception(f"Query parse failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query parsing failed: {str(e)}",
        )


@router.post("/batch", response_model=BatchRetrievalResponse)
async def batch_retrieval(request: BatchRetrievalRequest) -> BatchRetrievalResponse:
    """
    Batch retrieval for multiple queries.
    
    Process multiple queries in a single request.
    Useful for:
    - Pre-fetching related information
    - Comparative analysis across multiple queries
    - Bulk operations
    
    **Limits:**
    - Max 10 queries per batch
    - Max 20 results per query
    
    **Note:** Full retrieval requires database adapters.
    """
    start_time = time.time()
    
    try:
        # Without adapters, return error responses
        results = []
        for query in request.queries:
            results.append(LegalRetrievalResponse(
                success=False,
                error_message="Retrieval service not configured. Database adapters are required.",
            ))
        
        total_time = (time.time() - start_time) * 1000
        
        return BatchRetrievalResponse(
            success=True,
            results=results,
            total_time_ms=total_time,
        )
        
    except Exception as e:
        logger.exception(f"Batch retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch retrieval failed: {str(e)}",
        )


@router.get("/health")
async def retrieval_health():
    """
    Health check for the retrieval service.
    
    Verifies:
    - Query parser is functional
    - Basic parsing works
    """
    try:
        parser = get_parser()
        
        # Quick parse test
        test_result = parser.parse("Điều 1")
        
        return {
            "status": "healthy",
            "parser": "ok",
            "retriever": "ok",  # Parser-only for now
            "test_parse": {
                "query": "Điều 1",
                "intent": test_result.intent.value,
                "has_references": test_result.has_legal_reference(),
            }
        }
        
    except Exception as e:
        logger.error(f"Retrieval health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Retrieval service unhealthy: {str(e)}",
        )
