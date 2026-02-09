# LangGraph IRCoT Orchestration

Tài liệu hướng dẫn sử dụng LangGraph để thay thế logic IRCoT manual.

## Tổng quan

LangGraph là một framework trong hệ sinh thái LangChain, được thiết kế để xây dựng các ứng dụng stateful với:

- **Automatic State Management**: Tự động quản lý trạng thái giữa các node
- **Cycles & Loops**: Hỗ trợ vòng lặp (perfect cho IRCoT)
- **Checkpointing**: Lưu trạng thái để recovery
- **Human-in-the-loop**: Cho phép can thiệp của người dùng
- **Visual Debugging**: Debug trực quan với LangGraph Studio

## Kiến trúc Workflow

```
    ┌─────────┐
    │  START  │
    └────┬────┘
         │
    ┌────▼────┐
    │  PLAN   │ ← SmartPlanner: phân tích query, extract filters
    └────┬────┘
         │
    ┌────▼────┐
    │RETRIEVE │ ← RAG + Knowledge Graph (parallel)
4
    └────┬────┘
        /│\
       / │ \
      ▼  │  ▼
[continue]│[answer]
      │   │   │
      │   │   ▼
      │   │ ┌────────┐
      └───┴→│ ANSWER │ ← Generate final answer with citations
            └────┬───┘
                 │
            ┌────▼────┐
            │   END   │
            └─────────┘
```

## Cấu trúc Files

```
app/core/
├── langgraph_state.py      # State definition (IRCoTState)
├── langgraph_nodes.py      # Node functions (plan, retrieve, reason, answer)
├── langgraph_workflow.py   # Graph builder và orchestrator
└── container.py            # Updated with get_langgraph_orchestrator()
```

## Cách Sử dụng

### 1. Enable LangGraph Mode

Đặt biến môi trường:

```bash
# Enable LangGraph orchestration
USE_LANGGRAPH=true

# Optional: Enable checkpointing for state persistence
LANGGRAPH_CHECKPOINTING=true
```

### 2. Cài đặt Dependencies

```bash
pip install langgraph>=0.2.0 langchain-core>=0.3.0
```

### 3. Sử dụng trong Code

```python
from app.core.container import get_langgraph_orchestrator

# Get orchestrator
orchestrator = get_langgraph_orchestrator()

if orchestrator:
    # Process request
    response = await orchestrator.process_request(request)
    
    # Or with streaming for progress updates
    async for event in orchestrator.process_request_stream(request):
        if event["type"] == "progress":
            print(f"Phase: {event['phase']}, Iteration: {event['iteration']}")
        elif event["type"] == "answer":
            print(f"Answer: {event['content']}")
```

## IRCoTState - Trạng thái Workflow

State được quản lý tự động bởi LangGraph:

```python
class IRCoTState(TypedDict):
    # Input
    original_query: str
    session_id: str
    use_rag: bool
    use_knowledge_graph: bool
    
    # Planning
    plan_result: Optional[Dict]
    complexity: str
    complexity_score: float
    
    # Retrieval (accumulated across iterations)
    accumulated_documents: Annotated[List[Dict], operator.add]
    search_queries_used: Annotated[List[str], operator.add]
    
    # Reasoning (accumulated)
    reasoning_steps: Annotated[List[Dict], operator.add]
    current_confidence: float
    can_answer_now: bool
    
    # Graph Reasoning
    graph_context: Optional[str]
    graph_nodes_found: int
    
    # Output
    final_answer: str
    detailed_sources: List[Dict]
    processing_stats: Dict
```

## Nodes

### 1. Plan Node
- Contextual query rewriting (nếu có chat history)
- SmartPlanner phân tích complexity
- Extract filters (doc_types, faculties, years)
- Determine if KG needed

### 2. Retrieve Node
- RAG retrieval với rewritten queries
- Knowledge Graph reasoning (parallel nếu enabled)
- Merge và deduplicate documents
- Accumulate across iterations

### 3. Reason Node
- Generate Chain-of-Thought step
- Identify information gaps
- Propose next search query
- Calculate confidence score

### 4. Answer Node
- Compile reasoning chain
- Generate final answer với AnswerAgent
- Extract citations và sources

### 5. Conditional Edge (should_continue_ircot)
- Check max iterations
- Check confidence threshold (default 0.70)
- Check if model thinks it can answer

## So sánh với Implementation cũ

| Aspect | Cũ (Manual IRCoT) | Mới (LangGraph) |
|--------|-------------------|-----------------|
| State Management | Manual tracking | Automatic |
| Loop Control | Manual while loop | Conditional edges |
| Debugging | Console logs | LangGraph Studio |
| Checkpointing | Not supported | Built-in |
| Extension | Complex refactoring | Add new nodes |
| Human-in-loop | Not supported | Built-in |

## Cấu hình

### Environment Variables

```bash
# LangGraph
USE_LANGGRAPH=true
LANGGRAPH_CHECKPOINTING=false

# IRCoT (applies to both implementations)
IRCOT_ENABLED=true
IRCOT_MODE=automatic  # automatic, forced, disabled
IRCOT_MAX_ITERATIONS=3
IRCOT_COMPLEXITY_THRESHOLD=6.5
IRCOT_EARLY_STOPPING=true
```

## Fallback

Nếu LangGraph không available (chưa cài đặt), hệ thống tự động fallback về `OptimizedMultiAgentOrchestrator` với manual IRCoT loop.

## Debugging với LangGraph Studio

1. Install LangSmith CLI:
```bash
pip install langsmith
```

2. Set API key:
```bash
export LANGCHAIN_API_KEY="your-key"
export LANGCHAIN_TRACING_V2=true
```

3. View traces at: https://smith.langchain.com

## Migration Guide

### Từ OptimizedMultiAgentOrchestrator

1. Đảm bảo logic business vẫn giữ nguyên trong các node
2. Enable LangGraph với `USE_LANGGRAPH=true`
3. Test với các query types: simple, medium, complex
4. Monitor performance và latency

### API Compatibility

Response format không thay đổi - vẫn trả về `OrchestrationResponse`:

```python
{
    "response": "Final answer...",
    "session_id": "...",
    "rag_context": {...},
    "agent_metadata": {
        "pipeline": "langgraph_ircot",
        "reasoning_steps": [...],
        ...
    },
    "processing_stats": {...}
}
```

## Performance Notes

- LangGraph có slight overhead cho state management
- Checkpointing tăng latency nhưng cho phép recovery
- Parallel execution (RAG + KG) giữ nguyên
- Memory usage tăng nhẹ do state tracking
