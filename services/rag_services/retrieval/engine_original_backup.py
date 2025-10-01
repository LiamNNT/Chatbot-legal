# retrieval/engine.py
#
# Description:
# Clean architecture-compliant search engine interface.
# This module provides a simplified interface that delegates to the clean Ports & Adapters architecture.

import logging
from typing import List

# Clean architecture imports
from adapters.api_facade import get_search_facade
from app.api.schemas.search import SearchRequest, SearchHit

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
    if _cross_encoder is None and CrossEncoder is not None and settings.rerank_model:
        try:
            _cross_encoder = CrossEncoder(settings.rerank_model)
        except Exception:
            _cross_encoder = None
    return _cross_encoder

class HybridEngine:
    """
    Hybrid search engine that combines vector search, BM25, and cross-encoder reranking.
    Supports both traditional vector-only search and hybrid fusion search.
    """
    
    def __init__(self):
        """Initialize the hybrid engine with all necessary components."""
        self.vector_index = _load_or_create_index()
        self.fusion_engine = HybridFusionEngine(rrf_rank_constant=settings.rrf_rank_constant)
        
        # Initialize OpenSearch client if available and hybrid search is enabled
        self.opensearch_client = None
        if OPENSEARCH_AVAILABLE and settings.use_hybrid_search:
            try:
                self.opensearch_client = get_opensearch_client()
                logger.info("OpenSearch client initialized for hybrid search")
            except Exception as e:
                logger.warning(f"Could not initialize OpenSearch client: {e}")
                logger.warning("Falling back to vector-only search")

    def search(self, req: SearchRequest) -> List[SearchHit]:
        """
        Perform search using vector, BM25, or hybrid approach based on request and configuration.

        Args:
            req (SearchRequest): The search request from the API.

        Returns:
            List[SearchHit]: A list of formatted search results.
        """
        # Determine search mode
        use_hybrid = req.use_hybrid if req.use_hybrid is not None else settings.use_hybrid_search
        search_mode = req.search_mode or "hybrid"
        
        # Route to appropriate search method
        if search_mode == "vector" or not self.opensearch_client:
            return self._vector_search(req)
        elif search_mode == "bm25" and self.opensearch_client:
            return self._bm25_only_search(req)
        elif search_mode == "hybrid" and use_hybrid and self.opensearch_client:
            return self._hybrid_search(req)
        else:
            # Fallback to vector search
            logger.warning(f"Invalid search_mode '{search_mode}' or OpenSearch unavailable, falling back to vector search")
            return self._vector_search(req)

    def _vector_search(self, req: SearchRequest) -> List[SearchHit]:
        """Perform traditional vector-only search."""
        # Create a retriever from the index. Retrieve more candidates for better re-ranking.
        retriever = self.vector_index.as_retriever(similarity_top_k=max(req.top_k * 4, 16))
        nodes = retriever.retrieve(req.query)

        # Convert nodes to SearchResult format for consistency
        search_results = []
        for node in nodes:
            meta = node.metadata or {}
            search_result = create_search_result(
                doc_id=str(meta.get("file_name") or meta.get("doc_id") or "unknown"),
                chunk_id=str(meta.get("id") or meta.get("chunk_id") or ""),
                text=node.get_text(),
                metadata=meta,
                score=float(node.score or 0.0),
                source="vector"
            )
            search_results.append(search_result)

        # Apply reranking if requested
        if req.use_rerank:
            search_results = self._apply_cross_encoder_rerank(req.query, search_results)

        # Take top results and convert to API format
        top_results = search_results[:req.top_k]
        return self._format_search_hits(top_results, req.use_rerank, req)

    def _bm25_only_search(self, req: SearchRequest) -> List[SearchHit]:
        """Perform BM25-only search."""
        bm25_results = self._get_bm25_results(req, req.top_k * 2)
        
        # Apply reranking if requested
        if req.use_rerank:
            bm25_results = self._apply_cross_encoder_rerank(req.query, bm25_results)
        
        # Take top results and convert to API format
        top_results = bm25_results[:req.top_k]
        return self._format_search_hits(top_results, req.use_rerank, req)

    def _hybrid_search(self, req: SearchRequest) -> List[SearchHit]:
        """Perform hybrid search combining vector and BM25 results."""
        # Get more candidates for fusion
        candidate_count = max(req.top_k * 4, 20)
        
        # Perform vector search
        vector_results = self._get_vector_results(req.query, candidate_count)
        
        # Perform BM25 search
        bm25_results = self._get_bm25_results(req, candidate_count)
        
        # Use custom weights if provided, otherwise use defaults
        bm25_weight = req.bm25_weight if req.bm25_weight is not None else settings.bm25_weight
        vector_weight = req.vector_weight if req.vector_weight is not None else settings.vector_weight
        
        # Fuse results using RRF
        fused_results = self.fusion_engine.reciprocal_rank_fusion(
            bm25_results=bm25_results,
            vector_results=vector_results,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight
        )
        
        # Apply cross-encoder reranking if requested
        if req.use_rerank:
            fused_results = self._apply_cross_encoder_rerank(req.query, fused_results)
        
        # Take top results and convert to API format
        top_results = fused_results[:req.top_k]
        return self._format_search_hits(top_results, req.use_rerank, req, include_fusion_metadata=True)

    def _get_vector_results(self, query: str, top_k: int) -> List[SearchResult]:
        """Get results from vector search."""
        retriever = self.vector_index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            meta = node.metadata or {}
            result = create_search_result(
                doc_id=str(meta.get("file_name") or meta.get("doc_id") or "unknown"),
                chunk_id=str(meta.get("id") or meta.get("chunk_id") or ""),
                text=node.get_text(),
                metadata=meta,
                score=float(node.score or 0.0),
                source="vector"
            )
            results.append(result)
        
        return results

    def _get_bm25_results(self, req: SearchRequest, top_k: int) -> List[SearchResult]:
        """Get results from BM25 search via OpenSearch with enhanced filters."""
        if not self.opensearch_client:
            return []
            
        try:
            os_results = self.opensearch_client.search(
                query=req.query, 
                size=top_k,
                filters=req.filters,
                doc_types=req.doc_types,
                faculties=req.faculties,
                years=req.years,
                subjects=req.subjects,
                language=req.language,
                include_char_spans=req.include_char_spans
            )
            
            results = []
            for os_result in os_results:
                # Create enhanced metadata
                enhanced_metadata = os_result.get("metadata", {}).copy()
                enhanced_metadata.update({
                    "doc_type": os_result.get("doc_type"),
                    "faculty": os_result.get("faculty"), 
                    "year": os_result.get("year"),
                    "subject": os_result.get("subject"),
                    "language": os_result.get("language"),
                    "char_spans": os_result.get("char_spans", []),
                    "highlighted_text": os_result.get("highlighted_text", []),
                    "highlighted_title": os_result.get("highlighted_title", [])
                })
                
                result = create_search_result(
                    doc_id=os_result["doc_id"],
                    chunk_id=os_result["chunk_id"], 
                    text=os_result["text"],
                    metadata=enhanced_metadata,
                    score=float(os_result["bm25_score"]),
                    source="bm25"
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in BM25 search: {e}")
            return []

    def _apply_cross_encoder_rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Apply cross-encoder reranking to search results."""
        if not results:
            return results
            
        cross_encoder = _get_cross_encoder()
        if cross_encoder is None:
            logger.warning("Cross-encoder not available for reranking")
            return results
        
        try:
            # Prepare query-text pairs for the cross-encoder
            pairs = [(query, result.text) for result in results]
            
            # Get rerank scores
            rerank_scores = cross_encoder.predict(pairs)
            
            # Update results with rerank scores
            for result, score in zip(results, rerank_scores):
                result.score = float(score)
                result.source = f"{result.source}_reranked"
            
            # Sort by rerank score
            results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Applied cross-encoder reranking to {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in cross-encoder reranking: {e}")
            return results

    def _format_search_hits(self, results: List[SearchResult], use_rerank: bool, req: SearchRequest, include_fusion_metadata: bool = False) -> List[SearchHit]:
        """Convert SearchResult objects to enhanced API SearchHit format."""
        hits = []
        
        for result in results:
            metadata = result.metadata or {}
            
            # Extract character spans
            char_spans = []
            if req.include_char_spans and "char_spans" in metadata:
                for span_data in metadata["char_spans"]:
                    char_spans.append(CharacterSpan(
                        start=span_data.get("start", 0),
                        end=span_data.get("end", 0), 
                        text=span_data.get("text", ""),
                        type=span_data.get("type", "content")
                    ))
            
            source_meta = SourceMeta(
                doc_id=result.doc_id,
                chunk_id=result.chunk_id,
                page=metadata.get("page"),
                extra={k: v for k, v in metadata.items() 
                      if k not in ["file_name", "doc_id", "id", "chunk_id", "page", "char_spans", 
                                   "doc_type", "faculty", "year", "subject", "language"]}
            )
            
            # Enhanced citation with character spans
            citation = CitationSpan(
                doc_id=result.doc_id,
                chunk_id=result.chunk_id,
                page=metadata.get("page"),
                char_spans=char_spans if char_spans else None,
                section=metadata.get("section"),
                subsection=metadata.get("subsection"),
                highlighted_text=metadata.get("highlighted_text")
            )
            
            hit = SearchHit(
                text=result.text,
                title=metadata.get("title", ""),
                score=result.score,
                meta=source_meta,
                citation=citation,
                rerank_score=result.score if use_rerank else None,
                
                # Document classification
                doc_type=metadata.get("doc_type"),
                faculty=metadata.get("faculty"),
                year=metadata.get("year"),
                subject=metadata.get("subject"),
                language=metadata.get("language", "vi"),
                
                # Search metadata
                source_type=result.source,
                fusion_rank=result.rank,
                
                # Enhanced citation data
                char_spans=char_spans if char_spans else None,
                highlighted_text=metadata.get("highlighted_text"),
                highlighted_title=metadata.get("highlighted_title")
            )
            
            # Add fusion metadata if applicable
            if include_fusion_metadata:
                if hasattr(result, 'original_bm25_score'):
                    hit.bm25_score = getattr(result, 'original_bm25_score', None)
                if hasattr(result, 'original_vector_score'):
                    hit.vector_score = getattr(result, 'original_vector_score', None)
            
            hits.append(hit)
        
        return hits

# --- New Clean Architecture Implementation ---
# Import the integration adapter for smooth transition
from adapters.integration_adapter import get_integration_adapter

# --- Backward Compatibility Layer ---
class BackwardCompatibleEngine:
    """
    Backward compatibility wrapper that provides the old interface
    while delegating to the new clean architecture implementation.
    """
    
    def __init__(self):
        self.integration_adapter = get_integration_adapter()
        self._legacy_engine = None
    
    def search(self, req):
        """Maintain the old synchronous search interface."""
        try:
            # Use the integration adapter which handles sync/async properly
            return self.integration_adapter.search(req)
        except Exception as e:
            logger.error(f"Error in clean architecture search: {e}")
            logger.info("Falling back to legacy engine")
            return self._legacy_search(req)
    
    def _legacy_search(self, req):
        """Fallback to original engine logic if needed."""
        try:
            if self._legacy_engine is None:
                self._legacy_engine = HybridEngine()
            return self._legacy_engine.search(req)
        except Exception as e:
            logger.error(f"Error in legacy search fallback: {e}")
            return []

# Maintain backward compatibility
SimpleEngine = HybridEngine

# --- Singleton Factory for the Engine ---
_engine = None
_clean_engine = None

def get_query_engine() -> BackwardCompatibleEngine:
    """
    Factory function to get the singleton instance of the search engine.
    Now returns a backward compatible wrapper around the clean architecture.

    Returns:
        BackwardCompatibleEngine: The backward compatible search engine instance.
    """
    global _clean_engine
    if _clean_engine is None:
        _clean_engine = BackwardCompatibleEngine()
        logger.info("Created backward compatible engine using clean architecture")
    return _clean_engine

def get_legacy_engine() -> HybridEngine:
    """
    Factory function to get the original legacy engine if needed.

    Returns:
        HybridEngine: The original hybrid engine instance.
    """
    global _engine
    if _engine is None:
        _engine = HybridEngine()
        logger.info("Created legacy hybrid engine")
    return _engine