"""EmbeddingPort — interface for text embedding."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingPort(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        ...

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...
