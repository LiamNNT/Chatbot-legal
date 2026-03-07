# store/vector/qdrant_store.py
#
# Description:
# Qdrant client initialization and collection management for Vietnamese RAG system.
# This module provides a clean, simple interface to Qdrant vector database.

import os
import logging
from typing import Optional, List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    PayloadSchemaType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Collection name resolution
# ---------------------------------------------------------------------------

def _get_collection_name() -> str:
    """Get collection name from settings or environment, with fallback."""
    try:
        from app.shared.config.settings import settings
        return getattr(settings, "qdrant_collection_name", None) or "vietnamese_documents"
    except ImportError:
        return os.environ.get("QDRANT_COLLECTION_NAME", "vietnamese_documents")


_COLLECTION_NAME: Optional[str] = None


def get_collection_name() -> str:
    """Get the Qdrant collection name (cached)."""
    global _COLLECTION_NAME
    if _COLLECTION_NAME is None:
        _COLLECTION_NAME = _get_collection_name()
        logger.info(f"Using Qdrant collection name: {_COLLECTION_NAME}")
    return _COLLECTION_NAME


# Backward-compatible constant
DOCUMENT_COLLECTION = "vietnamese_documents"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def get_qdrant_client(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> QdrantClient:
    """
    Create and return a Qdrant client instance.

    Args:
        url: Qdrant server URL. Defaults to settings.qdrant_url (Qdrant Cloud).
        api_key: API key for Qdrant Cloud. Defaults to settings.qdrant_api_key.
        timeout: Connection timeout in seconds

    Returns:
        Connected QdrantClient
    """
    try:
        # Resolve defaults from settings if not provided
        from app.shared.config.settings import settings as _settings
        if url is None:
            url = _settings.qdrant_url
        if api_key is None:
            api_key = _settings.qdrant_api_key or None

        client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=timeout,
        )
        # quick connectivity check
        client.get_collections()
        logger.info(f"Successfully connected to Qdrant at {url}")
        return client

    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

# The default vector dimension for bge-m3 / multilingual-e5 embeddings
DEFAULT_VECTOR_DIM = 1024


def create_document_collection(
    client: QdrantClient,
    collection_name: Optional[str] = None,
    vector_size: int = DEFAULT_VECTOR_DIM,
) -> bool:
    """
    Create the Vietnamese document collection in Qdrant.

    The collection schema stores Vietnamese legal document chunks:
    text, doc_id, chunk_id, title, page, doc_type, faculty, year, subject … etc.
    Payload fields are indexed for filtered search.

    Args:
        client: Connected QdrantClient
        collection_name: Override collection name
        vector_size: Embedding dimension (1024 for bge-m3)

    Returns:
        True if collection was created or already exists
    """
    coll_name = collection_name or get_collection_name()

    try:
        collections = [c.name for c in client.get_collections().collections]
        if coll_name in collections:
            logger.info(f"Collection '{coll_name}' already exists")
            return True

        logger.info(f"Creating Qdrant collection '{coll_name}' (dim={vector_size})…")

        client.create_collection(
            collection_name=coll_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        # Create payload indexes for commonly filtered fields
        for field, schema in {
            "doc_id": PayloadSchemaType.KEYWORD,
            "chunk_id": PayloadSchemaType.KEYWORD,
            "doc_type": PayloadSchemaType.KEYWORD,
            "faculty": PayloadSchemaType.KEYWORD,
            "year": PayloadSchemaType.INTEGER,
            "subject": PayloadSchemaType.KEYWORD,
            "language": PayloadSchemaType.KEYWORD,
            "chapter": PayloadSchemaType.KEYWORD,
            "article": PayloadSchemaType.KEYWORD,
            "article_number": PayloadSchemaType.INTEGER,
            "structure_type": PayloadSchemaType.KEYWORD,
            "filename": PayloadSchemaType.KEYWORD,
        }.items():
            client.create_payload_index(
                collection_name=coll_name,
                field_name=field,
                field_schema=schema,
            )

        logger.info(f"Created collection '{coll_name}' with payload indexes")
        return True

    except Exception as e:
        logger.error(f"Failed to create collection '{coll_name}': {e}")
        return False


def delete_document_collection(
    client: QdrantClient,
    collection_name: Optional[str] = None,
) -> bool:
    """Delete the document collection."""
    coll_name = collection_name or get_collection_name()
    try:
        client.delete_collection(collection_name=coll_name)
        logger.info(f"Deleted collection '{coll_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to delete collection '{coll_name}': {e}")
        return False


def ensure_collection_exists(
    client: QdrantClient,
    collection_name: Optional[str] = None,
    vector_size: int = DEFAULT_VECTOR_DIM,
) -> bool:
    """Ensure the document collection exists, create if not."""
    coll_name = collection_name or get_collection_name()
    logger.info(f"Ensuring collection '{coll_name}' exists…")

    collections = [c.name for c in client.get_collections().collections]
    if coll_name in collections:
        logger.info(f"Collection '{coll_name}' already exists")
        return True
    return create_document_collection(client, coll_name, vector_size)


# ---------------------------------------------------------------------------
# Document-level deletion
# ---------------------------------------------------------------------------

def delete_documents_by_law_id(
    client: QdrantClient,
    law_id: str,
    collection_name: Optional[str] = None,
) -> int:
    """
    Delete all document chunks belonging to a specific law_id from Qdrant.

    Tries matching on ``doc_id`` field.

    Args:
        client: Connected QdrantClient
        law_id: The law identifier (e.g., "86/2015/QH13")
        collection_name: Override collection name

    Returns:
        Number of points deleted (approximate)
    """
    coll_name = collection_name or get_collection_name()

    try:
        collections = [c.name for c in client.get_collections().collections]
        if coll_name not in collections:
            logger.warning(f"Collection '{coll_name}' does not exist")
            return 0

        # Scroll to find matching points first (so we can count)
        deleted_count = 0
        for field in ("doc_id",):
            try:
                # Use filter-based delete
                filt = Filter(
                    must=[FieldCondition(key=field, match=MatchValue(value=law_id))]
                )

                # Count before delete
                count_result = client.count(
                    collection_name=coll_name,
                    count_filter=filt,
                    exact=True,
                )
                if count_result.count > 0:
                    client.delete(
                        collection_name=coll_name,
                        points_selector=filt,
                    )
                    deleted_count += count_result.count
                    logger.info(f"Deleted {count_result.count} points with {field}={law_id}")
            except Exception as field_err:
                logger.debug(f"Field {field} delete error: {field_err}")
                continue

        logger.info(f"Total deleted from Qdrant for {law_id}: {deleted_count}")
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to delete documents for {law_id}: {e}")
        return 0
