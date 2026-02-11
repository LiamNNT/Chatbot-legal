import logging
from typing import List

from ...ports.embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding(EmbeddingPort):
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        vector = self._model.encode(text)
        return vector.tolist() if hasattr(vector, "tolist") else list(vector)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        vectors = self._model.encode(texts)
        return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]
