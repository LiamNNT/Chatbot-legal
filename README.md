# 🤖 Chatbot-UIT

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Hệ thống Chatbot thông minh hỗ trợ sinh viên Trường Đại học Công nghệ Thông tin (UIT)**

*Sử dụng Retrieval-Augmented Generation (RAG) và Multi-Agent Architecture*

[Tính năng](#-tính-năng) •
[Kiến trúc](#-kiến-trúc) •
[Cài đặt](#-cài-đặt) •
[Sử dụng](#-sử-dụng) •
[API](#-api-documentation)

</div>

---

## 📋 Giới thiệu

Chatbot-UIT là hệ thống chatbot thông minh được xây dựng để hỗ trợ sinh viên UIT tra cứu thông tin về:
- 📚 Quy chế đào tạo, học vụ
- 📝 Thủ tục hành chính
- 🎓 Thông tin tuyển sinh
- 📅 Lịch học, lịch thi
- ❓ Các câu hỏi thường gặp

### Đặc điểm nổi bật

- **🔍 Hybrid RAG**: Kết hợp BM25 (keyword search) + Vector Search + Cross-Encoder Reranking
- **🤖 Multi-Agent System**: Sử dụng nhiều agent chuyên biệt để xử lý các loại câu hỏi khác nhau
- **📊 Knowledge Graph**: Tích hợp Neo4j để lưu trữ và truy vấn quan hệ giữa các thực thể
- **🇻🇳 Vietnamese NLP**: Hỗ trợ tối ưu cho tiếng Việt với custom tokenizer và stopwords
- **⚡ Real-time Streaming**: Phản hồi theo thời gian thực với SSE

---

## 🏗 Kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│                    (React + Vite + Tailwind CSS)                        │
│                         http://localhost:5173                            │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR SERVICE                              │
│                    (FastAPI - Port 8001)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Router     │  │  ReAct      │  │  IRCoT      │  │  Graph      │    │
│  │  Agent      │  │  Agent      │  │  Agent      │  │  Reasoning  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          RAG SERVICE                                     │
│                    (FastAPI - Port 8000)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  BM25       │  │  Vector     │  │  Hybrid     │  │  Reranker   │    │
│  │  Search     │  │  Search     │  │  Fusion     │  │             │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└────────┬────────────────┬────────────────┬──────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ OpenSearch  │  │  Qdrant     │  │   Neo4j     │
│ (BM25)      │  │  (Vector)   │  │   (Graph)   │
│ Port 9200   │  │  Port 6333  │  │  Port 7687  │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Cấu trúc thư mục

```
Chatbot-UIT/
├── backend/
│   ├── rag/                     # RAG Service (FastAPI - Port 8000)
│   │   ├── app/
│   │   │   ├── search/          # Hybrid Search (BM25 + Vector + Reranking)
│   │   │   ├── knowledge_graph/ # Knowledge Graph (Neo4j)
│   │   │   │   ├── models.py        # Domain models
│   │   │   │   ├── builders/         # Graph construction strategies
│   │   │   │   └── stores/           # Graph storage adapters
│   │   │   ├── embedding/       # Embedding service
│   │   │   ├── ingest/          # Document ingestion pipeline
│   │   │   ├── extraction/      # Rule extraction
│   │   │   ├── llm/             # LLM client adapters
│   │   │   └── shared/          # Config, DI container
│   │   └── requirements.txt
│   │
│   ├── orchestrator/            # Orchestrator Service (FastAPI - Port 8001)
│   │   ├── app/
│   │   │   ├── chat/            # Chat agents & LangGraph workflow
│   │   │   ├── reasoning/       # Graph reasoning & symbolic engine
│   │   │   ├── conversation/    # Conversation management
│   │   │   ├── admin/           # Admin routes
│   │   │   └── shared/          # Config, DI container, ports
│   │   ├── config/              # Agent YAML configs
│   │   └── requirements.txt
│   │
│   └── shared/                  # Shared domain models (pip-installable)
│       └── src/shared/
│           ├── domain/          # Entities, Value Objects, Exceptions
│           └── ports/           # Abstract port interfaces
│
├── frontend/                    # Streamlit Frontend
│   ├── app.py
│   └── api_client.py
│
├── infrastructure/              # Docker Compose files
│   ├── docker-compose.yml
│   └── docker-compose.opensearch.yml
│
├── scripts/                     # Utility scripts
│   ├── start_backend.py         # Start all backend services
│   └── stop_backend.py          # Stop all services
│
├── data/                        # Data files (uploads, exports, docs)
└── docs/                        # Project documentation
```

---

## 🛠 Cài đặt

### Yêu cầu hệ thống

- **Python** >= 3.11
- **Node.js** >= 18.x
- **Docker** & Docker Compose
- **Conda** (khuyến nghị)

### 1. Clone Repository

```bash
git clone https://github.com/LiamNNT/Chatbot-UIT.git
cd Chatbot-UIT
```

### 2. Tạo Conda Environment

```bash
# Tạo environment
conda create -n chatbot-UIT python=3.11 -y

# Activate environment
conda activate chatbot-UIT
```

### 3. Cài đặt Dependencies

```bash
# Backend - RAG Services
cd backend/rag
pip install -r requirements.txt

# Backend - Orchestrator
cd ../orchestrator
pip install -r requirements.txt

# Backend - Shared package
cd ../shared
pip install -e .

# Frontend
cd ../../frontend
pip install -r requirements.txt
```

### 4. Cấu hình Environment Variables

```bash
# RAG Services
cp backend/rag/.env.example backend/rag/.env

# Orchestrator (cần OPENROUTER_API_KEY)
cp backend/orchestrator/.env.example backend/orchestrator/.env
# Chỉnh sửa file .env và thêm API key
```

---

## 🚀 Sử dụng

### Khởi động Backend (Cách nhanh)

```bash
# Activate conda environment
conda activate chatbot-UIT

# Chạy script khởi động
cd scripts
python start_backend.py
```

Script sẽ tự động:
1. ✅ Stop các services đang chạy (nếu có)
2. ✅ Khởi động Docker services (OpenSearch)
3. ✅ Khởi động RAG Service (port 8000) — kết nối Qdrant Cloud & Neo4j Cloud
4. ✅ Khởi động Orchestrator Service (port 8001)

**Options:**
```bash
python start_backend.py --skip-docker  # Bỏ qua Docker services
python start_backend.py --stop         # Chỉ stop services
```

**Dừng Backend:** Nhấn `Ctrl+C` trong terminal

### Khởi động Frontend

```bash
cd frontend
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173

### Khởi động thủ công (từng service riêng lẻ)

Mỗi service chạy trong **1 terminal riêng**. Nhấn `Ctrl+C` để dừng service đó.

> **Lưu ý**: Dùng flag `-p <tên>` để đặt project name riêng, tránh xung đột giữa các compose file.

```bash
# Terminal 1 — OpenSearch (BM25 Search - port 9200)
cd infrastructure
docker compose -p opensearch -f docker-compose.opensearch.yml up
# Ctrl+C để dừng

# Terminal 2 — RAG Service (port 8000)
# Qdrant Cloud & Neo4j Cloud được cấu hình qua .env
cd backend/rag
python start_server.py
# hoặc: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3 — Orchestrator Service (port 8001)
cd backend/orchestrator
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### Chạy nền (detached mode)

Nếu không muốn giữ terminal mở, dùng flag `-d`:

```bash
cd infrastructure

# Khởi động nền (không cần giữ terminal)
docker compose -p opensearch -f docker-compose.opensearch.yml up -d

# Xem logs
docker logs -f opensearch-node1          # OpenSearch logs

# Dừng service
docker compose -p opensearch -f docker-compose.opensearch.yml down
```

#### Kiểm tra trạng thái services

```bash
# Kiểm tra containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Health check
curl -s http://localhost:9200                        # OpenSearch
```

---

## 📚 API Documentation

Sau khi khởi động services, truy cập API documentation tại:

| Service | Swagger UI | ReDoc |
|---------|------------|-------|
| RAG Service | http://localhost:8000/docs | http://localhost:8000/redoc |
| Orchestrator | http://localhost:8001/docs | http://localhost:8001/redoc |

### Các Endpoint chính

#### Chat API
```http
POST /api/v1/chat
Content-Type: application/json

{
  "query": "Hướng dẫn đăng ký học phần tại UIT?",
  "session_id": "user_123",
  "use_rag": true
}
```

#### RAG Search
```http
POST /v1/search
Content-Type: application/json

{
  "query": "quy chế đào tạo",
  "search_type": "hybrid_rerank",
  "top_k": 5
}
```

#### Health Check
```http
GET /api/v1/health
GET /v1/health
```

---

## 🗄 Database Credentials

| Database | URL | Username | Password |
|----------|-----|----------|----------|
| OpenSearch | http://localhost:9200 | - | - |
| Qdrant Cloud | Configured via `QDRANT_URL` env var | - | API key in `.env` |
| Neo4j Cloud | Configured via `NEO4J_URI` env var | - | Credentials in `.env` |

---

## 🧪 Testing

```bash
# RAG Services tests
cd backend/rag
pytest tests/

# Orchestrator tests
cd backend/orchestrator
pytest tests/
```

---

## 📁 Tài liệu bổ sung

- [RAG Services Documentation](backend/rag/README.md)
- [Orchestrator Documentation](backend/orchestrator/README.md)
- [Frontend Documentation](frontend/README.md)
- [Streaming Implementation](docs/STREAMING_CHANGES_SUMMARY.md)
- [Quick Start Guide](docs/QUICK_START_GUIDE.md)

---

## 👥 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📞 Liên hệ

- **Repository**: [https://github.com/LiamNNT/Chatbot-UIT](https://github.com/LiamNNT/Chatbot-UIT)
- **Issues**: [https://github.com/LiamNNT/Chatbot-UIT/issues](https://github.com/LiamNNT/Chatbot-UIT/issues)

---

<div align="center">
Made with ❤️ for UIT Students
</div>
