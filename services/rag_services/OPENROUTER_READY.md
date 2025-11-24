# ✅ CẤU HÌNH OPENROUTER - ĐÃ SẴN SÀNG

## ⚡ Quan trọng: Chỉ dùng OpenRouter

Hệ thống được cấu hình để **TẤT CẢ LLM calls đều qua OpenRouter**:

❌ **KHÔNG dùng:** OpenAI API trực tiếp  
❌ **KHÔNG dùng:** Google Gemini API trực tiếp  
✅ **CHỈ DÙNG:** OpenRouter API (truy cập tất cả models qua 1 endpoint)

**Lợi ích:**
- 🔑 Chỉ cần 1 API key duy nhất
- 💰 So sánh giá real-time
- 🚀 Truy cập 100+ models (GPT-4, Claude, Gemini, Llama, etc.)
- 💸 Pay-as-you-go, không cần subscription

## Tóm tắt

File `.env` của bạn **đã được cấu hình hoàn chỉnh** để sử dụng OpenRouter cho tất cả LLM calls.

## Những gì đã sẵn sàng

✅ **LLM Provider:** `openrouter` (dùng 100+ models qua 1 API)  
✅ **Default Model:** `google/gemini-flash-1.5` (rẻ, nhanh, tốt cho tiếng Việt)  
✅ **API Endpoint:** `https://openrouter.ai/api/v1`  
✅ **Neo4j Database:** Đang chạy tại localhost:7474  
✅ **Scripts:** Demo và test scripts đã sẵn sàng  

## Chỉ cần 1 bước: Điền API Key

### Cách 1: Tự động (Khuyến nghị)

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Check cấu hình hiện tại
bash scripts/setup_openrouter.sh
```

Script sẽ kiểm tra và báo bạn cần điền API key vào đâu.

### Cách 2: Thủ công

1. **Lấy API key từ OpenRouter:**
   - Truy cập: https://openrouter.ai/keys
   - Đăng nhập (GitHub/Google)
   - Click "Create Key"
   - Copy key (dạng: `sk-or-v1-...`)

2. **Mở file `.env`:**
   ```bash
   nano .env
   # Hoặc
   code .env
   ```

3. **Tìm dòng này:**
   ```bash
   OPENAI_API_KEY=                   # Your OpenRouter API key (sk-or-v1-...)
   ```

4. **Thay bằng:**
   ```bash
   OPENAI_API_KEY=sk-or-v1-abc123xyz...  # Key thật của bạn
   ```

5. **Save file** và đóng lại

## Models có sẵn

File `.env` đã set `google/gemini-flash-1.5` (recommended). 

Muốn đổi model? Edit dòng `LLM_MODEL` trong `.env`:

```bash
# FREE (unlimited)
LLM_MODEL=meta-llama/llama-3.1-8b-instruct

# CHEAP & FAST ⭐ (recommended)
LLM_MODEL=google/gemini-flash-1.5        # $0.075/1M tokens
LLM_MODEL=google/gemini-flash-1.5-8b     # Faster

# HIGH QUALITY
LLM_MODEL=anthropic/claude-3.5-sonnet    # $3/1M tokens
LLM_MODEL=google/gemini-pro-1.5          # $1.25/1M tokens
LLM_MODEL=openai/gpt-4-turbo

# Xem tất cả: https://openrouter.ai/models
```

## Test ngay

Sau khi điền API key, chạy:

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Option 1: Demo extraction
python scripts/demo_openrouter_extraction.py

# Option 2: Check status
python scripts/test_graph_status.py

# Option 3: Build graph từ data
python scripts/build_graph_from_indexed_data.py
```

## Xem kết quả trên Neo4j

1. Mở browser: http://localhost:7474
2. Login:
   - Username: `neo4j`
   - Password: `uitchatbot`
3. Chạy query:
   ```cypher
   MATCH (n) RETURN n LIMIT 50
   ```

## File cấu hình (.env) - Cấu trúc

```bash
# ==========================================
# LLM - OPENROUTER (Phần quan trọng)
# ==========================================
LLM_PROVIDER=openrouter                    # ← Đã set
LLM_MODEL=google/gemini-flash-1.5          # ← Có thể đổi
LLM_TEMPERATURE=0.0                        # ← Đã tối ưu
LLM_MAX_TOKENS=2000                        # ← Đủ dùng

OPENAI_API_KEY=                            # ← ĐIỀN VÀO ĐÂY!
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # ← Đã đúng

# ==========================================
# Neo4j
# ==========================================
NEO4J_URI=bolt://localhost:7687            # ← Đúng
NEO4J_USER=neo4j                           # ← Đúng  
NEO4J_PASSWORD=uitchatbot                  # ← Đúng

# (Phần còn lại cho vector store, embeddings, etc.)
```

## Troubleshooting

### "API key not set"
**Giải pháp:** Kiểm tra file `.env`, đảm bảo `OPENAI_API_KEY=sk-or-v1-...` (không có spaces, không có comments sau dấu =)

### "Timeout"  
**Giải pháp:** Đổi sang model nhanh hơn:
```bash
LLM_MODEL=google/gemini-flash-1.5-8b
```

### "Neo4j connection failed"
**Giải pháp:** 
```bash
docker-compose -f docker/docker-compose.neo4j.yml up -d
```

### "Cost too high"
**Giải pháp:** Dùng model free:
```bash
LLM_MODEL=meta-llama/llama-3.1-8b-instruct
```

## Summary

🎯 **File `.env` đã hoàn chỉnh** - Tất cả đã được config sẵn cho OpenRouter  
🔑 **Chỉ cần:** Điền `OPENAI_API_KEY` vào file `.env`  
🚀 **Sau đó:** Chạy `python scripts/demo_openrouter_extraction.py`  
📊 **Xem graph:** http://localhost:7474 (neo4j/uitchatbot)

**That's it! 🎉**
