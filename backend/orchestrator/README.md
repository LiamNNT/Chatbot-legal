# 🎯 Orchestrator Service

> FastAPI microservice điều phối multi-agent pipeline cho Chatbot-UIT.
> Nhận câu hỏi từ frontend → lên kế hoạch → gọi RAG Service lấy context → sinh câu trả lời bằng LLM.

| Thông tin | Giá trị |
|-----------|---------|
| **Port** | `8001` (Docker) / `8002` (local dev) |
| **Framework** | FastAPI + LangGraph |
| **LLM Provider** | OpenRouter (GPT-4o-mini, GPT-5.1-chat, …) |
| **Phụ thuộc runtime** | RAG Service (port 8000), Neo4j (port 7687, optional) |

---

## 📁 Cấu trúc thư mục

```
orchestrator/
├── app/
│   ├── main.py                          # FastAPI entrypoint + lifespan
│   │
│   ├── chat/                            # ★ Core chat orchestration
│   │   ├── routes.py                    #   POST /chat, /chat/simple, /chat/stream
│   │   ├── response_mappers.py          #   Map domain → API response
│   │   ├── exception_handlers.py        #   Fallback khi pipeline lỗi
│   │   │
│   │   ├── agents/                      #   Package-by-feature agents
│   │   │   ├── base.py                  #     ABC SpecializedAgent, AgentConfig, AnswerResult
│   │   │   ├── smart_planner/           #     Planning + Query Rewriting (1 LLM call)
│   │   │   │   ├── agent.py             #       SmartPlannerAgent class
│   │   │   │   ├── models.py            #       SmartPlanResult, ExtractedFilters
│   │   │   │   ├── rules.py             #       Rule-based logic (no LLM)
│   │   │   │   └── prompts.py           #       Prompt helpers
│   │   │   ├── answer/                  #     Answer Generation (1 LLM call)
│   │   │   │   ├── agent.py             #       AnswerAgent (stream + non-stream)
│   │   │   │   ├── utils.py             #       Citation, confidence, doc filtering
│   │   │   │   └── prompts.py           #       build_answer_prompt()
│   │   │   └── orchestrator/            #     Multi-Agent Orchestrator
│   │   │       ├── orchestrator.py      #       OptimizedMultiAgentOrchestrator
│   │   │       └── direct_responses.py  #       Hardcoded Vietnamese greetings
│   │   │
│   │   ├── adapters/                    #   Outbound adapters
│   │   │   ├── openrouter_adapter.py    #     LLM calls → OpenRouter
│   │   │   └── rag_adapter.py           #     HTTP calls → RAG Service
│   │   │
│   │   ├── services/                    #   Domain services
│   │   │   ├── orchestration_service.py #     Simple single-agent pipeline
│   │   │   ├── context_service.py       #     Contextual query rewriting
│   │   │   ├── ircot_service.py         #     IRCoT reasoning (deprecated → LangGraph)
│   │   │   └── planner_service.py       #     Planner helper
│   │   │
│   │   └── langgraph/                   #   LangGraph stateful orchestration
│   │       ├── workflow.py              #     StateGraph: plan → retrieve ⟷ reason → answer
│   │       ├── nodes.py                 #     Node implementations
│   │       └── state.py                 #     IRCoTState definition
│   │
│   ├── reasoning/                       #   Knowledge Graph reasoning
│   │   ├── graph_reasoning_agent.py     #     ReAct agent (local / global / multi-hop)
│   │   ├── symbolic_reasoning_agent.py  #     Symbolic rules R001-R008
│   │   ├── symbolic_engine.py           #     Rule execution engine
│   │   ├── reasoning_rules.py          #     Rule definitions
│   │   ├── query_analyzer.py            #     Query intent → graph query type
│   │   └── context_enricher.py          #     Merge rules + graph + Q&A
│   │
│   ├── conversation/                    #   Conversation management
│   │   ├── conversation_manager.py      #     In-memory sliding window (max 20 msgs)
│   │   └── routes.py                    #     GET/DELETE /conversations
│   │
│   ├── admin/                           #   Admin & debug
│   │   └── routes.py                    #     GET /health, /agents/info, POST /agents/test
│   │
│   └── shared/                          #   Cross-cutting concerns
│       ├── domain.py                    #     Re-export domain entities (từ shared pkg)
│       ├── ports.py                     #     AgentPort, RAGServicePort, ConversationManagerPort
│       ├── schemas.py                   #     Pydantic request/response schemas
│       ├── exceptions.py                #     Domain exceptions
│       ├── config/
│       │   ├── config_manager.py        #     Load agents_config_optimized.yaml
│       │   └── ircot_config.py          #     IRCoT configuration
│       └── container/
│           ├── container.py             #     DI container (singleton)
│           ├── agent_factory.py         #     Create agents from YAML config
│           ├── port_providers.py        #     Provide AgentPort, RAGServicePort
│           ├── graph_providers.py       #     Provide Neo4j adapter
│           └── orchestration_providers.py  # Provide orchestrators
│
├── config/
│   └── agents_config_optimized.yaml     # Agent models, system prompts, thresholds
│
├── Dockerfile                           # Multi-stage build, port 8001
├── start_server.sh                      # Dev startup script
├── requirements.txt                     # fastapi, langgraph, aiohttp, …
├── pytest.ini                           # Test configuration
└── .env.example                         # Template biến môi trường
```

---

## 🔀 Pipeline xử lý

```
User query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 0: Contextual Rewriting                           │
│  (Nếu có chat history → rewrite câu hỏi follow-up      │
│   thành standalone query)                               │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Smart Planner  (GPT-4o-mini, 1 LLM call)      │
│  • Phân loại intent (greeting / informational / …)      │
│  • Chấm complexity score 0-10                           │
│  • Chọn strategy: direct / standard_rag / advanced_rag  │
│  • Query rewriting + filter extraction                  │
└──────────────────────────┬──────────────────────────────┘
                           ▼
              ┌─ simple (score ≤ 3.5) ──→ Direct Response (no LLM)
              │
              ├─ medium ──→ Standard RAG retrieval
              │
              └─ complex (score ≥ 6.5) ──→ IRCoT + Graph Reasoning
                                              │
                    ┌─────────────────────────┤
                    ▼                         ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  Vector + BM25 (parallel)│  │  Neo4j Graph Reasoning   │
│  via RAG Service :8000   │  │  (ReAct / Symbolic R001- │
│                          │  │   R008 rules)            │
└────────────┬─────────────┘  └────────────┬─────────────┘
             └──────────┬──────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Answer Agent  (GPT-5.1-chat, 1 LLM call)      │
│  • Tổng hợp context → câu trả lời tiếng Việt           │
│  • Built-in formatting (emoji, structure, greeting)     │
│  • Citation với char_spans                              │
│  • Streaming support (SSE)                              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
                    Final response → Frontend
```

> **Cost:** ~2 LLM calls/request (vs 5 calls ở pipeline gốc) → tiết kiệm ~60 % chi phí, giảm ~33 % latency.

---

## 🚀 Khởi chạy

### Yêu cầu

- Python 3.11+
- RAG Service đang chạy tại `localhost:8000`
- Neo4j *(optional, cho Graph Reasoning)* tại `localhost:7687`

### Cài đặt

```bash
cd backend/orchestrator

# Virtual environment
python -m venv venv && source venv/bin/activate

# Shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Config
cp .env.example .env
# → Sửa .env: điền OPENROUTER_API_KEY bắt buộc
```

### Chạy

```bash
# Dev (hot-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Hoặc dùng script
bash start_server.sh

# Docker
docker build -t orchestrator .
docker run -p 8001:8001 --env-file .env orchestrator
```

### Swagger Docs

Khi service chạy → truy cập `http://localhost:8002/docs` (Swagger) hoặc `/redoc`.

---

## 📡 API Endpoints

| Method | Path | Mô tả |
|--------|------|--------|
| `POST` | `/api/v1/chat` | Multi-agent pipeline (stream / non-stream) |
| `POST` | `/api/v1/chat/simple` | Single-agent pipeline (nhanh hơn, ít phức tạp) |
| `GET` | `/api/v1/health` | Health check toàn bộ components |
| `GET` | `/api/v1/agents/info` | Thông tin agents, pipeline, IRCoT config |
| `POST` | `/api/v1/agents/test` | Test multi-agent system end-to-end |
| `GET` | `/api/v1/conversations` | List conversations đang active |
| `DELETE` | `/api/v1/conversations/{session_id}` | Xóa conversation |
| `POST` | `/api/v1/conversations/cleanup` | Dọn dẹp conversations cũ |

### Ví dụ request

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Điều kiện để học vượt tại UIT là gì?",
    "session_id": "user-123",
    "use_rag": true,
    "use_knowledge_graph": true,
    "rag_top_k": 5,
    "stream": false
  }'
```

### Streaming (SSE)

```bash
curl -N -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Quy trình đăng ký học phần?", "stream": true}'
```

---

## ⚙️ Biến môi trường chính

| Biến | Mô tả | Mặc định |
|------|--------|----------|
| `OPENROUTER_API_KEY` | **Bắt buộc** — API key từ openrouter.ai | — |
| `OPENROUTER_BASE_URL` | OpenRouter base URL | `https://openrouter.ai/api/v1` |
| `RAG_SERVICE_URL` | URL của RAG Service | `http://localhost:8001` |
| `NEO4J_URI` | Neo4j connection string | `bolt://localhost:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | Neo4j credentials | `neo4j` / `uitchatbot` |
| `USE_SYMBOLIC_REASONING` | Bật symbolic rules R001-R008 | `true` |
| `LOG_LEVEL` | Logging level (`DEBUG` / `INFO` / `WARNING`) | `INFO` |
| `PORT` | Server port | `8002` |

---

## 🧩 Kiến trúc chi tiết

### Ports & Adapters (Hexagonal Architecture)

```
              ┌─── Inbound ───┐           ┌─── Outbound ───┐
              │  FastAPI       │           │  OpenRouter     │
  Frontend ──→│  routes.py     │──→ Domain │  (LLM calls)   │
              │                │   Logic   │                 │
              └────────────────┘           │  RAG Service    │
                                           │  (HTTP client)  │
                                           │                 │
                                           │  Neo4j          │
                                           │  (graph adapter)│
                                           └─────────────────┘
```

- **Ports:** `AgentPort`, `RAGServicePort`, `ConversationManagerPort` — abstract interfaces
- **Adapters:** `OpenRouterAdapter`, `RAGServiceAdapter`, `Neo4jAdapter` — concrete implementations
- **Container:** DI container (`container.py`) wires everything together at startup

### Agent Config (YAML-driven)

Agent models, system prompts, và parameters được cấu hình trong `config/agents_config_optimized.yaml`.
Không cần sửa code khi thay đổi model hoặc prompt — chỉ cần sửa YAML.

### LangGraph Workflow

Cho complex queries, hệ thống dùng LangGraph `StateGraph` với IRCoT loop:

```
START → plan → retrieve ⟷ reason → answer → END
                  ↑______________|
              (loop nếu confidence thấp)
```

---

## 🧪 Testing

```bash
cd backend/orchestrator

# Chạy tất cả tests
pytest

# Chạy test cụ thể
pytest tests/ -k "test_planner"

# Coverage
pytest --cov=app

# Debug mode
LOG_LEVEL=DEBUG pytest -s
```

---

## 🐛 Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|------|-------------|-----------|
| `OPENROUTER_API_KEY is required` | Chưa set API key | Điền vào `.env` |
| `RAG service connection failed` | RAG Service chưa chạy | Chạy RAG Service trước (`cd ../rag && python start_server.py`) |
| `Graph Reasoning Agent not initialized` | Neo4j chưa chạy | Chạy Neo4j hoặc ignore (KG là optional) |
| `Import error: shared.domain` | Chưa cài shared package | `pip install -e ../shared` |
| Port conflict | Port 8002 đã bị chiếm | Đổi `PORT` trong `.env` hoặc kill process cũ |
