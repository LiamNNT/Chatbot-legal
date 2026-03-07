# LlamaIndex RAG Integration Guide

## Overview

This document describes the integration of LlamaIndex into the RAG (Retrieval-Augmented Generation) pipeline, replacing manual hybrid search implementations with LlamaIndex's retriever and postprocessor abstractions.

## Quick Start

### Enable LlamaIndex Pipeline

Set the environment variable to use LlamaIndex-based search:

```bash
# In .env file
USE_LLAMAINDEX=true
```

Or set it programmatically:

```python
import os
os.environ['USE_LLAMAINDEX'] = 'true'

from infrastructure.container import get_search_service

# This will automatically return LlamaIndexSearchService
search_service = get_search_service()
```

### Check Current Mode

```python
from infrastructure.container import is_using_llamaindex

if is_using_llamaindex():
    print("Using LlamaIndex pipeline")
else:
    print("Using legacy pipeline")
```

## Migration from Legacy SearchService

The legacy `SearchService` is **deprecated** and will be removed in a future version. The new `LlamaIndexSearchService` provides the same interface with improved internals.

### Automatic Migration

Simply set `USE_LLAMAINDEX=true` in your environment. The DI container will automatically:
1. Create `LlamaIndexSearchService` instead of `SearchService`
2. Use `RecursiveRankFusion` for hybrid search fusion
3. Apply postprocessor pipeline for reranking, filtering, etc.

### Manual Migration

If you're creating services manually:

```python
# Legacy (deprecated)
from core.domain.search_service import SearchService
service = SearchService(vector_repo, keyword_repo, reranker, fusion)

# New approach
from core.domain.llamaindex_search_service import LlamaIndexSearchService
service = LlamaIndexSearchService(vector_repo, keyword_repo, reranker)
```

### Deprecation Warnings

When using the legacy `SearchService`, you'll see deprecation warnings:

```
DeprecationWarning: SearchService is deprecated and will be removed in a future version. 
Use LlamaIndexSearchService instead by setting USE_LLAMAINDEX=true in your environment.
```

## Architecture

### Before (Manual Implementation)

```
SearchService
├── _vector_search() → VectorSearchRepository
├── _keyword_search() → KeywordSearchRepository
├── _hybrid_search()
│   ├── Execute searches in parallel
│   ├── FusionService.reciprocal_rank_fusion()
│   └── Manual deduplication
└── RerankingService.rerank()
```

### After (LlamaIndex Implementation)

```
LlamaIndexSearchService
├── LlamaIndexHybridRetriever
│   ├── PortBasedVectorRetriever → VectorSearchRepository
│   ├── PortBasedBM25Retriever → KeywordSearchRepository
│   └── RecursiveRankFusion (built-in RRF)
└── PostprocessorPipeline
    ├── DeduplicationPostprocessor
    ├── CrossEncoderRerankPostprocessor → RerankingService
    ├── MetadataFilterPostprocessor
    ├── ScoreThresholdPostprocessor
    ├── TopKPostprocessor
    └── CitationPostprocessor
```

## Components

### 1. Retrievers (`llamaindex_retriever.py`)

#### LlamaIndexHybridRetriever

Main hybrid retriever combining vector and BM25 search with RRF fusion.

```python
from core.domain.llamaindex_retriever import (
    LlamaIndexHybridRetriever,
    RetrievalConfig,
    FusionMode
)

config = RetrievalConfig(
    vector_top_k=20,
    bm25_top_k=20,
    final_top_k=10,
    fusion_mode=FusionMode.RECIPROCAL_RANK,
    vector_weight=0.5,
    bm25_weight=0.5
)

retriever = LlamaIndexHybridRetriever(
    vector_repository=qdrant_adapter,
    keyword_repository=opensearch_adapter,
    config=config
)

# Retrieve documents
query = QueryBundle(query_str="What are graduation requirements?")
nodes = await retriever._aretrieve(query)
```

#### PortBasedVectorRetriever / PortBasedBM25Retriever

Adapters that bridge LlamaIndex's retriever interface with our hexagonal architecture ports.

```python
from core.domain.llamaindex_retriever import (
    PortBasedVectorRetriever,
    PortBasedBM25Retriever
)

# These use existing repository implementations
vector_retriever = PortBasedVectorRetriever(
    vector_repository=qdrant_adapter,
    top_k=10
)
```

#### QueryExpansionRetriever

Generates multiple query variations and fuses results.

```python
from core.domain.llamaindex_retriever import QueryExpansionRetriever

expansion_retriever = QueryExpansionRetriever(
    base_retriever=hybrid_retriever,
    llm=llm,  # Optional LLM for query generation
    num_variations=3
)
```

### 2. Postprocessors (`llamaindex_postprocessors.py`)

#### DeduplicationPostprocessor

Removes duplicate documents based on content similarity.

```python
from core.domain.llamaindex_postprocessors import DeduplicationPostprocessor

dedup = DeduplicationPostprocessor(
    method="content_prefix",  # or "content_hash", "node_id"
    prefix_length=100,
    keep_highest_score=True
)
```

#### CrossEncoderRerankPostprocessor

Reranks using cross-encoder (wraps existing RerankingService).

```python
from core.domain.llamaindex_postprocessors import CrossEncoderRerankPostprocessor

reranker = CrossEncoderRerankPostprocessor(
    reranking_service=cross_encoder_service,
    top_n=10,
    min_score=0.0
)
```

#### MetadataFilterPostprocessor

Filters by document metadata.

```python
from core.domain.llamaindex_postprocessors import MetadataFilterPostprocessor

filter_pp = MetadataFilterPostprocessor(
    doc_types=["regulation", "syllabus"],
    faculties=["CNTT"],
    years=[2023, 2024]
)
```

#### PostprocessorPipeline

Chains multiple postprocessors.

```python
from core.domain.llamaindex_postprocessors import (
    PostprocessorPipeline,
    create_default_pipeline
)

# Custom pipeline
pipeline = (
    PostprocessorPipeline()
    .add(DeduplicationPostprocessor())
    .add(MetadataFilterPostprocessor(doc_types=["regulation"]))
    .add(CrossEncoderRerankPostprocessor(reranking_service=reranker))
    .add(TopKPostprocessor(top_k=10))
    .add(CitationPostprocessor())
    .build()
)

# Or use factory
pipeline = create_default_pipeline(
    reranking_service=reranker,
    enable_rerank=True,
    top_k=10
)
```

### 3. Search Service (`llamaindex_search_service.py`)

Drop-in replacement for SearchService using LlamaIndex.

```python
from core.domain.llamaindex_search_service import (
    LlamaIndexSearchService,
    create_llamaindex_search_service
)

# Using factory
service = create_llamaindex_search_service(
    vector_repository=qdrant_adapter,
    keyword_repository=opensearch_adapter,
    reranking_service=cross_encoder,
    vector_weight=0.5,
    bm25_weight=0.5,
    top_k=10,
    enable_rerank=True
)

# Execute search (same interface as original SearchService)
query = SearchQuery(
    text="What are the graduation requirements?",
    top_k=10,
    search_mode=SearchMode.HYBRID,
    use_rerank=True
)

response = await service.search(query)
```

## Migration Guide

### Step 1: Update Requirements

Add to `requirements.txt`:

```txt
llama-index-core>=0.12.0
llama-index-embeddings-huggingface>=0.5.0
```

### Step 2: Replace SearchService (Optional)

You can use LlamaIndexSearchService as a drop-in replacement:

```python
# Before
from core.domain.search_service import SearchService

search_service = SearchService(
    vector_repository=vector_repo,
    keyword_repository=keyword_repo,
    reranking_service=reranker,
    fusion_service=fusion
)

# After
from core.domain.llamaindex_search_service import LlamaIndexSearchService

search_service = LlamaIndexSearchService(
    vector_repository=vector_repo,
    keyword_repository=keyword_repo,
    reranking_service=reranker
)
```

### Step 3: Use Environment Variable (Recommended)

Control which implementation to use via environment variable:

```python
import os

USE_LLAMAINDEX = os.getenv("USE_LLAMAINDEX", "false").lower() == "true"

if USE_LLAMAINDEX:
    from core.domain.llamaindex_search_service import LlamaIndexSearchService
    search_service = LlamaIndexSearchService(...)
else:
    from core.domain.search_service import SearchService
    search_service = SearchService(...)
```

## Configuration

### RetrievalConfig

```python
@dataclass
class RetrievalConfig:
    # Search parameters
    vector_top_k: int = 20           # Candidates from vector search
    bm25_top_k: int = 20             # Candidates from BM25 search
    final_top_k: int = 10            # Final results after fusion
    
    # Fusion parameters  
    fusion_mode: FusionMode = FusionMode.RECIPROCAL_RANK
    vector_weight: float = 0.5       # Weight for vector results
    bm25_weight: float = 0.5         # Weight for BM25 results
    rrf_k: int = 60                  # RRF constant
    
    # Query expansion
    num_query_variations: int = 3    # Number of query variations
    enable_query_expansion: bool = True
    
    # Reranking
    enable_rerank: bool = True
    rerank_top_n: int = 10
    
    # Deduplication
    enable_dedup: bool = True
    similarity_threshold: float = 0.85
```

## Testing

Run LlamaIndex tests:

```bash
cd services/rag_services
pytest tests/test_llamaindex_integration.py -v
```

## Benefits

1. **Cleaner Code**: LlamaIndex abstractions reduce boilerplate
2. **Extensibility**: Easy to add new retrievers/postprocessors
3. **Ecosystem Access**: Use LlamaIndex's query transformers, routers, etc.
4. **Standardization**: Follow LlamaIndex patterns for consistency
5. **Backward Compatibility**: Original SearchService remains available

## File Structure

```
services/rag_services/
├── .env                           # Set USE_LLAMAINDEX=true here
├── .env.example                   # Template with USE_LLAMAINDEX option
│
├── core/domain/
│   ├── llamaindex_retriever.py        # LlamaIndex retriever implementations
│   ├── llamaindex_postprocessors.py   # LlamaIndex postprocessor implementations
│   ├── llamaindex_search_service.py   # LlamaIndex-based search service (NEW)
│   ├── search_service.py              # Legacy search service (DEPRECATED)
│   ├── fusion_service.py              # Legacy fusion service (DEPRECATED)
│   └── models.py                      # Domain models
│
├── infrastructure/
│   └── container.py               # DI container (auto-selects based on USE_LLAMAINDEX)
│
└── tests/
    └── test_llamaindex_integration.py # Tests for LlamaIndex components (33 tests)
```

## API Reference

### LlamaIndexSearchService

```python
class LlamaIndexSearchService:
    """Main search service using LlamaIndex."""
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Execute hybrid/vector/bm25 search."""
        
    async def index_documents(self, chunks: List[DocumentChunk]) -> bool:
        """Index documents in all repositories."""
        
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from all repositories."""
        
    async def highlight_results(
        self, 
        query: str, 
        results: List[SearchResult]
    ) -> List[SearchResult]:
        """Add highlighting to results."""
        
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
```

### Container Functions

```python
from infrastructure.container import (
    get_search_service,     # Returns appropriate service based on USE_LLAMAINDEX
    get_container,          # Get DI container instance
    is_using_llamaindex,    # Check if LlamaIndex is enabled
    reset_container         # Reset container (for testing)
)
```

## Troubleshooting

### Import Errors

If you get import errors, ensure LlamaIndex is installed:

```bash
pip install llama-index-core>=0.12.0
```

### Async Issues

All LlamaIndex retrievers and postprocessors support async execution. Use `_aretrieve()` and `process_async()` in async contexts:

```python
# Wrong (in async context)
nodes = retriever.retrieve(query)

# Correct
nodes = await retriever._aretrieve(query)
```

### Performance

For best performance:
1. Use parallel retrieval (default in hybrid retriever)
2. Limit rerank candidates with `rerank_top_n`
3. Use content prefix deduplication instead of full hash

## Related Documentation

- [LangGraph Integration](./LANGGRAPH_INTEGRATION.md) - For orchestration layer
- [Streaming Implementation](./STREAMING_IMPLEMENTATION.md) - For streaming responses
- [Parallel RAG Optimization](./PARALLEL_RAG_OPTIMIZATION.md) - For parallel query execution
