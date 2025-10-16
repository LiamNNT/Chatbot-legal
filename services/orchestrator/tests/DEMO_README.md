# Demo Agent + RAG Integration

Test xem Orchestrator Agent có tương tác được với RAG Service không.

## 🚀 Quick Start

### 1. Start Services

```bash
# Từ project root
cd services/orchestrator/tests
chmod +x start_services.sh stop_services.sh
./start_services.sh
```

Hoặc khởi động thủ công:

**Terminal 1 - RAG Service:**
```bash
cd services/rag_services
python start_server.py
# Running on http://localhost:8000
```

**Terminal 2 - Orchestrator:**
```bash
cd services/orchestrator
./start_server.sh
# Running on http://localhost:8001
```

### 2. Run Demo

```bash
cd services/orchestrator/tests
python demo_agent_rag.py
```

## 📋 Demo Modes

### Mode 1: Test RAG trực tiếp
- Gọi RAG API để search
- Không qua agent
- Kiểm tra RAG có hoạt động không

### Mode 2: Test Agent với RAG
- Gọi Orchestrator Agent
- Agent tự quyết định dùng RAG hay không
- Test 4 loại câu hỏi khác nhau

### Mode 3: Interactive Chat
- Chat trực tiếp với agent
- Hỏi đáp tự do
- Real-time response

## 🧪 Sample Questions

```
✅ Câu hỏi nên dùng RAG:
- "Chương trình đào tạo Khoa học Máy tính 2024 có gì?"
- "Điều kiện tốt nghiệp ngành KHMT là gì?"
- "Các học phần bắt buộc trong chương trình"

❌ Câu hỏi không cần RAG:
- "Hello, bạn là ai?"
- "2 + 2 = ?"
- "Thời tiết hôm nay thế nào?"
```

## 🛠️ Services

| Service | Port | Health Check |
|---------|------|--------------|
| RAG Service | 8000 | http://localhost:8000/health |
| Orchestrator | 8001 | http://localhost:8001/health |

## 📝 Expected Flow

```
User Query
    ↓
Orchestrator Agent
    ↓
[Decide: Need RAG?]
    ↓
Yes → Call RAG Service → Get context → Generate answer
No  → Generate answer directly
    ↓
Return to user
```

## 🐛 Troubleshooting

**Service không khởi động:**
```bash
# Check ports
lsof -i :8000
lsof -i :8001

# Check logs
tail -f /tmp/rag_service.log
tail -f /tmp/orchestrator_service.log
```

**Agent không gọi RAG:**
- Check agent routing logic
- Verify RAG service health
- Check agent prompt/instructions

**RAG trả về empty:**
- Verify data đã index: `python scripts/test_rag_quick.py`
- Check Weaviate: `docker ps | grep weaviate`

## 🛑 Stop Services

```bash
./stop_services.sh
```

Hoặc:
```bash
kill $(cat /tmp/rag_service.pid)
kill $(cat /tmp/orchestrator_service.pid)
```
