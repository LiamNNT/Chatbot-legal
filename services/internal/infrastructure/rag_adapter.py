import logging
from typing import Any, Dict, List, Optional

from ..domain.entities import RAGContext
from ..domain.exceptions import RAGRetrievalError
from ..domain.rag_models import (
    DocumentLanguage,
    SearchFilters,
    SearchMode,
    SearchQuery,
    SearchResponse,
)
from ..ports.rag_port import RAGServicePort
from ..use_cases.search_use_case import SearchUseCase

logger = logging.getLogger(__name__)

_MODE_MAP = {
    "hybrid": SearchMode.HYBRID,
    "vector": SearchMode.VECTOR,
    "bm25": SearchMode.BM25,
}


class LocalRAGAdapter(RAGServicePort):
    def __init__(self, search_use_case: SearchUseCase):
        self._search = search_use_case

    async def retrieve(self, query: str, top_k: int = 5, search_mode: str = "hybrid", use_rerank: bool = True, filters: Optional[Dict[str, Any]] = None) -> RAGContext:
        try:
            sq = self._build_search_query(query, top_k, search_mode, use_rerank, filters)
            response: SearchResponse = await self._search.execute(sq)
            return self._to_rag_context(query, response, search_mode, top_k, filters)

        except Exception as exc:
            logger.error("Local RAG search failed: %s", exc)
            raise RAGRetrievalError(
                f"Search pipeline error: {exc}",
                cause=exc,
            ) from exc

    async def health_check(self) -> bool:
        return True

    @staticmethod
    def _build_search_query(query: str, top_k: int, search_mode: str, use_rerank: bool, filters: Optional[Dict[str, Any]]) -> SearchQuery:
        mode = _MODE_MAP.get(search_mode, SearchMode.HYBRID)

        sf: Optional[SearchFilters] = None
        if filters:
            lang = None
            raw_lang = filters.get("language")
            if raw_lang == "en":
                lang = DocumentLanguage.ENGLISH
            elif raw_lang:
                lang = DocumentLanguage.VIETNAMESE

            sf = SearchFilters(
                doc_types=filters.get("doc_types"),
                faculties=filters.get("faculties"),
                years=filters.get("years"),
                subjects=filters.get("subjects"),
                language=lang,
            )

        return SearchQuery(
            text=query,
            top_k=top_k,
            search_mode=mode,
            use_rerank=use_rerank,
            filters=sf,
            include_char_spans=True,
            highlight_matches=True,
        )

    @staticmethod
    def _to_rag_context(query: str, resp: SearchResponse, search_mode: str, top_k: int, filters: Optional[Dict[str, Any]]) -> RAGContext:
        documents: List[Dict[str, Any]] = []
        scores: List[float] = []

        for r in resp.results:
            doc: Dict[str, Any] = {
                "text": r.text,
                "title": r.metadata.title or "",
                "score": r.score,
                "meta": r.metadata.extra or {},
                "rerank_score": r.rerank_score,
                "doc_type": r.metadata.doc_type,
                "faculty": r.metadata.faculty,
                "year": r.metadata.year,
            }

            if r.char_spans:
                doc["char_spans"] = [
                    {
                        "start": s.start,
                        "end": s.end,
                        "text": s.text,
                        "type": s.type,
                    }
                    for s in r.char_spans
                ]
            if r.highlighted_text:
                doc["highlighted_text"] = r.highlighted_text

            documents.append(doc)
            scores.append(r.score)

        return RAGContext(
            query=query,
            retrieved_documents=documents,
            search_metadata={
                "total_results": resp.total_hits,
                "search_mode": search_mode,
                "processing_time": resp.latency_ms,
                "top_k": top_k,
                "filters_applied": filters,
            },
            relevance_scores=scores,
        )
