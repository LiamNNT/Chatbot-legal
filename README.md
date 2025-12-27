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
│ OpenSearch  │  │  Weaviate   │  │   Neo4j     │
│ (BM25)      │  │  (Vector)   │  │   (Graph)   │
│ Port 9200   │  │  Port 8090  │  │  Port 7687  │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Cấu trúc thư mục

```
Chatbot-UIT/
├── frontend/                 # React Frontend
│   ├── src/
│   │   ├── components/      # UI Components
│   │   ├── hooks/           # Custom React Hooks
│   │   ├── services/        # API Services
│   │   └── utils/           # Utilities
│   └── package.json
│
├── services/
│   ├── orchestrator/        # Orchestrator Service
│   │   ├── app/
│   │   │   ├── agents/      # AI Agents (ReAct, IRCoT, Graph)
│   │   │   ├── adapters/    # External Service Adapters
│   │   │   ├── api/         # API Routes
│   │   │   └── core/        # Business Logic
│   │   └── requirements.txt
│   │
│   └── rag_services/        # RAG Service
│       ├── app/
│       │   ├── api/         # API Routes
│       │   └── core/        # Search Logic
│       ├── adapters/        # Database Adapters
│       └── requirements.txt
│
├── infrastructure/          # Docker Compose Files
│   ├── docker-compose.yml
│   ├── docker-compose.opensearch.yml
│   ├── docker-compose.weaviate.yml
│   └── docker-compose.neo4j.yml
│
├── scripts/                 # Utility Scripts
│   ├── start_backend.py     # Start all backend services
│   └── stop_backend.py      # Stop all services
│
└── docs/                    # Documentation
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
cd services/rag_services
pip install -r requirements.txt

# Backend - Orchestrator
cd ../orchestrator
pip install -r requirements.txt

# Frontend
cd ../../frontend
npm install
```

### 4. Cấu hình Environment Variables

```bash
# RAG Services
cp services/rag_services/.env.example services/rag_services/.env

# Orchestrator (cần OPENROUTER_API_KEY)
cp services/orchestrator/.env.example services/orchestrator/.env
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
2. ✅ Khởi động Docker services (OpenSearch, Weaviate, Neo4j)
3. ✅ Khởi động RAG Service (port 8000)
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

### Khởi động thủ công (từng service)

```bash
# 1. Docker Services
cd infrastructure
docker compose -f docker-compose.opensearch.yml up -d
docker compose -f docker-compose.weaviate.yml up -d
docker compose -f docker-compose.neo4j.yml up -d

# 2. RAG Service
cd services/rag_services
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Orchestrator Service
cd services/orchestrator
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
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
| Neo4j Browser | http://localhost:7474 | neo4j | uitchatbot |
| Neo4j Bolt | bolt://localhost:7687 | neo4j | uitchatbot |
| OpenSearch | http://localhost:9200 | - | - |
| Weaviate | http://localhost:8090 | - | - |

---

## 🧪 Testing

```bash
# RAG Services tests
cd services/rag_services
pytest tests/

# Orchestrator tests
cd services/orchestrator
pytest tests/
```

---

## 📁 Tài liệu bổ sung

- [RAG Services Documentation](services/rag_services/README.md)
- [Orchestrator Documentation](services/orchestrator/README.md)
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
