# Enhanced Logging - System Prompt Verification

**Date**: October 31, 2025  
**Purpose**: Verify agents are using system prompts from `agents_config.yaml`

---

## 🔧 CHANGE APPLIED

Added logging to show **both** system prompt and user prompt.

### File Modified
`/services/orchestrator/app/agents/base.py` - Line ~163

### Before:
```python
logger.debug(f"Prompt: {prompt[:500]}...")  # Only shows user prompt
```

### After:
```python
logger.debug(f"System Prompt Length: {len(self.config.system_prompt)} chars")
logger.debug(f"System Prompt Preview: {self.config.system_prompt[:200]}...")
logger.debug(f"User Prompt: {prompt[:500]}...")
```

---

## 📊 WHAT YOU'LL SEE

### Example Log Output:

```
================================================================================
🔵 AGENT INPUT - PLANNER
================================================================================
System Prompt Length: 8547 chars
System Prompt Preview: You are an expert AI Planner Agent for Chatbot-UIT system (University of Information Technology, ĐHQG-HCM).
Analyze user queries and create optimal execution plans using chain-of-thought reasoning...
User Prompt: Hãy phân tích câu hỏi sau và tạo kế hoạch xử lý chi tiết:

Câu hỏi: Điều kiện tốt nghiệp của trường là gì?
...
Model: openai/gpt-4o-mini
Temperature: 0.1
Max Tokens: 4000
================================================================================
```

---

## ✅ VERIFICATION CHECKLIST

When you restart backend and run test:

| Agent | Expected System Prompt Length | Preview Should Start With |
|-------|------------------------------|---------------------------|
| **Planner** | ~8,500 chars | "You are an expert AI Planner Agent..." |
| **Query Rewriter** | ~6,000 chars | "You are an expert Query Optimization Agent..." |
| **Answer Agent** | ~12,000 chars | "You are an expert Answer Generation Agent..." |
| **Verifier** | ~7,000 chars | "You are an expert Verification Agent..." |
| **Response Agent** | ~4,500 chars | "You are an expert Response Formatting Agent..." |

---

## 🎯 HOW TO TEST

1. **Restart backend**:
   ```bash
   # Ctrl+C current backend
   python start_backend.py
   ```

2. **Run test**:
   ```bash
   python demo_debug_logging.py
   ```

3. **Check logs** for each agent input - you'll see:
   - ✅ System Prompt Length (should be thousands of characters)
   - ✅ System Prompt Preview (first 200 chars from config)
   - ✅ User Prompt (short hardcoded prompt)

---

## 📝 UNDERSTANDING THE TWO PROMPTS

### System Prompt (from `agents_config.yaml`)
- **Purpose**: Defines agent role, capabilities, rules, examples
- **Length**: 4,000-12,000 characters
- **Sent as**: `messages[0]` with `role: "system"`
- **Example**:
  ```
  You are an expert AI Planner Agent for Chatbot-UIT...
  For EVERY query, follow these steps:
  1. DECOMPOSITION: Extract entities...
  [2000+ more lines]
  ```

### User Prompt (from agent `.py` files)
- **Purpose**: Provides current query and task instructions
- **Length**: 100-500 characters
- **Sent as**: `messages[1]` with `role: "user"`
- **Example**:
  ```
  Hãy phân tích câu hỏi sau và tạo kế hoạch xử lý chi tiết:
  Câu hỏi: Điều kiện tốt nghiệp của trường là gì?
  ```

### Combined Message to LLM:
```json
{
  "messages": [
    {
      "role": "system",
      "content": "<8500 chars from agents_config.yaml>"
    },
    {
      "role": "user",
      "content": "<500 chars from agent .py file>"
    }
  ]
}
```

---

## 🔍 TROUBLESHOOTING

### If System Prompt Length = 0 or very small:
❌ **Problem**: Config not loading correctly
✅ **Fix**: Check config file path in `config_manager.py`

### If System Prompt Preview doesn't match config:
❌ **Problem**: Wrong config being loaded
✅ **Fix**: Verify `agents_config.yaml` is in `/services/orchestrator/config/`

### If all agents show same system prompt:
❌ **Problem**: Factory not distinguishing agent types
✅ **Fix**: Check `agent_factory.py` agent_id mapping

---

**Status**: ✅ Enhanced logging ready - restart backend to see full details
