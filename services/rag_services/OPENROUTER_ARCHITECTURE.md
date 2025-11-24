# Architecture: OpenRouter cho TẤT CẢ LLM Calls

## Flow hiện tại (CHỈ DÙNG OPENROUTER)

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Service Application                   │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Entity Extractor │  │ Relation Extract │                │
│  │   (rule-based)   │  │   (LLM-powered)  │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                           │
│           │    ┌────────────────┘                           │
│           │    │                                            │
│  ┌────────▼────▼──────────────────────────┐                │
│  │     LLMRelationExtractor               │                │
│  │  (sử dụng OpenRouter cho extraction)   │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
│  ┌────────────────▼───────────────────────┐                │
│  │   create_llm_client_from_env()         │                │
│  │   - Đọc LLM_PROVIDER=openrouter        │                │
│  │   - Return OpenRouterClient            │                │
│  └────────────────┬───────────────────────┘                │
│                   │                                         │
│  ┌────────────────▼───────────────────────┐                │
│  │      OpenRouterClient                  │                │
│  │  (OpenAI-compatible API wrapper)       │                │
│  └────────────────┬───────────────────────┘                │
└───────────────────┼──────────────────────────────────────┘
                    │
                    │ HTTPS Request
                    │ Authorization: Bearer sk-or-v1-xxx
                    ▼
        ┌───────────────────────────┐
        │    OpenRouter API         │
        │  https://openrouter.ai    │
        └───────────┬───────────────┘
                    │
        ┌───────────┴────────────────┐
        │   Model Routing            │
        │  (OpenRouter chọn model)   │
        └───────────┬────────────────┘
                    │
        ┌───────────┴────────────────────────────────────┐
        │                                                │
        ▼                          ▼                     ▼
    ┌──────────┐            ┌──────────┐         ┌──────────┐
    │  Gemini  │            │  Claude  │         │  GPT-4   │
    │  (Google)│            │(Anthropic)│        │ (OpenAI) │
    └──────────┘            └──────────┘         └──────────┘
    
         ▼                         ▼                    ▼
    google/gemini-flash-1.5   anthropic/claude-3.5   openai/gpt-4
```

## Không dùng trực tiếp

```
❌ KHÔNG CÓ:

App ──X──> OpenAI API trực tiếp
App ──X──> Gemini API trực tiếp
App ──X──> Anthropic API trực tiếp

✅ CHỈ CÓ:

App ──> OpenRouter ──> [OpenAI | Gemini | Anthropic | ...]
```

## Cấu hình trong code

### File: `.env`
```bash
# TẤT CẢ LLM calls qua OpenRouter
LLM_PROVIDER=openrouter                    # ← Provider duy nhất
OPENAI_API_KEY=sk-or-v1-xxx                # ← OpenRouter key
OPENAI_BASE_URL=https://openrouter.ai/api/v1  # ← OpenRouter endpoint

# KHÔNG SỬ DỤNG (khi LLM_PROVIDER=openrouter)
# GEMINI_API_KEY=xxx                       # ← KHÔNG dùng
# OPENAI_API_KEY (from openai.com)         # ← KHÔNG dùng
```

### File: `adapters/llm/openrouter_client.py`
```python
class OpenRouterClient(LLMClient):
    """
    Unified LLM client qua OpenRouter.
    
    Hỗ trợ TẤT CẢ models:
    - Google: gemini-flash-1.5, gemini-pro-1.5
    - Anthropic: claude-3.5-sonnet, claude-3-opus
    - OpenAI: gpt-4-turbo, gpt-4, gpt-3.5-turbo
    - Meta: llama-3.1-70b, llama-3.1-405b
    - Mistral, Cohere, và nhiều hơn nữa
    
    Đều qua 1 API key duy nhất!
    """
```

### File: `indexing/llm_relation_extractor.py`
```python
# Sử dụng OpenRouter cho relation extraction
from adapters.llm import create_llm_client_from_env

llm_client = create_llm_client_from_env()
# ↑ Tự động tạo OpenRouterClient từ .env

extractor = LLMRelationExtractor(llm_client)
# ↑ Dùng OpenRouter để extract relations
```

## Lợi ích

### 1. Đơn giản hóa
- ✅ Chỉ 1 API key
- ✅ Chỉ 1 endpoint
- ✅ Không cần quản lý nhiều providers

### 2. Linh hoạt
```bash
# Đổi model chỉ bằng 1 dòng trong .env
LLM_MODEL=google/gemini-flash-1.5        # Cheap
LLM_MODEL=anthropic/claude-3.5-sonnet    # Quality
LLM_MODEL=meta-llama/llama-3.1-8b        # Free
```

### 3. Tối ưu chi phí
- OpenRouter tự động route đến provider rẻ nhất
- So sánh giá real-time
- Fallback tự động khi model busy

### 4. Không vendor lock-in
```bash
# Hôm nay dùng Gemini
LLM_MODEL=google/gemini-flash-1.5

# Ngày mai đổi sang Claude (không đổi code!)
LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Models available qua OpenRouter

Tất cả đều accessible với 1 API key:

**Google:**
- `google/gemini-flash-1.5` - $0.075/1M tokens ⭐
- `google/gemini-flash-1.5-8b` - $0.0375/1M tokens
- `google/gemini-pro-1.5` - $1.25/1M tokens

**Anthropic:**
- `anthropic/claude-3.5-sonnet` - $3/1M tokens
- `anthropic/claude-3-opus` - $15/1M tokens
- `anthropic/claude-3-haiku` - $0.25/1M tokens

**OpenAI:**
- `openai/gpt-4-turbo` - $10/1M tokens
- `openai/gpt-4` - $30/1M tokens
- `openai/gpt-3.5-turbo` - $0.50/1M tokens

**Meta (FREE):**
- `meta-llama/llama-3.1-8b-instruct` - FREE!
- `meta-llama/llama-3.1-70b-instruct` - $0.88/1M tokens
- `meta-llama/llama-3.1-405b-instruct` - $3/1M tokens

**Và hơn 100 models khác!**

Xem đầy đủ: https://openrouter.ai/models

## Summary

🎯 **Architecture:** TẤT CẢ LLM calls → OpenRouter → Models  
🔑 **API Key:** Chỉ cần 1 OpenRouter key  
💰 **Chi phí:** So sánh và chọn tự động  
🚀 **Models:** 100+ models accessible  
📦 **Code:** Không thay đổi khi đổi model  

**Đơn giản. Linh hoạt. Tiết kiệm.**
