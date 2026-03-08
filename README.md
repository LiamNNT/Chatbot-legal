# 🎓 Chatbot-Legal — Vietnamese Legal Document Assistant

> An AI-powered chatbot system for querying Vietnamese legal documents, built with a **microservices architecture** combining **Retrieval-Augmented Generation (RAG)**, **Knowledge Graph reasoning**, and **Multi-Agent orchestration**.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117-green.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-red.svg)](https://streamlit.io)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Services](#-services)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)

---

## 🔍 Overview

**Chatbot-Legal** is an end-to-end system that allows users to ask questions about Vietnamese legal documents (laws, regulations, university policies) and receive accurate, cited answers in Vietnamese.

### Key Features

- 🤖 **Multi-Agent Pipeline** — Smart Planner + Answer Agent architecture with only ~2 LLM calls per request
- 🔎 **Hybrid Search** — Combines Vector Search (Qdrant) + BM25 Keyword Search (OpenSearch) with RRF fusion
- 🧠 **Knowledge Graph Reasoning** — Neo4j-based graph with symbolic rules and ReAct agent for complex queries
- 📄 **Legal Document Parsing** — Structured extraction of Vietnamese legal hierarchy (Chương → Mục → Điều → Khoản → Điểm)
- 🔄 **IRCoT (Interleaving Retrieval with Chain-of-Thought)** — LangGraph-powered iterative reasoning for complex questions
- 💬 **Streaming Support** — Real-time Server-Sent Events (SSE) for token-by-token response delivery
- 📊 **Cross-Encoder Reranking** — Improves retrieval precision with neural reranking
- 🗂️ **Conversation Management** — Sliding window context with automatic query rewriting for follow-up questions

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Streamlit Frontend (:8501)                       │
│                    Chat │ RAG Debug │ System │ Ingestion                  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ HTTP / SSE
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     Orchestrator Service (:8002)                         │
│                                                                          │
│   ┌─────────────┐    ┌──────────────────┐    ┌───────────────────┐      │
│   │Smart Planner │───▶│  LangGraph IRCoT │───▶│   Answer Agent    │      │
│   │(GPT-4o-mini) │    │  Workflow Engine  │    │  (GPT-5.1-chat)  │      │
│   └─────────────┘    └──────────────────┘    └───────────────────┘      │
│                              │                         │                 │
│                    ┌─────────┴─────────┐               │                 │
│                    ▼                   ▼               │                 │
│          ┌──────────────┐   ┌──────────────────┐       │                 │
│          │ RAG Adapter  │   │ Neo4j Graph       │       │                 │
│          │ (HTTP Client)│   │ Reasoning Agent   │       │                 │
│          └──────┬───────┘   └──────────────────┘       │                 │
└─────────────────┼──────────────────────────────────────┘                 │
                  │ HTTP                                                    │
                  ▼                                                        │
┌──────────────────────────────────────────────────────────────────────────┐
│                        RAG Service (:8000)                               │
│                                                                          │
│   ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────────┐     │
│   │  Search   │  │  Ingestion │  │Extraction│  │ Knowledge Graph  │     │
│   │  Module   │  │  Pipeline  │  │ Pipeline │  │    Service       │     │
│   └─────┬────┘  └────────────┘  └──────────┘  └──────────────────┘     │
│         │                                                                │
│    ┌────┴────────────┬─────────────────┐                                │
│    ▼                 ▼                 ▼                                 │
│ ┌────────┐    ┌────────────┐    ┌──────────┐                            │
│ │ Qdrant │    │ OpenSearch  │    │  Neo4j   │                            │
│ │(Vector)│    │  (BM25)    │    │  (KG)    │                            │
│ └────────┘    └────────────┘    └──────────┘                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### Request Processing Pipeline

```
User Query
    │
    ├─ Step 0: Contextual Rewriting (if follow-up question → rewrite to standalone)
    │
    ├─ Step 1: Smart Planner (GPT-4o-mini)
    │     • Intent classification (greeting / informational / complex)
    │     • Complexity scoring (0-10)
    │     • Strategy selection: direct | standard_rag | advanced_rag
    │     • Query expansion & metadata filter extraction
    │
    ├─ Step 2: Retrieval
    │     ├─ Simple (score ≤ 3.5) → Direct response (no LLM needed)
    │     ├─ Medium → Standard RAG (Vector + BM25 hybrid search)
    │     └─ Complex (score ≥ 6.5) → IRCoT loop + Graph Reasoning
    │           ├─ Vector + BM25 search (parallel)
    │           ├─ Cross-Encoder reranking
    │           ├─ Neighbor chunk expansion
    │           └─ Neo4j symbolic rules (R001-R008) + ReAct agent
    │
    └─ Step 3: Answer Agent (GPT-5.1-chat)
          • Evidence-based synthesis in Vietnamese
          • Citation with character spans
          • Streaming support (SSE)
          • Hallucination guardrails
```

> **Efficiency:** ~2 LLM calls/request (vs. 5 in the original pipeline) → ~60% cost reduction, ~33% latency improvement.

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit |
| **Backend Framework** | FastAPI |
| **Orchestration** | LangGraph (StateGraph) |
| **LLM Provider** | OpenRouter (GPT-4o-mini, GPT-5.1-chat) |
| **Vector Database** | Qdrant Cloud (BAAI/bge-m3 embeddings) |
| **Keyword Search** | OpenSearch 2.12 (BM25) |
| **Knowledge Graph** | Neo4j Aura |
| **Reranker** | Cross-Encoder (ms-marco-MiniLM-L-6-v2) |
| **Language** | Python 3.11+ |
| **Architecture** | Hexagonal (Ports & Adapters), Microservices |

---

## 📁 Project Structure

```
Chatbot-Legal/
├── frontend/                     # Streamlit web interface
│   ├── app.py                    #   Main app (Chat, RAG Debug, System, Ingestion tabs)
│   ├── api_client.py             #   HTTP client for backend services
│   └── config.py                 #   Frontend configuration
│
├── backend/
│   ├── orchestrator/             # 🎯 Orchestrator Service (port 8002)
│   │   ├── app/
│   │   │   ├── main.py           #     FastAPI entrypoint
│   │   │   ├── chat/             #     Core chat orchestration
│   │   │   │   ├── agents/       #       Smart Planner + Answer Agent
│   │   │   │   ├── adapters/     #       OpenRouter LLM + RAG HTTP adapters
│   │   │   │   ├── services/     #       Orchestration & context services
│   │   │   │   └── langgraph/    #       LangGraph IRCoT workflow
│   │   │   ├── conversation/     #     Conversation management
│   │   │   ├── admin/            #     Health & debug endpoints
│   │   │   └── shared/           #     Config, DI container, ports
│   │   └── config/
│   │       └── agents_config_optimized.yaml  # Agent models & prompts (YAML-driven)
│   │
│   ├── rag/                      # 🔍 RAG Service (port 8000)
│   │   ├── app/
│   │   │   ├── main.py           #     FastAPI entrypoint
│   │   │   ├── search/           #     Hybrid search (Vector + BM25 + Reranking)
│   │   │   ├── ingest/           #     Document ingestion pipeline
│   │   │   ├── extraction/       #     KG entity extraction (LlamaIndex)
│   │   │   ├── knowledge_graph/  #     Neo4j KG queries & builders
│   │   │   ├── embedding/        #     Embedding endpoints
│   │   │   ├── llm/              #     LLM client adapters
│   │   │   └── shared/           #     Config, DI container, utilities
│   │   └── data/                 #     Document storage
│   │
│   └── shared/                   # 📦 Shared Python package (domain models)
│
├── infrastructure/               # 🐳 Docker Compose configs
│   ├── docker-compose.yml        #     OpenSearch
│   └── docker-compose.opensearch.yml
│
├── scripts/                      # 🔧 Utility scripts
│   ├── start_backend.py          #     Start all backend services
│   ├── stop_backend.py           #     Stop all services
│   └── ...                       #     DB management scripts
│
├── data/                         # 📄 Raw documents & exports
└── requirements-base.txt         # Base Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Qdrant Cloud** account (vector database)
- **Neo4j Aura** account (knowledge graph) — *optional*
- **OpenRouter** API key (LLM provider)
- **Docker & Docker Compose** (for OpenSearch)

### 1. Clone the Repository

```bash
git clone https://github.com/LiamNNT/Chatbot-legal.git
cd Chatbot-legal
```

### 2. Start Infrastructure (OpenSearch)

```bash
cd infrastructure
docker compose up -d
```

> Qdrant Cloud & Neo4j Aura are cloud-hosted — configure via `.env` files.

### 3. Set Up RAG Service

```bash
cd backend/rag

# Create virtual environment
python -m venv venv && source venv/bin/activate

# Install shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: add Qdrant Cloud URL, OpenSearch, Neo4j credentials

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Set Up Orchestrator Service

```bash
cd backend/orchestrator

# Create virtual environment
python -m venv venv && source venv/bin/activate

# Install shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: add OPENROUTER_API_KEY (required)

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 5. Start Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

### Quick Start (All Services)

```bash
python scripts/start_backend.py     # Start Docker + RAG + Orchestrator
cd frontend && streamlit run app.py  # Start frontend
```

Access the application at **http://localhost:8501**.

---

## ⚙️ Services

### RAG Service (`:8000`)

Handles document ingestion, indexing, and retrieval.

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Vector (Qdrant) + BM25 (OpenSearch) with RRF fusion |
| **Cross-Encoder Reranking** | ms-marco-MiniLM-L-6-v2 for precision improvement |
| **Legal Document Parser** | Structured extraction of Vietnamese legal hierarchy |
| **Knowledge Graph Builder** | Auto-build Neo4j graph from legal entities |
| **Neighbor Expansion** | Retrieve adjacent chunks for richer context |

### Orchestrator Service (`:8002`)

Multi-agent pipeline that plans, retrieves, reasons, and generates answers.

| Feature | Description |
|---------|-------------|
| **Smart Planner** | GPT-4o-mini for intent classification & routing |
| **Answer Agent** | GPT-5.1-chat for evidence-based answer synthesis |
| **IRCoT Workflow** | LangGraph iterative retrieval + reasoning loop |
| **Graph Reasoning** | Neo4j ReAct agent + symbolic rules (R001-R008) |
| **Conversation Memory** | Sliding window (max 20 messages) with query rewriting |

### Frontend (`:8501`)

Streamlit-based web interface with multiple tabs.

| Tab | Description |
|-----|-------------|
| 💬 **Chat** | Main conversational interface (streaming / non-streaming) |
| 🔍 **RAG Debug** | Inspect retrieved documents & processing statistics |
| ⚙️ **System** | Health checks, agent info, conversation management |
| 📄 **Ingestion** | Upload documents for indexing and KG extraction |

---

## 📡 API Reference

### Orchestrator Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Multi-agent chat (stream / non-stream) |
| `POST` | `/api/v1/chat/simple` | Single-agent chat (faster, simpler) |
| `GET` | `/api/v1/health` | Health check for all components |
| `GET` | `/api/v1/agents/info` | Agent configuration & pipeline info |
| `GET` | `/api/v1/conversations` | List active conversations |
| `DELETE` | `/api/v1/conversations/{session_id}` | Delete a conversation |

### RAG Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/search` | Hybrid search (vector / bm25 / hybrid) |
| `POST` | `/v1/retrieval/retrieve` | Legal retrieval with query parsing |
| `POST` | `/v1/ingest/docx` | Upload & ingest DOCX document |
| `GET` | `/v1/ingest/jobs/{job_id}` | Check ingestion job status |
| `POST` | `/v1/extraction/llamaindex` | Extract entities using LlamaIndex |
| `GET` | `/v1/kg/stats` | Knowledge Graph statistics |
| `GET` | `/v1/kg/search` | Search the Knowledge Graph |
| `GET` | `/v1/health` | Service health check |

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

## ⚙️ Configuration

### Environment Variables

#### Orchestrator Service

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key | ✅ |
| `OPENROUTER_BASE_URL` | OpenRouter base URL | No (default: `https://openrouter.ai/api/v1`) |
| `RAG_SERVICE_URL` | RAG Service URL | No (default: `http://localhost:8000`) |
| `NEO4J_URI` | Neo4j connection string | No (optional for graph reasoning) |
| `NEO4J_USERNAME` | Neo4j username | No |
| `NEO4J_PASSWORD` | Neo4j password | No |
| `USE_SYMBOLIC_REASONING` | Enable symbolic rules R001-R008 | No (default: `true`) |
| `LOG_LEVEL` | Logging level | No (default: `INFO`) |

#### RAG Service

| Variable | Description | Required |
|----------|-------------|----------|
| `QDRANT_URL` | Qdrant Cloud URL | ✅ |
| `QDRANT_API_KEY` | Qdrant Cloud API key | ✅ |
| `OPENSEARCH_HOST` | OpenSearch host | No (default: `localhost`) |
| `OPENSEARCH_PORT` | OpenSearch port | No (default: `9200`) |
| `NEO4J_URI` | Neo4j Aura connection string | No |
| `EMBEDDING_MODEL` | Embedding model name | No (default: `BAAI/bge-m3`) |

### Agent Configuration

Agent models, system prompts, and parameters are configured in `backend/orchestrator/config/agents_config_optimized.yaml`. No code changes required — just edit the YAML file.

---

## 🧪 Testing

```bash
# RAG Service tests
cd backend/rag
pytest

# Orchestrator Service tests
cd backend/orchestrator
pytest

# Run specific tests
pytest tests/ -k "test_search"

# With coverage
pytest --cov=app

# Debug mode
LOG_LEVEL=DEBUG pytest -s
```

---

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `OPENROUTER_API_KEY is required` | Missing API key | Add it to `backend/orchestrator/.env` |
| `RAG service connection failed` | RAG Service not running | Start RAG Service first on port 8000 |
| `Graph Reasoning Agent not initialized` | Neo4j not connected | Check `NEO4J_URI` and credentials in `.env` |
| `Import error: shared.domain` | Shared package not installed | Run `pip install -e ../shared` |
| `OpenSearch connection refused` | Docker not running | Run `docker compose up -d` in `infrastructure/` |
| Port conflict | Port already in use | Change port in `.env` or kill the existing process |

---

## 📄 License

This project is developed for academic purposes at the University of Information Technology (UIT), Vietnam National University Ho Chi Minh City.

---

<p align="center">
  Built with ❤️ using FastAPI, LangGraph, Qdrant, OpenSearch, and Neo4j
</p>
