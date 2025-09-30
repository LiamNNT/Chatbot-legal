# app/api/v1/routes/search.py
#
# Description:
# This module implements the core search endpoint for the RAG service.
# It handles search requests, delegates them to the retrieval engine,
# and returns the search results along with performance latency.

import time
from fastapi import APIRouter
from app.api.schemas.search import SearchRequest, SearchResponse
from app.config.settings import settings
from retrieval.engine import get_query_engine # The core search logic is in the retrieval engine

# Create an API router for the search functionality
router = APIRouter(tags=["search"])

@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Endpoint to perform a search query against the indexed documents.
    Supports vector, BM25, and hybrid search modes.

    Args:
        req (SearchRequest): The search request containing the query and other parameters.

    Returns:
        SearchResponse: A list of search hits, latency, and search metadata.
    """
    t0 = time.time()
    
    # Get the singleton instance of the query engine
    engine = get_query_engine()
    
    # Perform the search
    hits = engine.search(req)
    
    # Calculate latency
    latency = int((time.time() - t0) * 1000)
    
    # Prepare search metadata
    search_metadata = {
        "search_mode": req.search_mode or "hybrid",
        "use_rerank": req.use_rerank,
        "use_hybrid": req.use_hybrid,
        "total_results": len(hits),
        "latency_ms": latency
    }
    
    # Add weight information if applicable
    if req.search_mode == "hybrid":
        search_metadata["bm25_weight"] = req.bm25_weight or settings.bm25_weight
        search_metadata["vector_weight"] = req.vector_weight or settings.vector_weight
        search_metadata["rrf_constant"] = settings.rrf_rank_constant
    
    return SearchResponse(
        hits=hits, 
        latency_ms=latency,
        search_metadata=search_metadata
    )