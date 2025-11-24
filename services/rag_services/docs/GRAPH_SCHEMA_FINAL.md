# 📐 Knowledge Graph Schema - Quy Chế 790/QĐ-ĐHCNTT

## Naming Conventions

### Node Labels
**PascalCase**: `Document`, `Chapter`, `Article`, `Clause`, `Rule`, `Concept`

### Relationship Types
**UPPER_SNAKE_CASE**: `HAS_CHAPTER`, `HAS_ARTICLE`, `DEFINES_RULE`, `ABOUT_CONCEPT`

### Properties
**lower_snake_case**: `doc_id`, `article_no`, `clause_no`, `title_vi`, `raw_text`

### ID Format
Hierarchical, human-readable IDs:
- Document: `QD_790_2022`
- Chapter: `QD_790_2022_CH_III`
- Article: `QD_790_2022_ART_14`
- Clause: `QD_790_2022_ART_14_CL_1`
- Rule: `QD_790_2022_R_MIN_MAX_CREDITS_MAIN_SEM`
- Concept: `C_SV_DANG_KY_HOC_TAP`

---

## 📦 Node Definitions

### 1. Document
Toàn bộ văn bản quy chế

**Label**: `Document`

**Properties**:
```python
{
    "doc_id": "QD_790_2022",                 # Primary key
    "code": "790/QĐ-ĐHCNTT",
    "title_vi": "Quy chế đào tạo trình độ đại học theo hệ thống tín chỉ",
    "issue_date": "2022-09-28",              # ISO date string
    "effective_date": "2022-10-01",          # ISO date string
    "version": "1.0",
    "source_file": "790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf",
    "issuing_authority": "Trường ĐHCNTT - ĐHQG-HCM",
    "status": "active"                        # active | superseded | draft
}
```

---

### 2. Chapter
Chương trong quy chế

**Label**: `Chapter`

**Properties**:
```python
{
    "chapter_id": "QD_790_2022_CH_III",      # Primary key
    "doc_id": "QD_790_2022",                 # Foreign key
    "chapter_no": 3,                         # Integer
    "title_vi": "Đăng ký học phần và kế hoạch học tập",
    "page_start": 10,                        # Optional
    "page_end": 15                           # Optional
}
```

---

### 3. Article
Điều trong quy chế

**Label**: `Article`

**Properties**:
```python
{
    "article_id": "QD_790_2022_ART_14",      # Primary key
    "doc_id": "QD_790_2022",
    "chapter_id": "QD_790_2022_CH_III",
    "article_no": 14,                        # Integer
    "title_vi": "Đăng ký học phần",
    "raw_text": "Điều 14. Đăng ký học phần...",  # Full text
    "page_start": 12,                        # Optional
    "page_end": 13                           # Optional
}
```

---

### 4. Clause
Khoản trong mỗi điều

**Label**: `Clause`

**Properties**:
```python
{
    "clause_id": "QD_790_2022_ART_14_CL_1",  # Primary key
    "article_id": "QD_790_2022_ART_14",
    "clause_no": 1,                          # Integer or "a", "b", "c"
    "raw_text": "1. Trong học kỳ chính...",
    "item_index": null,                      # For sub-items (optional)
    "span_start": 0,                         # Character offset in article (optional)
    "span_end": 250                          # Character offset in article (optional)
}
```

---

### 5. Rule ⭐
**Linh hồn của GraphRAG** - Biểu diễn điều kiện/ràng buộc cụ thể

**Label**: `Rule`

**Properties**:
```python
{
    "rule_id": "QD_790_2022_R_MIN_MAX_CREDITS_MAIN_SEM",
    "name": "Giới hạn số tín chỉ đăng ký học kỳ chính",
    "rule_type": "LIMIT",                    # LIMIT | PERMISSION | OBLIGATION | PROHIBITION
    "severity": "INFO",                      # INFO | WARNING | CRITICAL
    "description_vi": "SV được đăng ký từ 14 đến 24 tín chỉ/học kỳ chính; tối đa 30 tín chỉ nếu ĐTBHK ≥ 8.0",
    "formula": "14 <= credits <= 24; if gpa_sem >= 8.0 then credits <= 30",
    "is_active": true,
    "source_doc_id": "QD_790_2022",
    "source_article_no": 14,
    "source_clause_no": 1
}
```

**Rule Types**:
- `LIMIT` - Giới hạn (tín chỉ, điểm số)
- `PERMISSION` - Được phép làm gì
- `OBLIGATION` - Bắt buộc phải làm
- `PROHIBITION` - Cấm làm

---

### 6. Concept
Cụm chủ đề để cluster Articles/Rules

**Label**: `Concept`

**Properties**:
```python
{
    "concept_id": "C_SV_DANG_KY_HOC_TAP",
    "name": "Sinh viên - Đăng ký học tập",
    "group": "STUDENT_RIGHTS",               # STUDENT_RIGHTS | ACADEMIC_STATUS | GRADUATION
    "description_vi": "Các quy định liên quan đến việc sinh viên đăng ký học phần...",
    "keywords": "đăng ký học phần; tín chỉ; khung tín chỉ; học hè"
}
```

**Concept Groups**:
- `STUDENT_RIGHTS` - Quyền của sinh viên
- `ACADEMIC_STATUS` - Trạng thái học vụ
- `GRADUATION` - Tốt nghiệp
- `REGISTRATION` - Đăng ký học tập
- `ASSESSMENT` - Kiểm tra đánh giá
- `TRANSFER` - Chuyển đổi chương trình

---

## 🔗 Relationship Definitions

### Structural Relationships

#### HAS_CHAPTER
```cypher
(:Document)-[:HAS_CHAPTER {order: int}]->(:Chapter)
```

#### HAS_ARTICLE
```cypher
(:Chapter)-[:HAS_ARTICLE {order: int}]->(:Article)
```

#### HAS_CLAUSE
```cypher
(:Article)-[:HAS_CLAUSE {order: int}]->(:Clause)
```

#### NEXT_ARTICLE
Sequential navigation between articles
```cypher
(:Article)-[:NEXT_ARTICLE]->(:Article)
```

#### NEXT_CLAUSE
Sequential navigation between clauses
```cypher
(:Clause)-[:NEXT_CLAUSE]->(:Clause)
```

---

### Semantic Relationships

#### DEFINES_RULE
Clause/Article defines a rule
```cypher
(:Clause)-[:DEFINES_RULE]->(:Rule)
(:Article)-[:DEFINES_RULE]->(:Rule)  // If rule at article level
```

#### ABOUT_CONCEPT
Rule belongs to a concept
```cypher
(:Rule)-[:ABOUT_CONCEPT {confidence: float}]->(:Concept)
```

---

## 📊 Mapping Table Schema

### regulation_rule_mapping

**Purpose**: LLM extraction output mapping Điều → Rule → Concept

**Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `doc_id` | string | Document ID | `QD_790_2022` |
| `chapter_no` | int | Chapter number | `3` |
| `article_no` | int | Article number | `14` |
| `clause_no` | int/string | Clause number | `1` or `"a"` |
| `article_id` | string | Article ID | `QD_790_2022_ART_14` |
| `clause_id` | string | Clause ID | `QD_790_2022_ART_14_CL_1` |
| `rule_id` | string | Rule ID | `QD_790_2022_R_MIN_MAX_CREDITS_MAIN_SEM` |
| `rule_name` | string | Rule name | `Giới hạn số tín chỉ HK chính` |
| `rule_type` | string | LIMIT/PERMISSION/OBLIGATION/PROHIBITION | `LIMIT` |
| `rule_severity` | string | INFO/WARNING/CRITICAL | `INFO` |
| `rule_description_vi` | text | Natural language description | `SV được ĐK từ 14–24 TC/học kỳ chính...` |
| `rule_formula` | text | Machine-readable expression | `14 <= credits <= 24; if gpa_sem >= 8.0...` |
| `concept_id` | string | Concept ID | `C_SV_DANG_KY_HOC_TAP` |
| `concept_name` | string | Concept name | `Sinh viên - Đăng ký học tập` |
| `concept_group` | string | Concept group | `STUDENT_RIGHTS` |
| `keywords` | text | Semicolon-separated keywords | `tín chỉ; đăng ký; học kỳ chính` |

---

## 📝 Example Rows

### Example 1: Credit Limit (Article 14, Clause 1)

```csv
doc_id,chapter_no,article_no,clause_no,article_id,clause_id,rule_id,rule_name,rule_type,rule_severity,rule_description_vi,rule_formula,concept_id,concept_name,concept_group,keywords
QD_790_2022,3,14,1,QD_790_2022_ART_14,QD_790_2022_ART_14_CL_1,QD_790_2022_R_MIN_MAX_CREDITS_MAIN_SEM,Giới hạn số tín chỉ HK chính,LIMIT,INFO,"SV được ĐK từ 14–24 TC/học kỳ chính; nếu ĐTBHK ≥ 8.0 thì có thể ĐK tối đa 30 TC theo quy định của trường","14 <= credits <= 24; if gpa_sem >= 8.0 then credits <= 30",C_SV_DANG_KY_HOC_TAP,Sinh viên - Đăng ký học tập,STUDENT_RIGHTS,"tín chỉ; đăng ký; học kỳ chính; số lượng tín chỉ"
```

### Example 2: Academic Warning (Article 16, Clause 1)

```csv
doc_id,chapter_no,article_no,clause_no,article_id,clause_id,rule_id,rule_name,rule_type,rule_severity,rule_description_vi,rule_formula,concept_id,concept_name,concept_group,keywords
QD_790_2022,3,16,1,QD_790_2022_ART_16,QD_790_2022_ART_16_CL_1,QD_790_2022_R_ACADEMIC_WARNING_CONDITION,Điều kiện cảnh báo học vụ,OBLIGATION,WARNING,"SV bị cảnh báo học vụ nếu ĐTBHK dưới ngưỡng quy định hoặc nhiều học kỳ liên tiếp không đạt yêu cầu theo Điều 16","if gpa_sem < threshold or consecutive_low_sem >= N then status = 'warning'",C_SV_XU_LY_HOC_VU,Sinh viên - Xử lý học vụ,ACADEMIC_STATUS,"cảnh báo học vụ; ĐTBHK; ngưỡng điểm; học vụ"
```

### Example 3: Dual Program (Article 18, Clause 1)

```csv
doc_id,chapter_no,article_no,clause_no,article_id,clause_id,rule_id,rule_name,rule_type,rule_severity,rule_description_vi,rule_formula,concept_id,concept_name,concept_group,keywords
QD_790_2022,4,18,1,QD_790_2022_ART_18,QD_790_2022_ART_18_CL_1,QD_790_2022_R_DUAL_PROGRAM_ELIGIBILITY,Điều kiện học cùng lúc 2 chương trình,PERMISSION,INFO,"SV được phép học 2 CTĐT nếu đã hoàn thành năm thứ nhất và ĐTBCTL, số TC tích lũy đạt ngưỡng theo quy định Điều 18","if completed_years >= 1 and gpa_cum >= x and credits_cum >= y then allow_dual_program = true",C_SV_HOC_2_CHUONG_TRINH,Sinh viên - Học cùng lúc 2 chương trình,STUDENT_RIGHTS,"học 2 chương trình; song ngành; điều kiện; ĐTBCTL; số tín chỉ"
```

---

## 🛠️ Implementation Pipeline

### Phase 1: Structure Extraction
```python
# Extract from PDF/Weaviate
documents = extract_documents()
chapters = extract_chapters()
articles = extract_articles()
clauses = extract_clauses()

# Create nodes in Neo4j
create_structural_nodes(documents, chapters, articles, clauses)
```

### Phase 2: Rule Extraction (LLM)
```python
# For each clause
for clause in clauses:
    # LLM extracts 0-n rules
    rules = llm_extract_rules(clause)
    
    # Save to mapping table
    save_to_mapping_table(rules)
```

### Phase 3: Graph Construction
```cypher
// Import from regulation_rule_mapping CSV

// 1. Create Rule nodes
LOAD CSV WITH HEADERS FROM 'file:///regulation_rule_mapping.csv' AS row
MERGE (r:Rule {rule_id: row.rule_id})
SET r.name = row.rule_name,
    r.rule_type = row.rule_type,
    r.severity = row.rule_severity,
    r.description_vi = row.rule_description_vi,
    r.formula = row.rule_formula,
    r.is_active = true,
    r.source_doc_id = row.doc_id,
    r.source_article_no = toInteger(row.article_no),
    r.source_clause_no = toInteger(row.clause_no);

// 2. Create Concept nodes
LOAD CSV WITH HEADERS FROM 'file:///regulation_rule_mapping.csv' AS row
MERGE (c:Concept {concept_id: row.concept_id})
SET c.name = row.concept_name,
    c.group = row.concept_group,
    c.keywords = row.keywords;

// 3. Create DEFINES_RULE relationships
LOAD CSV WITH HEADERS FROM 'file:///regulation_rule_mapping.csv' AS row
MATCH (cl:Clause {clause_id: row.clause_id})
MATCH (r:Rule {rule_id: row.rule_id})
MERGE (cl)-[:DEFINES_RULE]->(r);

// 4. Create ABOUT_CONCEPT relationships
LOAD CSV WITH HEADERS FROM 'file:///regulation_rule_mapping.csv' AS row
MATCH (r:Rule {rule_id: row.rule_id})
MATCH (c:Concept {concept_id: row.concept_id})
MERGE (r)-[:ABOUT_CONCEPT {confidence: 1.0}]->(c);
```

---

## 🎯 Query Examples

### Find all rules about registration
```cypher
MATCH (c:Concept {concept_id: 'C_SV_DANG_KY_HOC_TAP'})
      <-[:ABOUT_CONCEPT]-(r:Rule)
      <-[:DEFINES_RULE]-(cl:Clause)
      <-[:HAS_CLAUSE]-(a:Article)
RETURN a.article_no, a.title_vi, r.name, r.description_vi, cl.raw_text
```

### Find credit limits for main semester
```cypher
MATCH (r:Rule)
WHERE r.rule_type = 'LIMIT' 
  AND r.name CONTAINS 'tín chỉ'
  AND r.name CONTAINS 'học kỳ chính'
RETURN r.formula, r.description_vi
```

### Get full citation for a rule
```cypher
MATCH (r:Rule {rule_id: 'QD_790_2022_R_MIN_MAX_CREDITS_MAIN_SEM'})
      <-[:DEFINES_RULE]-(cl:Clause)
      <-[:HAS_CLAUSE]-(a:Article)
      <-[:HAS_ARTICLE]-(ch:Chapter)
      <-[:HAS_CHAPTER]-(d:Document)
RETURN 
  d.code AS quy_che,
  ch.chapter_no AS chuong,
  a.article_no AS dieu,
  cl.clause_no AS khoan,
  r.description_vi AS quy_dinh
```

---

## 📋 Implementation Checklist

### ✅ Phase 1: Structure
- [ ] Extract Document nodes
- [ ] Extract Chapter nodes  
- [ ] Extract Article nodes
- [ ] Extract Clause nodes
- [ ] Create HAS_* relationships
- [ ] Create NEXT_* relationships

### ⏳ Phase 2: Rules & Concepts
- [ ] Define Concept taxonomy (8-10 concepts)
- [ ] Create LLM prompt for rule extraction
- [ ] Extract rules for top 20 articles
- [ ] Generate regulation_rule_mapping.csv
- [ ] Import to Neo4j

### 🔮 Phase 3: Advanced
- [ ] Cross-reference detection (Article refers to Article)
- [ ] Rule conflict detection
- [ ] Temporal rules (effective dates)
- [ ] Multi-document support

---

**Version**: 2.0  
**Status**: Schema finalized, ready for implementation  
**Next**: Build Phase 1 extraction script with new naming convention
