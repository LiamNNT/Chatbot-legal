"""
OpenSearchKeywordAdapter - BM25 keyword search via OpenSearch.

Implements KeywordStorePort.
Ported from rag_services/adapters/opensearch_keyword_adapter.py.
"""

import logging
from typing import Any, Dict, List, Optional

from ...domain.rag_models import (
    CharacterSpan,
    DocumentChunk,
    DocumentLanguage,
    DocumentMetadata,
    SearchQuery,
    SearchResult,
)
from ...ports.keyword_store_port import KeywordStorePort

logger = logging.getLogger(__name__)


class OpenSearchKeywordAdapter(KeywordStorePort):
    """
    Adapter: OpenSearch BM25 keyword search.

    Wraps an OpenSearch client instance (from infrastructure/store/).
    """

    def __init__(self, opensearch_client: Any):
        self._client = opensearch_client

    # ── KeywordStorePort ─────────────────────────

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        try:
            params = self._build_params(query)
            raw_hits = self._client.search(**params) if hasattr(self._client, "search") else []

            results: List[SearchResult] = []
            for i, hit in enumerate(raw_hits):
                meta = self._to_metadata(hit)

                char_spans = None
                if query.include_char_spans and "char_spans" in hit:
                    char_spans = [
                        CharacterSpan(
                            start=s.get("start", 0),
                            end=s.get("end", 0),
                            text=s.get("text", ""),
                            type=s.get("type", "content"),
                        )
                        for s in hit["char_spans"]
                    ]

                results.append(
                    SearchResult(
                        text=hit.get("text", ""),
                        metadata=meta,
                        score=float(hit.get("bm25_score", 0.0)),
                        source_type="bm25",
                        rank=i + 1,
                        char_spans=char_spans,
                        highlighted_text=hit.get("highlighted_text"),
                        highlighted_title=hit.get("highlighted_title"),
                        bm25_score=float(hit.get("bm25_score", 0.0)),
                    )
                )
            return results

        except Exception as exc:
            logger.error("OpenSearch search failed: %s", exc)
            return []

    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        try:
            docs = [
                {
                    "doc_id": c.metadata.doc_id,
                    "chunk_id": c.metadata.chunk_id or "",
                    "text": c.text,
                    "title": c.metadata.title or "",
                    "page": c.metadata.page,
                    "doc_type": c.metadata.doc_type,
                    "faculty": c.metadata.faculty,
                    "year": c.metadata.year,
                    "subject": c.metadata.subject,
                    "language": c.metadata.language.value if c.metadata.language else "vi",
                    "section": c.metadata.section,
                    "subsection": c.metadata.subsection,
                    "chunk_index": c.chunk_index,
                    "metadata": c.metadata.extra,
                }
                for c in chunks
            ]
            if hasattr(self._client, "bulk_index"):
                return self._client.bulk_index(docs)
            logger.warning("OpenSearch client has no bulk_index method")
            return False
        except Exception as exc:
            logger.error("OpenSearch indexing failed: %s", exc)
            return False

    async def delete_by_doc_id(self, doc_id: str) -> bool:
        try:
            if hasattr(self._client, "delete_by_query"):
                return self._client.delete_by_query({"query": {"term": {"doc_id": doc_id}}})
            return False
        except Exception as exc:
            logger.error("OpenSearch delete failed: %s", exc)
            return False

    async def get_facets(self, query: SearchQuery) -> Dict[str, Any]:
        try:
            if hasattr(self._client, "aggregate"):
                return self._client.aggregate(
                    query=query.text,
                    aggs={
                        "doc_types": {"terms": {"field": "doc_type"}},
                        "faculties": {"terms": {"field": "faculty"}},
                        "years": {"terms": {"field": "year"}},
                    },
                )
            return {}
        except Exception as exc:
            logger.error("OpenSearch facets failed: %s", exc)
            return {}

    # ── Helpers ──────────────────────────────────

    @staticmethod
    def _build_params(query: SearchQuery) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "query": query.text,
            "size": query.top_k,
            "include_char_spans": query.include_char_spans,
            "language": (
                query.filters.language.value
                if query.filters and query.filters.language
                else "vi"
            ),
        }
        if query.filters:
            if query.filters.doc_types:
                params["doc_types"] = query.filters.doc_types
            if query.filters.faculties:
                params["faculties"] = query.filters.faculties
            if query.filters.years:
                params["years"] = query.filters.years
            if query.filters.subjects:
                params["subjects"] = query.filters.subjects
        return params

    @staticmethod
    def _to_metadata(hit: Dict[str, Any]) -> DocumentMetadata:
        lang = DocumentLanguage.ENGLISH if hit.get("language") == "en" else DocumentLanguage.VIETNAMESE
        return DocumentMetadata(
            doc_id=hit.get("doc_id", ""),
            chunk_id=hit.get("chunk_id"),
            title=hit.get("title"),
            page=hit.get("page"),
            doc_type=hit.get("doc_type"),
            faculty=hit.get("faculty"),
            year=hit.get("year"),
            subject=hit.get("subject"),
            language=lang,
            section=hit.get("section"),
            subsection=hit.get("subsection"),
            extra=hit.get("metadata", {}),
        )
