# Ports & Adapters Architecture Implementation

## Tổng quan

Hệ thống RAG đã được tái cấu trúc để tuân thủ nghiêm ngặt kiến trúc "Ports & Adapters" (còn gọi là Hexagonal Architecture). Kiến trúc này tách biệt hoàn toàn logic nghiệp vụ khỏi các chi tiết kỹ thuật và framework.

## Cấu trúc thư mục mới

```
services/rag_services/
├── core/                          # Domain layer - Lõi nghiệp vụ
│   ├── domain/                    # Domain models và services
│   │   ├── models.py             # Domain entities (SearchQuery, SearchResult, etc.)
│   │   └── search_service.py     # Core business logic
│   ├── ports/                     # Port interfaces
│   │   ├── repositories.py       # Data access ports
│   │   └── services.py          # External service ports
│   └── container.py              # Dependency injection container
├── adapters/                      # Infrastructure layer - Adapters
│   ├── llamaindex_vector_adapter.py    # LlamaIndex vector search adapter
│   ├── opensearch_keyword_adapter.py   # OpenSearch BM25 adapter
│   ├── service_adapters.py             # Service adapters (reranking, fusion)
│   ├── integration_adapter.py          # Migration/compatibility adapter
│   ├── api_facade.py                   # API layer facade
│   └── mappers/
│       └── search_mappers.py           # API ↔ Domain mapping
├── retrieval/
│   ├── engine.py                 # Legacy engine (với backward compatibility)
│   └── clean_engine.py          # New clean engine
└── app/                         # Application layer
    └── api/                     # API endpoints
```

## Các thành phần chính

### 1. Core Domain (core/)

**Domain Models (`core/domain/models.py`)**
- `SearchQuery`: Domain representation của search request
- `SearchResult`: Domain representation của search result  
- `DocumentMetadata`: Metadata structure độc lập với framework
- `SearchMode`, `DocumentLanguage`: Domain enums

**Search Service (`core/domain/search_service.py`)**
- `SearchService`: Core business logic cho search operations
- Hoàn toàn độc lập với external frameworks
- Chỉ phụ thuộc vào ports (interfaces)

### 2. Ports (core/ports/)

**Repository Ports (`repositories.py`)**
- `VectorSearchRepository`: Interface cho vector search
- `KeywordSearchRepository`: Interface cho BM25/keyword search  
- `DocumentRepository`: Interface cho document storage

**Service Ports (`services.py`)**
- `RerankingService`: Interface cho reranking operations
- `FusionService`: Interface cho result fusion
- `EmbeddingService`: Interface cho text embeddings

### 3. Adapters (adapters/)

**Infrastructure Adapters**
- `LlamaIndexVectorAdapter`: Implements `VectorSearchRepository` using LlamaIndex
- `OpenSearchKeywordAdapter`: Implements `KeywordSearchRepository` using OpenSearch
- `CrossEncoderRerankingAdapter`: Implements `RerankingService` using sentence-transformers
- `HybridFusionAdapter`: Implements `FusionService` using RRF algorithm

**API Layer Adapters**
- `SearchApiFacade`: Bridges API layer và domain layer
- `SearchMapper`: Converts giữa API schemas và domain models
- `IntegrationAdapter`: Provides sync interface cho async domain

### 4. Dependency Injection

**Container (`core/container.py`)**
- Quản lý lifecycle của tất cả dependencies
- Implements dependency injection pattern
- Ensures proper separation of concerns

## Lợi ích của kiến trúc mới

### 1. Tách biệt quan tâm (Separation of Concerns)
- **Core Domain**: Chỉ chứa business logic, không biết về framework
- **Ports**: Định nghĩa contracts rõ ràng
- **Adapters**: Handle technical details và framework integration

### 2. Testability
- Core domain có thể test mà không cần external dependencies
- Mock implementations dễ dàng tạo ra thông qua ports
- Unit tests vs Integration tests được tách biệt rõ ràng

### 3. Maintainability  
- Thay đổi technology (VectorDB, SearchEngine) không ảnh hưởng đến business logic
- Code rõ ràng, dễ hiểu với responsibility được định nghĩa rõ
- Ít coupling giữa các components

### 4. Extensibility
- Dễ dàng thêm new search strategies
- Support multiple vector stores hoặc search engines đồng thời
- Plugin architecture cho new features

## Migration Strategy

### Phase 1: Backward Compatibility (Hiện tại)
- New architecture hoạt động song song với legacy code
- `BackwardCompatibleEngine` provides bridge giữa old và new
- Environment variable `USE_CLEAN_ARCHITECTURE` controls việc sử dụng

### Phase 2: Gradual Migration
- Migrate individual components từng bước
- Test thoroughly ở mỗi step
- Keep legacy as fallback

### Phase 3: Full Migration
- Remove legacy code hoàn toàn
- Clean up backward compatibility layers
- Full clean architecture implementation

## Usage Examples

### Using Clean Architecture (New)

```python
from core.container import get_search_service
from core.domain.models import SearchQuery, SearchMode

# Get service from DI container
search_service = get_search_service()

# Create domain query
query = SearchQuery(
    text="machine learning",
    top_k=10,
    search_mode=SearchMode.HYBRID
)

# Execute search
response = await search_service.search(query)
```

### Using API Facade

```python
from adapters.api_facade import get_search_facade
from app.api.schemas.search import SearchRequest

# Get facade
facade = get_search_facade()

# Use API schemas
request = SearchRequest(query="AI research", top_k=5)
response = await facade.search(request)
```

### Configuration

Environment variables để control behavior:

```bash
# Use clean architecture (default: true)
USE_CLEAN_ARCHITECTURE=true

# Vector backend
VECTOR_BACKEND=faiss

# Enable hybrid search  
USE_HYBRID_SEARCH=true

# Reranking model
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
```

## Testing

### Unit Tests
```python
# Test core domain with mocked dependencies
from unittest.mock import Mock
from core.domain.search_service import SearchService

# Mock repositories
vector_repo = Mock()
keyword_repo = Mock()

# Create service with mocks
service = SearchService(vector_repo, keyword_repo)

# Test business logic
result = await service.search(query)
```

### Integration Tests
```python
# Test with real adapters
from core.container import get_container

container = get_container()
service = container.get_search_service()

# Test end-to-end
result = await service.search(query)
```

## Best Practices

1. **Keep Core Pure**: Domain layer không import framework code
2. **Use Interfaces**: Luôn program against interfaces, not implementations  
3. **Dependency Injection**: Inject dependencies thông qua constructor
4. **Single Responsibility**: Mỗi adapter chỉ handle một concern
5. **Error Handling**: Proper exception handling ở boundary layers

## Troubleshooting

### Common Issues

1. **Async/Sync Mismatch**: Use `IntegrationAdapter` for bridging
2. **Dependency Injection Errors**: Check container configuration
3. **Import Cycles**: Ensure proper layering (core không import adapters)

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger("core").setLevel(logging.DEBUG)
logging.getLogger("adapters").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Event Sourcing**: Add domain events cho audit trail
2. **CQRS**: Separate command và query responsibilities  
3. **Streaming**: Support real-time search updates
4. **Multi-tenancy**: Support multiple clients với isolated data
