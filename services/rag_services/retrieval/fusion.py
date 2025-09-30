# retrieval/fusion.py
#
# Description:
# This module implements hybrid search fusion techniques, combining BM25 and vector search results.
# It provides Reciprocal Rank Fusion (RRF) and weighted score fusion methods.

import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

@dataclass 
class SearchResult:
    """Unified search result structure for fusion."""
    doc_id: str
    chunk_id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    source: str  # "bm25", "vector", or "fused"
    rank: Optional[int] = None

class HybridFusionEngine:
    """
    Hybrid search fusion engine that combines BM25 and vector search results
    using various fusion strategies.
    """
    
    def __init__(self, rrf_rank_constant: int = 60):
        """
        Initialize fusion engine.
        
        Args:
            rrf_rank_constant: RRF rank constant (typically 60)
        """
        self.rrf_k = rrf_rank_constant

    def reciprocal_rank_fusion(
        self, 
        bm25_results: List[SearchResult], 
        vector_results: List[SearchResult],
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5
    ) -> List[SearchResult]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).
        
        RRF Formula: score = w1/(k + rank1) + w2/(k + rank2)
        
        Args:
            bm25_results: BM25 search results
            vector_results: Vector search results
            bm25_weight: Weight for BM25 results
            vector_weight: Weight for vector results
            
        Returns:
            List of fused and ranked search results
        """
        # Create result maps for efficient lookup
        bm25_map = {self._create_key(r): (i + 1, r) for i, r in enumerate(bm25_results)}
        vector_map = {self._create_key(r): (i + 1, r) for i, r in enumerate(vector_results)}
        
        # Get all unique document keys
        all_keys = set(bm25_map.keys()) | set(vector_map.keys())
        
        fused_results = []
        
        for key in all_keys:
            # Calculate RRF score
            rrf_score = 0.0
            
            # Get result from best available source (prefer BM25 for metadata)
            result = None
            
            if key in bm25_map:
                bm25_rank, bm25_result = bm25_map[key]
                rrf_score += bm25_weight / (self.rrf_k + bm25_rank)
                result = bm25_result
                
            if key in vector_map:
                vector_rank, vector_result = vector_map[key]
                rrf_score += vector_weight / (self.rrf_k + vector_rank)
                # If we don't have result from BM25, use vector result
                if result is None:
                    result = vector_result
            
            if result:
                # Create fused result
                fused_result = SearchResult(
                    doc_id=result.doc_id,
                    chunk_id=result.chunk_id,
                    text=result.text,
                    metadata=result.metadata,
                    score=rrf_score,
                    source="fused"
                )
                fused_results.append(fused_result)
        
        # Sort by RRF score (descending)
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        # Add rank information
        for i, result in enumerate(fused_results):
            result.rank = i + 1
            
        return fused_results

    def weighted_score_fusion(
        self,
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult],
        bm25_weight: float = 0.5,
        vector_weight: float = 0.5,
        normalize_scores: bool = True
    ) -> List[SearchResult]:
        """
        Combine results using weighted score fusion.
        
        Args:
            bm25_results: BM25 search results
            vector_results: Vector search results  
            bm25_weight: Weight for BM25 scores
            vector_weight: Weight for vector scores
            normalize_scores: Whether to normalize scores before fusion
            
        Returns:
            List of fused and ranked search results
        """
        # Normalize scores if requested
        if normalize_scores:
            bm25_results = self._normalize_scores(bm25_results)
            vector_results = self._normalize_scores(vector_results)
        
        # Create result maps
        bm25_map = {self._create_key(r): r for r in bm25_results}
        vector_map = {self._create_key(r): r for r in vector_results}
        
        # Get all unique keys
        all_keys = set(bm25_map.keys()) | set(vector_map.keys())
        
        fused_results = []
        
        for key in all_keys:
            bm25_score = 0.0
            vector_score = 0.0
            result = None
            
            if key in bm25_map:
                bm25_score = bm25_map[key].score
                result = bm25_map[key]
                
            if key in vector_map:
                vector_score = vector_map[key].score
                if result is None:
                    result = vector_map[key]
            
            if result:
                # Calculate weighted fusion score
                fused_score = (bm25_weight * bm25_score + 
                             vector_weight * vector_score)
                
                fused_result = SearchResult(
                    doc_id=result.doc_id,
                    chunk_id=result.chunk_id, 
                    text=result.text,
                    metadata=result.metadata,
                    score=fused_score,
                    source="fused"
                )
                fused_results.append(fused_result)
        
        # Sort by fused score (descending)
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        # Add rank information
        for i, result in enumerate(fused_results):
            result.rank = i + 1
            
        return fused_results

    def _create_key(self, result: SearchResult) -> str:
        """Create a unique key for deduplication."""
        return f"{result.doc_id}_{result.chunk_id}"

    def _normalize_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Normalize scores to [0, 1] range using min-max normalization.
        """
        if not results:
            return results
            
        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        # Avoid division by zero
        score_range = max_score - min_score
        if score_range == 0:
            # All scores are the same, set to 1.0
            for result in results:
                result.score = 1.0
            return results
        
        # Normalize scores
        for result in results:
            result.score = (result.score - min_score) / score_range
            
        return results

    def interleave_fusion(
        self,
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult],
        bm25_ratio: float = 0.5
    ) -> List[SearchResult]:
        """
        Combine results using interleaving strategy.
        
        Args:
            bm25_results: BM25 search results
            vector_results: Vector search results
            bm25_ratio: Ratio of BM25 results to include
            
        Returns:
            List of interleaved search results
        """
        # Calculate how many results to take from each source
        total_results = len(bm25_results) + len(vector_results)
        bm25_count = int(total_results * bm25_ratio)
        vector_count = total_results - bm25_count
        
        # Take top results from each source
        selected_bm25 = bm25_results[:bm25_count]
        selected_vector = vector_results[:vector_count]
        
        # Interleave results
        fused_results = []
        bm25_idx = 0
        vector_idx = 0
        
        while bm25_idx < len(selected_bm25) or vector_idx < len(selected_vector):
            # Add BM25 result
            if bm25_idx < len(selected_bm25):
                result = selected_bm25[bm25_idx]
                result.source = "fused"
                fused_results.append(result)
                bm25_idx += 1
            
            # Add vector result  
            if vector_idx < len(selected_vector):
                result = selected_vector[vector_idx]
                result.source = "fused"
                fused_results.append(result)
                vector_idx += 1
        
        # Remove duplicates while preserving order
        seen_keys = set()
        unique_results = []
        
        for result in fused_results:
            key = self._create_key(result)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_results.append(result)
        
        # Add rank information
        for i, result in enumerate(unique_results):
            result.rank = i + 1
            
        return unique_results

def create_search_result(
    doc_id: str,
    chunk_id: str, 
    text: str,
    metadata: Dict[str, Any],
    score: float,
    source: str
) -> SearchResult:
    """Helper function to create SearchResult instances."""
    return SearchResult(
        doc_id=doc_id,
        chunk_id=chunk_id,
        text=text,
        metadata=metadata,
        score=score,
        source=source
    )
