# Báo cáo Vi phạm Kiến trúc Ports & Adapters

## Tổng quan
Sau khi phân tích cẩn thận hệ thống `rag_services` và `orchestrator`, đã phát hiện các vi phạm kiến trúc Ports & Adapters. Báo cáo này liệt kê các vi phạm và cách sửa chữa.

---

## 📋 DANH SÁCH VI PHẠM

### ✅ RAG_SERVICES - Tuân thủ tốt

Hệ thống rag_services đã được implement khá đúng theo kiến trúc Ports & Adapters:

#### Điểm tốt:
1. **Core Domain** (`core/domain/`) - Clean ✓
   - `models.py`: Chỉ import thư viện chuẩn Python (typing, dataclasses, enum)
   - `search_service.py`: Chỉ phụ thuộc vào ports và domain models
   - KHÔNG có dependency vào adapters hay app layer

2. **Ports** (`core/ports/`) - Clean ✓
   - `repositories.py`: Abstract interfaces cho data access
   - `services.py`: Abstract interfaces cho external services
   - Chỉ phụ thuộc vào domain models

3. **Adapters** (`adapters/`) - Đúng vai trò ✓
   - Tất cả adapters đều implement ports một cách đúng đắn
   - `llamaindex_vector_adapter.py`: Implements `VectorSearchRepository`
   - `opensearch_keyword_adapter.py`: Implements `KeywordSearchRepository`
   - `service_adapters.py`: Implements `RerankingService`, `FusionService`
   - `cross_encoder_reranker.py`: Implements `RerankingService`

#### ⚠️ Vấn đề nhỏ cần chú ý:

**Vi phạm #1: Container nằm sai vị trí**
- **File**: `core/container.py`
- **Vấn đề**: DI Container là composition root thuộc infrastructure layer nhưng lại đặt trong `core/`
- **Mức độ**: THÔNG TIN (không phải vi phạm nghiêm trọng vì container là special case)
- **Giải thích**: 
  - DI Container là "composition root" - nơi duy nhất được phép biết về tất cả implementations
  - Nó cần import adapters để wire dependencies - điều này là ĐÚNG
  - Tuy nhiên nó không phải là core domain logic
- **Đề xuất**: 
  - Có thể di chuyển sang `infrastructure/container.py` hoặc `app/container.py`
  - Hoặc giữ nguyên nhưng thêm comment giải thích (đã làm ở bước sửa)
- **Trạng thái**: ✅ ĐÃ SỬA (thêm comment và lazy import để rõ ràng hơn)

**Vi phạm #2: Adapter phụ thuộc vào legacy code**
- **File**: `adapters/service_adapters.py`
- **Vấn đề**: Import từ `retrieval.fusion` (legacy layer)
```python
from retrieval.fusion import HybridFusionEngine
from retrieval.fusion import SearchResult as FusionSearchResult, create_search_result
```
- **Mức độ**: TRUNG BÌNH
- **Giải thích**: Adapter đang phụ thuộc vào code cũ thay vì tự implement logic
- **Đề xuất**: Move fusion logic vào adapter hoặc tạo port riêng
- **Trạng thái**: ⚠️ CẦN SỬA

---

### ✅ ORCHESTRATOR - Tuân thủ tốt

Hệ thống orchestrator cũng được implement khá đúng:

#### Điểm tốt:
1. **Core Domain** (`app/core/domain.py`) - Clean ✓
   - Chỉ import thư viện chuẩn Python
   - Domain models hoàn toàn pure
   - KHÔNG có dependency vào adapters

2. **Ports** (`app/ports/agent_ports.py`) - Clean ✓
   - Định nghĩa rõ ràng các interfaces
   - Chỉ phụ thuộc vào domain models

3. **Adapters** (`app/adapters/`) - Correct ✓
   - `openrouter_adapter.py`: Implements `AgentPort`
   - `rag_adapter.py`: Implements `RAGServicePort`
   - `conversation_manager.py`: Implements `ConversationManagerPort`
   - Tất cả đều implement ports đúng cách

4. **Services** (`app/core/orchestration_service.py`) - Clean ✓
   - Chỉ phụ thuộc vào ports
   - Business logic thuần túy
   - KHÔNG import adapters

#### ⚠️ Vấn đề nhỏ:

**Vi phạm #3: Agent Factory trong core nhưng import agents**
- **File**: `app/core/agent_factory.py`
- **Vấn đề**: Factory pattern nằm trong core nhưng import concrete agent classes
```python
from ..agents.planner_agent import PlannerAgent
from ..agents.query_rewriter_agent import QueryRewriterAgent
from ..agents.answer_agent import AnswerAgent
from ..agents.verifier_agent import VerifierAgent
from ..agents.response_agent import ResponseAgent
```
- **Mức độ**: THÔNG TIN
- **Giải thích**: 
  - Factory pattern là một trường hợp đặc biệt
  - Nhiệm vụ của nó là tạo objects nên phải biết về concrete classes
  - Tuy nhiên nó nên ở infrastructure layer chứ không phải core
- **Đề xuất**: Di chuyển sang `app/infrastructure/` hoặc `app/factories/`
- **Trạng thái**: ℹ️ GHI CHÚ (không cần sửa ngay)

---

## 🎯 KẾT LUẬN

### Điểm mạnh:
✅ **Core Domain** của cả 2 services đều CLEAN - không phụ thuộc vào infrastructure
✅ **Ports** được định nghĩa rõ ràng với abstract interfaces
✅ **Adapters** đều implement ports một cách đúng đắn
✅ **Dependency direction** đúng: Domain ← Ports ← Adapters

### Điểm cần cải thiện:
1. ⚠️ **Adapter phụ thuộc legacy code** - cần refactor
2. ℹ️ **DI Container và Factory** - vị trí có thể tối ưu hơn (không bắt buộc)

### Đánh giá chung:
**8.5/10** - Hệ thống đã tuân thủ rất tốt kiến trúc Ports & Adapters. Chỉ có một số vấn đề nhỏ cần điều chỉnh.

---

## 🔧 HƯỚNG DẪN SỬA CHỮA

### Sửa Vi phạm #2: Loại bỏ dependency vào retrieval.fusion

#### Tạo domain fusion logic trong core:

```python
# core/domain/fusion_service.py
from typing import List, Dict
from .models import SearchResult

class FusionAlgorithms:
    """Pure domain logic for result fusion."""
    
    @staticmethod
    def reciprocal_rank_fusion(
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        rrf_constant: int = 60
    ) -> List[SearchResult]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).
        Pure business logic without infrastructure dependencies.
        """
        # Create result maps
        def create_key(result: SearchResult) -> str:
            return f"{result.metadata.doc_id}_{result.metadata.chunk_id}"
        
        vector_map = {create_key(r): (i + 1, r) for i, r in enumerate(vector_results)}
        keyword_map = {create_key(r): (i + 1, r) for i, r in enumerate(keyword_results)}
        
        all_keys = set(vector_map.keys()) | set(keyword_map.keys())
        fused_results = []
        
        for key in all_keys:
            rrf_score = 0.0
            result = None
            
            if key in keyword_map:
                rank, kw_result = keyword_map[key]
                rrf_score += keyword_weight / (rrf_constant + rank)
                result = kw_result
                
            if key in vector_map:
                rank, vec_result = vector_map[key]
                rrf_score += vector_weight / (rrf_constant + rank)
                if result is None:
                    result = vec_result
            
            if result:
                # Create new result with fused score
                fused_result = SearchResult(
                    text=result.text,
                    metadata=result.metadata,
                    score=rrf_score,
                    source_type="fused",
                    rank=None,
                    char_spans=result.char_spans,
                    highlighted_text=result.highlighted_text,
                    highlighted_title=result.highlighted_title,
                    bm25_score=result.bm25_score,
                    vector_score=result.vector_score
                )
                fused_results.append(fused_result)
        
        # Sort by score
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        # Add ranks
        for i, result in enumerate(fused_results):
            result.rank = i + 1
        
        return fused_results
```

#### Update adapter để sử dụng domain logic:

```python
# adapters/service_adapters.py
from core.ports.services import FusionService
from core.domain.models import SearchResult
from core.domain.fusion_service import FusionAlgorithms  # Use domain logic

class HybridFusionAdapter(FusionService):
    """Adapter using pure domain fusion logic."""
    
    def __init__(self, rrf_constant: int = 60):
        self.rrf_constant = rrf_constant
    
    async def fuse_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float = 0.5,
        keyword_weight: float = 0.5,
        rrf_constant: int = 60
    ) -> List[SearchResult]:
        """Fuse results using domain logic."""
        return FusionAlgorithms.reciprocal_rank_fusion(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            rrf_constant=rrf_constant or self.rrf_constant
        )
```

---

## 📊 TRƯỚC VÀ SAU KHI SỬA

### Trước:
```
adapters/service_adapters.py
    ↓ depends on
retrieval/fusion.py (LEGACY)
```
❌ Adapter phụ thuộc vào legacy code

### Sau:
```
adapters/service_adapters.py
    ↓ implements
core/ports/services.py (FusionService port)
    ↓ uses
core/domain/fusion_service.py (Pure domain logic)
```
✅ Clean architecture: Adapter → Port → Domain

---

## 📝 CHECKLIST SỬA CHỮA

- [x] Phân tích và tìm vi phạm
- [x] Tạo báo cáo chi tiết
- [ ] Tạo `core/domain/fusion_service.py` với pure logic
- [ ] Refactor `adapters/service_adapters.py` để dùng domain logic
- [ ] Xóa dependency vào `retrieval.fusion`
- [ ] Test lại toàn bộ hệ thống
- [ ] Update documentation

---

## 🎓 BÀI HỌC RÚT RA

1. **DI Container và Factory** là composition roots - được phép biết về implementations
2. **Adapters** chỉ nên chứa integration code, không nên có business logic
3. **Domain logic** phải thuộc về domain layer, có thể reuse ở nhiều adapters
4. **Dependency direction** luôn là: Infrastructure → Application → Domain
5. **Legacy code** nên được wrap trong adapters, không để adapters phụ thuộc trực tiếp

---

*Báo cáo này được tạo tự động bởi AI Assistant vào ngày 15/10/2025*
