# 🎯 OPENROUTER SETUP - CHỈ DÙNG 1 API

## Quan trọng

✅ **TẤT CẢ LLM calls qua OpenRouter** (không dùng OpenAI/Gemini API trực tiếp)

## Tại sao?

**1 API key = Truy cập 100+ models:**
- Google Gemini (flash, pro)
- Anthropic Claude (opus, sonnet, haiku)  
- OpenAI GPT (4, 3.5)
- Meta Llama (free!)
- Mistral, Cohere, và nhiều hơn

## Đã cấu hình

File `.env` của bạn:

```bash
# CHỈ DÙNG OPENROUTER
LLM_PROVIDER=openrouter                      # ✅
OPENAI_BASE_URL=https://openrouter.ai/api/v1 # ✅
LLM_MODEL=google/gemini-flash-1.5            # ✅

# CHỈ CẦN ĐIỀN API KEY
OPENAI_API_KEY=                              # ← sk-or-v1-xxx
```

## Chỉ 1 bước

1. Lấy key: https://openrouter.ai/keys
2. Điền vào `.env`: `OPENAI_API_KEY=sk-or-v1-xxx`
3. Done!

## LLM được dùng ở đâu?

### 1. Relation Extraction
```python
# File: indexing/llm_relation_extractor.py
LLMRelationExtractor(llm_client)
# ↑ Dùng OpenRouter để extract quan hệ từ text
```

### 2. Entity Enrichment  
```python
# File: indexing/category_guided_entity_extractor.py
# Rule-based (không cần LLM)
# Nhưng có thể thêm LLM enhancement sau
```

### 3. RAG Generation
```python
# File: core/services/
# Tất cả LLM calls đều qua OpenRouter
```

## Models đề xuất

```bash
# Rẻ nhất ($0.075/1M)
LLM_MODEL=google/gemini-flash-1.5

# Miễn phí
LLM_MODEL=meta-llama/llama-3.1-8b-instruct

# Chất lượng cao
LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Test

```bash
# Sau khi điền API key
python scripts/demo_openrouter_extraction.py

# Sẽ:
# 1. Extract entities (rule-based)
# 2. Extract relations (OpenRouter LLM)
# 3. Build graph trong Neo4j
```

## Xem graph

- URL: http://localhost:7474
- Login: neo4j / uitchatbot
- Query: `MATCH (n) RETURN n LIMIT 50`

## Flow

```
App → OpenRouterClient → OpenRouter API → [Gemini|Claude|GPT-4|Llama|...]
                ↑
         1 API key duy nhất!
```

Xem chi tiết: `OPENROUTER_ARCHITECTURE.md`
