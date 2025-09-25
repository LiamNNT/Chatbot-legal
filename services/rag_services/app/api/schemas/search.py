from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from .common import SourceMeta, CitationSpan

class SearchRequest(BaseModel):
    query: str
    top_k: int = 8
    filters: Optional[Dict[str, Any]] = None
    need_citation: bool = True
    use_rerank: bool = True

class SearchHit(BaseModel):
    text: str
    score: float
    meta: SourceMeta
    citation: Optional[CitationSpan] = None
    rerank_score: Optional[float] = None

class SearchResponse(BaseModel):
    hits: List[SearchHit]
    latency_ms: int
