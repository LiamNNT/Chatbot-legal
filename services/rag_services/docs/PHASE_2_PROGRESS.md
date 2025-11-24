# 🤖 Phase 2 Progress - Rule Extraction with LLM

## ✅ Hoàn thành

### 1. Concept Taxonomy (8 nodes)
```
✅ C_SV_DANG_KY_HOC_TAP     - Đăng ký học tập (STUDENT_RIGHTS)
✅ C_SV_XU_LY_HOC_VU         - Xử lý học vụ (ACADEMIC_STATUS)  
✅ C_SV_HOC_2_CHUONG_TRINH   - Học 2 chương trình (STUDENT_RIGHTS)
✅ C_SV_TOT_NGHIEP           - Tốt nghiệp (GRADUATION)
✅ C_SV_CHUYEN_NGANH         - Chuyển ngành (ACADEMIC_STATUS)
✅ C_SV_HOC_PHI              - Học phí & tín chỉ (REGISTRATION)
✅ C_SV_DANH_GIA             - Đánh giá & kiểm tra (ASSESSMENT)
✅ C_SV_THUC_TAP             - Thực tập & khóa luận (GRADUATION)
```

### 2. LLM Prompt Template
- ✅ System prompt với clear instructions
- ✅ JSON output format với 6 fields: rule_name, rule_type, severity, description_vi, formula, concepts
- ✅ 5 examples covering all rule types
- ✅ Support for complex formulas: `if...then...`, `AND`, `OR`, `>=`, `<=`

### 3. Extraction Script
- ✅ `scripts/build_graph_phase2_rules.py` - Main pipeline
- ✅ OpenRouter API integration (Claude 3.5 Sonnet)
- ✅ Batch processing by articles
- ✅ Auto create Rule nodes + relationships
- ✅ CSV export for review
- ✅ CLI arguments: `--test`, `--articles`, `--all`, `--limit`

### 4. Test Extraction
**Command**: `python scripts/build_graph_phase2_rules.py --test --limit 3`

**Results**:
```
✅ 3 rules extracted successfully
✅ CSV exported: data/extracted_rules_20251119_180510.csv
✅ All relationships created
```

**Sample Rule**:
```json
{
  "rule_id": "QD_790_2022_R_ART14_CL3_1",
  "name": "Khoi_luong_thuc_tap_toi_thieu_chuong_trinh_chuyen_sau",
  "rule_type": "LIMIT",
  "severity": "CRITICAL",
  "description_vi": "Đối với chương trình đào tạo chuyên sâu đặc thù, khối lượng thực tập tối thiểu là 8 tín chỉ",
  "formula": "if program_type == 'chuyen_sau_dac_thu' then credits_thuc_tap >= 8",
  "concepts": ["C_SV_THUC_TAP"]
}
```

---

## 📊 Current Graph State

### Nodes
| Label | Count |
|-------|-------|
| Document | 1 |
| Chapter | 7 |
| Article | 433 |
| Clause | 4,565 |
| **Concept** | **8** ⭐ |
| **Rule** | **3** ⭐ (test only) |

### Relationships
| Type | Count |
|------|-------|
| HAS_CHAPTER | 7 |
| HAS_ARTICLE | 433 |
| HAS_CLAUSE | 4,565 |
| NEXT_ARTICLE | 5,186 |
| NEXT_CLAUSE | 160,085 |
| **DEFINES_RULE** | **117** ⭐ (includes duplicates from parsing) |
| **ABOUT_CONCEPT** | **3** ⭐ |

---

## 🎯 Next Steps

### Option 1: Full Extraction (Recommended)
Extract rules from ALL priority articles:

```bash
# Top 11 priority articles (estimated 50-100 rules)
python scripts/build_graph_phase2_rules.py

# Articles: 14, 16, 18, 33, 4, 25, 19, 11, 17, 31, 32
# Estimated cost: ~$0.50 - $1.00 (Claude 3.5 Sonnet via OpenRouter)
# Estimated time: 5-10 minutes
```

### Option 2: Targeted Extraction
Extract specific articles:

```bash
# Just registration + graduation rules
python scripts/build_graph_phase2_rules.py --articles 14,33

# Just academic status rules
python scripts/build_graph_phase2_rules.py --articles 16,17
```

### Option 3: Review & Refine
Before full extraction, you may want to:
1. Review `data/extracted_rules_*.csv` quality
2. Adjust prompt template if needed
3. Test with different LLM model (cheaper: `google/gemini-2.0-flash-exp`)
4. Fix duplicate clause issue in Phase 1 parser

---

## 🔍 Query Examples (Ready to Test)

### Find all rules about registration
```cypher
MATCH (c:Concept {concept_id: 'C_SV_DANG_KY_HOC_TAP'})
      <-[:ABOUT_CONCEPT]-(r:Rule)
      <-[:DEFINES_RULE]-(cl:Clause)
      <-[:HAS_CLAUSE]-(a:Article)
RETURN a.article_no AS article,
       a.title_vi AS article_title,
       r.name AS rule_name,
       r.formula AS formula,
       r.description_vi AS description
ORDER BY a.article_no
```

### Find credit limit rules
```cypher
MATCH (r:Rule)
WHERE r.rule_type = 'LIMIT' 
  AND r.formula CONTAINS 'credits'
RETURN r.name, r.formula, r.description_vi
```

### Get graduation requirements
```cypher
MATCH (c:Concept {concept_id: 'C_SV_TOT_NGHIEP'})
      <-[:ABOUT_CONCEPT]-(r:Rule)
WHERE r.severity = 'CRITICAL'
RETURN r.name, r.formula, r.description_vi
ORDER BY r.source_article_no
```

### Full context query
```cypher
MATCH (d:Document)-[:HAS_CHAPTER]->(ch:Chapter)
      -[:HAS_ARTICLE]->(a:Article)
      -[:HAS_CLAUSE]->(cl:Clause)
      -[:DEFINES_RULE]->(r:Rule)
      -[:ABOUT_CONCEPT]->(c:Concept)
WHERE a.article_no = 14
RETURN d.code AS regulation,
       ch.chapter_no + ': ' + ch.title_vi AS chapter,
       a.article_no + ': ' + a.title_vi AS article,
       cl.clause_no AS clause,
       r.name AS rule,
       r.formula AS formula,
       collect(c.name) AS concepts
```

---

## 📁 Files Created

### Scripts
- ✅ `scripts/create_concepts.py` - Create 8 Concept nodes
- ✅ `scripts/rule_extraction_prompts.py` - LLM prompt templates
- ✅ `scripts/build_graph_phase2_rules.py` - Main extraction pipeline

### Data
- ✅ `data/extracted_rules_20251119_180510.csv` - Test extraction output
- ✅ `data/regulation_rule_mapping_template.csv` - Manual mapping template

### Documentation
- ✅ `docs/GRAPH_SCHEMA_FINAL.md` - Complete schema spec
- ✅ `docs/PHASE_1_COMPLETE.md` - Phase 1 summary

---

## ⚠️ Known Issues

### 1. Duplicate Clauses in Phase 1
**Problem**: Parser creates multiple Article 14 nodes with same clause_no

**Impact**: 
- 117 DEFINES_RULE relationships for only 3 rules
- Inflated relationship counts

**Solution Options**:
- A. Fix parser in `scripts/build_graph_phase1.py`
- B. Add UNIQUE constraint on clause_id
- C. Deduplicate in Phase 2 extraction query

### 2. LLM Output Variability
**Observation**: Rule names use snake_case instead of Vietnamese spaces

**Example**: 
- Got: `Khoi_luong_thuc_tap_toi_thieu_chuong_trinh_chuyen_sau`
- Expected: `Khối lượng thực tập tối thiểu chương trình chuyên sâu`

**Solution**: Update prompt to specify Vietnamese naming convention

---

## 💰 Cost Estimate

### Test Run (3 clauses)
- **Model**: Claude 3.5 Sonnet
- **Tokens**: ~1,500 input + ~500 output per clause
- **Cost**: ~$0.02
- **Quality**: ⭐⭐⭐⭐⭐ Excellent

### Full Priority Extraction (estimated 200 clauses)
- **Cost**: ~$1.50 - $2.00
- **Expected rules**: 50-100 high-quality rules
- **Time**: 10-15 minutes

### Alternative: Gemini Flash
- **Model**: `google/gemini-2.0-flash-exp`
- **Cost**: 90% cheaper (~$0.15 for full extraction)
- **Quality**: ⭐⭐⭐⭐ Very good
- **Speed**: Faster

---

## 🎓 Recommendations

### Immediate Next Steps
1. ✅ **Review test output** - Check `data/extracted_rules_*.csv` quality
2. ⏳ **Run full extraction** - Extract from priority articles
3. ⏳ **Test GraphRAG queries** - Verify semantic search works
4. ⏳ **Fix duplicate clauses** - Clean up Phase 1 parser

### Phase 3 (Optional)
- Add Entity nodes: STUDENT, PROGRAM, COURSE
- Add Process nodes: REGISTRATION, ACADEMIC_WARNING, GRADUATION_REVIEW
- Cross-reference detection: Article→Article
- Temporal rules: Effective dates, version control

---

**Status**: ✅ Phase 2 Infrastructure Complete - Ready for Full Extraction  
**Next Action**: Run `python scripts/build_graph_phase2_rules.py` to extract all rules  
**Updated**: 2025-11-19 18:05
