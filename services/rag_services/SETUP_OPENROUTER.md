# SETUP OPENROUTER - HƯỚNG DẪN NHANH

## Bước 1: Lấy API Key

1. Truy cập: **https://openrouter.ai/keys**
2. Đăng nhập (GitHub/Google)
3. Click "Create Key"
4. Copy key (dạng: `sk-or-v1-...`)
5. Miễn phí $1 credit để test!

## Bước 2: Cấu hình trong .env

Mở file `.env` và điền API key vào dòng này:

```bash
OPENAI_API_KEY=sk-or-v1-YOUR_KEY_HERE  # ← Thay YOUR_KEY_HERE bằng key thật
```

**Ví dụ:**
```bash
OPENAI_API_KEY=sk-or-v1-abc123xyz456...
```

## Bước 3: Chọn Model (Tùy chọn)

File `.env` đã set sẵn `google/gemini-flash-1.5` (rẻ & nhanh).

Bạn có thể đổi sang model khác:

```bash
# Miễn phí
LLM_MODEL=meta-llama/llama-3.1-8b-instruct

# Rẻ & nhanh (recommended)
LLM_MODEL=google/gemini-flash-1.5         # $0.075/1M tokens
LLM_MODEL=google/gemini-flash-1.5-8b      # Nhanh hơn

# Chất lượng cao
LLM_MODEL=anthropic/claude-3.5-sonnet     # $3/1M tokens
LLM_MODEL=google/gemini-pro-1.5           # $1.25/1M tokens
LLM_MODEL=openai/gpt-4-turbo              # Via OpenRouter
```

Xem thêm models: https://openrouter.ai/models

## Bước 4: Test ngay!

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Test extraction
python scripts/demo_openrouter_extraction.py

# Hoặc check status
python scripts/test_graph_status.py
```

## Cấu hình đã sẵn sàng

File `.env` của bạn đã được cấu hình:

✅ **LLM_PROVIDER=openrouter** - Dùng OpenRouter  
✅ **LLM_MODEL=google/gemini-flash-1.5** - Model mặc định  
✅ **OPENAI_BASE_URL=https://openrouter.ai/api/v1** - Endpoint đúng  
✅ **Neo4j** - Database sẵn sàng  

**Chỉ cần điền OPENAI_API_KEY là xong!**

## Xem Graph sau khi chạy

1. Mở Neo4j Browser: **http://localhost:7474**
2. Login: `neo4j` / `uitchatbot`
3. Query:
   ```cypher
   MATCH (n) RETURN n LIMIT 50
   ```

## Troubleshooting

**"API key not set"** → Kiểm tra lại dòng `OPENAI_API_KEY` trong `.env`

**"Timeout"** → Đổi sang model nhanh hơn: `google/gemini-flash-1.5-8b`

**"Cost too high"** → Dùng model free: `meta-llama/llama-3.1-8b-instruct`

---

**That's it!** Điền API key và chạy demo thôi! 🚀
