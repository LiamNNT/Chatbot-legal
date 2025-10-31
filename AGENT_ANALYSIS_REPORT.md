# Báo Cáo Phân Tích Logs Agent System
**Ngày**: 31/10/2025  
**Query test**: "Nguyên tắc xác định học phí là gì?"

---

## 📊 Tổng Quan Pipeline

| Step | Agent | Status | Model | Tokens | Time |
|------|-------|--------|-------|--------|------|
| 1 | Planner | ✅ OK | gpt-4o-mini | 2,108 | ~14s |
| 2 | Query Rewriter | ✅ OK | gpt-4o-mini | 1,865 | ~4s |
| 2.5 | RAG Retrieval | ⚠️ OK with issues | - | - | ~0.6s |
| 3 | Answer Agent | ❌ **FAILED** | deepseek-v3.2-exp | 0 | ~30s |
| 4 | Verifier | ⏭️ SKIPPED | - | - | - |
| 5 | Response Agent | ⚠️ OK (bad input) | gpt-4o-mini | 1,671 | ~7s |

**Total Time**: ~56s  
**Critical Error**: Answer Agent failed to generate response

---

## ✅ AGENTS HOẠT ĐỘNG ĐÚNG

### 1. **Planner Agent** ✅

**Input from config**: ✅ ĐÚNG
- Prompt khớp với `agents_config.yaml`
- System prompt về UIT domain context
- Few-shot examples cho simple/medium/complex
- Chain-of-thought reasoning process

**Output**:
```json
{
  "intent": "fee_inquiry",
  "complexity": "medium", 
  "complexity_score": 5.0,
  "reasoning_chain": [
    "Câu hỏi yêu cầu thông tin về nguyên tắc xác định học phí...",
    "Cần tổng hợp thông tin từ nhiều nguồn...",
    "...không yêu cầu thông tin theo thời gian cụ thể..."
  ],
  "estimated_tokens": 250
}
```

**Đánh giá**:
- ✅ Phân loại intent đúng: `fee_inquiry`
- ✅ Complexity score hợp lý: 5.0 (medium)
- ✅ Reasoning chain có logic
- ✅ JSON format hợp lệ
- ✅ Estimated tokens khá chính xác (250 vs thực tế ~2100)

### 2. **Query Rewriter Agent** ✅

**Input from config**: ✅ ĐÚNG
- Prompt có UIT terminology map
- Expansion/Refinement/Specialization strategies
- Few-shot examples

**Output**:
```json
{
  "original_query": "Nguyên tắc xác định học phí là gì?",
  "rewritten_queries": [
    "Nguyên tắc xác định học phí tại UIT",
    "Cách thức xác định học phí cho sinh viên Đại học Công nghệ Thông tin",
    "Yêu cầu và nguyên tắc tính học phí tại ĐHQG-HCM"
  ],
  "search_terms": ["học phí", "nguyên tắc", "xác định", "sinh viên", "UIT", "ĐHQG-HCM"],
  "confidence": 0.92
}
```

**Đánh giá**:
- ✅ 3 biến thể query hợp lý, tăng dần độ specific
- ✅ Thêm context "tại UIT", "ĐHQG-HCM" đúng domain
- ✅ Search terms extracted đầy đủ
- ✅ Confidence score reasonable (0.92)

### 3. **RAG Retrieval** ⚠️

**Process**:
- 3 queries → 3 API calls to RAG service
- Retrieved 5 documents total
- Scores: 5.15, 4.87, 3.84, 3.56, 3.28

**Issues Found**:
```
⚠️ Document title field is EMPTY
Mapped doc 1: content_length=2948, title=
Mapped doc 2: content_length=3107, title=
```

**Đánh giá**:
- ✅ Documents có content đầy đủ (2000-3000 chars)
- ⚠️ **Title field trống** - có thể gây confusion cho agent
- ✅ Scores reasonable (3-5 range)
- ✅ Deduplication và ranking hoạt động

**Recommendation**:
```python
# Fix title extraction in RAG service or orchestrator
if not doc.get("title"):
    doc["title"] = f"Quy định {doc.get('doc_id', 'N/A')}"
```

---

## ❌ AGENTS BỊ LỖI

### 4. **Answer Agent** ❌ CRITICAL FAILURE

**Error Log**:
```
2025-10-31 16:23:39,911 - ERROR - Answer generation failed: 
```

**Problems**:
1. **Exception message RỖNG** - không rõ lý do lỗi
2. Model `deepseek/deepseek-v3.2-exp` timeout hoặc API error?
3. Prompt quá dài (5 docs × 3000 chars = 15KB)?
4. Không có fallback mechanism

**Input Analysis**:
```
Prompt includes:
- Query: "Nguyên tắc xác định học phí là gì ?"
- 3 rewritten queries
- 5 documents with FULL content (not truncated)
- Tasks and requirements from system prompt
```

**Potential Causes**:
- ⚠️ **Deepseek API timeout** (30s elapsed)
- ⚠️ **Token limit exceeded** (input ~15K chars)
- ⚠️ **API rate limit / quota**
- ⚠️ **Model unavailable / error**

**Impact**:
- Skip Verification step
- Response Agent receives "Không thể tạo câu trả lời."
- User gets **hallucinated answer** not based on documents!

**Fix Applied**:
```python
# Added exc_info=True to see full traceback
logger.error(f"Answer generation failed: {e}", exc_info=True)
```

---

## ⚠️ AGENTS HOẠT ĐỘNG NHƯNG CÓ VẤN ĐỀ

### 5. **Response Agent** ⚠️

**Input**: 
```
THÔNG TIN ĐÃ KIỂM CHỨNG:
Không thể tạo câu trả lời.
```

**Output**:
```json
{
  "final_response": "Chào bạn! 👋\n\nNguyên tắc xác định học phí tại UIT thường dựa vào các yếu tố sau:\n\n**1. Chi phí đào tạo:**\n- Bao gồm chi phí giảng viên...\n\n**4. Học kỳ:**\n- Học phí được tính theo từng học kỳ, thường là **7,200,000 V...",
  "tone": "friendly",
  "user_friendliness_score": 0.95
}
```

**Problems**:
- ❌ **HALLUCINATION**: Model tự nghĩ ra thông tin không có trong documents
- ❌ Số tiền "7,200,000 VNĐ" có trong docs nhưng không được verify
- ❌ Không warning user về việc thiếu thông tin

**Expected Behavior**:
```
"Xin lỗi, hiện tại hệ thống gặp sự cố khi xử lý câu hỏi của bạn.
Vui lòng thử lại sau hoặc liên hệ phòng Đào tạo để được hỗ trợ trực tiếp."
```

---

## 🔍 PROMPT ANALYSIS

### Prompts từ `agents_config.yaml`:

#### ✅ Planner Prompt - **EXCELLENT**
- Detailed 6-step reasoning process
- Clear complexity scoring (0-10 scale with 4 factors)
- 3 few-shot examples (simple/medium/complex)
- UIT domain context
- JSON validation rules
- **Length**: ~2000 lines - very comprehensive

#### ✅ Query Rewriter Prompt - **GOOD**
- 3 rewriting strategies clearly defined
- UIT terminology map (HP, KHMT, CNTT, etc.)
- 3 diverse few-shot examples
- Quality rules for output
- **Length**: ~1000 lines

#### ✅ Answer Agent Prompt - **EXCELLENT BUT TOO LONG**
- 5-step reasoning process (Context → Extraction → Synthesis → Construction → Quality)
- UIT context awareness
- 3 detailed few-shot examples
- Answer principles and formatting
- **Problem**: Combined với 5 docs × 3000 chars → quá dài
- **Length**: ~3000 lines + documents

**Recommendation**:
```yaml
# Cân nhắc rút gọn Answer Agent prompt hoặc limit doc length
parameters:
  max_doc_length: 1000  # chars per doc
  max_total_context: 5000  # total chars from all docs
```

#### ✅ Verifier Prompt - **GOOD**
- 5-step self-review
- Weighted scoring (accuracy 40%, completeness 25%, etc.)
- Issue classification (critical/major/minor)
- **Length**: ~1500 lines

#### ✅ Response Agent Prompt - **CONCISE & CLEAR**
- Simple 4-step process
- Formatting guidelines
- Emoji usage rules
- **Length**: ~800 lines - just right

---

## 📈 RECOMMENDATIONS

### IMMEDIATE FIXES (P0):

1. **Fix Answer Agent Error Logging** ✅ DONE
   ```python
   logger.error(f"Answer generation failed: {e}", exc_info=True)
   ```

2. **Add Fallback for Answer Agent Failure**
   ```python
   if answer_result is None:
       return OrchestrationResponse(
           response="Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại sau.",
           session_id=request.session_id,
           error_code="ANSWER_AGENT_FAILED"
       )
   ```

3. **Fix Empty Title in Documents**
   ```python
   for doc in mapped_documents:
       if not doc.get("title"):
           doc["title"] = f"Tài liệu {doc.get('metadata', {}).get('doc_id', 'Unknown')}"
   ```

### OPTIMIZATION (P1):

4. **Limit Document Content Length**
   ```python
   max_chars_per_doc = 1000
   doc["content"] = doc["content"][:max_chars_per_doc] + "..." if len(doc["content"]) > max_chars_per_doc else doc["content"]
   ```

5. **Add Timeout Handling for Answer Agent**
   ```python
   async with asyncio.timeout(45):  # 45s timeout
       answer_result = await self.answer_agent.process(answer_input)
   ```

6. **Try Alternative Model if Deepseek Fails**
   ```yaml
   answer_model_fallback:
     name: "openai/gpt-4o-mini"  # fallback if deepseek fails
   ```

### MONITORING (P2):

7. **Add Metrics Logging**
   ```python
   logger.info(f"Agent performance: planner={plan_time}s, rewriter={rewrite_time}s, answer={answer_time}s")
   ```

8. **Alert on Answer Agent Failures**
   ```python
   if answer_result is None:
       send_alert("Answer Agent failure", query, error_details)
   ```

---

## 🎯 SUMMARY

### ✅ What's Working:
- Planner, Query Rewriter agents hoạt động xuất sắc
- Prompts từ config file được load và sử dụng đúng
- RAG retrieval tìm được documents relevant
- Response Agent format output đẹp (nhưng hallucinate)

### ❌ Critical Issues:
- **Answer Agent fails completely** - root cause chưa rõ
- Error logging không đủ thông tin (đã fix)
- Không có fallback khi Answer Agent fail
- User nhận response không accurate (hallucination)

### 📊 Next Steps:
1. Chạy lại với logging cải thiện để thấy error chi tiết
2. Test riêng Answer Agent với input nhỏ hơn
3. Xem xét switch sang model khác nếu Deepseek không stable
4. Implement proper error handling và fallback

---

**Prepared by**: GitHub Copilot  
**Date**: October 31, 2025
