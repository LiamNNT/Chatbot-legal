# app/core/retrieval/__init__.py
"""
Unified Retrieval Layer for Vietnamese Legal RAG.

This module provides:
- Legal query parsing (law_id, article, clause, point extraction)
- Metadata filter building for VectorDB
- Neighbor context expansion (prev/next/parent chunks)
- Unified retrieval orchestration with citations

Usage:
    from app.search.retrieval import (
        LegalQueryParser,
        UnifiedRetriever,
        LegalQuery,
        RetrievalResult,
        Citation,
    )
    
    # Parse query
    parser = LegalQueryParser()
    parsed = parser.parse("Khoản 2 Điều 11 Luật 20/2023/QH15 nói gì về học phí?")
    
    # Retrieve with unified interface
    retriever = UnifiedRetriever.from_config(settings)
    result = await retriever.retrieve(parsed, top_k=5)
    
    # Access results
    for chunk in result.chunks:
        print(f"{chunk.citation}: {chunk.content[:100]}...")
"""

from app.search.retrieval.schemas import (
    LegalQuery,
    QueryIntent,
    RetrievalResult,
    RetrievedChunk,
    Citation,
    NeighborContext,
    RetrievalConfig,
)

from app.search.retrieval.legal_query_parser import (
    LegalQueryParser,
)

from app.search.retrieval.metadata_filter_builder import (
    MetadataFilterBuilder,
    QdrantFilterBuilder,
    OpenSearchFilterBuilder,
)

from app.search.retrieval.neighbor_expander import (
    NeighborExpander,
)

from app.search.retrieval.unified_retriever import (
    UnifiedRetriever,
)

__all__ = [
    # Schemas
    "LegalQuery",
    "QueryIntent",
    "RetrievalResult",
    "RetrievedChunk",
    "Citation",
    "NeighborContext",
    "RetrievalConfig",
    # Parser
    "LegalQueryParser",
    # Filter Builders
    "MetadataFilterBuilder",
    "QdrantFilterBuilder",
    "OpenSearchFilterBuilder",
    # Expander
    "NeighborExpander",
    # Main Retriever
    "UnifiedRetriever",
]
