import asyncio
import logging
import time
from typing import List, Optional


from ..domain.rag_models import (
    SearchMode,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from ..ports.fusion_port import FusionPort
from ..ports.keyword_store_port import KeywordStorePort
from ..ports.reranker_port import RerankerPort
from ..ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


class SearchUseCase:
    def __init__(self, vector_store: VectorStorePort,keyword_store: Optional[KeywordStorePort] = None,reranker: Optional[RerankerPort] = None, fusion: Optional[FusionPort] = None):
        self._vector = vector_store
        self._keyword = keyword_store
        self._reranker = reranker
        self._fusion = fusion

    async def execute(self, query: SearchQuery) -> SearchResponse:
        start = time.time()

        if query.search_mode == SearchMode.VECTOR:
            results = await self._vector_search(query)
        elif query.search_mode == SearchMode.BM25:
            results = await self._bm25_search(query)
        else:
            results = await self._hybrid_search(query)

        if (
            query.use_rerank
            and self._reranker
            and self._reranker.is_available()
        ):
            rerank_top = min(len(results), query.top_k * 2)
            results = await self._reranker.rerank(query.text, results, top_k=rerank_top)
            logger.info("Reranked %d results", len(results))

        results = results[: query.top_k]

        latency_ms = int((time.time() - start) * 1000)

        return SearchResponse(
            results=results,
            total_hits=len(results),
            latency_ms=latency_ms,
            search_metadata={
                "search_mode": query.search_mode.value,
                "use_rerank": query.use_rerank,
                "has_filters": query.filters is not None,
            },
        )

    async def _vector_search(self, query: SearchQuery) -> List[SearchResult]:
        expanded = _expand_query(query, factor=4, min_k=16)
        results = await self._vector.search(expanded)
        for r in results:
            r.source_type = "vector"
        return results

    async def _bm25_search(self, query: SearchQuery) -> List[SearchResult]:
        if not self._keyword:
            raise SearchError("BM25 search unavailable — no keyword store configured")

        expanded = _expand_query(query, factor=2, min_k=12)
        results = await self._keyword.search(expanded)
        for r in results:
            r.source_type = "bm25"
        return results

    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        if not self._keyword:
            logger.warning("Hybrid requested but no keyword store — falling back to vector")
            return await self._vector_search(query)

        if not self._fusion:
            raise SearchError("Hybrid search unavailable — no fusion service configured")

        candidate_k = max(query.top_k * 4, 20)

        vec_q = SearchQuery(
            text=query.text,
            top_k=candidate_k,
            search_mode=SearchMode.VECTOR,
            filters=query.filters,
            include_char_spans=query.include_char_spans,
        )
        bm25_q = SearchQuery(
            text=query.text,
            top_k=candidate_k,
            search_mode=SearchMode.BM25,
            filters=query.filters,
            include_char_spans=query.include_char_spans,
        )

        vec_results, kw_results = await asyncio.gather(
            self._vector.search(vec_q),
            self._keyword.search(bm25_q),
        )

        for r in vec_results:
            r.source_type = "vector"
        for r in kw_results:
            r.source_type = "bm25"

        v_weight = query.vector_weight or 0.5
        k_weight = query.bm25_weight or 0.5

        fused = await self._fusion.fuse(
            vector_results=vec_results,
            keyword_results=kw_results,
            vector_weight=v_weight,
            keyword_weight=k_weight,
        )
        for r in fused:
            r.source_type = "fused"

        logger.info(
            "Hybrid: %d vector + %d bm25 → %d fused",
            len(vec_results),
            len(kw_results),
            len(fused),
        )
        return fused



def _expand_query(query: SearchQuery, *, factor: int, min_k: int) -> SearchQuery:
    return SearchQuery(
        text=query.text,
        top_k=max(query.top_k * factor, min_k),
        search_mode=query.search_mode,
        filters=query.filters,
        include_char_spans=query.include_char_spans,
        highlight_matches=query.highlight_matches,
    )


class SearchError(Exception):