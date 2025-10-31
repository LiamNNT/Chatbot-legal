# 🚀 Hướng dẫn khởi động nhanh Chatbot UIT

## Tổng quan
Hệ thống Chatbot UIT bao gồm:
- **Backend**: Multi-agent RAG system (Python/FastAPI)
- **Frontend**: React + Tailwind CSS interface
- **Database**: Weaviate (Vector) + OpenSearch (Keyword)

## Khởi động hệ thống

### Bước 1: Khởi động Backend

```bash
# Tại thư mục gốc Chatbot-UIT
conda activate chatbot-UIT
python start_backend.py
```

Backend services sẽ chạy tại:
- Orchestrator API: http://localhost:8001
- RAG Service: http://localhost:8000
- OpenSearch: http://localhost:9200
- Weaviate: http://localhost:8090

### Bước 2: Khởi động Frontend

Mở terminal mới:

```bash
cd frontend
./start_frontend.sh

# Hoặc thủ công:
npm install
npm run dev
```

Frontend sẽ chạy tại: http://localhost:5173

### Bước 3: Sử dụng

1. Truy cập http://localhost:5173 trên trình duyệt
2. Nhập câu hỏi về UIT trong ô chat
3. Xem kết quả và tài liệu tham khảo bên phải (nếu bật RAG)

## Cấu trúc Frontend

```
frontend/
├── src/
│   ├── components/          # UI Components
│   │   ├── ChatInterface.jsx      # Container chính
│   │   ├── MessageList.jsx        # Danh sách tin nhắn
│   │   ├── MessageInput.jsx       # Input gửi tin
│   │   ├── Sidebar.jsx            # Menu bên trái
│   │   ├── RAGContextPanel.jsx    # Panel tài liệu
│   │   ├── SettingsModal.jsx      # Cài đặt
│   │   └── SystemInfoModal.jsx    # Thông tin hệ thống
│   ├── hooks/
│   │   └── useChat.js             # Hook quản lý chat
│   ├── services/
│   │   └── api.js                 # API calls
│   ├── utils/
│   │   └── helpers.js             # Utilities
│   ├── App.jsx                    # Component chính
│   └── main.jsx                   # Entry point
└── .env                           # Config
```

## Tính năng Frontend

### ✅ Đã hoàn thành

1. **Chat Interface**
   - Gửi/nhận tin nhắn real-time
   - Hiển thị typing indicator
   - Copy tin nhắn
   - Markdown rendering

2. **RAG Context Panel**
   - Hiển thị tài liệu được tìm thấy
   - Điểm số liên quan
   - Metadata của tài liệu
   - Có thể mở rộng/thu gọn

3. **Session Management**
   - Tạo cuộc hội thoại mới
   - Lưu lịch sử (localStorage)
   - Xóa cuộc hội thoại
   - Chuyển đổi giữa các session

4. **Settings**
   - Bật/tắt RAG
   - Số lượng tài liệu (1-10)
   - Temperature (0-2)
   - Max tokens (500-4000)
   - Hiển thị/ẩn RAG context

5. **System Info**
   - Health check các services
   - Thông tin multi-agent system
   - Models đang sử dụng
   - Pipeline steps

6. **Responsive Design**
   - Desktop: Sidebar + Chat + RAG panel
   - Tablet: Collapsible sidebar
   - Mobile: Slide-out menu

## Cấu hình

File `.env`:
```
VITE_API_URL=http://localhost:8001/api/v1
```

Thay đổi URL nếu backend chạy ở port khác.

## Troubleshooting

### Backend connection failed
- Đảm bảo backend đang chạy: `python start_backend.py`
- Check health: http://localhost:8001/api/v1/health
- Kiểm tra CORS trong backend (đã config cho phép *)

### npm install lỗi
- Node version >= 18.x
- Xóa `node_modules` và `package-lock.json` rồi cài lại
- Check logs trong terminal

### Tailwind không work
- Build lại: `npm run build`
- Clear browser cache
- Check `tailwind.config.js`

### Messages không gửi được
- Mở DevTools (F12) > Console tab
- Kiểm tra Network tab xem API call
- Verify backend đang chạy

## API Endpoints sử dụng

Frontend gọi các endpoint sau:

1. **POST /api/v1/chat**
   - Gửi tin nhắn với multi-agent pipeline
   - Body: `{ query, session_id, use_rag, rag_top_k, ... }`

2. **GET /api/v1/health**
   - Kiểm tra health của tất cả services

3. **GET /api/v1/agents/info**
   - Lấy thông tin về multi-agent system

4. **GET /api/v1/conversations**
   - Lấy danh sách conversations (chưa implement backend)

5. **DELETE /api/v1/conversations/{id}**
   - Xóa conversation (chưa implement backend)

## Tips

1. **Debug Mode**: Mở DevTools Console để xem logs chi tiết
2. **Hot Reload**: Frontend tự reload khi code thay đổi
3. **Settings**: Thử các cấu hình khác nhau để thấy khác biệt
4. **RAG Context**: Bật panel bên phải để xem tài liệu được sử dụng

## Next Steps

Tính năng có thể thêm:
- [ ] Streaming responses
- [ ] Voice input
- [ ] File upload
- [ ] Export chat history
- [ ] User authentication
- [ ] Multi-language
- [ ] Dark mode toggle
- [ ] Advanced search

## Demo Screenshots

Giao diện sẽ có:
- Sidebar đen bên trái với danh sách sessions
- Khu vực chat chính ở giữa
- Panel tài liệu RAG bên phải (có thể ẩn/hiện)
- Input box dưới cùng với nút gửi

---

**Happy Coding! 🎉**

Nếu có lỗi, check:
1. Terminal backend
2. Terminal frontend  
3. Browser Console (F12)
