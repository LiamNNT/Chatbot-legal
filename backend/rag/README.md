# 🔍 RAG Service (Retrieval-Augmented Generation)

> FastAPI microservice xử lý tìm kiếm, indexing và trích xuất tri thức cho Chatbot-UIT.
> Kết hợp **Vector Search (Weaviate) + BM25 (OpenSearch) + Cross-Encoder Reranking** với hỗ trợ ngôn ngữ Tiếng Việt.

| Thông tin | Giá trị |
|-----------|---------|
| **Port** | `8000` |
| **Framework** | FastAPI |
| **Vector DB** | Weaviate (multilingual-e5-base) |
| **Keyword Search** | OpenSearch (BM25) |
| **Knowledge Graph** | Neo4j |
| **Reranker** | ms-marco-MiniLM-L-6-v2 (cross-encoder) |

---

## 📁 Cấu trúc thư mục

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
│   │   │   ├── legal_query_parser.py        #     Parse Điều/Khoản/Điểm references
│   │   │   ├── metadata_filter_builder.py   #     Build Weaviate metadata filters
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
│   │       ├── weaviate_vector_adapter.py   #     Weaviate vector search
│   │       ├── opensearch_keyword_adapter.py#     OpenSearch BM25 search
│   │       ├── cross_encoder_reranker.py    #     Cross-encoder reranking
│   │       ├── integration_adapter.py       #     RRF score fusion
│   │       ├── service_adapters.py          #     Embedding adapter
│   │       ├── llamaindex_vector_adapter.py #     LlamaIndex-based vector search
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
│   │   │   ├── llamaindex_legal_parser.py   #     LlamaParse + GPT-4o extraction
│   │   │   └── vietnam_legal_docx_parser.py #     Vietnamese legal DOCX structure parser
│   │   │
│   │   ├── indexing/                        #   Index builders
│   │   │   ├── index_semantic_data.py       #     Index → Weaviate (vector)
│   │   │   ├── index_opensearch_data.py     #     Index → OpenSearch (BM25)
│   │   │   ├── graph_builder.py             #     Build Knowledge Graph (Neo4j)
│   │   │   └── sync_entity_nodes.py         #     Sync entities across stores
│   │   │
│   │   ├── store/                           #   Low-level store operations
│   │   │   ├── opensearch/                  #     OpenSearch index management
│   │   │   └── vector/                      #     Weaviate collection management
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
│       │   └── ingest_factory.py            #     Factory cho ingestion components
│       ├── schemas/                         #     Shared Pydantic schemas
│       └── utils/                           #     Utility functions
│
├── data/                                    # Document storage (uploads, exports)
├── start_server.py                          # Dev startup script
├── Dockerfile                               # Not yet (use manual startup)
├── requirements.txt                         # Dependencies
├── pytest.ini                               # Test configuration
├── .env.example                             # Template biến môi trường
└── .env.openrouter                          # OpenRouter-specific config
```

---

## 🔀 Pipeline tìm kiếm (Hybrid Search)

```
User query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Query Parsing                                  │
│  • Legal query parser (Điều 5, Khoản 2, Điểm a)        │
│  • Extract metadata filters (document, article, clause) │
│  • Query rewriting (optional)                           │
└──────────────────────────┬──────────────────────────────┘
                           ▼
         ┌─────────────────┼─────────────────┐
         ▼                                   ▼
┌──────────────────┐              ┌──────────────────┐
│  Vector Search   │              │  BM25 Search     │
│  (Weaviate)      │              │  (OpenSearch)    │
│  multilingual-   │              │  Vietnamese      │
│  e5-base         │              │  keyword match   │
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
│  • ms-marco-MiniLM-L-6-v2                               │
│  • Re-score (query, document) pairs                     │
│  • Filter by threshold                                  │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: Neighbor Expansion (optional)                  │
│  • Lấy thêm chunks liền kề để tăng context             │
└──────────────────────────┬──────────────────────────────┘
                           ▼
                   Ranked documents → Orchestrator
```

---

## 📥 Pipeline ingestion (Document → Index)

```
DOCX file upload
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Parse                                          │
│  • vietnam_legal_docx_parser.py → structured hierarchy  │
│  • Detect: Chương, Mục, Điều, Khoản, Điểm             │
│  • Preserve metadata (article_number, clause, etc.)     │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: Chunk & Embed                                  │
│  • Semantic chunking (respect article boundaries)       │
│  • multilingual-e5-base embeddings                      │
└──────────────────────────┬──────────────────────────────┘
                           ▼
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                  ▼
┌────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  Weaviate      │ │  OpenSearch  │ │  Neo4j KG       │
│  (vectors)     │ │  (BM25 text) │ │  (entities &    │
│                │ │              │ │   relations)    │
└────────────────┘ └──────────────┘ └─────────────────┘
```

---

## 🚀 Khởi chạy

### Yêu cầu

- Python 3.11+
- Weaviate (port 8080) — vector database
- OpenSearch (port 9200) — keyword search
- Neo4j (port 7687) — knowledge graph
- Redis (port 6379, optional) — background job state

### Cài đặt

```bash
cd backend/rag

# Virtual environment
python -m venv venv && source venv/bin/activate

# Shared package + dependencies
pip install -e ../shared
pip install -r requirements.txt

# Config
cp .env.example .env
# → Sửa .env: điền connection strings cho Weaviate, OpenSearch, Neo4j
```

### Chạy infrastructure (Docker)

```bash
cd infrastructure

# Tất cả services
docker compose up -d

# Hoặc từng service
docker compose -f docker-compose.weaviate.yml up -d
docker compose -f docker-compose.opensearch.yml up -d
docker compose -f docker-compose.neo4j.yml up -d
```

### Chạy RAG Service

```bash
# Dev (hot-reload)
python start_server.py
# → mặc định: http://localhost:8000

# Hoặc trực tiếp
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Swagger Docs

Khi service chạy → truy cập `http://localhost:8000/docs` (Swagger) hoặc `/redoc`.

---

## 📡 API Endpoints

### Search

| Method | Path | Mô tả |
|--------|------|--------|
| `POST` | `/v1/search` | Hybrid search (vector / bm25 / hybrid mode) |
| `POST` | `/v1/retrieval/retrieve` | Legal retrieval với query parsing + metadata filter |

### Ingestion

| Method | Path | Mô tả |
|--------|------|--------|
| `POST` | `/v1/ingest/docx` | Upload & ingest DOCX document |
| `GET` | `/v1/ingest/jobs/{job_id}` | Kiểm tra trạng thái ingestion job |
| `POST` | `/v1/ingest/opensearch` | Ingest trực tiếp vào OpenSearch |

### Extraction

| Method | Path | Mô tả |
|--------|------|--------|
| `POST` | `/v1/extraction/llamaindex` | Extract entities bằng LlamaIndex + LlamaParse |

### Knowledge Graph

| Method | Path | Mô tả |
|--------|------|--------|
| `GET` | `/v1/kg/stats` | Thống kê KG (nodes, relations, labels) |
| `GET` | `/v1/kg/graph` | Visualize graph data |
| `POST` | `/v1/kg/search` | Search entities / relations trong KG |

### Embedding & Health

| Method | Path | Mô tả |
|--------|------|--------|
| `POST` | `/v1/embedding/embed` | Generate embeddings cho text |
| `GET` | `/v1/health` | Health check toàn bộ dependencies |

### Ví dụ request

```bash
# Hybrid search
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Điều kiện đăng ký học phần",
    "mode": "hybrid",
    "top_k": 5
  }'

# Legal retrieval (có query parsing)
curl -X POST http://localhost:8000/v1/retrieval/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Theo Điều 5 Khoản 2 về quy chế đào tạo",
    "top_k": 5,
    "rerank": true
  }'

# Upload document
curl -X POST http://localhost:8000/v1/ingest/docx \
  -F "file=@Luật-24-2018-QH14.docx"
```

---

## ⚙️ Biến môi trường chính

| Biến | Mô tả | Mặc định |
|------|--------|----------|
| **Weaviate** | | |
| `WEAVIATE_URL` | Weaviate connection URL | `http://localhost:8080` |
| `WEAVIATE_COLLECTION` | Tên collection | `LegalDocuments` |
| **OpenSearch** | | |
| `OPENSEARCH_URL` | OpenSearch URL | `https://localhost:9200` |
| `OPENSEARCH_INDEX` | Tên index | `legal_documents` |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | Credentials | `admin` / `admin` |
| **Neo4j** | | |
| `NEO4J_URI` | Neo4j connection | `bolt://localhost:7687` |
| `NEO4J_USER` / `NEO4J_PASSWORD` | Credentials | `neo4j` / `password` |
| **Embedding** | | |
| `EMBEDDING_MODEL` | Sentence-transformer model | `intfloat/multilingual-e5-base` |
| `EMBEDDING_DEVICE` | Device (cpu/cuda) | `cpu` |
| **Reranking** | | |
| `RERANKER_MODEL` | Cross-encoder model | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| `RERANKER_TOP_K` | Số documents sau rerank | `5` |
| **LLM** | | |
| `OPENROUTER_API_KEY` | OpenRouter API key | — |
| `OPENAI_API_KEY` | OpenAI API key (cho extraction) | — |
| `GEMINI_API_KEY` | Google Gemini API key | — |
| **General** | | |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis URL (job state) | `redis://localhost:6379` |

---

## 🧩 Kiến trúc chi tiết

### Ports & Adapters

```
                ┌─── Inbound ───┐           ┌─── Outbound ───────────┐
                │  FastAPI       │           │  Weaviate (vectors)    │
 Orchestrator ─→│  routes.py     │──→ Domain │  OpenSearch (BM25)     │
                │                │   Logic   │  Neo4j (KG)            │
                └────────────────┘           │  Cross-encoder (local) │
                                             │  OpenRouter / OpenAI   │
                                             │  Redis (jobs)          │
                                             └────────────────────────┘
```

- **Ports:** `VectorStorePort`, `KeywordStorePort`, `EmbeddingPort`, `RerankerPort`, `FusionPort`
- **Adapters:** `WeaviateVectorAdapter`, `OpenSearchKeywordAdapter`, `CrossEncoderReranker`, `IntegrationAdapter`
- **Container:** `container.py` — singleton DI, lazy initialization

### Legal Query Parser

Vietnamese legal document references được tự động parse:

```
"Theo Điều 5 Khoản 2 Điểm a Luật 24/2018"
    → article_number: 5
    → clause_number: 2
    → point: "a"
    → document_ref: "Luật 24/2018"
```

Parser trích xuất metadata → filter trực tiếp trên Weaviate/OpenSearch → precision cao hơn.

### Reciprocal Rank Fusion (RRF)

Kết hợp kết quả từ Vector + BM25 bằng RRF scoring:

$$\text{RRF}(d) = \sum_{r \in R} \frac{1}{k + r(d)}$$

Với $k = 60$, $r(d)$ là rank của document $d$ trong mỗi ranking list.

---

## 🧪 Testing

```bash
cd backend/rag

# Chạy tất cả tests
pytest

# Chạy test cụ thể
pytest tests/ -k "test_search"

# Coverage
pytest --cov=app

# Debug mode
LOG_LEVEL=DEBUG pytest -s
```

---

## 🐛 Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|------|-------------|-----------|
| `Weaviate connection failed` | Weaviate chưa chạy | `docker compose -f docker-compose.weaviate.yml up -d` |
| `OpenSearch SSL error` | Certificate issue | Set `OPENSEARCH_VERIFY_CERTS=false` trong .env |
| `Neo4j authentication failed` | Wrong credentials | Kiểm tra `NEO4J_USER` / `NEO4J_PASSWORD` |
| `CUDA out of memory` | GPU hết RAM cho embedding | Set `EMBEDDING_DEVICE=cpu` |
| `Import error: shared` | Chưa cài shared package | `pip install -e ../shared` |
| Collection not found | Chưa tạo Weaviate collection | Chạy ingestion hoặc tạo collection thủ công |
| Port 8000 already in use | Port bị chiếm | Kill process cũ hoặc đổi port trong `start_server.py` |
