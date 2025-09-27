# app/api/v1/routes/search.py
#
# Description:
# This module implements the core search endpoint for the RAG service.
# It handles search requests, delegates them to the retrieval engine,
# and returns the search results along with performance latency.

import time
from fastapi import APIRouter
from app.api.schemas.search import SearchRequest, SearchResponse
from retrieval.engine import get_query_engine # The core search logic is in the retrieval engine

# Create an API router for the search functionality
router = APIRouter(tags=["search"])

@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """
    Endpoint to perform a search query against the indexed documents.

    Args:
        req (SearchRequest): The search request containing the query and other parameters.

    Returns:
        SearchResponse: A list of search hits and the request latency in milliseconds.
    """
    t0 = time.time()
    
    # Get the singleton instance of the query engine
    engine = get_query_engine()
    
    # Perform the search
    hits = engine.search(req)
    
    # Calculate latency
    latency = int((time.time() - t0) * 1000)
    
    return SearchResponse(hits=hits, latency_ms=latency)