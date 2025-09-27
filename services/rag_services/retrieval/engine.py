# retrieval/engine.py
#
# Description:
# This module implements the core query and retrieval engine for the RAG service.
# It is responsible for loading the pre-built index from storage, handling search requests,
# retrieving relevant nodes, and optionally re-ranking them for improved accuracy.
#
# Key Responsibilities:
# - Loading the LlamaIndex VectorStoreIndex from disk.
# - Providing a singleton `SimpleEngine` instance to handle all search operations.
# - Performing similarity search to retrieve candidate nodes.
# - Optionally applying a CrossEncoder model for re-ranking search results.
# - Formatting the results into the API's `SearchHit` schema.

from typing import List, Optional
from pathlib import Path

# API schemas for request/response and common data structures
from app.api.schemas.search import SearchRequest, SearchHit
from app.api.schemas.common import SourceMeta, CitationSpan
from app.config.settings import settings

# LlamaIndex core components for loading and querying the index
from llama_index.core import VectorStoreIndex, StorageContext, Settings, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Handlers for specific vector store implementations
from store.vector.faiss_store import get_faiss_vector_store
from store.vector.chroma_store import get_chroma_vector_store

# Optional import for the CrossEncoder reranker
try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

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

def _get_cross_encoder() -> Optional["CrossEncoder"]:
    """
    Loads and caches the CrossEncoder model if it's configured and available.
    Implements a singleton pattern for the reranker model.
    """
    global _cross_encoder
    if _cross_encoder is None and CrossEncoder is not None and settings.rerank_model:
        try:
            _cross_encoder = CrossEncoder(settings.rerank_model)
        except Exception:
            _cross_encoder = None
    return _cross_encoder

class SimpleEngine:
    """
    A simple search engine class that encapsulates the retrieval and re-ranking logic.
    """
    def __init__(self):
        """Initializes the engine by loading the index."""
        self.index = _load_or_create_index()

    def search(self, req: SearchRequest) -> List[SearchHit]:
        """
        Performs a search based on the request, retrieves nodes, optionally re-ranks them,
        and formats the output.

        Args:
            req (SearchRequest): The search request from the API.

        Returns:
            List[SearchHit]: A list of formatted search results.
        """
        # Create a retriever from the index. Retrieve more candidates than needed for better re-ranking.
        retriever = self.index.as_retriever(similarity_top_k=max(req.top_k * 4, 16))
        nodes = retriever.retrieve(req.query)

        # Optional re-ranking step using a CrossEncoder model
        if req.use_rerank and _get_cross_encoder() is not None and len(nodes) > 0:
            ce = _get_cross_encoder()
            pairs = [(req.query, n.get_text()) for n in nodes]
            scores = ce.predict(pairs)
            for n, s in zip(nodes, scores):
                n.score = float(s) # Overwrite the original similarity score with the rerank score
            nodes = sorted(nodes, key=lambda x: x.score, reverse=True)

        # Format the top nodes into the `SearchHit` API schema
        top_nodes = nodes[: req.top_k]
        hits: List[SearchHit] = []
        for n in top_nodes:
            meta = n.metadata or {}
            source_meta = SourceMeta(
                doc_id=str(meta.get("file_name") or meta.get("doc_id") or "unknown"),
                chunk_id=str(meta.get("id") or meta.get("chunk_id") or ""),
                page=meta.get("page"),
                extra={k: v for k, v in meta.items() if k not in ["file_name", "doc_id", "id", "chunk_id", "page"]},
            )
            hits.append(
                SearchHit(
                    text=n.get_text(),
                    score=float(n.score or 0.0),
                    meta=source_meta,
                    citation=CitationSpan(doc_id=source_meta.doc_id, page=source_meta.page, span=None),
                    rerank_score=float(n.score or 0.0) if req.use_rerank else None,
                )
            )
        return hits

# --- Singleton Factory for the Engine ---
_engine = None
def get_query_engine() -> SimpleEngine:
    """
    Factory function to get the singleton instance of the SimpleEngine.

    Returns:
        SimpleEngine: The singleton query engine instance.
    """
    global _engine
    if _engine is None:
        _engine = SimpleEngine()
    return _engine