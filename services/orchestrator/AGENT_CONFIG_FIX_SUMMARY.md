# Agent Configuration Fix Summary

## Vấn Đề
Có sự mâu thuẫn giữa cấu hình trong code Python và file `agents_config.yaml`:

**Hardcoded trong Python (SAI):**
- Planner: `mistralai/mistral-7b-instruct:free`
- Query Rewriter: `mistralai/mistral-7b-instruct:free`
- Answer Agent: `google/gemma-3-27b-it:free`
- Verifier: `deepseek/deepseek-r1-free`
- Response Agent: `meituan/longcat-flash-chat:free`

**Cấu hình YAML (ĐÚNG - nguồn chân lý):**
- Planner: `openai/gpt-4o-mini` (temperature: 0.1)
- Query Rewriter: `openai/gpt-4o-mini` (temperature: 0.4)
- Answer Agent: `deepseek/deepseek-v3.2-exp` (temperature: 0.2)
- Verifier: `openai/gpt-4o-mini` (temperature: 0.1)
- Response Agent: `openai/gpt-4o-mini` (temperature: 0.1)

## Nguyên Nhân
Hệ thống **ĐÃ DÙNG** `ConfigurableAgentFactory` để load config từ YAML, nhưng các agent classes vẫn có method `create_default_config()` với models hardcoded. Method này:
- Được `StaticAgentFactory` sử dụng (factory không được dùng trong production)
- Gây confusion và không đồng bộ với YAML
- Có thể gây lỗi nếu ai đó vô tình dùng StaticAgentFactory

## Vấn Đề 2: Lỗi Logic Luồng Dữ Liệu (rewritten_queries)

**Vấn đề nghiêm trọng**: Query Rewriter Agent tạo ra `rewritten_queries` nhưng **KHÔNG được truyền** đến Answer Agent.

**Lỗi cụ thể:**
- `_execute_retrieval_step()` tạo biến local `rewrite_queries` từ Query Rewriter
- Biến này được dùng để RAG retrieval nhưng **không được return**
- `_execute_answer_step()` hardcode `"rewritten_queries": []` thay vì nhận từ retrieval step
- Answer Agent **MẤT thông tin về query variants**, chỉ thấy query gốc

**Hậu quả:**
- Answer Agent không biết những cách diễn đạt khác nhau đã được dùng để search
- Mất context về query optimization strategy
- Giảm chất lượng synthesis vì thiếu thông tin về semantic variations

## Giải Pháp Đã Áp Dụng

### Phần 1: Sửa Cấu Hình Agents


Đã xóa hoàn toàn method `create_default_config()` từ tất cả agent files:
- ✅ `planner_agent.py` - Xóa 60+ dòng hardcoded config
- ✅ `query_rewriter_agent.py` - Xóa 60+ dòng hardcoded config
- ✅ `answer_agent.py` - Xóa 70+ dòng hardcoded config
- ✅ `verifier_agent.py` - Xóa 70+ dòng hardcoded config
- ✅ `response_agent.py` - Xóa 70+ dòng hardcoded config

**Tổng cộng: ~330 dòng hardcoded config đã bị xóa**

#### 2. Refactor StaticAgentFactory


Thay vì dùng `create_default_config()`, giờ `StaticAgentFactory` delegate sang `ConfigurableAgentFactory`:

```python
class StaticAgentFactory(AgentFactory):
    """Backward compatibility wrapper - delegates to ConfigurableAgentFactory"""
    
    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        self.config_manager = config_manager or get_config_manager()
        self.configurable_factory = ConfigurableAgentFactory(self.config_manager)
    
    def create_agent(self, agent_id, agent_port, config_overrides=None):
        return self.configurable_factory.create_agent(
            agent_id, agent_port, config_overrides
        )
```

### 3. Thêm Logging cho Debug
Đã thêm logging trong `multi_agent_orchestrator.py` để verify models được load từ YAML:

```python
logger.info(f"✓ Planner Agent initialized with model: {self.planner.config.model}")
logger.info(f"✓ Query Rewriter initialized with model: {self.query_rewriter.config.model}")
logger.info(f"✓ Answer Agent initialized with model: {self.answer_agent.config.model}")
logger.info(f"✓ Verifier Agent initialized with model: {self.verifier.config.model}")
logger.info(f"✓ Response Agent initialized with model: {self.response_agent.config.model}")
```

### Phần 2: Sửa Luồng Dữ Liệu

#### 1. Thêm Field `rewritten_queries` vào RAGContext

Cập nhật `services/orchestrator/app/core/domain.py`:

```python
@dataclass
class RAGContext:
    """Context from RAG system to be used in agent requests."""
    query: str
    retrieved_documents: List[Dict[str, Any]]
    search_metadata: Optional[Dict[str, Any]] = None
    relevance_scores: Optional[List[float]] = None
    rewritten_queries: Optional[List[str]] = None  # NEW: Queries from query rewriter
```

#### 2. Return `rewritten_queries` từ Retrieval Step

Sửa `_execute_retrieval_step()` trong `multi_agent_orchestrator.py`:

```python
# Before (SAI - không return rewritten_queries):
return RAGContext(
    query=request.user_query,
    retrieved_documents=rag_data.get("retrieved_documents", []),
    search_metadata=rag_data.get("search_metadata"),
    relevance_scores=rag_data.get("relevance_scores", [])
)

# After (ĐÚNG - return rewritten_queries):
return RAGContext(
    query=request.user_query,
    retrieved_documents=rag_data.get("retrieved_documents", []),
    search_metadata=rag_data.get("search_metadata"),
    relevance_scores=rag_data.get("relevance_scores", []),
    rewritten_queries=rewrite_queries  # Pass to Answer Agent
)
```

#### 3. Nhận `rewritten_queries` trong Answer Step

Sửa `_execute_answer_step()` trong `multi_agent_orchestrator.py`:

```python
# Before (SAI - hardcode empty array):
answer_input = {
    "query": request.user_query,
    "context_documents": rag_context.retrieved_documents if rag_context else [],
    "rewritten_queries": [],  # ❌ Hardcoded empty!
    "previous_context": ""
}

# After (ĐÚNG - lấy từ RAGContext):
answer_input = {
    "query": request.user_query,
    "context_documents": rag_context.retrieved_documents if rag_context else [],
    "rewritten_queries": rag_context.rewritten_queries if rag_context and rag_context.rewritten_queries else [],
    "previous_context": ""
}
```

```
agents_config.yaml
    ↓
ConfigurationManager.get_agent_full_config()
    ↓
ConfigurableAgentFactory._create_agent_config()
    ↓
AgentConfig(model=YAML_VALUE, temperature=YAML_VALUE, ...)
    ↓
MultiAgentOrchestrator.__init__()
    ↓
Agents sử dụng đúng models từ YAML
```

## Kết Quả Mong Đợi

Khi start backend và test query, logs sẽ hiển thị:
```
✓ Planner Agent initialized with model: openai/gpt-4o-mini
✓ Query Rewriter initialized with model: openai/gpt-4o-mini
✓ Answer Agent initialized with model: deepseek/deepseek-v3.2-exp
✓ Verifier Agent initialized with model: openai/gpt-4o-mini
✓ Response Agent initialized with model: openai/gpt-4o-mini
```

## Lợi Ích

### Từ Config Fix:

1. **Single Source of Truth**: `agents_config.yaml` là nguồn cấu hình duy nhất
2. **Không còn confusion**: Xóa code hardcoded gây mâu thuẫn
3. **Dễ maintain**: Chỉ cần sửa YAML để thay đổi model/prompt
4. **Consistency**: Tất cả agents dùng cùng pattern config
5. **Backward compatible**: StaticAgentFactory vẫn hoạt động (qua delegation)

### Từ Data Flow Fix:

1. **Complete Context**: Answer Agent nhận đủ thông tin (query variants + documents)
2. **Better Synthesis**: Hiểu được nhiều cách diễn đạt khác nhau của câu hỏi
3. **Traceability**: Có thể trace được queries nào đã được dùng để search
4. **Quality Improvement**: Answer Agent có thể tạo câu trả lời chính xác hơn với full context
5. **Debugging**: Dễ debug khi biết được query optimization strategy

## Files Đã Sửa

### Config Fix:

1. `services/orchestrator/app/agents/planner_agent.py` - Xóa create_default_config()
2. `services/orchestrator/app/agents/query_rewriter_agent.py` - Xóa create_default_config()
3. `services/orchestrator/app/agents/answer_agent.py` - Xóa create_default_config()
4. `services/orchestrator/app/agents/verifier_agent.py` - Xóa create_default_config()
5. `services/orchestrator/app/agents/response_agent.py` - Xóa create_default_config()
6. `services/orchestrator/app/core/agent_factory.py` - Refactor StaticAgentFactory
7. `services/orchestrator/app/agents/multi_agent_orchestrator.py` - Thêm logging

### Data Flow Fix:

8. `services/orchestrator/app/core/domain.py` - Thêm `rewritten_queries` field vào RAGContext
9. `services/orchestrator/app/agents/multi_agent_orchestrator.py` - Sửa `_execute_retrieval_step()` return rewritten_queries
10. `services/orchestrator/app/agents/multi_agent_orchestrator.py` - Sửa `_execute_answer_step()` nhận rewritten_queries

## Verification Steps

1. **Start backend:** `python start_backend.py`
2. **Check logs** cho agent initialization messages (verify models)
3. **Test query:** 
   ```bash
   curl -X POST http://localhost:8001/api/v1/chat \
     -H "Content-Type: application/json" \
     -d '{"query":"Đăng ký HP thế nào?"}'
   ```
4. **Verify trong logs:**
   - Agent models match với YAML config
   - rewritten_queries được tạo và truyền đúng
5. **Check response** có chất lượng tốt hơn với full context

## Ngày Sửa
29 October 2025

## Status
✅ Hoàn thành - Code đã compile không lỗi, sẵn sàng test
