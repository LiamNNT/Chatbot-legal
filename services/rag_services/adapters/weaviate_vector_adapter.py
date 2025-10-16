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

from core.ports.repositories import VectorSearchRepository
from core.domain.models import DocumentChunk, SearchQuery, SearchResult, DocumentMetadata, DocumentLanguage
from store.vector.weaviate_store import (
    get_weaviate_client,
    ensure_collection_exists,
    DOCUMENT_COLLECTION
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
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client and ensure schema exists."""
        try:
            self._client = get_weaviate_client(
                url=self.weaviate_url,
                api_key=self.api_key
            )
            
            # Ensure collection exists
            if ensure_collection_exists(self._client):
                self._collection = self._client.collections.get(DOCUMENT_COLLECTION)
                logger.info(f"Initialized Weaviate adapter with collection '{DOCUMENT_COLLECTION}'")
            else:
                raise RuntimeError(f"Failed to create collection '{DOCUMENT_COLLECTION}'")
                
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
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
            return vector
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
            chunks: List of document chunks to index
            
        Returns:
            True if successful
        """
        try:
            if not chunks:
                logger.warning("No chunks to index")
                return True
            
            # Batch insert for efficiency
            with self._collection.batch.dynamic() as batch:
                for chunk in chunks:
                    # Generate embedding
                    vector = self._embed_text(chunk.text)
                    
                    # Convert to Weaviate format
                    obj = self._chunk_to_weaviate_object(chunk, vector)
                    
                    # Add to batch with vector
                    batch.add_object(
                        properties=obj,
                        vector=vector
                    )
            
            logger.info(f"Successfully indexed {len(chunks)} chunks to Weaviate")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return False
    
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
            
            # Build Weaviate query
            search_builder = self._collection.query.near_vector(
                near_vector=query_vector,
                limit=query.top_k,
                return_metadata=MetadataQuery(distance=True, score=True)
            )
            
            # Apply filters if provided
            if query.filters:
                filters = self._build_filters(query.filters)
                if filters:
                    search_builder = search_builder.where(filters)
            
            # Execute search (v4 API - no .do() needed)
            response = search_builder
            
            # Convert results to domain format
            results = []
            for i, obj in enumerate(response.objects):
                result = self._weaviate_object_to_result(obj, rank=i + 1)
                results.append(result)
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []
    
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
