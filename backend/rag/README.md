# 🔍 RAG Service (Retrieval-Augmented Generation)

> FastAPI microservice handling search, indexing, and knowledge extraction for Chatbot-Legal.
> Combines **Vector Search (Qdrant) + BM25 (OpenSearch) + Cross-Encoder Reranking** with Vietnamese language support.

| Info | Value |
|------|-------|
| **Port** | `8000` |
| **Framework** | FastAPI |
| **Vector DB** | Qdrant Cloud (BAAI/bge-m3) |
| **Keyword Search** | OpenSearch (BM25) |
| **Knowledge Graph** | Neo4j Aura |
| **Reranker** | BAAI/bge-reranker-v2-m3 (cross-encoder) |

---

## 📁 Directory Structure

```
rag/
├── app/
│   ├── main.py                              # FastAPI entrypoint, router includes
│   │
│   ├── search/                              # ★ Core search module
│   │   ├── routes.py                        #   POST /v1/search (vector/bm25/hybrid)
│   │   ├── schemas.py                       #   SearchRequest, SearchResponse
│   │   ├── retrieval_routes.py              #   POST /v1/retrieval/retrieve (legal)
│   │   ├── retrieval_schemas.py             #   RetrievalRequest, RetrievalResponse
│   │   │
│   │   ├── retrieval/                       #   Advanced legal retrieval
│   │   │   ├── unified_retriever.py         #     UnifiedRetriever (RRF fusion + rerank)
│   │   │   ├── legal_query_parser.py        #     Parse article/clause/point references
│   │   │   ├── metadata_filter_builder.py   #     Build Qdrant/OpenSearch metadata filters
│   │   │   ├── neighbor_expander.py         #     Expand to neighboring chunks
│   │   │   └── schemas.py                   #     Internal retrieval schemas
│   │   │
│   │   ├── services/                        #   Application services
│   │   │   ├── search_service.py            #     Main search orchestration
│   │   │   └── api_facade.py                #     Simplified facade for routes
│   │   │
│   │   ├── ports/                           #   Abstract interfaces
│   │   │   ├── repositories.py              #     VectorStorePort, KeywordStorePort
│   │   │   └── services.py                  #     EmbeddingPort, RerankerPort, FusionPort
│   │   │
│   │   └── adapters/                        #   Concrete implementations
│   │       ├── qdrant_vector_adapter.py     #     Qdrant vector search
│   │       ├── opensearch_keyword_adapter.py#     OpenSearch BM25 search
│   │       ├── cross_encoder_reranker.py    #     Cross-encoder reranking
│   │       ├── integration_adapter.py       #     RRF score fusion
│   │       ├── service_adapters.py          #     Embedding adapter
│   │       ├── mappers/                     #     Data mapping helpers
│   │       └── llamaindex/                  #     LlamaIndex hybrid retriever
│   │           ├── hybrid_retriever.py      #       Custom hybrid retriever
│   │           ├── retriever.py             #       Base retriever wrapper
│   │           ├── search_service.py        #       LlamaIndex search service
│   │           └── postprocessors.py        #       Result post-processing
│   │
│   ├── ingest/                              # ★ Document ingestion pipeline
│   │   ├── routes.py                        #   POST /v1/ingest/docx, job management
│   │   ├── opensearch_routes.py             #   OpenSearch-specific ingestion
│   │   ├── schemas.py                       #   IngestRequest, IngestResponse
│   │   │
│   │   ├── loaders/                         #   Document parsers
│   │   │   └── llamaindex_legal_parser.py   #     LlamaParse + python-docx for PDF/DOCX
│   │   │
│   │   ├── indexing/                        #   Index builders
│   │   │   ├── index_semantic_data.py       #     Index → Qdrant (vector)
│   │   │   ├── index_opensearch_data.py     #     Index → OpenSearch (BM25)
│   │   │   ├── graph_builder.py             #     Build Knowledge Graph (Neo4j)
│   │   │   └── sync_entity_nodes.py         #     Sync entities across stores
│   │   │
│   │   ├── store/                           #   Low-level store operations
│   │   │   ├── opensearch/                  #     OpenSearch index management
│   │   │   └── vector/                      #     Qdrant collection management
│   │   │
│   │   └── services/                        #   Ingestion services
│   │       ├── ingest_service.py            #     Main ingestion orchestration
│   │       ├── legal_ingestion_service.py   #     Legal-specific ingestion
│   │       ├── job_store.py                 #     Background job state (Redis)
│   │       └── query_optimizer.py           #     Query optimization
│   │
│   ├── extraction/                          # ★ KG entity extraction
│   │   ├── routes.py                        #   POST /v1/extraction/llamaindex
│   │   └── pipeline/                        #   Extraction pipeline
│   │       ├── llamaindex_extractor.py      #     LlamaIndex + LlamaParse main extractor
│   │       ├── cleaner.py                   #     Text cleaning / normalization
│   │       ├── page_merger.py               #     Merge extracted pages
│   │       ├── post_processor.py            #     Post-extraction processing
│   │       └── schemas.py                   #     Extraction schemas
│   │
│   ├── knowledge_graph/                     # ★ Knowledge Graph service
│   │   ├── routes.py                        #   GET /v1/kg/stats, /v1/kg/graph, /v1/kg/search
│   │   ├── models.py                        #   KG data models
│   │   ├── schema_mapper.py                 #   Map extracted entities → Neo4j schema
│   │   ├── builders/                        #   KG construction
│   │   │   ├── config.py                    #     KG builder configuration
│   │   │   └── llm_builder.py               #     LLM-assisted KG building
│   │   └── stores/                          #   KG storage
│   │       ├── base.py                      #     Abstract KG store
│   │       └── neo4j_store.py               #     Neo4j implementation
│   │
│   ├── embedding/                           #   Embedding endpoints
│   │   ├── routes.py                        #   POST /v1/embedding/embed
│   │   └── schemas.py                       #   EmbedRequest, EmbedResponse
│   │
│   ├── health/                              #   Health monitoring
│   │   ├── routes.py                        #   GET /v1/health
│   │   └── health_v2.py                     #   Comprehensive dependency checks
│   │
│   ├── admin/                               #   Admin operations
│   │   └── routes.py                        #   Admin endpoints
│   │
│   ├── llm/                                 #   LLM client adapters
│   │   ├── llm_client.py                    #   Base LLM client
│   │   ├── openai_client.py                 #   OpenAI adapter
│   │   ├── openrouter_client.py             #   OpenRouter adapter
│   │   └── gemini_client.py                 #   Google Gemini adapter
│   │
│   └── shared/                              #   Cross-cutting concerns
│       ├── config/
│       │   ├── settings.py                  #     Pydantic BaseSettings (all env vars)
│       │   └── logging.py                   #     Logging configuration
│       ├── container/
│       │   ├── container.py                 #     DI container (singleton)
│       │   └── ingest_factory.py            #     Factory for ingestion components
│       ├── schemas/                         #     Shared Pydantic schemas
│       └── utils/                           #     Utility functions
│
├── data/                                    # Document storage (uploads, exports)
├── start_server.py                          # Dev startup script
├── requirements.txt                         # Dependencies
├── pytest.ini                               # Test configuration
├── .env.example                             # Environment variable template
└── .env.openrouter                          # OpenRouter-specific config
```

---

## 🔀 Search Pipeline (Hybrid Search)

```
User query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Query Parsing                                  │
│  • Legal query parser (Article 5, Clause 2, Point a)    │
│  • Extract metadata filters (document, article, clause) │
│  • Query rewriting (optional)                           │
└──────────────────────────┬──────────────────────────────┘
                           ▼
         ┌─────────────────┼─────────────────┐
         ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  Vector Search   │              │  BM25 Search     │
│  (Qdrant)        │              │  (OpenSearch)    │
│  BAAI/bge-m3     │              │  Vietnamese      │
│  embeddings      │              │                  │
└────────┬─────────┘              └────────┬─────────┘
         │                                 │
         └────────────┬────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: RRF Fusion (Reciprocal Rank Fusion)            │
│  • Merge rankings from vector + BM25                    │
│  • k = 60, normalize scores                             │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Cross-Encoder Reranking                        │
│  • BAAI/bge-reranker-v2-m3                              │
│  • Re-score (query, document) pairs                     │
│  • Filter by threshold                                  │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: Neighbor Expansion (optional)                  │
│  • Fetch adjacent chunks for richer context             │
└──────────────────────────┬──────────────────────────────┘
                           ▼
                   Ranked documents → Orchestrator
```

---

## 📥 Ingestion Pipeline (Document → Index)

```
DOCX/PDF file upload
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Parse                                          │
│  • llamaindex_legal_parser.py → structured hierarchy    │
│  • Detect: Chapter, Section, Article, Clause, Point     │
│  • Preserve metadata (article_number, clause, etc.)     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Chunk & Embed                                  │
│  • Semantic chunking (respect article boundaries)       │
│  • BAAI/bge-m3 embeddings                               │
└──────────────────────────┬──────────────────────────────┘
                           ▼
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                  ▼
┌────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  Qdrant        │ │  OpenSearch  │ │  Neo4j KG       │
│  (vectors)     │ │  (BM25 text) │ │  (entities &    │
│                │ │              │ │   relations)    │
└────────────────┘ └──────────────┘ └─────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Qdrant Cloud — vector database
- OpenSearch (port 9200) — keyword search
- Neo4j Aura — knowledge graph
- Redis (port 6379, optional) — background job state

### Installation

```bash
cd backend/rag

# Virtual environment
python -m venv venv && source venv/bin/activate

# Shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Config
cp .env.example .env
# → Edit .env: add connection strings for Qdrant Cloud, OpenSearch, Neo4j Aura
```

### Running Infrastructure (Docker)

```bash
cd infrastructure

# All services
docker compose up -d

# Or individual services
docker compose -f docker-compose.opensearch.yml up -d
# Qdrant Cloud & Neo4j Aura — no Docker needed, configure via .env
```

### Running the RAG Service

```bash
# Dev (hot-reload)
python start_server.py
# → default: http://localhost:8000

# Or directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Swagger Docs

Once the service is running → visit `http://localhost:8000/docs` (Swagger) or `/redoc`.

---

## 📡 API Endpoints

### Search

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/search` | Hybrid search (vector / bm25 / hybrid mode) |
| `POST` | `/v1/retrieval/retrieve` | Legal retrieval with query parsing + metadata filter |

### Ingestion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/ingest/docx` | Upload & ingest DOCX document |
| `GET` | `/v1/ingest/jobs/{job_id}` | Check ingestion job status |
| `POST` | `/v1/ingest/opensearch` | Ingest directly into OpenSearch |

### Extraction

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/extraction/llamaindex` | Extract entities using LlamaIndex + LlamaParse |

### Knowledge Graph

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/kg/stats` | KG statistics (nodes, relations, labels) |
| `GET` | `/v1/kg/graph` | Visualize graph data |
| `POST` | `/v1/kg/search` | Search entities / relations in the KG |

### Embedding & Health

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/embedding/embed` | Generate embeddings for text |
| `GET` | `/v1/health` | Health check for all dependencies |

### Example Requests

```bash
# Hybrid search
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Course registration conditions",
    "mode": "hybrid",
    "top_k": 5
  }'

# Legal retrieval (with query parsing)
curl -X POST http://localhost:8000/v1/retrieval/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "According to Article 5 Clause 2 of the training regulations",
    "top_k": 5,
    "rerank": true
  }'

# Upload document
curl -X POST http://localhost:8000/v1/ingest/docx \
  -F "file=@Legal-Document-24-2018.docx"
```

---

## ⚙️ Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| **Qdrant** | | |
| `QDRANT_URL` | Qdrant Cloud URL | Qdrant Cloud endpoint |
| `QDRANT_COLLECTION_NAME` | Collection name | `vietnamese_documents` |
| **OpenSearch** | | |
| `OPENSEARCH_URL` | OpenSearch URL | `https://localhost:9200` |
| `OPENSEARCH_INDEX` | Index name | `legal_documents` |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | Credentials | `admin` / `admin` |
| **Neo4j** | | |
| `NEO4J_URI` | Neo4j Aura URI | Neo4j Aura endpoint |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | Credentials | Set in `.env` |
| **Embedding** | | |
| `EMBEDDING_MODEL` | Sentence-transformer model | `BAAI/bge-m3` |
| `EMBEDDING_DEVICE` | Device (cpu/cuda) | `cpu` |
| **Reranking** | | |
| `RERANKER_MODEL` | Cross-encoder model | `BAAI/bge-reranker-v2-m3` |
| `RERANKER_TOP_K` | Number of documents after reranking | `5` |
| **LLM** | | |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `OPENAI_API_KEY` | OpenAI API key (for extraction) | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| **General** | | |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis URL (job state) | `redis://localhost:6379` |

---

## 🧩 Architecture Details

### Ports & Adapters

```
                ┌─── Inbound ───┐           ┌─── Outbound ───────────┐
                │  FastAPI       │           │  Qdrant (vectors)      │
 Orchestrator ─→│  routes.py     │──→ Domain │  OpenSearch (BM25)     │
                │                │   Logic   │  Neo4j (KG)            │
                └────────────────┘           │  Cross-encoder (local) │
                                             │  OpenRouter / OpenAI   │
                                             │  Redis (jobs)          │
                                             └────────────────────────┘
```

- **Ports:** `VectorStorePort`, `KeywordStorePort`, `EmbeddingPort`, `RerankerPort`, `FusionPort`
- **Adapters:** `QdrantVectorAdapter`, `OpenSearchKeywordAdapter`, `CrossEncoderReranker`, `IntegrationAdapter`
- **Container:** `container.py` — singleton DI, lazy initialization

### Legal Query Parser

Vietnamese legal document references are automatically parsed:

```
"According to Article 5 Clause 2 Point a of Law 24/2018"
    → article_number: 5
    → clause_number: 2
    → point: "a"
    → document_ref: "Law 24/2018"
```

The parser extracts metadata → filters directly on Qdrant/OpenSearch → higher precision.

### Reciprocal Rank Fusion (RRF)

Combines results from Vector + BM25 using RRF scoring:

$$\text{RRF}(d) = \sum_{r \in R} \frac{1}{k + r(d)}$$

Where $k = 60$ and $r(d)$ is the rank of document $d$ in each ranking list.

---

## 🧪 Testing

```bash
cd backend/rag

# Run all tests
pytest

# Run specific tests
pytest tests/ -k "test_search"

# Coverage
pytest --cov=app

# Debug mode
LOG_LEVEL=DEBUG pytest -s
```

---

## 🐛 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `Qdrant connection failed` | Cannot reach Qdrant Cloud | Check `QDRANT_URL` and `QDRANT_API_KEY` in `.env` |
| `OpenSearch SSL error` | Certificate issue | Set `OPENSEARCH_VERIFY_CERTS=false` in `.env` |
| `Neo4j authentication failed` | Wrong credentials | Check `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `.env` |
| `CUDA out of memory` | GPU out of RAM for embedding | Set `EMBEDDING_DEVICE=cpu` |
| `Import error: shared` | Shared package not installed | Run `pip install -e ../shared` |
| Collection not found | Qdrant collection not created | Run ingestion or create collection manually |
| Port 8000 already in use | Port occupied | Kill the existing process or change port in `start_server.py` |
