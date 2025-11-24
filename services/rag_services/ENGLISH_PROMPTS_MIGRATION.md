# English Prompts Migration Summary

## 📋 Overview

Successfully migrated all LLM prompts from Vietnamese to English to improve compatibility with GPT-4, Gemini, and other English-trained LLMs while maintaining full support for Vietnamese text analysis.

**Date:** November 19, 2025  
**Status:** ✅ Complete & Tested  
**Impact:** Production-ready optimization

---

## 🎯 Motivation

### Why English Prompts?

1. **Better LLM Performance**
   - GPT-4, Gemini, Claude primarily trained on English
   - English instructions → More accurate understanding
   - Better few-shot learning with English patterns

2. **Clearer Instructions**
   - Standardized technical terminology
   - International best practices
   - Easier to debug and maintain

3. **Vietnamese Text Analysis Preserved**
   - Input text remains Vietnamese
   - Evidence kept in Vietnamese (source language)
   - Only instructions converted to English

---

## 📁 Files Modified

### 1. **config/prompts/relation_extraction.yaml**

**Changes Made:**
- Main prompt: Vietnamese → English
- 7 relation types: Documented in English with Vietnamese type names
- Few-shot examples: English categories (COURSE, REGULATION, etc.)
- Validation prompt: Converted to English
- **JSON escaped:** `{...}` → `{{...}}` for Python `.format()` compatibility

**Before:**
```yaml
relation_extraction_prompt: |
  Bạn là chuyên gia phân tích văn bản học thuật từ UIT.
  
  **NHIỆM VỤ:** Trích xuất quan hệ giữa các entities...
  **VĂN BẢN CẦN PHÂN TÍCH:**
  {text}
```

**After:**
```yaml
relation_extraction_prompt: |
  You are an expert in analyzing academic documents from UIT.
  
  **TASK:** Extract relationships between entities...
  **TEXT TO ANALYZE (Vietnamese):**
  {text}
```

### 2. **indexing/llm_relation_extractor.py**

**Changes Made:**
- Few-shot header: `**VÍ DỤ MINH HỌA:**` → `**FEW-SHOT EXAMPLES:**`
- Text section header: `**VĂN BẢN CẦN PHÂN TÍCH:**` → `**TEXT TO ANALYZE (Vietnamese):**`
- Example labels: `Ví dụ {i}:` → `Example {i}:`
- Entity context: `(Không có entities...)` → `(No entities detected...)`
- Fallback prompt: Converted to English

**Code Example:**
```python
# Old
few_shot_text = "\n\n**VÍ DỤ MINH HỌA:**\n"
for i, example in enumerate(examples[:2], 1):
    few_shot_text += f"\nVí dụ {i}:\n"

# New
few_shot_text = "\n\n**FEW-SHOT EXAMPLES:**\n"
for i, example in enumerate(examples[:2], 1):
    few_shot_text += f"\nExample {i}:\n"
```

---

## ✅ Validation & Testing

### Test Results: **4/4 Passed** 🎉

**Test Script:** `scripts/test_english_prompts.py`

#### Test 1: Prompt Loading ✅
- YAML loads without errors
- All 6 prompt keys present
- English headers verified:
  - `TEXT TO ANALYZE` ✓
  - `DETECTED ENTITIES` ✓
  - `ALLOWED RELATIONSHIP` ✓
  - `OUTPUT FORMAT` ✓

#### Test 2: Prompt Formatting ✅
- Template variables work: `{text}`, `{entities}`
- Vietnamese text preserved in output
- JSON examples intact (escaped correctly)
- English instructions present

#### Test 3: LLMRelationExtractor Compatibility ✅
- Prompts load correctly in extractor
- English instructions detected
- Formatting works with Vietnamese input
- 2,463 chars formatted prompt

#### Test 4: Extraction Prompt Structure ✅
- All critical components present:
  - Task description ✓
  - Relation types (7 types) ✓
  - Output format (JSON) ✓
  - Important rules ✓
  - Evidence requirement ✓
  - Confidence threshold ✓

---

## 🔧 Technical Details

### JSON Escaping in YAML

**Problem:** Python `.format()` interprets `{...}` as placeholders

**Solution:** Escape with `{{...}}`

```yaml
# Before (causes KeyError)
output: |
  [
    {
      "source_entity": "IT003",
      "confidence": 0.95
    }
  ]

# After (works correctly)
output: |
  [
    {{
      "source_entity": "IT003",
      "confidence": 0.95
    }}
  ]
```

### Prompt Structure

**Total Length:** ~2,436 chars (main prompt)

**Sections:**
1. **Role Definition** (English)
   - "You are an expert in analyzing academic documents..."

2. **Task Description** (English)
   - Extract relationships from Vietnamese text
   - 7 allowed relationship types

3. **Output Format** (JSON with English keys)
   - `source_entity`, `relation_type`, `confidence`, `evidence`

4. **Important Rules** (English)
   - Confidence >= 0.7
   - Evidence must be from original text (Vietnamese)
   - Correct categories

5. **Input Placeholders** (Vietnamese content)
   - `{text}` - Vietnamese text to analyze
   - `{entities}` - Detected entities

---

## 🌐 Language Strategy

### English Components
- ✅ Instructions to LLM
- ✅ Relation type descriptions
- ✅ Output format specifications
- ✅ Rules and guidelines
- ✅ Few-shot example labels

### Vietnamese Components
- ✅ Input text (`{text}`)
- ✅ Evidence field (quoted from source)
- ✅ Relation type names (e.g., `DIEU_KIEN_TIEN_QUYET`)
- ✅ Entity text values

### Hybrid Example
```json
{
  "source_entity": "IT003",          // Vietnamese entity
  "source_category": "COURSE",       // English category
  "relation_type": "DIEU_KIEN_TIEN_QUYET",  // Vietnamese type name
  "target_entity": "IT002",          // Vietnamese entity
  "target_category": "COURSE",       // English category
  "confidence": 0.95,
  "evidence": "Môn IT003 cần hoàn thành IT002 trước"  // Vietnamese evidence
}
```

---

## 📊 Impact Assessment

### Performance Improvements (Expected)
- **Better LLM Understanding:** English-trained models (GPT-4, Gemini) understand instructions more accurately
- **Fewer Parsing Errors:** Standardized JSON output format
- **Easier Debugging:** English prompts easier to review and modify
- **International Compatibility:** Works with any LLM provider

### Backward Compatibility
- ✅ No breaking changes to API
- ✅ Same input/output format
- ✅ All tests pass (82 tests, ~83% coverage)
- ✅ Existing code works unchanged

### Risks & Mitigations
| Risk | Mitigation | Status |
|------|-----------|--------|
| JSON escaping breaks formatting | Comprehensive testing with `.format()` | ✅ Resolved |
| Header mismatches in code | Updated all string literals in Python code | ✅ Resolved |
| Vietnamese text analysis degrades | Evidence field kept in Vietnamese | ✅ No impact |
| Fallback prompt still Vietnamese | Converted fallback to English | ✅ Resolved |

---

## 🚀 Usage Examples

### Example 1: Course Prerequisites

**Input Text (Vietnamese):**
```
Môn IT003 - Cấu trúc dữ liệu và giải thuật yêu cầu sinh viên
phải hoàn thành môn IT002 - Lập trình hướng đối tượng trước.
```

**Prompt (English Instructions):**
```
You are an expert in analyzing academic documents from UIT...

**TASK:** Extract relationships between entities from the Vietnamese text below.

**ALLOWED RELATIONSHIP TYPES:**
1. DIEU_KIEN_TIEN_QUYET (Prerequisite): Course A requires completing Course B first

**TEXT TO ANALYZE (Vietnamese):**
Môn IT003 - Cấu trúc dữ liệu...
```

**Expected Output:**
```json
[
  {
    "source_entity": "IT003",
    "source_category": "COURSE",
    "relation_type": "DIEU_KIEN_TIEN_QUYET",
    "target_entity": "IT002",
    "target_category": "COURSE",
    "confidence": 0.95,
    "evidence": "yêu cầu sinh viên phải hoàn thành môn IT002 trước"
  }
]
```

### Example 2: Regulation Application

**Input Text (Vietnamese):**
```
Quy chế 790/QĐ-ĐHCNTT áp dụng cho tất cả sinh viên khóa 2022
của các ngành thuộc Khoa Công nghệ Thông tin.
```

**Output:**
```json
[
  {
    "source_entity": "Quy chế 790/QĐ-ĐHCNTT",
    "source_category": "REGULATION",
    "relation_type": "AP_DUNG_CHO",
    "target_entity": "KHOA CNTT",
    "target_category": "DEPARTMENT",
    "confidence": 0.90,
    "evidence": "áp dụng cho...các ngành thuộc Khoa Công nghệ Thông tin"
  }
]
```

---

## 🔄 Migration Checklist

- [x] Convert main `relation_extraction_prompt` to English
- [x] Convert `course_prerequisites_prompt` to English
- [x] Convert `regulation_application_prompt` to English
- [x] Convert `validation_prompt` to English
- [x] Update few-shot example categories
- [x] Escape JSON in YAML (`{` → `{{`)
- [x] Update Python code string literals
- [x] Update fallback prompts
- [x] Update entity context messages
- [x] Create comprehensive tests
- [x] Run test suite (4/4 passed)
- [x] Update documentation

---

## 📚 Related Files

**Core Files:**
- `config/prompts/relation_extraction.yaml` - All prompts
- `indexing/llm_relation_extractor.py` - Prompt usage

**Testing:**
- `scripts/test_english_prompts.py` - Validation tests
- `tests/unit/test_llm_relation_extractor.py` - Unit tests (20 tests)

**Documentation:**
- `WEEK2_TESTING_SUMMARY.md` - Full testing docs
- `TESTING_GUIDE.md` - How to run tests

---

## 🎓 Best Practices Learned

1. **YAML + Python Format Strings**
   - Always escape `{` and `}` in YAML when using `.format()`
   - Use `{{...}}` for literal braces

2. **Prompt Engineering**
   - English instructions > Vietnamese for modern LLMs
   - Keep evidence in source language
   - Use clear section headers

3. **Hybrid Language Approach**
   - Instructions: English (LLM understanding)
   - Data: Original language (accuracy)
   - Schema: English (standardization)

4. **Testing Strategy**
   - Test YAML loading separately
   - Test template formatting
   - Test integration with system
   - Verify prompt structure

---

## 🏁 Conclusion

✅ **All English prompts successfully integrated**

**Key Achievements:**
- 100% test pass rate (4/4 tests)
- No breaking changes
- Better LLM compatibility
- Production-ready

**Next Steps:**
1. Monitor LLM extraction quality in production
2. Compare English vs Vietnamese prompt performance
3. Tune few-shot examples if needed
4. Consider adding more domain-specific prompts

---

**Status:** 🚀 **Ready for Production**

**Tested:** ✅ November 19, 2025  
**Approved:** Week 2 Complete - 100%
