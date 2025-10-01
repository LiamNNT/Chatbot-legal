# adapters/service_adapters.py
#
# Description:
# Adapter implementations for various external services like reranking, fusion, etc.
# These adapters implement the service ports defined in the core domain.

import logging
from typing import List
from sentence_transformers import CrossEncoder

from core.ports.services import RerankingService, FusionService
from core.domain.models import SearchResult
from retrieval.fusion import HybridFusionEngine

logger = logging.getLogger(__name__)


class CrossEncoderRerankingAdapter(RerankingService):
    """
    Adapter for reranking using CrossEncoder models.
    
    This adapter wraps the CrossEncoder functionality to implement
    the RerankingService port from the core domain.
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the CrossEncoder model."""
        try:
            if CrossEncoder is not None:
                self._model = CrossEncoder(self.model_name)
                logger.info(f"Initialized CrossEncoder model: {self.model_name}")
            else:
                logger.warning("CrossEncoder not available")
        except Exception as e:
            logger.error(f"Failed to initialize CrossEncoder model: {e}")
            self._model = None
    
    async def rerank(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank search results based on query-result relevance."""
        if not self.is_available() or not results:
            return results
        
        try:
            # Prepare query-text pairs for the cross-encoder
            pairs = [(query, result.text) for result in results]
            
            # Get rerank scores
            rerank_scores = self._model.predict(pairs)
            
            # Update results with rerank scores and sort
            reranked_results = []
            for result, score in zip(results, rerank_scores):
                # Create a new result with updated score
                reranked_result = SearchResult(
                    text=result.text,
                    metadata=result.metadata,
                    score=float(score),
                    source_type=f"{result.source_type}_reranked",
                    rank=result.rank,
                    char_spans=result.char_spans,
                    highlighted_text=result.highlighted_text,
                    highlighted_title=result.highlighted_title,
                    bm25_score=result.bm25_score,
                    vector_score=result.vector_score,
                    rerank_score=float(score)
                )
                reranked_results.append(reranked_result)
            
            # Sort by rerank score
            reranked_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Reranked {len(results)} results using CrossEncoder")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Error in reranking: {e}")
            return results
    
    def is_available(self) -> bool:
        """Check if the reranking service is available."""
        return self._model is not None


class HybridFusionAdapter(FusionService):
    """
    Adapter for search result fusion using RRF (Reciprocal Rank Fusion).
    
    This adapter wraps the existing HybridFusionEngine to implement
    the FusionService port from the core domain.
    """
    
    def __init__(self, rrf_constant: int = 60):
        self.fusion_engine = HybridFusionEngine(rrf_rank_constant=rrf_constant)
    
    async def fuse_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        rrf_constant: int = 60
    ) -> List[SearchResult]:
        """Fuse results from different search methods using RRF."""
        try:
            # Convert domain results to the format expected by HybridFusionEngine
            from retrieval.fusion import SearchResult as FusionSearchResult, create_search_result
            
            # Convert vector results
            vector_fusion_results = []
            for result in vector_results:
                fusion_result = create_search_result(
                    doc_id=result.metadata.doc_id,
                    chunk_id=result.metadata.chunk_id or "",
                    text=result.text,
                    metadata=self._convert_metadata_to_dict(result.metadata),
                    score=result.score,
                    source="vector"
                )
                vector_fusion_results.append(fusion_result)
            
            # Convert keyword results
            keyword_fusion_results = []
            for result in keyword_results:
                fusion_result = create_search_result(
                    doc_id=result.metadata.doc_id,
                    chunk_id=result.metadata.chunk_id or "",
                    text=result.text,
                    metadata=self._convert_metadata_to_dict(result.metadata),
                    score=result.score,
                    source="bm25"
                )
                keyword_fusion_results.append(fusion_result)
            
            # Perform fusion
            fused_fusion_results = self.fusion_engine.reciprocal_rank_fusion(
                bm25_results=keyword_fusion_results,
                vector_results=vector_fusion_results,
                bm25_weight=keyword_weight,
                vector_weight=vector_weight
            )
            
            # Convert back to domain format
            fused_results = []
            for fusion_result in fused_fusion_results:
                domain_result = self._convert_fusion_result_to_domain(fusion_result)
                fused_results.append(domain_result)
            
            logger.info(f"Fused {len(vector_results)} vector + {len(keyword_results)} keyword results into {len(fused_results)} results")
            return fused_results
            
        except Exception as e:
            logger.error(f"Error in result fusion: {e}")
            # Return combined results as fallback
            return (vector_results + keyword_results)[:len(vector_results)]
    
    def _convert_metadata_to_dict(self, metadata) -> dict:
        """Convert domain metadata to dictionary format."""
        result = {
            "doc_id": metadata.doc_id,
            "chunk_id": metadata.chunk_id,
            "title": metadata.title,
            "page": metadata.page,
            "doc_type": metadata.doc_type,
            "faculty": metadata.faculty,
            "year": metadata.year,
            "subject": metadata.subject,
            "language": metadata.language.value if metadata.language else "vi",
            "section": metadata.section,
            "subsection": metadata.subsection,
        }
        result.update(metadata.extra)
        return {k: v for k, v in result.items() if v is not None}
    
    def _convert_fusion_result_to_domain(self, fusion_result) -> SearchResult:
        """Convert fusion result back to domain format."""
        from core.domain.models import DocumentMetadata, DocumentLanguage
        
        metadata_dict = fusion_result.metadata or {}
        
        language = DocumentLanguage.VIETNAMESE
        if metadata_dict.get("language") == "en":
            language = DocumentLanguage.ENGLISH
        
        metadata = DocumentMetadata(
            doc_id=fusion_result.doc_id,
            chunk_id=fusion_result.chunk_id,
            title=metadata_dict.get("title"),
            page=metadata_dict.get("page"),
            doc_type=metadata_dict.get("doc_type"),
            faculty=metadata_dict.get("faculty"),
            year=metadata_dict.get("year"),
            subject=metadata_dict.get("subject"),
            language=language,
            section=metadata_dict.get("section"),
            subsection=metadata_dict.get("subsection"),
            extra={k: v for k, v in metadata_dict.items() 
                  if k not in ["doc_id", "chunk_id", "title", "page", "doc_type",
                               "faculty", "year", "subject", "language", "section", "subsection"]}
        )
        
        return SearchResult(
            text=fusion_result.text,
            metadata=metadata,
            score=fusion_result.score,
            source_type="fused",
            rank=fusion_result.rank,
            bm25_score=getattr(fusion_result, 'original_bm25_score', None),
            vector_score=getattr(fusion_result, 'original_vector_score', None)
        )
