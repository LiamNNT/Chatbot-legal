"""
Ports Layer - Abstract interfaces that the domain depends on.

Ports define WHAT the application needs, not HOW it's implemented.
Infrastructure adapters implement these ports.

Dependency rule:
    Domain → Ports ← Infrastructure
    (Domain depends on Ports, Infrastructure implements Ports)
"""

from .agent_port import AgentPort
from .conversation_port import ConversationManagerPort
from .rag_port import RAGServicePort

# RAG infrastructure ports
from .vector_store_port import VectorStorePort
from .keyword_store_port import KeywordStorePort
from .embedding_port import EmbeddingPort
from .reranker_port import RerankerPort
from .fusion_port import FusionPort

__all__ = [
    # Core ports
    "AgentPort",
    "ConversationManagerPort",
    "RAGServicePort",
    # RAG infrastructure ports
    "VectorStorePort",
    "KeywordStorePort",
    "EmbeddingPort",
    "RerankerPort",
    "FusionPort",
]
