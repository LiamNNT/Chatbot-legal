"""
WeaviateVectorAdapter - Vector search via Weaviate.

Implements VectorStorePort.
Ported from rag_services/adapters/weaviate_vector_adapter.py.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ...domain.rag_models import (
    DocumentChunk,
    DocumentLanguage,
    DocumentMetadata,
    SearchQuery,
    SearchResult,
)
from ...ports.embedding_port import EmbeddingPort
from ...ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


class WeaviateVectorAdapter(VectorStorePort):
    """
    Adapter: Weaviate v4 vector search.

    Requires a running Weaviate instance and an EmbeddingPort for vectorisation.
    """

    def __init__(
        self,
        weaviate_url: str,
        embedding: EmbeddingPort,
        collection_name: str = "VietnameseDocumentV3",
        api_key: Optional[str] = None,
    ):
        import weaviate

        self._embedding = embedding
        self._collection_name = collection_name

        # Connect
        if api_key:
            self._client = weaviate.connect_to_local(
                host=weaviate_url.replace("http://", "").split(":")[0],
                port=int(weaviate_url.split(":")[-1]) if ":" in weaviate_url.split("//")[-1] else 8090,
                auth_credentials=weaviate.auth.AuthApiKey(api_key),
            )
        else:
            self._client = weaviate.connect_to_local(
                host=weaviate_url.replace("http://", "").split(":")[0],
                port=int(weaviate_url.split(":")[-1]) if ":" in weaviate_url.split("//")[-1] else 8090,
            )

        # Ensure collection
        if not self._client.collections.exists(collection_name):
            logger.warning("Collection '%s' does not exist — creating", collection_name)
            self._client.collections.create(collection_name)

        self._collection = self._client.collections.get(collection_name)
        logger.info("WeaviateVectorAdapter initialised on %s/%s", weaviate_url, collection_name)

    # ── VectorStorePort ──────────────────────────

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        try:
            from weaviate.classes.query import MetadataQuery

            query_vector = self._embedding.embed_text(query.text)

            return_props = [
                "text", "doc_id", "chunk_id", "chunk_index", "title",
                "page", "doc_type", "faculty", "year", "subject",
                "section", "subsection", "language", "structure_type",
                "chapter", "article", "article_number", "filename",
                "metadata_json",
            ]

            response = self._collection.query.near_vector(
                near_vector=query_vector,
                limit=query.top_k,
                return_metadata=MetadataQuery(distance=True, score=True),
                return_properties=return_props,
            )

            results: List[SearchResult] = []
            for obj in response.objects:
                sr = self._to_search_result(obj, rank=len(results) + 1)
                if query.filters and not self._matches(obj, query.filters):
                    continue
                results.append(sr)
                if len(results) >= query.top_k:
                    break

            logger.info("Weaviate vector search returned %d results", len(results))
            return results

        except Exception as exc:
            logger.error("Weaviate search failed: %s", exc)
            return []

    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        try:
            with self._collection.batch.dynamic() as batch:
                for chunk in chunks:
                    vector = (
                        chunk.embedding
                        if chunk.embedding is not None
                        else self._embedding.embed_text(chunk.text)
                    )
                    props = self._to_weaviate_props(chunk)
                    batch.add_object(properties=props, vector=vector)

            logger.info("Indexed %d chunks in Weaviate", len(chunks))
            return True
        except Exception as exc:
            logger.error("Weaviate indexing failed: %s", exc)
            return False

    async def delete_by_doc_id(self, doc_id: str) -> bool:
        try:
            from weaviate.classes.query import Filter

            self._collection.data.delete_many(
                where=Filter.by_property("doc_id").equal(doc_id)
            )
            logger.info("Deleted vectors for doc_id=%s", doc_id)
            return True
        except Exception as exc:
            logger.error("Weaviate delete failed: %s", exc)
            return False

    # ── Helpers ──────────────────────────────────

    @staticmethod
    def _to_weaviate_props(chunk: DocumentChunk) -> Dict[str, Any]:
        extra_json = json.dumps(chunk.metadata.extra) if chunk.metadata.extra else "{}"
        extra = chunk.metadata.extra or {}
        return {
            "text": chunk.text,
            "doc_id": chunk.metadata.doc_id,
            "chunk_id": chunk.metadata.chunk_id or f"{chunk.metadata.doc_id}_{chunk.chunk_index}",
            "chunk_index": chunk.chunk_index,
            "title": chunk.metadata.title or "",
            "page": chunk.metadata.page or 0,
            "doc_type": chunk.metadata.doc_type or "",
            "faculty": chunk.metadata.faculty or "",
            "year": chunk.metadata.year or 0,
            "subject": chunk.metadata.subject or "",
            "section": chunk.metadata.section or "",
            "subsection": chunk.metadata.subsection or "",
            "language": chunk.metadata.language.value if chunk.metadata.language else "vi",
            "chapter": extra.get("chapter"),
            "article": extra.get("article"),
            "article_number": extra.get("article_number"),
            "structure_type": extra.get("structure_type"),
            "filename": extra.get("filename"),
            "metadata_json": extra_json,
        }

    @staticmethod
    def _to_search_result(obj: Any, rank: int) -> SearchResult:
        props = obj.properties
        extra: Dict[str, Any] = {}
        if props.get("metadata_json"):
            try:
                extra = json.loads(props["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        metadata = DocumentMetadata(
            doc_id=props.get("doc_id", "unknown"),
            chunk_id=props.get("chunk_id", ""),
            title=props.get("title"),
            page=props.get("page"),
            doc_type=props.get("doc_type"),
            faculty=props.get("faculty"),
            year=props.get("year"),
            subject=props.get("subject"),
            section=props.get("section"),
            subsection=props.get("subsection"),
            language=DocumentLanguage(props.get("language", "vi")),
            extra=extra,
        )

        score = 0.0
        if hasattr(obj.metadata, "score") and obj.metadata.score is not None:
            score = float(obj.metadata.score)
        elif hasattr(obj.metadata, "distance") and obj.metadata.distance is not None:
            score = 1.0 - float(obj.metadata.distance)

        return SearchResult(
            text=props.get("text", ""),
            metadata=metadata,
            score=score,
            source_type="vector",
            rank=rank,
            vector_score=score,
        )

    @staticmethod
    def _matches(obj: Any, filters) -> bool:
        props = obj.properties
        if filters.doc_types and props.get("doc_type") not in filters.doc_types:
            return False
        if filters.faculties and props.get("faculty") not in filters.faculties:
            return False
        if filters.years and props.get("year") not in filters.years:
            return False
        if filters.subjects and props.get("subject") not in filters.subjects:
            return False
        return True

    def close(self) -> None:
        if self._client:
            self._client.close()
