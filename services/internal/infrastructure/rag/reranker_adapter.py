import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

from ...domain.rag_models import RerankingMetadata, SearchResult
from ...ports.reranker_port import RerankerPort

logger = logging.getLogger(__name__)


class CrossEncoderReranker(RerankerPort):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length: int = 512, batch_size: int = 16, device: Optional[str] = None, trust_remote_code: bool = False,):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.device = device
        self.trust_remote_code = trust_remote_code
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._load_model()


    def _load_model(self) -> None:
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading cross-encoder model: %s", self.model_name)
            self._model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                device=self.device,
                trust_remote_code=self.trust_remote_code,
            )
            logger.info(
                "Cross-encoder loaded on device: %s", self._model.device
            )
        except ImportError:
            logger.error(
                "sentence-transformers not installed — reranker unavailable"
            )
            self._model = None
        except Exception as exc:
            logger.error("Failed to load cross-encoder %s: %s", self.model_name, exc)
            self._model = None

    def is_available(self) -> bool:
        return self._model is not None

    async def rerank(self, query: str, results: List[SearchResult], top_k: Optional[int] = None,) -> List[SearchResult]:
        if not self.is_available():
            logger.warning("Cross-encoder unavailable — returning original order")
            return results
        if not results:
            return results

        start = time.time()

        try:
            pairs: List[Tuple[str, str]] = [
                (query, r.text) for r in results
            ]
            scores = await self._scores_async(pairs)

            reranked: List[SearchResult] = []
            for idx, (result, score) in enumerate(zip(results, scores)):
                meta = RerankingMetadata(
                    original_rank=idx + 1,
                    original_score=result.score,
                    rerank_score=float(score),
                    model_name=self.model_name,
                    processing_time_ms=int((time.time() - start) * 1000),
                )
                reranked.append(
                    SearchResult(
                        text=result.text,
                        metadata=result.metadata,
                        score=float(score),
                        source_type=result.source_type,
                        rank=result.rank,
                        char_spans=result.char_spans,
                        highlighted_text=result.highlighted_text,
                        highlighted_title=result.highlighted_title,
                        bm25_score=result.bm25_score,
                        vector_score=result.vector_score,
                        rerank_score=float(score),
                        reranking_metadata=meta,
                    )
                )

            reranked.sort(key=lambda r: r.rerank_score or 0, reverse=True)
            for i, r in enumerate(reranked):
                r.rank = i + 1

            if top_k is not None:
                reranked = reranked[:top_k]

            elapsed_ms = int((time.time() - start) * 1000)
            logger.info("Reranked %d results in %dms", len(results), elapsed_ms)
            return reranked

        except Exception as exc:
            logger.error("Reranking failed: %s", exc)
            return results

    async def _scores_async(
        self, pairs: List[Tuple[str, str]]
    ) -> List[float]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._scores_sync, pairs
        )

    def _scores_sync(self, pairs: List[Tuple[str, str]]) -> List[float]:
        all_scores: List[float] = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i : i + self.batch_size]
            raw = self._model.predict(batch)
            if hasattr(raw, "tolist"):
                raw = raw.tolist()
            elif not isinstance(raw, list):
                raw = [float(s) for s in raw]
            all_scores.extend(raw)
        return all_scores

    def __del__(self) -> None:
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)

class NoOpReranker(RerankerPort):
    async def rerank(self, query: str, results: List[SearchResult], top_k: Optional[int] = None,) -> List[SearchResult]:
        return results[:top_k] if top_k else results

    def is_available(self) -> bool:
        return True
