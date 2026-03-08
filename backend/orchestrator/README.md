# 🎯 Orchestrator Service

> FastAPI microservice that orchestrates the multi-agent pipeline for Chatbot-Legal.
> Receives questions from the frontend → plans a strategy → calls the RAG Service for context → generates answers via LLM.

| Info | Value |
|------|-------|
| **Port** | `8001` (Docker) / `8002` (local dev) |
| **Framework** | FastAPI + LangGraph |
| **LLM Provider** | OpenRouter (GPT-4o-mini, GPT-5.1-chat, …) |
| **Runtime Dependencies** | RAG Service (port 8000), Neo4j (port 7687, optional) |

---

## 📁 Directory Structure

```
orchestrator/
├── app/
│   ├── main.py                          # FastAPI entrypoint + lifespan
│   │
│   ├── chat/                            # ★ Core chat orchestration
│   │   ├── routes.py                    #   POST /chat, /chat/simple, /chat/stream
│   │   ├── response_mappers.py          #   Map domain → API response
│   │   ├── exception_handlers.py        #   Fallback when pipeline fails
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
│       ├── domain.py                    #     Re-export domain entities (from shared pkg)
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
└── .env.example                         # Environment variable template
```

---

## 🔀 Processing Pipeline

```
User query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 0: Contextual Rewriting                           │
│  (If chat history exists → rewrite follow-up question   │
│   into a standalone query)                              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Smart Planner  (GPT-4o-mini, 1 LLM call)      │
│  • Classify intent (greeting / informational / …)       │
│  • Score complexity 0-10                                │
│  • Select strategy: direct / standard_rag / advanced_rag│
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
│  • Synthesize context → Vietnamese answer               │
│  • Built-in formatting (emoji, structure, greeting)     │
│  • Citation with char_spans                             │
│  • Streaming support (SSE)                              │
└──────────────────────────┬──────────────────────────────┘
                           ▼
                    Final response → Frontend
```

> **Cost:** ~2 LLM calls/request (vs. 5 in the original pipeline) → saves ~60% cost, reduces ~33% latency.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- RAG Service running at `localhost:8000`
- Neo4j Cloud *(optional, for Graph Reasoning)* — configure via `NEO4J_URI` in `.env`

### Installation

```bash
cd backend/orchestrator

# Virtual environment
python -m venv venv && source venv/bin/activate

# Shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Config
cp .env.example .env
# → Edit .env: OPENROUTER_API_KEY is required
```

### Running

```bash
# Dev (hot-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Or use the startup script
bash start_server.sh

# Docker
docker build -t orchestrator .
docker run -p 8001:8001 --env-file .env orchestrator
```

### Swagger Docs

Once the service is running → visit `http://localhost:8002/docs` (Swagger) or `/redoc`.

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/chat` | Multi-agent pipeline (stream / non-stream) |
| `POST` | `/api/v1/chat/simple` | Single-agent pipeline (faster, less complex) |
| `GET` | `/api/v1/health` | Health check for all components |
| `GET` | `/api/v1/agents/info` | Agent info, pipeline config, IRCoT config |
| `POST` | `/api/v1/agents/test` | Test multi-agent system end-to-end |
| `GET` | `/api/v1/conversations` | List active conversations |
| `DELETE` | `/api/v1/conversations/{session_id}` | Delete a conversation |
| `POST` | `/api/v1/conversations/cleanup` | Clean up old conversations |

### Example Request

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the conditions for course overloading at UIT?",
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
  -d '{"query": "What is the course registration process?", "stream": true}'
```

---

## ⚙️ Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | **Required** — API key from openrouter.ai | — |
| `OPENROUTER_BASE_URL` | OpenRouter base URL | `https://openrouter.ai/api/v1` |
| `RAG_SERVICE_URL` | RAG Service URL | `http://localhost:8001` |
| `NEO4J_URI` | Neo4j Cloud connection string | Neo4j Aura endpoint |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Neo4j credentials | Set in `.env` |
| `USE_SYMBOLIC_REASONING` | Enable symbolic rules R001-R008 | `true` |
| `LOG_LEVEL` | Logging level (`DEBUG` / `INFO` / `WARNING`) | `INFO` |
| `PORT` | Server port | `8002` |

---

## 🧩 Architecture Details

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

Agent models, system prompts, and parameters are configured in `config/agents_config_optimized.yaml`.
No code changes needed when switching models or prompts — just edit the YAML file.

### LangGraph Workflow

For complex queries, the system uses a LangGraph `StateGraph` with an IRCoT loop:

```
START → plan → retrieve ⟷ reason → answer → END
                  ↑______________|
              (loop if confidence is low)
```

---

## 🧪 Testing

```bash
cd backend/orchestrator

# Run all tests
pytest

# Run specific tests
pytest tests/ -k "test_planner"

# Coverage
pytest --cov=app

# Debug mode
LOG_LEVEL=DEBUG pytest -s
```

---

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `OPENROUTER_API_KEY is required` | API key not set | Add it to `.env` |
| `RAG service connection failed` | RAG Service not running | Start RAG Service first (`cd ../rag && python start_server.py`) |
| `Graph Reasoning Agent not initialized` | Cannot connect to Neo4j Cloud | Check `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env` |
| `Import error: shared.domain` | Shared package not installed | Run `pip install -e ../shared` |
| Port conflict | Port 8002 already in use | Change `PORT` in `.env` or kill the existing process |
