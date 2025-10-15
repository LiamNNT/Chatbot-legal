# Hướng Dẫn Nhanh: Ports & Adapters Architecture

## 📚 Quy Tắc Cơ Bản

### ✅ ĐƯỢC PHÉP

#### 1. Domain Layer (`core/domain/`)
```python
# ✅ ĐÚNG - Chỉ import Python stdlib
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

# ✅ ĐÚNG - Import từ cùng layer
from .models import SearchQuery, SearchResult
```

#### 2. Ports Layer (`core/ports/`)
```python
# ✅ ĐÚNG - Import từ domain
from ..domain.models import SearchResult, DocumentChunk

# ✅ ĐÚNG - Abstract classes
from abc import ABC, abstractmethod
```

#### 3. Adapters Layer (`adapters/`)
```python
# ✅ ĐÚNG - Import ports để implement
from core.ports.repositories import VectorSearchRepository

# ✅ ĐÚNG - Import domain models
from core.domain.models import SearchResult

# ✅ ĐÚNG - Import external libraries
from sentence_transformers import CrossEncoder
from llama_index.core import VectorStoreIndex
```

#### 4. Application Layer (`app/`)
```python
# ✅ ĐÚNG - Import adapters để sử dụng
from adapters.api_facade import get_search_facade

# ✅ ĐÚNG - Import domain models cho API schemas
from core.domain.models import SearchMode
```

---

### ❌ KHÔNG ĐƯỢC PHÉP

#### 1. Domain KHÔNG được import adapters
```python
# ❌ SAI - Domain phụ thuộc adapters
from core.domain.search_service import SearchService
    from adapters.llamaindex_adapter import LlamaIndexAdapter  # WRONG!
```

#### 2. Domain KHÔNG được import application
```python
# ❌ SAI - Domain phụ thuộc application
from core.domain.models import SearchQuery
    from app.api.schemas import ApiRequest  # WRONG!
```

#### 3. Ports KHÔNG được import adapters
```python
# ❌ SAI - Ports phụ thuộc concrete implementations
from core.ports.repositories import VectorSearchRepository
    from adapters.llamaindex_adapter import LlamaIndexAdapter  # WRONG!
```

#### 4. Adapters KHÔNG được import legacy trực tiếp
```python
# ❌ SAI - Adapter phụ thuộc legacy code
from adapters.service_adapters import HybridFusionAdapter
    from retrieval.fusion import HybridFusionEngine  # WRONG!

# ✅ ĐÚNG - Sử dụng domain logic
from adapters.service_adapters import HybridFusionAdapter
    from core.domain.fusion_service import FusionAlgorithms  # CORRECT!
```

---

## 🎯 Dependency Direction

```
┌─────────────┐
│ Application │ (FastAPI, API routes)
└──────┬──────┘
       │ uses
       ▼
┌─────────────┐
│  Adapters   │ (LlamaIndex, OpenSearch implementations)
└──────┬──────┘
       │ implements
       ▼
┌─────────────┐
│   Ports     │ (Abstract interfaces)
└──────┬──────┘
       │ uses
       ▼
┌─────────────┐
│   Domain    │ (Business logic, models)
└─────────────┘
```

**Quy tắc**: Mũi tên chỉ xuống, KHÔNG BAO GIỜ đi ngược lên!

---

## 🔍 Kiểm Tra Vi Phạm

### Cách 1: Grep imports trong domain
```bash
cd services/rag_services
grep -r "from adapters" core/domain/
grep -r "from app" core/domain/

# Nếu có kết quả => VI PHẠM!
```

### Cách 2: Grep imports trong ports
```bash
grep -r "from adapters" core/ports/

# Nếu có kết quả => VI PHẠM!
```

### Cách 3: Kiểm tra adapter có business logic
```python
# ❌ SAI - Business logic trong adapter
class MyAdapter:
    def process(self, data):
        # Complex algorithm here - WRONG!
        result = self._calculate_score(data)
        return result

# ✅ ĐÚNG - Adapter chỉ có integration code
class MyAdapter:
    def process(self, data):
        # Use domain logic
        result = DomainService.calculate_score(data)
        return self._convert_to_external_format(result)
```

---

## 📦 Vị Trí File

### RAG Services
```
services/rag_services/
├── core/                      # ⭐ CORE - Không phụ thuộc gì
│   ├── domain/
│   │   ├── models.py         # Domain entities
│   │   ├── search_service.py # Business logic
│   │   └── fusion_service.py # Fusion algorithms
│   └── ports/
│       ├── repositories.py   # Data access interfaces
│       └── services.py       # Service interfaces
│
├── adapters/                  # 🔌 ADAPTERS - Implement ports
│   ├── llamaindex_vector_adapter.py
│   ├── opensearch_keyword_adapter.py
│   ├── service_adapters.py
│   └── cross_encoder_reranker.py
│
└── app/                       # 🌐 APPLICATION - HTTP, API
    ├── main.py
    └── api/
        └── v1/routes/
```

### Orchestrator
```
services/orchestrator/app/
├── core/                      # ⭐ CORE
│   ├── domain.py             # Domain models
│   ├── orchestration_service.py
│   └── container.py          # ⚠️ Special case
│
├── ports/                     # 📋 PORTS
│   └── agent_ports.py
│
└── adapters/                  # 🔌 ADAPTERS
    ├── openrouter_adapter.py
    ├── rag_adapter.py
    └── conversation_manager.py
```

---

## ⚠️ Trường Hợp Đặc Biệt

### 1. DI Container (Composition Root)
```python
# ✅ ĐƯỢC PHÉP - Container là composition root
# File: core/container.py

def _lazy_import_adapters():
    """Container được phép import adapters để wire dependencies."""
    from adapters.llamaindex_adapter import LlamaIndexAdapter
    from app.config.settings import settings
    return {'LlamaIndexAdapter': LlamaIndexAdapter, 'settings': settings}
```

**Lý do**: Container là nơi duy nhất biết về tất cả implementations.

### 2. Factory Pattern
```python
# ✅ ĐƯỢC PHÉP - Factory biết về concrete classes
class AgentFactory:
    AGENT_CLASSES = {
        "planner": PlannerAgent,
        "answer": AnswerAgent,
    }
```

**Lý do**: Factory pattern cần biết concrete classes để tạo objects.

### 3. API Mappers
```python
# ✅ ĐƯỢC PHÉP - Mappers convert giữa layers
from app.api.schemas import ApiSearchRequest
from core.domain.models import SearchQuery

class Mapper:
    @staticmethod
    def api_to_domain(api_req: ApiSearchRequest) -> SearchQuery:
        # Convert between layers
        pass
```

---

## 🛠️ Sửa Vi Phạm Thường Gặp

### Vi phạm 1: Business Logic trong Adapter
```python
# ❌ TRƯỚC
class MyAdapter(MyPort):
    def process(self, results):
        # Complex business logic here
        scored_results = []
        for r in results:
            score = self._calculate_complex_score(r)  # Business logic!
            scored_results.append(score)
        return scored_results

# ✅ SAU
# 1. Tạo domain service
# File: core/domain/scoring_service.py
class ScoringService:
    @staticmethod
    def calculate_scores(results):
        # Business logic here
        pass

# 2. Adapter chỉ gọi domain service
class MyAdapter(MyPort):
    def process(self, results):
        return ScoringService.calculate_scores(results)
```

### Vi phạm 2: Adapter phụ thuộc Legacy
```python
# ❌ TRƯỚC
from adapters.my_adapter import MyAdapter
    from legacy.old_module import OldService  # Legacy dependency

# ✅ SAU
# 1. Extract logic vào domain
# core/domain/my_service.py
class MyDomainService:
    @staticmethod
    def do_something():
        # Pure logic extracted from legacy
        pass

# 2. Adapter sử dụng domain logic
from core.domain.my_service import MyDomainService
```

---

## ✅ Checklist Tự Kiểm Tra

- [ ] Domain không import adapters
- [ ] Domain không import application
- [ ] Ports chỉ import domain
- [ ] Adapters implement ports
- [ ] Business logic trong domain
- [ ] Adapter chỉ có integration code
- [ ] Dependency direction đúng (xuống)
- [ ] DI Container có comment giải thích
- [ ] Không có circular imports

---

## 📚 Tài Liệu Tham Khảo

1. **Clean Architecture** - Robert C. Martin
2. **Ports & Adapters Pattern** - Alistair Cockburn
3. **Dependency Inversion Principle** - SOLID
4. [Project Documentation](./PORTS_AND_ADAPTERS.md)
5. [Violations Report](./PORTS_AND_ADAPTERS_VIOLATIONS_REPORT.md)
6. [Fix Summary](./ARCHITECTURE_FIX_SUMMARY.md)

---

*Quick Reference Guide - Chatbot-UIT Project*
