# Tóm Tắt: Thêm Debug Logging cho Chatbot-UIT

## Ngày: 31 Tháng 10, 2025

## Mục tiêu
Thêm khả năng hiển thị log chi tiết về input và output của các agent khi chạy backend để dễ dàng debug và theo dõi hoạt động của hệ thống.

## Các thay đổi đã thực hiện

### 1. Cập nhật `start_backend.py`
- ✅ Thêm option `--debug` để bật chế độ debug logging
- ✅ Truyền `debug_mode` parameter vào `start_rag_service()` và `start_orchestrator_service()`
- ✅ Set biến môi trường `LOG_LEVEL=DEBUG` khi chạy với `--debug`

**Cách sử dụng:**
```bash
# Chạy với debug mode
python start_backend.py --debug

# Chạy bình thường
python start_backend.py

# Chạy với debug mode, bỏ qua Docker
python start_backend.py --debug --skip-docker
```

### 2. Cập nhật `services/orchestrator/app/main.py`
- ✅ Thay đổi cấu hình logging để đọc từ biến môi trường `LOG_LEVEL`
- ✅ Mặc định là `INFO`, khi set `LOG_LEVEL=DEBUG` sẽ hiển thị log chi tiết

**Thay đổi:**
```python
# Trước:
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Sau:
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger.info(f"Logging level set to: {log_level}")
```

### 3. Cập nhật `services/orchestrator/app/agents/base.py`
- ✅ Thêm logging chi tiết trong method `_make_agent_request()`
- ✅ Log input trước khi gọi agent (prompt, model, temperature, max_tokens, context)
- ✅ Log output sau khi nhận response (content, tokens_used)
- ✅ Chỉ log khi `LOG_LEVEL=DEBUG`

**Format log:**
```
================================================================================
🔵 AGENT INPUT - [AGENT_TYPE]
================================================================================
Prompt: [prompt text]
Model: [model name]
Temperature: [value]
Max Tokens: [value]
Context keys: [list of keys]
================================================================================

================================================================================
🟢 AGENT OUTPUT - [AGENT_TYPE]
================================================================================
Response: [response text]
Tokens Used: [number]
================================================================================
```

### 4. Cập nhật `services/orchestrator/app/agents/multi_agent_orchestrator.py`
- ✅ Thêm logging chi tiết cho từng bước trong pipeline:
  - 📋 **STEP 1: PLANNING** - Log query, intent, complexity
  - 🔍 **STEP 2: QUERY REWRITING & RAG RETRIEVAL** - Log original query, rewritten queries, documents retrieved
  - 💡 **STEP 3: ANSWER GENERATION** - Log answer length, confidence, sources
  - ✅ **STEP 4: VERIFICATION** - Log verification confidence, issues found
  - 🎯 **STEP 5: RESPONSE FORMATTING** - Log final response, tone, friendliness score

**Ví dụ log output:**
```
================================================================================
📋 STEP 1: PLANNING
================================================================================
Query: Điều kiện tốt nghiệp là gì?
Plan Intent: information_query
Plan Complexity: simple
Estimated Tokens: 250
================================================================================
```

### 5. Tài liệu
- ✅ Tạo `DEBUG_LOGGING_GUIDE.md` - Hướng dẫn chi tiết về cách sử dụng debug logging
- ✅ Tạo `test_with_debug.sh` - Script nhanh để test với debug mode
- ✅ Cập nhật `README.md` - Thêm thông tin về debug mode

## Lợi ích

### 1. **Debug dễ dàng hơn**
- Thấy rõ input/output của từng agent
- Xác định được agent nào gây ra vấn đề
- Theo dõi token usage để optimize cost

### 2. **Hiểu rõ flow xử lý**
- Thấy toàn bộ pipeline từ đầu đến cuối
- Biết được query được rewrite như thế nào
- Xem documents nào được retrieve
- Theo dõi confidence score của từng bước

### 3. **Optimize performance**
- Xem thời gian xử lý của từng bước
- Xác định bottleneck
- Đánh giá chất lượng RAG retrieval

### 4. **Production ready**
- Debug mode chỉ bật khi cần
- Không ảnh hưởng đến production khi tắt
- Logs rõ ràng, dễ đọc với emoji

## Testing

### Test 1: Chạy với debug mode
```bash
conda activate chatbot-UIT
python start_backend.py --debug
```

### Test 2: Test một query
```bash
# Terminal 1: Start backend
python start_backend.py --debug

# Terminal 2: Test
curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Học phí UIT là bao nhiêu?", "use_rag": true}'
```

Bạn sẽ thấy logs chi tiết về:
- Planning step
- Query rewriting
- RAG retrieval (documents, scores)
- Answer generation
- Verification
- Response formatting

## Lưu ý

1. **Performance**: Debug mode có thể tạo nhiều logs, có thể làm chậm một chút
2. **Production**: Không nên dùng debug mode trong production
3. **Sensitive data**: Debug logs có thể chứa thông tin nhạy cảm
4. **Storage**: Logs không được lưu file, chỉ hiển thị trên terminal

## Các file đã thay đổi

1. `start_backend.py` - Thêm --debug flag
2. `services/orchestrator/app/main.py` - Dynamic log level
3. `services/orchestrator/app/agents/base.py` - Agent I/O logging
4. `services/orchestrator/app/agents/multi_agent_orchestrator.py` - Pipeline step logging
5. `DEBUG_LOGGING_GUIDE.md` - Hướng dẫn sử dụng (NEW)
6. `test_with_debug.sh` - Test script (NEW)
7. `README.md` - Cập nhật documentation

## Next Steps

Để sử dụng tính năng này:

1. Pull code mới nhất
2. Chạy: `python start_backend.py --debug`
3. Đọc `DEBUG_LOGGING_GUIDE.md` để hiểu rõ hơn
4. Test với các query khác nhau để xem logs

---

**Author**: GitHub Copilot  
**Date**: October 31, 2025  
**Status**: ✅ Completed
