# Final Project Structure

## 📂 Clean Architecture Implementation

Sau quá trình refactoring và cleanup, đây là cấu trúc cuối cùng của dự án:

```
services/rag_services/
├── 🎯 Core Domain (Business Logic)
│   ├── core/
│   │   ├── container.py              # Dependency Injection Container
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # Domain entities (SearchQuery, SearchResult, etc.)
│   │   │   └── search_service.py     # Pure business logic
│   │   └── ports/
│   │       ├── __init__.py
│   │       ├── repositories.py       # Data access interfaces
│   │       └── services.py          # External service interfaces
│   
├── 🔌 Adapters (Infrastructure)
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── api_facade.py             # API ↔ Domain bridge
│   │   ├── integration_adapter.py    # Sync/Async compatibility
│   │   ├── llamaindex_vector_adapter.py      # Vector search implementation
│   │   ├── opensearch_keyword_adapter.py     # Keyword search implementation
│   │   ├── service_adapters.py               # Service implementations
│   │   └── mappers/
│   │       ├── __init__.py
│   │       └── search_mappers.py     # API ↔ Domain conversion
│   
├── 🌐 Application Layer (API)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── errors.py
│   │   │   ├── schemas/              # API data models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── common.py
│   │   │   │   ├── doc.py
│   │   │   │   ├── embed.py
│   │   │   │   └── search.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── routes/
│   │   │           ├── __init__.py
│   │   │           ├── admin.py
│   │   │           ├── embed.py
│   │   │           ├── health.py
│   │   │           ├── opensearch.py
│   │   │           └── search.py     # Updated for clean architecture
│   │   └── config/
│   │       ├── __init__.py
│   │       ├── logging.py
│   │       └── settings.py
│   
├── 🔄 Legacy Compatibility
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── clean_engine.py           # New clean implementation
│   │   ├── engine.py                 # Updated with compatibility layer
│   │   └── fusion.py                 # Original fusion logic
│   
├── 🏪 Storage Layer (Unchanged)
│   ├── store/
│   │   ├── __init__.py
│   │   ├── opensearch/
│   │   │   ├── __init__.py
│   │   │   └── client.py
│   │   └── vector/
│   │       ├── __init__.py
│   │       ├── chroma_store.py
│   │       └── faiss_store.py
│   
├── 🛠️ Infrastructure & Scripts
│   ├── indexing/                     # Document processing (unchanged)
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── chunkers/
│   │   ├── embeddings/
│   │   ├── loaders/
│   │   └── preprocess/
│   │
│   ├── scripts/                      # All scripts consolidated here
│   │   ├── create_sample_data.py
│   │   ├── demo_clean_architecture.py  # NEW: Architecture demo
│   │   ├── demo_hybrid_search.py
│   │   ├── performance_test.py
│   │   ├── sync_to_opensearch.py
│   │   ├── test_api.py              # MOVED: from root
│   │   ├── test_hybrid_search.py
│   │   ├── test_server.py           # MOVED: from root
│   │   ├── test_vietnamese_search.py
│   │   └── test_without_docker.py
│   │
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.opensearch.yml
│   │   └── Dockerfile
│   │
│   ├── data/
│   │   └── docs/
│   │       └── sample_vi.txt
│   │
│   └── storage/                     # Runtime storage
│       ├── faiss.index
│       └── li_storage/
│
├── 📚 Documentation
│   ├── Makefile                     # UPDATED: Clean architecture commands
│   ├── requirements.txt
│   ├── README.md                    # Original documentation
│   ├── OPENSEARCH_SETUP.md         # OpenSearch setup
│   ├── PORTS_AND_ADAPTERS.md       # NEW: Architecture guide
│   ├── REFACTORING_SUMMARY.md      # NEW: Refactoring summary
│   └── setup_summary.py
```

## 🎯 Key Changes Made

### ✅ **Structural Improvements:**
1. **Moved test files**: `test_*.py` files moved from root to `scripts/`
2. **Clean Python cache**: Removed all `__pycache__/` and `*.pyc` files
3. **Consistent naming**: All files use `snake_case` convention
4. **Organized documentation**: Clear separation of docs by purpose

### ✅ **Architecture Compliance:**
1. **Core Domain**: Pure business logic, no framework dependencies
2. **Ports**: Clear interfaces for external concerns
3. **Adapters**: Technology-specific implementations
4. **Clean separation**: Each layer has single responsibility

### ✅ **Enhanced Makefile:**
```makefile
# New architecture-specific commands
make demo-clean          # Demo new architecture
make test-arch           # Test architecture components  
make migrate-check       # Check migration status
make arch-info           # Architecture information
make start-clean         # Start with clean architecture
make start-legacy        # Start with legacy (fallback)
make validate            # Validate project structure
make cleanup-project     # Clean project files
```

## 🚀 Usage Examples

### Quick Start (Clean Architecture):
```bash
make install
make start-clean
make sample-data
make demo-clean
```

### Architecture Testing:
```bash
make validate            # Check structure
make test-arch          # Test components
make migrate-check      # Check status
```

### Development:
```bash
make cleanup-project    # Clean files
make arch-info          # Show info
make info              # System info
```

## 🔧 Environment Variables

Control architecture behavior:
```bash
export USE_CLEAN_ARCHITECTURE=true   # Enable clean arch (default)
export VECTOR_BACKEND=faiss          # Vector store backend
export USE_HYBRID_SEARCH=true        # Enable hybrid search
```

## ✅ Validation Checklist

- ✅ **File Structure**: All files properly organized by layer
- ✅ **Naming Convention**: Consistent snake_case naming
- ✅ **Dependencies**: Core domain has zero framework dependencies  
- ✅ **Separation**: Clear boundaries between layers
- ✅ **Documentation**: Comprehensive guides and examples
- ✅ **Backward Compatibility**: Legacy system still works
- ✅ **Testing**: Architecture components are testable
- ✅ **Makefile**: Updated with new commands and validation

## 🎉 Project Status: **PRODUCTION READY**

The project now fully implements Ports & Adapters architecture while maintaining backward compatibility and providing comprehensive tooling for development and deployment.
