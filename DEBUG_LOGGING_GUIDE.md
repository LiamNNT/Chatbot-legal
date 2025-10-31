# Hướng Dẫn Sử Dụng Debug Logging

## Giới thiệu
Tài liệu này hướng dẫn cách sử dụng debug logging để theo dõi input và output của các agent trong hệ thống Chatbot-UIT.

**⚠️ LƯU Ý: Debug mode được BẬT MẶC ĐỊNH để giúp bạn dễ dàng theo dõi hoạt động của hệ thống.**

## Cách sử dụng

### 1. Chạy Backend (Debug mode MẶC ĐỊNH)

```bash
# Activate conda environment
conda activate chatbot-UIT

# Chạy với debug logging (MẶC ĐỊNH)
python start_backend.py
```

### 2. Tắt Debug Mode (nếu không cần log chi tiết)

```bash
# Chạy KHÔNG có debug logging
python start_backend.py --no-debug
```

### 3. Bỏ qua Docker services (nếu đã chạy)

```bash
# Với debug (mặc định)
python start_backend.py --skip-docker

# Không debug
python start_backend.py --skip-docker --no-debug
```

### 4. Dừng tất cả services

```bash
python start_backend.py --stop
```

## Các option có sẵn

| Option | Mô tả |
|--------|-------|
| `--no-debug` | **TẮT** debug logging (debug được BẬT mặc định) |
| `--skip-docker` | Bỏ qua việc khởi động Docker services (OpenSearch, Weaviate) |
| `--stop` | Dừng tất cả các services đang chạy |

**💡 Lưu ý:** Debug mode được BẬT MẶC ĐỊNH để giúp bạn dễ dàng debug và theo dõi. Chỉ dùng `--no-debug` khi bạn không cần xem logs chi tiết.

## Log Output khi sử dụng --debug

Khi bật `--debug`, bạn sẽ thấy các log chi tiết như sau:

### 1. **Planning Step**
```
================================================================================
📋 STEP 1: PLANNING
================================================================================
Query: [câu hỏi của user]
Plan Intent: [intent được phát hiện]
Plan Complexity: [simple/medium/complex]
Estimated Tokens: [số tokens ước tính]
================================================================================
```

### 2. **Agent Input/Output**
Mỗi agent sẽ log input và output:
```
================================================================================
🔵 AGENT INPUT - PLANNER
================================================================================
Prompt: [prompt được gửi đến agent]
Model: [tên model]
Temperature: [giá trị temperature]
Max Tokens: [số token tối đa]
Context keys: [các key trong context]
================================================================================

================================================================================
🟢 AGENT OUTPUT - PLANNER
================================================================================
Response: [response từ agent]
Tokens Used: [số tokens đã sử dụng]
================================================================================
```

### 3. **Query Rewriting & RAG Retrieval**
```
================================================================================
🔍 STEP 2: QUERY REWRITING & RAG RETRIEVAL
================================================================================
Original Query: [câu hỏi gốc]
Rewritten Queries (3):
  1. [query 1]
  2. [query 2]
  3. [query 3]
Performing RAG retrieval with top_k=5...
Documents Retrieved: 5
  Doc 1: [title] (score: 0.95, 1234 chars)
  Doc 2: [title] (score: 0.89, 987 chars)
  ...
================================================================================
```

### 4. **Answer Generation**
```
================================================================================
💡 STEP 3: ANSWER GENERATION
================================================================================
Query: [câu hỏi]
Documents: 5
Answer Length: 567 chars
Confidence: 0.85
Sources Used: 3
================================================================================
```

### 5. **Verification**
```
================================================================================
✅ STEP 4: VERIFICATION
================================================================================
Verifying answer...
Verification Confidence: 0.90
Issues Found: 0
================================================================================
```

### 6. **Response Formatting**
```
================================================================================
🎯 STEP 5: RESPONSE FORMATTING
================================================================================
Final Response Length: 612 chars
Tone: friendly
Friendliness Score: 0.92
================================================================================
```

## Ví dụ sử dụng

### Ví dụ 1: Chạy lần đầu (debug mặc định)
```bash
conda activate chatbot-UIT
python start_backend.py
```

### Ví dụ 2: Restart services (Docker đã chạy)
```bash
python start_backend.py --skip-docker
```

### Ví dụ 3: Chạy KHÔNG có debug (production mode)
```bash
python start_backend.py --no-debug
```

### Ví dụ 4: Test một query và xem logs
```bash
# Terminal 1: Start backend với debug
python start_backend.py --debug

# Terminal 2: Test API
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Điều kiện tốt nghiệp của trường là gì?",
    "use_rag": true,
    "rag_top_k": 5
  }'
```

## Lưu ý

1. **Performance**: Debug mode sẽ tạo ra nhiều log hơn, có thể làm chậm hệ thống một chút
2. **Log file**: Logs được hiển thị trực tiếp trên terminal, không lưu vào file
3. **Sensitive data**: Debug logs có thể chứa thông tin nhạy cảm, không nên sử dụng trong production
4. **Màn hình**: Logs có thể cuộn nhanh, hãy sử dụng scroll back của terminal để xem lại

## Kiểm tra logs của từng service riêng biệt

Nếu muốn xem logs của từng service riêng:

### RAG Service
```bash
cd services/rag_services
LOG_LEVEL=DEBUG python start_server.py
```

### Orchestrator Service
```bash
cd services/orchestrator
LOG_LEVEL=DEBUG python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level debug
```

## Troubleshooting

### Không thấy debug logs?
- Debug đã được BẬT mặc định. Kiểm tra xem có dùng `--no-debug` không
- Xem biến môi trường `LOG_LEVEL` có được set đúng không

### Logs quá nhiều?
- Sử dụng `--no-debug` để tắt debug logging
- Hoặc grep để lọc logs: `python start_backend.py 2>&1 | grep "AGENT INPUT"`

### Muốn lưu logs vào file?
```bash
python start_backend.py 2>&1 | tee backend_debug.log
```

## Các thông tin hữu ích trong logs

Khi debug, hãy chú ý đến:
- **Token usage**: Giúp optimize cost
- **Processing time**: Xác định bottleneck
- **Document retrieval**: Kiểm tra RAG có lấy đúng context không
- **Agent confidence**: Đánh giá chất lượng response
- **Errors**: Nếu có lỗi, logs sẽ hiển thị chi tiết

## Tắt services

Khi xong việc, nhấn `Ctrl+C` hoặc:
```bash
python start_backend.py --stop
```
