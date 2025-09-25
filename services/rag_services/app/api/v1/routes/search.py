import time
from fastapi import APIRouter
from app.api.schemas.search import SearchRequest, SearchResponse
from retrieval.engine import get_query_engine

router = APIRouter(tags=["search"])

@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    t0 = time.time()
    engine = get_query_engine()
    hits = engine.search(req)
    latency = int((time.time() - t0) * 1000)
    return SearchResponse(hits=hits, latency_ms=latency)
