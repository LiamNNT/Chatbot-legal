# Simplified Prompts - Use Config Only

**Date**: October 31, 2025  
**Issue**: Duplicate instructions in hardcoded user prompts vs system prompts from config

---

## ❌ PROBLEM

**BEFORE**: Each agent had TWO sets of instructions:

1. **System Prompt** (from `agents_config.yaml`) - 6000-12000 chars
   - Complete instructions, examples, rules, format requirements
   
2. **User Prompt** (hardcoded in `.py` files) - 500-1000 chars
   - **Duplicate** instructions: "Hãy phân tích...", "NHIỆM VỤ:", "YÊU CẦU:"
   - Conflicting or redundant with system prompt

**Result**: 
- ❌ Waste tokens on duplicate instructions
- ❌ Potential conflicts between two instruction sets
- ❌ Harder to maintain (need to update 2 places)
- ❌ System prompt không được tận dụng

---

## ✅ SOLUTION

**AFTER**: Only ONE set of instructions (from config):

1. **System Prompt** (from `agents_config.yaml`) - Complete instructions
2. **User Prompt** (minimal) - Just the data: query, documents, context

**Benefits**:
- ✅ Save ~500-1000 tokens per request
- ✅ Single source of truth (config file)
- ✅ Easier to maintain and update
- ✅ Full utilization of system prompts from config

---

## 🔧 CHANGES APPLIED

### 1. Planner Agent

**Before**:
```python
def _build_analysis_prompt(self, query: str) -> str:
    return f"""Hãy phân tích câu hỏi sau và tạo kế hoạch xử lý chi tiết:

Câu hỏi: {query}

Hãy đưa ra một phân tích toàn diện về:
1. Ý định của người dùng
2. Độ phức tạp của câu hỏi  
3. Các bước cần thực hiện để trả lời
4. Tài nguyên cần thiết

Trả lời bằng tiếng Việt một cách tự nhiên và chi tiết."""
```

**After**:
```python
def _build_analysis_prompt(self, query: str) -> str:
    # System prompt already contains all instructions from config
    # Just pass the user's query directly
    return query
```

**Saved**: ~250 chars per request

---

### 2. Query Rewriter Agent

**Before**: ~600 chars of hardcoded instructions
```python
prompt_parts.extend([
    "NHIỆM VỤ:",
    "1. Phân tích câu hỏi và xác định ý định chính",
    "2. Viết lại câu hỏi thành 3-5 biến thể tối ưu cho tìm kiếm",
    ...
])
```

**After**:
```python
def _build_optimization_prompt(...) -> str:
    prompt_parts = [f"Query: {query}"]
    if intent:
        prompt_parts.append(f"Intent: {intent}")
    if context:
        prompt_parts.append(f"Context: {json.dumps(context)}")
    return "\n".join(prompt_parts)
```

**Saved**: ~600 chars per request

---

### 3. Answer Agent

**Before**: ~1000 chars of instructions
```python
prompt_parts.extend([
    "NHIỆM VỤ:",
    "1. Phân tích tất cả thông tin được cung cấp",
    "2. Tạo câu trả lời đầy đủ, chính xác và có cấu trúc",
    ...
    "YÊU CẦU ĐẶC BIỆT:",
    "- Ưu tiên thông tin chính thức từ UIT",
    ...
])
```

**After**:
```python
def _build_answer_prompt(...) -> str:
    prompt_parts = [f"Query: {query}"]
    if rewritten_queries:
        prompt_parts.append(f"Query Variations: {', '.join(rewritten_queries)}")
    if context_documents:
        prompt_parts.append("\nDocuments:")
        for i, doc in enumerate(context_documents, 1):
            prompt_parts.append(f"[{i}] {doc['title']}")
            prompt_parts.append(doc['content'])
    return "\n".join(prompt_parts)
```

**Saved**: ~1000 chars per request

---

### 4. Verifier Agent

**Before**: ~1200 chars of verification instructions

**After**:
```python
def _build_verification_prompt(...) -> str:
    prompt_parts = [
        f"Query: {query}",
        f"\nAnswer to verify:\n{answer}",
        f"\nOriginal confidence: {original_confidence:.2f}"
    ]
    if context_documents:
        for i, doc in enumerate(context_documents, 1):
            prompt_parts.append(f"[{i}] {doc['title']}: {doc['content'][:800]}")
    return "\n".join(prompt_parts)
```

**Saved**: ~1200 chars per request

---

### 5. Response Agent

**Before**: ~800 chars of formatting instructions

**After**:
```python
def _build_response_prompt(...) -> str:
    prompt_parts = [
        f"Query: {query}",
        f"\nVerified Answer:\n{verified_answer}"
    ]
    if verification_result:
        prompt_parts.append(f"\nAccuracy: {is_accurate}, Confidence: {confidence:.2f}")
    return "\n".join(prompt_parts)
```

**Saved**: ~800 chars per request

---

## 📊 TOKEN SAVINGS

| Agent | Before (chars) | After (chars) | Saved |
|-------|---------------|---------------|-------|
| Planner | ~250 | ~50 | **200** |
| Query Rewriter | ~600 | ~100 | **500** |
| Answer Agent | ~1000 | ~200 | **800** |
| Verifier | ~1200 | ~150 | **1050** |
| Response Agent | ~800 | ~100 | **700** |
| **TOTAL per query** | ~3850 | ~600 | **~3250 chars** |

**Estimated token savings**: **~800 tokens per query** (at ~4 chars/token)

**Cost savings** (assuming $0.01/1K tokens):
- Per query: ~$0.008 saved
- 1000 queries/day: **$8/day** or **$240/month** saved

---

## 🎯 MESSAGE STRUCTURE

### Before (Redundant):
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Planner Agent...\n\nFor EVERY query, follow these steps:\n1. DECOMPOSITION: Extract entities...\n[8000+ chars of instructions]"
    },
    {
      "role": "user",
      "content": "Hãy phân tích câu hỏi sau và tạo kế hoạch xử lý chi tiết:\n\nCâu hỏi: Điều kiện tốt nghiệp?\n\nHãy đưa ra:\n1. Ý định người dùng\n2. Độ phức tạp\n... [250 chars duplicate instructions]"
    }
  ]
}
```

### After (Clean):
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Planner Agent...\n\nFor EVERY query, follow these steps:\n1. DECOMPOSITION: Extract entities...\n[8000+ chars - ALL instructions here]"
    },
    {
      "role": "user",
      "content": "Điều kiện tốt nghiệp của trường là gì?"
    }
  ]
}
```

---

## ✅ FILES MODIFIED

1. `/services/orchestrator/app/agents/planner_agent.py`
2. `/services/orchestrator/app/agents/query_rewriter_agent.py`
3. `/services/orchestrator/app/agents/answer_agent.py`
4. `/services/orchestrator/app/agents/verifier_agent.py`
5. `/services/orchestrator/app/agents/response_agent.py`

---

## 🧪 TESTING

**Restart backend và test**:

```bash
# Stop current backend (Ctrl+C)
python start_backend.py

# Test
python demo_debug_logging.py
```

**Verify in logs**:
- ✅ System Prompt Length: Still 6000-12000 chars (unchanged)
- ✅ User Prompt: Now SHORT (~50-200 chars) - just data, no instructions
- ✅ Agents still work correctly (instructions from system prompt)

---

## 📝 BEST PRACTICES ESTABLISHED

### ✅ DO:
- Put ALL instructions in `agents_config.yaml` system_prompt
- Use user prompt ONLY for data: query, documents, context
- Keep user prompts minimal and data-focused
- Update instructions in ONE place (config file)

### ❌ DON'T:
- Duplicate instructions in user prompt
- Add task requirements in user prompt
- Override system prompt instructions
- Maintain instructions in multiple files

---

## 🔍 EXAMPLE COMPARISON

### Query: "Điều kiện tốt nghiệp là gì?"

**Before**:
```
System: [8500 chars of instructions]
User: Hãy phân tích câu hỏi sau và tạo kế hoạch chi tiết:

Câu hỏi: Điều kiện tốt nghiệp là gì?

Hãy đưa ra:
1. Ý định người dùng
2. Độ phức tạp câu hỏi
3. Các bước xử lý
4. Tài nguyên cần thiết

Trả lời bằng tiếng Việt...
```
**Total**: 8500 + 250 = **8750 chars**

**After**:
```
System: [8500 chars of instructions]
User: Điều kiện tốt nghiệp là gì?
```
**Total**: 8500 + 27 = **8527 chars**

**Saved**: **223 chars** (~56 tokens) per Planner call

---

## 🎉 BENEFITS

### Efficiency:
- ✅ ~800 tokens saved per query
- ✅ Faster response (less tokens to process)
- ✅ Lower API costs

### Maintainability:
- ✅ Single source of truth (config file)
- ✅ Easy to update instructions
- ✅ No sync issues between files
- ✅ Cleaner, simpler code

### Quality:
- ✅ No conflicting instructions
- ✅ Consistent behavior across agents
- ✅ Better utilization of system prompts
- ✅ Easier to debug (check config file only)

---

**Status**: ✅ All agents simplified - ready to test!
