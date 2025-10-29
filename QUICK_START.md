# 🎯 Hướng Dẫn Khởi Động Backend - Chatbot-UIT

## ✨ Những gì đã được tạo

Tôi đã tạo một hệ thống khởi động backend **đơn giản và thống nhất** cho bạn:

### 📁 Files mới tạo:

1. **`start_backend.py`** ⭐ - Script chính để khởi động toàn bộ backend
2. **`stop_backend.py`** - Script dừng backend  
3. **`test_backend.py`** - Script test các API endpoints
4. **`quick-ref.sh`** - Quick reference commands
5. **`frontend_integration_examples.py`** - Ví dụ tích hợp frontend
6. **`BACKEND_SETUP.md`** - Hướng dẫn chi tiết đầy đủ

---

## 🚀 Cách Sử Dụng (Siêu Đơn Giản!)

### Bước 1: Setup môi trường (chỉ làm 1 lần)

```bash
# Tạo conda environment
conda create -n chatbot-UIT python=3.11 -y

# Kích hoạt
conda activate chatbot-UIT

# Cài dependencies
cd services/rag_services
pip install -r requirements.txt

cd ../orchestrator  
pip install -r requirements.txt
```

### Bước 2: Khởi động Backend

```bash
# Kích hoạt conda env
conda activate chatbot-UIT

# Chạy backend (1 lệnh duy nhất!)
python start_backend.py
```

**Điều gì sẽ xảy ra:**
1. ✅ Script tự động kiểm tra Docker
2. ✅ Khởi động OpenSearch (port 9200)
3. ✅ Khởi động Weaviate (port 8090)  
4. ✅ Khởi động RAG Service (port 8000)
5. ✅ Khởi động Orchestrator (port 8001)
6. ✅ **Hiển thị logs REAL-TIME trong terminal**
7. ✅ Giữ các services chạy

### Bước 3: Dừng Backend

**Cách 1:** Nhấn `Ctrl+C` trong terminal đang chạy `start_backend.py`
- → Script tự động dừng TẤT CẢ services (RAG, Orchestrator, Docker)

**Cách 2:** Đóng terminal
- → Tất cả processes cũng sẽ bị kill

**Cách 3:** Chạy script dừng
```bash
python stop_backend.py
```

---

## 📊 Cách Hoạt Động

### Khi chạy `python start_backend.py`:

```
┌─────────────────────────────────────────────────────────────┐
│  Terminal của bạn                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🚀 Starting Backend Services...                           │
│  ✓ Docker services started                                 │
│  ✓ RAG Service started on port 8000                        │
│  ✓ Orchestrator started on port 8001                       │
│                                                             │
│  📊 Service URLs:                                          │
│    - RAG: http://localhost:8000                            │
│    - Orchestrator: http://localhost:8001                   │
│                                                             │
│  ──────────────────────────────────────────────────────────│
│  Logs đang hiển thị real-time bên dưới...                 │
│  Nhấn Ctrl+C để dừng tất cả services                       │
│  ──────────────────────────────────────────────────────────│
│                                                             │
│  INFO: RAG Service starting...                             │
│  INFO: Loading embeddings model...                         │
│  INFO: Uvicorn running on http://0.0.0.0:8000             │
│  INFO: Orchestrator service started                        │
│  INFO: Connected to RAG service                            │
│  ...                                                        │
│  [Logs tiếp tục hiển thị real-time]                       │
│                                                             │
│  👈 Nhấn Ctrl+C ở đây để dừng                              │
└─────────────────────────────────────────────────────────────┘
```

### Khi nhấn Ctrl+C:

```
^C
Interrupted by user
🛑 Stopping all backend services...
ℹ Stopping process on port 8000...
ℹ Stopping process on port 8001...
ℹ Stopping Docker services...
✓ All services stopped
```

---

## 🧪 Test Backend

Sau khi khởi động backend, mở **terminal mới** và chạy:

```bash
# Test tất cả endpoints
python test_backend.py

# Hoặc test thủ công
curl http://localhost:8000/v1/health
curl http://localhost:8001/api/v1/health
```

---

## 🎨 Phát Triển Frontend

Backend đã sẵn sàng! Bạn có thể:

### 1. Giữ backend chạy trong 1 terminal:
```bash
terminal-1$ conda activate chatbot-UIT
terminal-1$ python start_backend.py
# [Logs hiển thị ở đây, giữ terminal này mở]
```

### 2. Phát triển frontend trong terminal khác:
```bash
terminal-2$ cd frontend
terminal-2$ npm run dev  # hoặc framework bạn chọn
```

### 3. Frontend gọi API:
```javascript
// Gửi tin nhắn
const response = await fetch('http://localhost:8001/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Học phí UIT là bao nhiêu?',
    conversation_id: 'user-123'
  })
});

const data = await response.json();
console.log(data.response); // Câu trả lời từ bot
```

Xem thêm ví dụ trong file: `frontend_integration_examples.py`

---

## 🔧 Options

### Skip Docker (nếu Docker đã chạy rồi):
```bash
python start_backend.py --skip-docker
```

### Chỉ dừng services:
```bash
python start_backend.py --stop
```

---

## 📖 Documentation

- **Quick Start**: File này
- **Chi tiết đầy đủ**: `BACKEND_SETUP.md`
- **Frontend examples**: `frontend_integration_examples.py`
- **Quick commands**: `./quick-ref.sh`

---

## 🎯 TL;DR - Quá Dài Không Đọc?

```bash
# 1. Setup (1 lần)
conda create -n chatbot-UIT python=3.11 -y
conda activate chatbot-UIT
cd services/rag_services && pip install -r requirements.txt
cd ../orchestrator && pip install -r requirements.txt

# 2. Chạy backend
conda activate chatbot-UIT
python start_backend.py

# 3. Dừng backend  
# → Nhấn Ctrl+C trong terminal đang chạy

# 4. Test
python test_backend.py
```

**Xong!** Giờ bạn có thể phát triển frontend rồi! 🎉

---

## 💡 Tips

1. **Logs real-time**: Tất cả logs từ RAG và Orchestrator hiển thị trong terminal
2. **Auto cleanup**: Khi Ctrl+C hoặc đóng terminal → tất cả services tự động dừng
3. **Error handling**: Nếu service nào lỗi, script sẽ báo và dừng
4. **Health checks**: Script tự động đợi services ready trước khi báo success

---

## 🆘 Troubleshooting

### Port bị chiếm?
```bash
python stop_backend.py
# hoặc
lsof -ti:8000 | xargs kill -9
lsof -ti:8001 | xargs kill -9
```

### Docker không chạy?
```bash
# Start Docker Desktop hoặc
sudo systemctl start docker
```

### Conda env không đúng?
```bash
conda activate chatbot-UIT
python --version  # Should be 3.11.x
```

Xem thêm trong `BACKEND_SETUP.md` 📖

---

**Chúc bạn code frontend vui vẻ! 🚀**
