"""
Factory for IngestService — wires infrastructure adapters.

This module owns all ``from app.config.settings`` and concrete-adapter
imports so that ``core/services/ingest_service.py`` stays free of
infrastructure coupling.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.ingest.services.ingest_service import IngestService

logger = logging.getLogger(__name__)


def _create_embedder(model_name: str):
    """Create a SentenceTransformer embedding model."""
    from sentence_transformers import SentenceTransformer

    embedder = SentenceTransformer(model_name)
    logger.info("Loaded embedding model: %s", model_name)
    return embedder


def _create_vector_adapter(backend: str, embedder):
    """Instantiate the vector-store adapter for *backend* ("qdrant" | "opensearch")."""
    from app.shared.config.settings import settings

    if backend == "qdrant":
        from app.search.adapters.qdrant_vector_adapter import QdrantVectorAdapter

        class _SimpleEmbedding:
            """Thin wrapper so QdrantVectorAdapter can call .get_text_embedding()."""

            def __init__(self, enc):
                self.embedder = enc

            def get_text_embedding(self, text: str):
                return self.embedder.encode(text).tolist()

        adapter = QdrantVectorAdapter(
            qdrant_url=settings.qdrant_url,
            embedding_model=_SimpleEmbedding(embedder),
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
        )
        logger.info("Initialized Qdrant adapter: %s", settings.qdrant_url)
        return adapter

    # OpenSearch fallback
    from app.ingest.store.opensearch.client import get_opensearch_client
    from app.search.adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter

    adapter = OpenSearchKeywordAdapter(get_opensearch_client())
    logger.info("Initialized OpenSearch adapter")
    return adapter


def _create_graph_adapter():
    """Instantiate the Neo4j graph adapter (returns None on failure)."""
    try:
        from app.knowledge_graph.stores.neo4j_store import Neo4jGraphAdapter
        from app.shared.config.settings import settings

        adapter = Neo4jGraphAdapter(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        )
        logger.info("Initialized Neo4j adapter: %s", settings.neo4j_uri)
        return adapter
    except Exception as exc:
        logger.warning("Failed to initialize Neo4j adapter: %s", exc)
        return None


# ── Singleton management ─────────────────────────────────────────────

_ingest_service: Optional[IngestService] = None


def get_ingest_service() -> IngestService:
    """Return (and lazily create) the singleton IngestService.

    All infrastructure wiring happens here — *not* inside IngestService itself.
    """
    global _ingest_service
    if _ingest_service is not None:
        return _ingest_service

    from app.shared.config.settings import settings

    embedding_model = settings.emb_model
    vector_backend = settings.vector_backend
    token_threshold = 800

    embedder = _create_embedder(embedding_model)
    vector_adapter = _create_vector_adapter(vector_backend, embedder)
    graph_adapter = _create_graph_adapter()

    _ingest_service = IngestService(
        vector_backend=vector_backend,
        embedding_model=embedding_model,
        token_threshold=token_threshold,
        embedder=embedder,
        vector_adapter=vector_adapter,
        graph_adapter=graph_adapter,
    )
    return _ingest_service
