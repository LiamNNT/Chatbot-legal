# retrieval/engine_legacy.py
#
# Description:
# DEPRECATED: Legacy engine implementation for backward compatibility only.
# This file is kept temporarily during migration but should not be used in new code.
# Use the clean Ports & Adapters architecture instead.

import logging
from typing import List, Optional
from pathlib import Path

# API schemas for request/response and common data structures
from app.api.schemas.search import SearchRequest, SearchHit, SearchFacet
from app.api.schemas.common import SourceMeta, CitationSpan, CharacterSpan
from app.config.settings import settings

# LlamaIndex core components for loading and querying the index
from llama_index.core import VectorStoreIndex, StorageContext, Settings, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Handlers for specific vector store implementations
from store.vector.faiss_store import get_faiss_vector_store
from store.vector.chroma_store import get_chroma_vector_store

# Hybrid search components
from retrieval.fusion import HybridFusionEngine, SearchResult, create_search_result

# OpenSearch for BM25
try:
    from store.opensearch.client import get_opensearch_client
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    
# Optional import for the CrossEncoder reranker
try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

logger = logging.getLogger(__name__)

# --- Global Caches ---
# Cache the loaded index and models to avoid reloading on every request.
_index = None
_cross_encoder = None

def _ensure_settings():
    """Configures the global LlamaIndex Settings for the retrieval process."""
    Settings.embed_model = HuggingFaceEmbedding(model_name=settings.emb_model)

def _get_vector_store():
    """Factory function to get the vector store based on configuration."""
    if settings.vector_backend.lower() == "faiss":
        return get_faiss_vector_store()
    else:
        return get_chroma_vector_store()

def _load_or_create_index():
    """
    Loads the VectorStoreIndex from the persistence directory. If it doesn't exist,
    it creates and persists a new empty index skeleton.
    This function implements a singleton pattern for the index.
    """
    global _index
    if _index is not None:
        return _index

    _ensure_settings()
    persist_dir = Path(settings.storage_dir) / "li_storage"

    if persist_dir.exists():
        # IMPORTANT: Pass the vector_store instance during loading to prevent
        # LlamaIndex from defaulting to a SimpleVectorStore from JSON.
        vector_store = _get_vector_store()
        storage_context = StorageContext.from_defaults(
            persist_dir=str(persist_dir),
            vector_store=vector_store
        )
        _index = load_index_from_storage(storage_context=storage_context)
    else:
        # First run: create an empty vector store, build an empty index, and persist the skeleton.
        vector_store = _get_vector_store()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex.from_documents([], storage_context=storage_context)
        storage_context.persist(persist_dir=str(persist_dir))

    return _index

def _get_cross_encoder():
    """
    Loads and caches the CrossEncoder model if it's configured and available.
    Implements a singleton pattern for the reranker model.
    """
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    if not settings.use_rerank or not settings.rerank_model or CrossEncoder is None:
        logger.info("Cross-encoder reranking is disabled.")
        return None

    try:
        _cross_encoder = CrossEncoder(settings.rerank_model)
        logger.info(f"Cross-encoder reranker loaded: {settings.rerank_model}")
        return _cross_encoder
    except Exception as e:
        logger.warning(f"Failed to load cross-encoder '{settings.rerank_model}': {e}")
        return None

class HybridEngine:
    """
    DEPRECATED: Legacy hybrid search engine.
    
    WARNING: This class is deprecated and will be removed in future versions.
    Use the clean Ports & Adapters architecture instead through:
    - adapters.api_facade.get_search_facade()
    - core.container.get_search_service()
    """
    
    def __init__(self):
        logger.warning("HybridEngine is deprecated. Use clean architecture instead.")
        self.index = _load_or_create_index()
        self.fusion_engine = None
        
        # Initialize fusion engine if hybrid search is enabled
        if settings.use_hybrid_search and OPENSEARCH_AVAILABLE:
            try:
                self.fusion_engine = HybridFusionEngine()
                logger.info("Hybrid fusion engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize fusion engine: {e}")
                self.fusion_engine = None

    def search(self, req: SearchRequest) -> List[SearchHit]:
        """
        DEPRECATED: Legacy search method.
        
        Args:
            req: Search request
            
        Returns:
            List of search hits
        """
        logger.warning("Using deprecated HybridEngine.search(). Migrate to clean architecture.")
        
        # Simple vector-only search fallback
        try:
            query_engine = self.index.as_query_engine(
                similarity_top_k=req.top_k or 10,
                response_mode="no_text"
            )
            
            response = query_engine.query(req.query)
            hits = []
            
            for node in response.source_nodes:
                metadata = node.node.metadata
                hit = SearchHit(
                    text=node.node.text,
                    title=metadata.get("title", ""),
                    score=float(node.score or 0.0),
                    meta=SourceMeta(
                        doc_id=metadata.get("doc_id", ""),
                        chunk_id=metadata.get("chunk_id", ""),
                        page=metadata.get("page"),
                        extra={}
                    ),
                    citation=CitationSpan(
                        doc_id=metadata.get("doc_id", ""),
                        chunk_id=metadata.get("chunk_id", ""),
                        page=metadata.get("page")
                    )
                )
                hits.append(hit)
            
            return hits
            
        except Exception as e:
            logger.error(f"Legacy search failed: {e}")
            return []

# Maintain backward compatibility
SimpleEngine = HybridEngine

# Global engine instance
_engine = None

def get_legacy_engine() -> HybridEngine:
    """
    DEPRECATED: Factory function to get the legacy engine.
    
    WARNING: This function is deprecated. Use clean architecture instead.
    
    Returns:
        HybridEngine: The legacy hybrid engine instance.
    """
    logger.warning("get_legacy_engine() is deprecated. Use clean architecture instead.")
    global _engine
    if _engine is None:
        _engine = HybridEngine()
        logger.info("Created legacy hybrid engine")
    return _engine
