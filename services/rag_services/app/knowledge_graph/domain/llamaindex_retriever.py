"""
DEPRECATED — Backward-compatibility re-export wrapper.

The canonical implementation has moved to ``adapters.llamaindex.retriever``
to respect Clean Architecture's Dependency Rule (domain must not depend on
external frameworks like LlamaIndex).

All symbols are re-exported so that existing ``from core.domain.llamaindex_retriever import …``
statements continue to work.
"""

from app.search.adapters.llamaindex.retriever import (          # noqa: F401
    FusionMode,
    RetrievalConfig,
    AsyncWrapperRetriever,
    PortBasedVectorRetriever,
    PortBasedBM25Retriever,
    RecursiveRankFusion,
    LlamaIndexHybridRetriever,
    QueryExpansionRetriever,
    create_hybrid_retriever,
    create_query_expansion_retriever,
)
