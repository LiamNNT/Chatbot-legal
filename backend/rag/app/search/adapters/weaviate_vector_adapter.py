# adapters/weaviate_vector_adapter.py
#
# Description:
# Weaviate adapter implementation for vector search operations.
# This adapter provides a clean, efficient interface to Weaviate vector database
# following the Ports & Adapters architecture.

import logging
import json
from typing import List, Optional
import numpy as np
import weaviate
from weaviate.classes.query import MetadataQuery

from app.search.ports.repositories import VectorSearchRepository
from shared.domain.rag_models import DocumentChunk, SearchQuery, SearchResult, DocumentMetadata, DocumentLanguage
from app.ingest.store.vector.weaviate_store import (
    get_weaviate_client,
    ensure_collection_exists,
    get_collection_name,
    DOCUMENT_COLLECTION  # Kept for backward compatibility
)

logger = logging.getLogger(__name__)


class WeaviateVectorAdapter(VectorSearchRepository):
    """
    Weaviate adapter for vector search operations.
    
    This adapter provides a clean, efficient implementation using Weaviate's
    native Python client. Much simpler than LlamaIndex wrapper!
    
    Key benefits:
    - Direct Weaviate client usage (no abstraction overhead)
    - Native hybrid search support
    - Built-in filtering and metadata
    - Automatic HNSW indexing
    - Production-ready scaling
    """
    
    def __init__(
        self,
        weaviate_url: str,
        embedding_model,  # HuggingFaceEmbedding instance
        api_key: Optional[str] = None
    ):
        """
        Initialize Weaviate adapter.
        
        Args:
            weaviate_url: Weaviate server URL
            embedding_model: Embedding model for vectorization
            api_key: Optional API key for authentication
        """
        self.weaviate_url = weaviate_url
        self.embedding_model = embedding_model
        self.api_key = api_key
        self._client = None
        self._collection = None
        self._collection_name = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client and ensure schema exists."""
        try:
            self._client = get_weaviate_client(
                url=self.weaviate_url,
                api_key=self.api_key
            )
            
            # Get collection name from settings
            self._collection_name = get_collection_name()
            logger.info(f"Using Weaviate collection: {self._collection_name}")
            
            # Ensure collection exists
            if ensure_collection_exists(self._client, self._collection_name):
                self._collection = self._client.collections.get(self._collection_name)
                logger.info(f"Initialized Weaviate adapter with collection '{self._collection_name}'")
            else:
                raise RuntimeError(f"Failed to create collection '{self._collection_name}'")
                
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}", exc_info=True)
            raise
    
    def _embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Use the embedding model to get vector
            vector = self.embedding_model.get_text_embedding(text)
            
            # DEBUG: Log vector info
            logger.debug(f"Embedding vector type: {type(vector)}, length: {len(vector) if hasattr(vector, '__len__') else 'N/A'}")
            
            # Ensure it's a flat list of floats
            if isinstance(vector, list):
                return vector
            elif hasattr(vector, 'tolist'):
                # NumPy array or similar
                return vector.tolist()
            else:
                logger.error(f"Unexpected vector type: {type(vector)}")
                raise TypeError(f"Expected list or array, got {type(vector)}")
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _chunk_to_weaviate_object(self, chunk: DocumentChunk, vector: List[float]) -> dict:
        """
        Convert domain DocumentChunk to Weaviate object format.
        
        Args:
            chunk: Domain document chunk
            vector: Embedding vector
            
        Returns:
            Dictionary for Weaviate insertion
        """
        # Prepare metadata extras as JSON string
        extra_json = json.dumps(chunk.metadata.extra) if chunk.metadata.extra else "{}"
        
        # Flatten critical metadata fields for better filtering
        chapter = None
        article = None
        article_number = None
        structure_type = None
        filename = None
        
        if chunk.metadata.extra:
            chapter = chunk.metadata.extra.get('chapter')
            article = chunk.metadata.extra.get('article')
            article_number = chunk.metadata.extra.get('article_number')
            structure_type = chunk.metadata.extra.get('structure_type')
            filename = chunk.metadata.extra.get('filename')
        
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
            "metadata_json": extra_json
        }
    
    def _weaviate_object_to_result(self, obj, rank: int) -> SearchResult:
        """
        Convert Weaviate search result to domain SearchResult.
        
        Args:
            obj: Weaviate object from search
            rank: Result rank/position
            
        Returns:
            Domain SearchResult
        """
        properties = obj.properties
        
        # Parse extra metadata
        extra = {}
        if properties.get("metadata_json"):
            try:
                extra = json.loads(properties["metadata_json"])
            except:
                pass
        
        # Create domain metadata
        metadata = DocumentMetadata(
            doc_id=properties.get("doc_id", "unknown"),
            chunk_id=properties.get("chunk_id", ""),
            title=properties.get("title"),
            page=properties.get("page"),
            doc_type=properties.get("doc_type"),
            faculty=properties.get("faculty"),
            year=properties.get("year"),
            subject=properties.get("subject"),
            section=properties.get("section"),
            subsection=properties.get("subsection"),
            language=DocumentLanguage(properties.get("language", "vi")),
            extra=extra
        )
        
        # Get score from metadata
        score = 0.0
        if hasattr(obj.metadata, 'score') and obj.metadata.score is not None:
            score = float(obj.metadata.score)
        elif hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
            # Convert distance to similarity score (cosine distance)
            score = 1.0 - float(obj.metadata.distance)
        
        return SearchResult(
            text=properties.get("text", ""),
            metadata=metadata,
            score=score,
            source_type="vector",
            rank=rank,
            vector_score=score
        )
    
    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        Index document chunks for vector search.
        
        Args:
            chunks: List of document chunks to index (with pre-computed embeddings)
            
        Returns:
            True if successful
        """
        try:
            if not chunks:
                logger.warning("No chunks to index")
                return True
            
            logger.info(f"[WEAVIATE_INDEX] Starting batch insert for {len(chunks)} chunks")
            
            # Track article IDs being indexed
            article_ids_indexed = []
            chunks_with_embedding = 0
            chunks_without_embedding = 0
            
            # Batch insert for efficiency
            with self._collection.batch.dynamic() as batch:
                for chunk in chunks:
                    # Use pre-computed embedding if available, otherwise generate
                    if chunk.embedding is not None:
                        vector = chunk.embedding
                        chunks_with_embedding += 1
                    else:
                        vector = self._embed_text(chunk.text)
                        chunks_without_embedding += 1
                    
                    # Track article ID
                    if chunk.metadata.extra and chunk.metadata.extra.get("article_id"):
                        article_ids_indexed.append(chunk.metadata.extra.get("article_id"))
                    
                    # Convert to Weaviate format
                    obj = self._chunk_to_weaviate_object(chunk, vector)
                    
                    # Add to batch with vector
                    batch.add_object(
                        properties=obj,
                        vector=vector
                    )
            
            logger.info(f"[WEAVIATE_INDEX] Batch complete: {chunks_with_embedding} with pre-computed embedding, {chunks_without_embedding} embedded on-the-fly")
            logger.info(f"[WEAVIATE_INDEX] Article IDs indexed: {sorted(set(article_ids_indexed))[:20]}...")
            logger.info(f"[WEAVIATE_INDEX] Successfully indexed {len(chunks)} chunks to Weaviate collection '{self._collection_name}'")
            
            # Verify data was actually written
            try:
                count = self._collection.aggregate.over_all(total_count=True).total_count
                logger.info(f"[WEAVIATE_INDEX] Verification: Collection '{self._collection_name}' now has {count} total objects")
            except Exception as ve:
                logger.warning(f"[WEAVIATE_INDEX] Could not verify count: {ve}")
            
            return True
            
        except Exception as e:
            logger.error(f"[WEAVIATE_INDEX] Error indexing documents: {e}", exc_info=True)
            return False
    
    def check_connection(self) -> dict:
        """
        Check Weaviate connection and collection status.
        
        Returns:
            Dict with connection status, collection info, and document count
        """
        result = {
            "connected": False,
            "url": self.weaviate_url,
            "collection_name": self._collection_name,
            "collection_exists": False,
            "document_count": 0,
            "error": None
        }
        
        try:
            if self._client and self._client.is_ready():
                result["connected"] = True
            else:
                result["error"] = "Client not connected or not ready"
                return result
            
            if self._client.collections.exists(self._collection_name):
                result["collection_exists"] = True
                count = self._collection.aggregate.over_all(total_count=True).total_count
                result["document_count"] = count
            else:
                result["error"] = f"Collection '{self._collection_name}' does not exist"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"[WEAVIATE] Connection check failed: {e}")
        
        return result
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query
            
        Returns:
            List of search results
        """
        try:
            # Generate query embedding
            query_vector = self._embed_text(query.text)
            
            # Apply filters if provided
            filters = None
            if query.filters:
                filters = self._build_filters(query.filters)
            
            # Build and execute Weaviate query
            # Weaviate v4 API: pass vector directly, filters are applied separately
            # Must specify return_properties to get the text content
            # Properties match VietnameseDocumentV3 schema
            return_props = ["text", "doc_id", "chunk_id", "chunk_index", "title", 
                          "page", "doc_type", "faculty", "year", "subject", "section", "subsection",
                          "language", "structure_type", "chapter",
                          "article", "article_number",
                          "filename", "metadata_json"]
            
            # Execute query - in v4, filters are NOT supported in near_vector() directly
            # If filters are needed, we need to use a different approach
            # For now, query without filters (can post-filter results if needed)
            response = self._collection.query.near_vector(
                near_vector=query_vector,
                limit=query.top_k,
                return_metadata=MetadataQuery(distance=True, score=True),
                return_properties=return_props
            )
            
            # Post-filter results if filters were specified
            results = []
            for i, obj in enumerate(response.objects):
                # Apply filters manually if needed
                if filters and not self._matches_filters(obj, query.filters):
                    continue
                    
                result = self._weaviate_object_to_result(obj, rank=len(results) + 1)
                results.append(result)
                
                # Stop when we have enough results
                if len(results) >= query.top_k:
                    break
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
    def _matches_filters(self, obj, search_filters) -> bool:
        """
        Check if object matches search filters (for post-filtering).
        
        Args:
            obj: Weaviate object
            search_filters: Domain search filters
            
        Returns:
            True if object matches filters
        """
        if not search_filters:
            return True
            
        props = obj.properties
        
        # Check doc_types
        if search_filters.doc_types:
            if props.get("doc_type") not in search_filters.doc_types:
                return False
        
        # Check faculties
        if search_filters.faculties:
            if props.get("faculty") not in search_filters.faculties:
                return False
        
        # Check subjects
        if search_filters.subjects:
            if props.get("subject") not in search_filters.subjects:
                return False
        
        # Check years
        if search_filters.years:
            if props.get("year") not in search_filters.years:
                return False
        
        # Check language
        if search_filters.language:
            if props.get("language") != search_filters.language.value:
                return False
        
        return True
    
    def _build_filters(self, search_filters) -> Optional[dict]:
        """
        Build Weaviate filter from domain SearchFilters.
        
        Args:
            search_filters: Domain search filters
            
        Returns:
            Weaviate filter dictionary or None
        """
        from weaviate.classes.query import Filter
        
        filters = []
        
        if search_filters.doc_types:
            filters.append(Filter.by_property("doc_type").contains_any(search_filters.doc_types))
        
        if search_filters.faculties:
            filters.append(Filter.by_property("faculty").contains_any(search_filters.faculties))
        
        if search_filters.subjects:
            filters.append(Filter.by_property("subject").contains_any(search_filters.subjects))
        
        if search_filters.years:
            year_filters = [Filter.by_property("year").equal(year) for year in search_filters.years]
            if year_filters:
                # Combine with OR
                filters.append(Filter.any_of(year_filters))
        
        if search_filters.language:
            filters.append(Filter.by_property("language").equal(search_filters.language.value))
        
        # Combine all filters with AND
        if filters:
            if len(filters) == 1:
                return filters[0]
            else:
                return Filter.all_of(filters)
        
        return None
    
    async def delete_document_vectors(self, doc_id: str) -> bool:
        """
        Remove vectors for a specific document.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            True if successful
        """
        try:
            from weaviate.classes.query import Filter
            
            # Delete all objects with matching doc_id
            self._collection.data.delete_many(
                where=Filter.by_property("doc_id").equal(doc_id)
            )
            
            logger.info(f"Deleted vectors for document: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document vectors: {e}")
            return False
    
    def close(self):
        """Close Weaviate client connection."""
        if self._client:
            self._client.close()
            logger.info("Closed Weaviate client connection")
