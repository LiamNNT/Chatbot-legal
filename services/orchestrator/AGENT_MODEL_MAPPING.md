# Agent-Model Mapping và Model Cleanup Report

**Date:** October 15, 2025  
**Status:** ✅ Completed

## 📊 Tổng Quan

Đã kiểm tra và làm sạch các model không sử dụng trong hệ thống Orchestrator. Bản báo cáo này chi tiết về việc mapping giữa các agent và model của chúng, cũng như các thay đổi đã thực hiện.

---

## 🎯 Agent-to-Model Mapping (Sau khi cập nhật)

### 1. **PlannerAgent**
- **Model:** `mistralai/mistral-7b-instruct:free`
- **Temperature:** 0.3 (Low for consistent planning)
- **Max Tokens:** 1000
- **Nhiệm vụ:** Phân tích câu hỏi và tạo kế hoạch xử lý
- **Lý do chọn model:** Mistral-7B có khả năng reasoning tốt cho việc lập kế hoạch

### 2. **QueryRewriterAgent**
- **Model:** `mistralai/mistral-7b-instruct:free`
- **Temperature:** 0.4 (Moderate creativity)
- **Max Tokens:** 800
- **Nhiệm vụ:** Tối ưu hóa câu hỏi cho tìm kiếm
- **Lý do chọn model:** Cùng model với Planner để tối ưu chi phí, đủ tốt cho query rewriting

### 3. **AnswerAgent**
- **Model:** `google/gemma-3-27b-it:free`
- **Temperature:** 0.2 (Low for factual accuracy)
- **Max Tokens:** 1500
- **Nhiệm vụ:** Tạo câu trả lời toàn diện từ context
- **Lý do chọn model:** Gemma-3 27B có khả năng tổng hợp thông tin tốt với instruction following cao

### 4. **VerifierAgent**
- **Model:** `deepseek/deepseek-r1-free`
- **Temperature:** 0.1 (Very low for critical evaluation)
- **Max Tokens:** 1200
- **Nhiệm vụ:** Kiểm tra chất lượng và độ chính xác
- **Lý do chọn model:** DeepSeek R1 có khả năng reasoning và critical thinking mạnh

### 5. **ResponseAgent**
- **Model:** `meituan/longcat-flash-chat:free`
- **Temperature:** 0.6 (Moderate-high for natural responses)
- **Max Tokens:** 1000
- **Nhiệm vụ:** Tạo phản hồi thân thiện cho người dùng
- **Lý do chọn model:** LongCat Flash optimized cho conversation và natural language generation

---

## 🔧 Thay Đổi Đã Thực Hiện

### 1. **File: `config/agents_config.yaml`**

#### ❌ Models ĐÃ XÓA (không được sử dụng):
```yaml
# TRƯỚC ĐÂY (SAI):
query_rewriter_model:
  name: "microsoft/wizardlm-2-8x22b:free"  # ❌ Không được dùng

verifier_model:
  name: "meta-llama/llama-3.1-8b-instruct:free"  # ❌ Không được dùng

response_model:
  name: "anthropic/claude-3.5-haiku:beta"  # ❌ Không được dùng
```

#### ✅ Models ĐÃ CẬP NHẬT (khớp với code thực tế):
```yaml
# SAU KHI SỬA (ĐÚNG):
query_rewriter_model:
  name: "mistralai/mistral-7b-instruct:free"  # ✅ Đúng model được dùng
  temperature: 0.4
  max_tokens: 800

verifier_model:
  name: "deepseek/deepseek-r1-free"  # ✅ Đúng model được dùng
  temperature: 0.1
  max_tokens: 1200

response_model:
  name: "meituan/longcat-flash-chat:free"  # ✅ Đúng model được dùng
  temperature: 0.6
  max_tokens: 1000
```

### 2. **File: `app/adapters/openrouter_adapter.py`**

#### ❌ Models ĐÃ XÓA khỏi `get_supported_models()`:
```python
# TRƯỚC ĐÂY (9 models - nhiều thừa):
self._supported_models = [
    "openai/gpt-4",                      # ❌ Xóa - không dùng
    "openai/gpt-4-turbo",               # ❌ Xóa - không dùng
    "openai/gpt-3.5-turbo",             # ❌ Xóa - không dùng
    "anthropic/claude-3-opus",          # ❌ Xóa - không dùng
    "anthropic/claude-3-sonnet",        # ❌ Xóa - không dùng
    "anthropic/claude-3-haiku",         # ❌ Xóa - không dùng
    "google/gemini-pro",                # ❌ Xóa - không dùng
    "meta-llama/llama-2-70b-chat",      # ❌ Xóa - không dùng
    "mistralai/mixtral-8x7b-instruct"   # ❌ Xóa - không dùng
]
```

#### ✅ Models GIỮ LẠI (chỉ những model thực sử dụng):
```python
# SAU KHI SỬA (4 models - chỉ những gì cần):
self._supported_models = [
    "mistralai/mistral-7b-instruct:free",      # ✅ PlannerAgent, QueryRewriterAgent
    "google/gemma-3-27b-it:free",              # ✅ AnswerAgent
    "deepseek/deepseek-r1-free",               # ✅ VerifierAgent
    "meituan/longcat-flash-chat:free"          # ✅ ResponseAgent
]
```

**Kết quả:** Giảm từ 9 models xuống còn 4 models (giảm 55%)

---

## 📈 Lợi Ích Của Việc Cleanup

### 1. **Rõ ràng hơn**
- Configuration file giờ đây chính xác phản ánh model thực sử dụng
- Không còn confusion giữa config và implementation

### 2. **Bảo trì dễ hơn**
- Developer biết chính xác agent nào dùng model nào
- Dễ dàng track cost và performance cho từng agent

### 3. **Tối ưu tài nguyên**
- Không load metadata cho models không dùng
- Code cleaner và focused hơn

### 4. **Consistency**
- Config file và agent code giờ đây 100% đồng bộ
- Không còn discrepancy giữa documented và actual models

---

## 🔍 Chi Tiết Model Được Sử Dụng

### **Mistral-7B Instruct (FREE)** - 2 agents sử dụng

```
Provider: Mistral AI
Size: 7 billion parameters
Type: Instruction-tuned
Cost: FREE tier
Agents: PlannerAgent, QueryRewriterAgent
Default Model: YES (used as fallback/default)
```

**Ưu điểm:**
- Reasoning capability tốt
- Hiệu quả với instruction following
- Free tier - không tốn chi phí
- Nhanh và ổn định
- Được sử dụng làm DEFAULT_MODEL cho hệ thống

**Use cases:**
- Planning và strategy (PlannerAgent)
- Query optimization (QueryRewriterAgent)
- Fallback model khi không chỉ định model cụ thể

---

### **Google Gemma-3 27B IT (FREE)** - 1 agent sử dụng
```
Provider: Google
Size: 27 billion parameters
Type: Instruction-tuned
Cost: FREE tier
Agent: AnswerAgent
```

**Ưu điểm:**
- Large model với capability cao
- Excellent at information synthesis
- Strong context understanding
- Free tier available

**Use cases:**
- Comprehensive answer generation
- Multi-source information synthesis
- Detailed explanations

---

### **DeepSeek R1 (FREE)** - 1 agent sử dụng
```
Provider: DeepSeek
Model: R1 (Reasoning model)
Type: Critical thinking & verification
Cost: FREE tier
Agent: VerifierAgent
```

**Ưu điểm:**
- Specialized for reasoning
- Excellent critical thinking
- Strong fact-checking capability
- Chain-of-thought reasoning

**Use cases:**
- Answer verification
- Quality assurance
- Fact-checking

---

### **Meituan LongCat Flash Chat (FREE)** - 1 agent sử dụng
```
Provider: Meituan
Model: LongCat Flash Chat
Type: Conversational AI
Cost: FREE tier
Agent: ResponseAgent
```

**Ưu điểm:**
- Optimized for natural conversation
- Fast response generation
- User-friendly tone
- Good at formatting responses

**Use cases:**
- Final response formatting
- User-friendly communication
- Conversational polish

---

## 📝 Kiểm Tra Sau Cleanup

### ✅ Checklist đã hoàn thành:

- [x] Verify tất cả agents có model được config đúng
- [x] Remove các models không sử dụng từ `agents_config.yaml`
- [x] Update `get_supported_models()` chỉ return models thực tế
- [x] Add comments giải thích model assignment
- [x] Verify temperature settings phù hợp với từng agent
- [x] Ensure consistency giữa config và code
- [x] Document agent-model mapping
- [x] Update max_tokens cho VerifierAgent (800 → 1200)

---

## 🎓 Bài Học & Best Practices

### 1. **Configuration Consistency**
Luôn đảm bảo config file và actual implementation đồng bộ. Sử dụng config file làm single source of truth.

### 2. **Model Selection Strategy**
- **Planning/Reasoning:** Models với reasoning capability (Mistral, DeepSeek)
- **Information Synthesis:** Large models (Gemma-3 27B)
- **Verification:** Specialized reasoning models (DeepSeek R1)
- **Response Generation:** Conversational models (LongCat)

### 3. **Temperature Settings**
- **0.1-0.3:** Critical tasks (verification, planning)
- **0.4-0.6:** Creative but controlled (query rewriting, response)
- **0.7+:** High creativity (không dùng trong system này)

### 4. **Free Tier Usage**
Tất cả models đều sử dụng free tier để tối ưu chi phí trong development và testing.

---

## 🔄 Future Improvements

### Potential Enhancements:
1. **Dynamic Model Selection:** Cho phép switch models dựa trên workload
2. **Model Performance Monitoring:** Track latency và quality metrics
3. **A/B Testing:** Test different models cho cùng agent role
4. **Fallback Strategy:** Define fallback models khi primary model unavailable
5. **Cost Optimization:** Monitor usage và optimize cho production

---

## 📞 Support & Questions

Nếu có thắc mắc về model selection hoặc cần thay đổi model cho agent nào:

1. Tham khảo document này để hiểu current mapping
2. Review agent requirements và model capabilities
3. Update cả 2 files: `agents_config.yaml` và agent code
4. Test thoroughly trước khi deploy

---

## 📚 References

- OpenRouter Models: https://openrouter.ai/models
- Mistral AI: https://mistral.ai/
- Google Gemma: https://ai.google.dev/gemma
- DeepSeek: https://www.deepseek.com/
- Agent Architecture: See `services/orchestrator/README.md`

---

**Report Generated:** October 15, 2025  
**Last Updated:** October 15, 2025  
**Version:** 1.0  
**Status:** ✅ Production Ready
