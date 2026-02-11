import logging
from typing import Dict, List, Set

from ...domain.rag_models import SearchResult
from ...ports.fusion_port import FusionPort

logger = logging.getLogger(__name__)


class RRFFusionService(FusionPort):
    def __init__(self, rrf_constant: int = 60):
        self.rrf_constant = rrf_constant

    async def fuse(self, vector_results: List[SearchResult], keyword_results: List[SearchResult], vector_weight: float = 0.5, keyword_weight: float = 0.5,) -> List[SearchResult]:
        try:
            fused = self._reciprocal_rank_fusion(
                vector_results=vector_results,
                keyword_results=keyword_results,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
                rrf_constant=self.rrf_constant,
            )
            logger.info(
                "Fused %d vector + %d keyword → %d results (RRF k=%d)",
                len(vector_results),
                len(keyword_results),
                len(fused),
                self.rrf_constant,
            )
            return fused

        except Exception as exc:
            logger.error("Fusion failed: %s", exc)
            combined = vector_results + keyword_results
            combined.sort(key=lambda r: r.score, reverse=True)
            return combined[: max(len(vector_results), len(keyword_results))]

    @staticmethod
    def _reciprocal_rank_fusion(vector_results: List[SearchResult], keyword_results: List[SearchResult], vector_weight: float, keyword_weight: float, rrf_constant: int,) -> List[SearchResult]:
        def _key(r: SearchResult) -> str:
            return f"{r.metadata.doc_id}_{r.metadata.chunk_id or ''}"

        vector_map: Dict[str, tuple[int, SearchResult]] = {
            _key(r): (i + 1, r) for i, r in enumerate(vector_results)
        }
        keyword_map: Dict[str, tuple[int, SearchResult]] = {
            _key(r): (i + 1, r) for i, r in enumerate(keyword_results)
        }
        all_keys: Set[str] = set(vector_map) | set(keyword_map)

        fused: List[SearchResult] = []

        for key in all_keys:
            rrf_score = 0.0
            result = None
            orig_vector: float | None = None
            orig_bm25: float | None = None

            if key in keyword_map:
                rank, kw = keyword_map[key]
                rrf_score += keyword_weight / (rrf_constant + rank)
                result = kw
                orig_bm25 = kw.score

            if key in vector_map:
                rank, vec = vector_map[key]
                rrf_score += vector_weight / (rrf_constant + rank)
                orig_vector = vec.score
                if result is None:
                    result = vec

            if result is not None:
                fused.append(
                    SearchResult(
                        text=result.text,
                        metadata=result.metadata,
                        score=rrf_score,
                        source_type="fused",
                        rank=None,
                        char_spans=result.char_spans,
                        highlighted_text=result.highlighted_text,
                        highlighted_title=result.highlighted_title,
                        bm25_score=orig_bm25,
                        vector_score=orig_vector,
                        rerank_score=result.rerank_score,
                    )
                )

        fused.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(fused):
            r.rank = i + 1

        return fused
