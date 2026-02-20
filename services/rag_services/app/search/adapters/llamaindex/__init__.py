"""
LlamaIndex adapter layer for the RAG pipeline.

This package contains LlamaIndex-specific implementations that were
previously (incorrectly) in core/domain/.  Moving them here respects
the Dependency Rule: domain knows nothing about frameworks.

Re-exports
----------
- retriever     — LlamaIndexHybridRetriever, RecursiveRankFusion, etc.
- postprocessors — Deduplication, Reranking, Metadata filters, etc.
- search_service — LlamaIndexSearchService (drop-in for SearchService)
"""

from .retriever import (                                    # noqa: F401
    LlamaIndexHybridRetriever,
    PortBasedVectorRetriever,
    PortBasedBM25Retriever,
    RecursiveRankFusion,
    QueryExpansionRetriever,
    RetrievalConfig,
    FusionMode,
    create_hybrid_retriever,
    create_query_expansion_retriever,
)

from .postprocessors import (                               # noqa: F401
    PostprocessorPipeline,
    DeduplicationPostprocessor,
    CrossEncoderRerankPostprocessor,
    MetadataFilterPostprocessor,
    ScoreThresholdPostprocessor,
    CitationPostprocessor,
    TopKPostprocessor,
    create_default_pipeline,
)

from .search_service import LlamaIndexSearchService         # noqa: F401
