# Backend Setup Guide - Chatbot-UIT

Hướng dẫn khởi động backend cho dự án Chatbot-UIT.

## 📋 Prerequisites

### 1. Docker
Đảm bảo Docker đã được cài đặt và đang chạy:
```bash
docker --version
docker ps
```

Nếu chưa có Docker:
- **Linux**: `sudo apt-get install docker.io docker-compose`
- **macOS/Windows**: Cài Docker Desktop từ https://www.docker.com/products/docker-desktop

### 2. Conda Environment
Tạo và kích hoạt conda environment:
```bash
# Tạo environment (chỉ cần làm 1 lần)
conda create -n chatbot-UIT python=3.11 -y

# Kích hoạt environment
conda activate chatbot-UIT

# Cài đặt dependencies
cd services/rag_services
pip install -r requirements.txt

cd ../orchestrator
pip install -r requirements.txt
```

### 3. Environment Variables
Đảm bảo file `.env` đã được cấu hình:

**services/orchestrator/.env:**
```bash
OPENROUTER_API_KEY=your_api_key_here
RAG_SERVICE_URL=http://localhost:8000
PORT=8001
LOG_LEVEL=info
```

**services/rag_services/.env:**
```bash
APP_ENV=dev
PORT=8000
VECTOR_BACKEND=weaviate
WEAVIATE_URL=http://localhost:8090
```

## 🚀 Quick Start

### Khởi động toàn bộ backend (1 lệnh duy nhất):

```bash
# 1. Kích hoạt conda environment
conda activate chatbot-UIT

# 2. Chạy script khởi động
python start_backend.py
```

Script này sẽ tự động:
1. ✅ Kiểm tra Docker đang chạy
2. ✅ Khởi động OpenSearch (port 9200)
3. ✅ Khởi động Weaviate (port 8090)
4. ✅ Khởi động RAG Service (port 8000)
5. ✅ Khởi động Orchestrator Service (port 8001)
6. ✅ Kiểm tra health của tất cả services
7. ✅ Giữ các services chạy cho đến khi bạn nhấn Ctrl+C

## 📝 Usage

### Khởi động backend
```bash
conda activate chatbot-UIT
python start_backend.py
```

### Bỏ qua Docker services (nếu đã chạy rồi)
```bash
python start_backend.py --skip-docker
```

### Dừng tất cả services
```bash
python start_backend.py --stop
```

hoặc nhấn **Ctrl+C** khi script đang chạy.

## 🔍 Kiểm tra Services

### Health Checks
```bash
# RAG Service
curl http://localhost:8000/v1/health

# Orchestrator Service
curl http://localhost:8001/api/v1/health

# OpenSearch
curl http://localhost:9200/_cluster/health

# Weaviate
curl http://localhost:8090/v1/.well-known/ready
```

### API Documentation
- **RAG Service**: http://localhost:8000/docs
- **Orchestrator Service**: http://localhost:8001/docs
- **OpenSearch Dashboards**: http://localhost:5601

### View Logs
```bash
# Docker logs
docker logs opensearch-node1
docker logs vietnamese-rag-weaviate

# Service output trong terminal nơi bạn chạy start_backend.py
```

## 🧪 Testing

### Test với demo script
```bash
conda activate chatbot-UIT
python services/orchestrator/tests/demo_agent_rag.py
```

### Test API endpoints
```bash
# Test RAG search
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Quy định về học phí UIT", "top_k": 5}'

# Test Orchestrator chat
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Học phí UIT năm 2024 là bao nhiêu?",
    "conversation_id": "test-123"
  }'
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Port 3000)                     │
│                    (Bạn sẽ phát triển)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Service (Port 8001)                │
│         - Agent routing                                      │
│         - Conversation management                            │
│         - LLM integration                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│                RAG Service (Port 8000)                       │
│         - Vector search (Weaviate)                           │
│         - Keyword search (OpenSearch)                        │
│         - Hybrid ranking                                     │
└──────────────┬──────────────────┬───────────────────────────┘
               │                  │
               ↓                  ↓
    ┌──────────────────┐  ┌──────────────────┐
    │    Weaviate       │  │   OpenSearch     │
    │   (Port 8090)     │  │   (Port 9200)    │
    └──────────────────┘  └──────────────────┘
```

## 🐛 Troubleshooting

### Port đã được sử dụng
```bash
# Kiểm tra process đang dùng port
lsof -i :8000
lsof -i :8001

# Kill process
kill -9 <PID>
```

### Docker không khởi động
```bash
# Kiểm tra Docker
sudo systemctl status docker

# Khởi động Docker
sudo systemctl start docker
```

### Dependencies bị thiếu
```bash
conda activate chatbot-UIT
cd services/rag_services
pip install -r requirements.txt --force-reinstall

cd ../orchestrator
pip install -r requirements.txt --force-reinstall
```

### Network conflict (Docker)
```bash
# Xóa tất cả Docker services
cd services/rag_services/docker
docker-compose -f docker-compose.weaviate.yml down
docker-compose -f docker-compose.opensearch.yml down

# Xóa network
docker network rm docker_rag-network

# Chạy lại start_backend.py
```

### Import error: No module named 'sentence_transformers'
```bash
conda activate chatbot-UIT
pip install sentence-transformers transformers torch
```

## 📦 Services Details

### RAG Service (Port 8000)
- **Mục đích**: Tìm kiếm tài liệu liên quan
- **Endpoints chính**:
  - `POST /v1/search` - Hybrid search
  - `GET /v1/health` - Health check
  - `POST /v1/opensearch/search` - Keyword search only
  
### Orchestrator Service (Port 8001)
- **Mục đích**: Điều phối agents và LLM
- **Endpoints chính**:
  - `POST /api/v1/chat` - Chat với agent
  - `GET /api/v1/health` - Health check
  - `GET /api/v1/conversations` - Lấy lịch sử conversation

### OpenSearch (Port 9200)
- **Mục đích**: BM25 keyword search
- **Dashboard**: http://localhost:5601

### Weaviate (Port 8090)
- **Mục đích**: Vector similarity search
- **API**: http://localhost:8090/v1

## 🔄 Development Workflow

### Phát triển Frontend

Sau khi backend đã chạy với `start_backend.py`, bạn có thể:

1. Tạo frontend app (React/Vue/Next.js) ở thư mục `frontend/`
2. Frontend sẽ gọi API tới:
   - `http://localhost:8001` - Orchestrator (main API)
   - `http://localhost:8000` - RAG Service (nếu cần direct access)

3. Ví dụ integration từ frontend:
```javascript
// Gửi tin nhắn chat
const response = await fetch('http://localhost:8001/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Học phí UIT là bao nhiêu?',
    conversation_id: 'user-123'
  })
});

const data = await response.json();
console.log(data.response); // Câu trả lời từ chatbot
```

### Restart Backend
Khi thay đổi code backend:
```bash
# Dừng services
Ctrl+C

# Khởi động lại
python start_backend.py
```

## 📚 Next Steps

1. ✅ Backend đã chạy thành công
2. 🎨 Phát triển Frontend:
   - Tạo UI chat interface
   - Integrate với API endpoint `http://localhost:8001/api/v1/chat`
   - Hiển thị conversation history
   - Real-time updates (WebSocket hoặc polling)

3. 📊 Monitoring:
   - Xem logs trong terminal
   - Check OpenSearch Dashboards cho data
   - Monitor Docker containers

## 🆘 Support

Nếu gặp vấn đề:
1. Check logs trong terminal
2. Verify tất cả ports đang free: `lsof -i :8000,8001,9200,8090`
3. Kiểm tra Docker: `docker ps`
4. Ensure conda env: `conda env list`

## 📄 License

MIT License - Chatbot-UIT Project
