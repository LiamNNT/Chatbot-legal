# app/api/schemas/search.py
#
# Description:
# This file defines the Pydantic models for the core search functionality,
# including the search request, a single search result (hit), and the final search response.

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .common import SourceMeta, CitationSpan

class SearchRequest(BaseModel):
    """
    Defines the request body for the /search endpoint.
    """
    query: str
    top_k: int = 8
    filters: Optional[Dict[str, Any]] = None
    need_citation: bool = True
    use_rerank: bool = True

class SearchHit(BaseModel):
    """
    Defines the structure of a single search result item.
    """
    text: str
    score: float
    meta: SourceMeta
    citation: Optional[CitationSpan] = None
    rerank_score: Optional[float] = None

class SearchResponse(BaseModel):
    """
    Defines the final response structure for the /search endpoint.
    """
    hits: List[SearchHit]
    latency_ms: int