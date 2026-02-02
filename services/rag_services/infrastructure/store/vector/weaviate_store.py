# store/vector/weaviate_store.py
#
# Description:
# Weaviate client initialization and schema management for Vietnamese RAG system.
# This module provides a clean, simple interface to Weaviate vector database.

import os
import logging
import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.classes.init import Auth
from typing import Optional

logger = logging.getLogger(__name__)

# Collection name for document chunks - configurable via env or settings
# Default to "VietnameseDocumentV3" for backward compatibility
def _get_collection_name() -> str:
    """Get collection name from settings or environment, with fallback."""
    try:
        from app.config.settings import settings
        return getattr(settings, 'weaviate_class_name', None) or "VietnameseDocumentV3"
    except ImportError:
        return os.environ.get("WEAVIATE_CLASS_NAME", "VietnameseDocumentV3")

# Lazy evaluation - will be computed on first access
_DOCUMENT_COLLECTION: Optional[str] = None

def get_collection_name() -> str:
    """Get the Weaviate collection name (cached)."""
    global _DOCUMENT_COLLECTION
    if _DOCUMENT_COLLECTION is None:
        _DOCUMENT_COLLECTION = _get_collection_name()
        logger.info(f"Using Weaviate collection name: {_DOCUMENT_COLLECTION}")
    return _DOCUMENT_COLLECTION

# For backward compatibility - but prefer using get_collection_name()
DOCUMENT_COLLECTION = "VietnameseDocumentV3"  # Will be overwritten on import


def get_weaviate_client(
    url: str = "http://localhost:8090",
    api_key: Optional[str] = None,
    timeout: int = 30
) -> weaviate.WeaviateClient:
    """
    Create and return a Weaviate client instance.
    
    Args:
        url: Weaviate server URL
        api_key: Optional API key for authentication
        timeout: Connection timeout in seconds
        
    Returns:
        Connected Weaviate client
    """
    try:
        # Parse URL to extract host and port
        host = url.replace("http://", "").replace("https://", "")
        port = 8090  # Default port
        
        # Extract port if it's in the URL
        if ":" in host:
            host_parts = host.split(":")
            host = host_parts[0]
            port = int(host_parts[1])
        
        # Determine if we're using HTTPS
        use_https = url.startswith("https://")
        
        # Create client configuration
        if api_key and api_key.strip():  # Check for non-empty API key
            auth_config = Auth.api_key(api_key)
            client = weaviate.connect_to_custom(
                http_host=host,
                http_port=port,
                http_secure=use_https,
                grpc_host=host,
                grpc_port=50051,
                grpc_secure=use_https,
                auth_credentials=auth_config,
                skip_init_checks=True  # Skip OIDC checks for local dev
            )
        else:
            # Connect without authentication (for self-hosted development)
            client = weaviate.connect_to_custom(
                http_host=host,
                http_port=port,
                http_secure=use_https,
                grpc_host=host,
                grpc_port=50051,
                grpc_secure=use_https,
                skip_init_checks=True  # Skip OIDC checks for local dev
            )
        
        logger.info(f"Successfully connected to Weaviate at {url}")
        return client
        
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}")
        raise


def create_document_collection(client: weaviate.WeaviateClient, collection_name: Optional[str] = None) -> bool:
    """
    Create the Vietnamese document collection schema in Weaviate.
    
    This schema is optimized for Vietnamese text with proper metadata fields
    for academic documents (syllabus, regulations, etc.).
    
    Args:
        client: Connected Weaviate client
        collection_name: Optional collection name override
        
    Returns:
        True if collection was created or already exists
    """
    try:
        coll_name = collection_name or get_collection_name()
        
        # Check if collection already exists
        if client.collections.exists(coll_name):
            logger.info(f"Collection '{coll_name}' already exists")
            return True
        
        logger.info(f"Creating Weaviate collection '{coll_name}'...")
        
        # Create collection with schema
        client.collections.create(
            name=coll_name,
            description="Vietnamese academic documents for RAG system",
            
            # Vectorizer configuration - we'll provide our own vectors
            vectorizer_config=Configure.Vectorizer.none(),
            
            # Vector index configuration - explicitly set distance metric
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE
            ),
            
            # Properties/fields for document chunks
            properties=[
                Property(
                    name="text",
                    data_type=DataType.TEXT,
                    description="Document chunk text content",
                    skip_vectorization=True  # We handle vectorization ourselves
                ),
                Property(
                    name="doc_id",
                    data_type=DataType.TEXT,
                    description="Document identifier"
                ),
                Property(
                    name="chunk_id",
                    data_type=DataType.TEXT,
                    description="Chunk identifier within document"
                ),
                Property(
                    name="chunk_index",
                    data_type=DataType.INT,
                    description="Index of chunk in document"
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Document title"
                ),
                Property(
                    name="page",
                    data_type=DataType.INT,
                    description="Page number in original document"
                ),
                Property(
                    name="doc_type",
                    data_type=DataType.TEXT,
                    description="Document type (syllabus, regulation, etc.)"
                ),
                Property(
                    name="faculty",
                    data_type=DataType.TEXT,
                    description="Faculty/department (CNTT, KHTN, etc.)"
                ),
                Property(
                    name="year",
                    data_type=DataType.INT,
                    description="Academic year"
                ),
                Property(
                    name="subject",
                    data_type=DataType.TEXT,
                    description="Subject or course code"
                ),
                Property(
                    name="section",
                    data_type=DataType.TEXT,
                    description="Document section"
                ),
                Property(
                    name="subsection",
                    data_type=DataType.TEXT,
                    description="Document subsection"
                ),
                Property(
                    name="language",
                    data_type=DataType.TEXT,
                    description="Document language (vi, en)"
                ),
                Property(
                    name="chapter",
                    data_type=DataType.TEXT,
                    description="Chapter (Chương) for legal documents"
                ),
                Property(
                    name="article",
                    data_type=DataType.TEXT,
                    description="Article (Điều) for legal documents"
                ),
                Property(
                    name="article_number",
                    data_type=DataType.INT,
                    description="Article number (numeric part of Điều)"
                ),
                Property(
                    name="structure_type",
                    data_type=DataType.TEXT,
                    description="Type: chapter, article, clause, point"
                ),
                Property(
                    name="filename",
                    data_type=DataType.TEXT,
                    description="Original PDF filename"
                ),
                Property(
                    name="metadata_json",
                    data_type=DataType.TEXT,
                    description="Additional metadata as JSON string"
                )
            ]
        )
        
        logger.info(f"Created collection '{coll_name}' successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create collection '{coll_name}': {e}")
        return False


def delete_document_collection(client: weaviate.WeaviateClient, collection_name: Optional[str] = None) -> bool:
    """
    Delete the document collection (useful for testing/reset).
    
    Args:
        client: Connected Weaviate client
        collection_name: Optional collection name override
        
    Returns:
        True if deleted successfully
    """
    try:
        coll_name = collection_name or get_collection_name()
        
        if client.collections.exists(coll_name):
            client.collections.delete(coll_name)
            logger.info(f"Deleted collection '{coll_name}'")
            return True
        else:
            logger.warning(f"Collection '{coll_name}' does not exist")
            return False
            
    except Exception as e:
        logger.error(f"Failed to delete collection '{coll_name}': {e}")
        return False


def ensure_collection_exists(client: weaviate.WeaviateClient, collection_name: Optional[str] = None) -> bool:
    """
    Ensure the document collection exists, create if not.
    
    Args:
        client: Connected Weaviate client
        collection_name: Optional collection name override
        
    Returns:
        True if collection exists or was created
    """
    coll_name = collection_name or get_collection_name()
    logger.info(f"Ensuring collection '{coll_name}' exists...")
    
    if not client.collections.exists(coll_name):
        return create_document_collection(client, coll_name)
    
    logger.info(f"Collection '{coll_name}' already exists")
    return True


def delete_documents_by_law_id(client: weaviate.WeaviateClient, law_id: str, collection_name: Optional[str] = None) -> int:
    """
    Delete all document chunks belonging to a specific law_id from Weaviate.
    
    Args:
        client: Connected Weaviate client
        law_id: The law identifier (e.g., "86/2015/QH13")
        collection_name: Optional collection name override
        
    Returns:
        Number of documents deleted
    """
    try:
        coll_name = collection_name or get_collection_name()
        
        if not client.collections.exists(coll_name):
            logger.warning(f"Collection '{coll_name}' does not exist")
            return 0
        
        collection = client.collections.get(coll_name)
        
        # Use batch delete with filter
        from weaviate.classes.query import Filter
        
        deleted_count = 0
        
        # Delete by doc_id field (which contains law_id)
        # Try multiple field patterns
        fields_to_check = ["doc_id", "law_id", "document_number"]
        
        for field in fields_to_check:
            try:
                # Build filter for this field
                filter_condition = Filter.by_property(field).equal(law_id)
                
                # Get objects matching filter
                result = collection.query.fetch_objects(
                    filters=filter_condition,
                    limit=10000
                )
                
                if result.objects:
                    # Delete each object
                    for obj in result.objects:
                        collection.data.delete_by_id(obj.uuid)
                        deleted_count += 1
                    
                    logger.info(f"Deleted {len(result.objects)} objects with {field}={law_id}")
                    
            except Exception as field_err:
                logger.debug(f"Field {field} not found or error: {field_err}")
                continue
        
        # Also try partial match on doc_id (e.g., doc_id contains law_id)
        try:
            filter_condition = Filter.by_property("doc_id").like(f"*{law_id}*")
            result = collection.query.fetch_objects(
                filters=filter_condition,
                limit=10000
            )
            
            if result.objects:
                for obj in result.objects:
                    collection.data.delete_by_id(obj.uuid)
                    deleted_count += 1
                
                logger.info(f"Deleted {len(result.objects)} objects with doc_id containing {law_id}")
                
        except Exception as e:
            logger.debug(f"Partial match delete error: {e}")
        
        logger.info(f"Total deleted from Weaviate for {law_id}: {deleted_count}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to delete documents for {law_id}: {e}")
        return 0
