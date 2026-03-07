# adapters/qdrant_vector_adapter.py
#
# Description:
# Qdrant adapter implementation for vector search operations.
# This adapter provides a clean, efficient interface to Qdrant vector database
# following the Ports & Adapters architecture.

import logging
import json
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SearchParams,
    HnswConfigDiff,
)

from app.search.ports.repositories import VectorSearchRepository
from shared.domain.rag_models import (
    DocumentChunk,
    SearchQuery,
    SearchResult,
    DocumentMetadata,
    DocumentLanguage,
)
from app.ingest.store.vector.qdrant_store import (
    get_qdrant_client,
    ensure_collection_exists,
    get_collection_name,
    DOCUMENT_COLLECTION,  # backward compat
)

logger = logging.getLogger(__name__)


class QdrantVectorAdapter(VectorSearchRepository):
    """
    Qdrant adapter for vector search operations.

    Key benefits:
    - Simple REST/gRPC API with native Python client
    - Built-in payload filtering
    - Efficient batch upsert with UUID-based point IDs
    - Lower memory footprint for on-disk payload mode
    - Production-ready horizontal scaling with sharding
    """

    def __init__(
        self,
        qdrant_url: str,
        embedding_model,  # object with .get_text_embedding(text) -> List[float]
        api_key: Optional[str] = None,
    ):
        """
        Initialize Qdrant adapter.

        Args:
            qdrant_url: Qdrant server URL (e.g. ``http://localhost:6333``)
            embedding_model: Embedding model for vectorization
            api_key: Optional API key for Qdrant Cloud
        """
        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.api_key = api_key
        self._client: Optional[QdrantClient] = None
        self._collection_name: Optional[str] = None
        self._initialize_client()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_client(self):
        """Connect to Qdrant and ensure collection exists."""
        try:
            self._client = get_qdrant_client(
                url=self.qdrant_url,
                api_key=self.api_key,
            )
            self._collection_name = get_collection_name()
            logger.info(f"Using Qdrant collection: {self._collection_name}")

            ensure_collection_exists(self._client, self._collection_name)
            logger.info(f"Initialized Qdrant adapter with collection '{self._collection_name}'")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Embedding helper
    # ------------------------------------------------------------------

    def _embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for *text*."""
        try:
            vector = self.embedding_model.get_text_embedding(text)
            if isinstance(vector, list):
                return vector
            if hasattr(vector, "tolist"):
                return vector.tolist()
            raise TypeError(f"Expected list or array, got {type(vector)}")
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    # ------------------------------------------------------------------
    # Domain ↔ Qdrant mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_to_payload(chunk: DocumentChunk) -> dict:
        """Convert a domain *DocumentChunk* to a Qdrant payload dict."""
        extra_json = json.dumps(chunk.metadata.extra) if chunk.metadata.extra else "{}"

        chapter = article = article_number = structure_type = filename = None
        if chunk.metadata.extra:
            chapter = chunk.metadata.extra.get("chapter")
            article = chunk.metadata.extra.get("article")
            article_number = chunk.metadata.extra.get("article_number")
            structure_type = chunk.metadata.extra.get("structure_type")
            filename = chunk.metadata.extra.get("filename")

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
            "chapter": chapter,
            "article": article,
            "article_number": article_number,
            "structure_type": structure_type,
            "filename": filename,
            "metadata_json": extra_json,
        }

    @staticmethod
    def _scored_point_to_result(point, rank: int) -> SearchResult:
        """Convert a Qdrant ScoredPoint to a domain *SearchResult*."""
        p = point.payload or {}

        extra = {}
        if p.get("metadata_json"):
            try:
                extra = json.loads(p["metadata_json"])
            except Exception:
                pass

        metadata = DocumentMetadata(
            doc_id=p.get("doc_id", "unknown"),
            chunk_id=p.get("chunk_id", ""),
            title=p.get("title"),
            page=p.get("page"),
            doc_type=p.get("doc_type"),
            faculty=p.get("faculty"),
            year=p.get("year"),
            subject=p.get("subject"),
            section=p.get("section"),
            subsection=p.get("subsection"),
            language=DocumentLanguage(p.get("language", "vi")),
            extra=extra,
        )

        score = float(point.score) if point.score is not None else 0.0

        return SearchResult(
            text=p.get("text", ""),
            metadata=metadata,
            score=score,
            source_type="vector",
            rank=rank,
            vector_score=score,
        )

    # ------------------------------------------------------------------
    # VectorSearchRepository interface
    # ------------------------------------------------------------------

    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        Index document chunks into Qdrant.

        Uses pre-computed embeddings when available, otherwise generates
        on-the-fly.  Batch upsert for efficiency.
        """
        try:
            if not chunks:
                logger.warning("No chunks to index")
                return True

            logger.info(f"[QDRANT_INDEX] Starting batch upsert for {len(chunks)} chunks")

            points: List[PointStruct] = []
            article_ids_indexed: List[str] = []
            chunks_with_emb = 0
            chunks_without_emb = 0

            for chunk in chunks:
                if chunk.embedding is not None:
                    vector = chunk.embedding if isinstance(chunk.embedding, list) else chunk.embedding.tolist()
                    chunks_with_emb += 1
                else:
                    vector = self._embed_text(chunk.text)
                    chunks_without_emb += 1

                if chunk.metadata.extra and chunk.metadata.extra.get("article_id"):
                    article_ids_indexed.append(chunk.metadata.extra["article_id"])

                payload = self._chunk_to_payload(chunk)
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, payload["chunk_id"]))

                points.append(
                    PointStruct(id=point_id, vector=vector, payload=payload)
                )

            # Batch upsert (qdrant_client handles batching internally)
            BATCH = 100
            for i in range(0, len(points), BATCH):
                self._client.upsert(
                    collection_name=self._collection_name,
                    points=points[i : i + BATCH],
                )

            logger.info(
                f"[QDRANT_INDEX] Batch complete: {chunks_with_emb} pre-computed, "
                f"{chunks_without_emb} embedded on-the-fly"
            )
            logger.info(
                f"[QDRANT_INDEX] Article IDs indexed: "
                f"{sorted(set(article_ids_indexed))[:20]}…"
            )

            # Verify
            try:
                info = self._client.get_collection(self._collection_name)
                logger.info(
                    f"[QDRANT_INDEX] Verification: collection '{self._collection_name}' "
                    f"has {info.points_count} total points"
                )
            except Exception as ve:
                logger.warning(f"[QDRANT_INDEX] Could not verify count: {ve}")

            return True

        except Exception as e:
            logger.error(f"[QDRANT_INDEX] Error indexing documents: {e}", exc_info=True)
            return False

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform vector similarity search with optional payload filtering."""
        try:
            query_vector = self._embed_text(query.text)

            # Build Qdrant filter from domain SearchFilters
            qdrant_filter = self._build_filter(query.filters) if query.filters else None

            hits = self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=query.top_k,
                with_payload=True,
                score_threshold=None,  # return all results up to limit
            )

            results = [
                self._scored_point_to_result(hit, rank=idx + 1)
                for idx, hit in enumerate(hits)
            ]

            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []

    async def delete_document_vectors(self, doc_id: str) -> bool:
        """Remove all vectors for a specific document."""
        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
            )
            logger.info(f"Deleted vectors for document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document vectors: {e}")
            return False

    # ------------------------------------------------------------------
    # Extra public methods
    # ------------------------------------------------------------------

    def check_connection(self) -> dict:
        """Check Qdrant connection and collection status."""
        result = {
            "connected": False,
            "url": self.qdrant_url,
            "collection_name": self._collection_name,
            "collection_exists": False,
            "document_count": 0,
            "error": None,
        }
        try:
            collections = [c.name for c in self._client.get_collections().collections]
            result["connected"] = True

            if self._collection_name in collections:
                result["collection_exists"] = True
                info = self._client.get_collection(self._collection_name)
                result["document_count"] = info.points_count
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[QDRANT] Connection check failed: {e}")
        return result

    def close(self):
        """Close the Qdrant client connection."""
        if self._client:
            self._client.close()
            logger.info("Closed Qdrant client connection")

    # ------------------------------------------------------------------
    # Filter builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filter(search_filters) -> Optional[Filter]:
        """Build a Qdrant ``Filter`` from domain ``SearchFilters``."""
        conditions: list = []

        if search_filters.doc_types:
            conditions.append(
                FieldCondition(key="doc_type", match=MatchAny(any=search_filters.doc_types))
            )
        if search_filters.faculties:
            conditions.append(
                FieldCondition(key="faculty", match=MatchAny(any=search_filters.faculties))
            )
        if search_filters.subjects:
            conditions.append(
                FieldCondition(key="subject", match=MatchAny(any=search_filters.subjects))
            )
        if search_filters.years:
            conditions.append(
                FieldCondition(key="year", match=MatchAny(any=search_filters.years))
            )
        if search_filters.language:
            conditions.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(value=search_filters.language.value),
                )
            )

        if not conditions:
            return None
        return Filter(must=conditions)
