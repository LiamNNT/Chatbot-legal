# 📊 Knowledge Graph Schema V2 - Quy Chế Đào Tạo UIT

## Tổng Quan

Schema được thiết kế theo **2-layer architecture**:
- **Layer 1**: Structural nodes (Document → Chapter → Article → Clause)
- **Layer 2**: Semantic nodes (Entities, Processes, Rules, Concepts)

Mục tiêu: Hỗ trợ GraphRAG trả lời chính xác với citation đến Điều/Khoản cụ thể.

---

## 🏗️ LAYER 1: Structural Nodes

### 1.1. Node Types

#### `DOCUMENT`
Đại diện cho văn bản quy chế chính

**Properties**:
```python
{
    "ma_van_ban": "790/QD-DHCNTT",           # Primary key
    "ten_van_ban": "Quy chế đào tạo...",
    "ngay_ban_hanh": "2022-09-28",
    "co_quan_ban_hanh": "Trường ĐH CNTT",
    "hieu_luc": "active",                     # active | superseded | draft
    "file_path": "data/quy_dinh/790-qd..."
}
```

#### `CHAPTER` (Chương)
Mỗi chương trong quy chế

**Properties**:
```python
{
    "ma_chuong": "QD790_CH01",               # Primary key
    "so_chuong": 1,                          # Chương 1
    "tieu_de": "QUY ĐỊNH CHUNG",
    "ma_van_ban": "790/QD-DHCNTT",
    "mo_ta": "Các quy định chung về..."      # Optional
}
```

#### `ARTICLE` (Điều)
Mỗi điều trong quy chế

**Properties**:
```python
{
    "ma_dieu": "QD790_ART14",                # Primary key
    "so_dieu": 14,                           # Điều 14
    "tieu_de": "Đăng ký học phần",
    "tieu_de_ngan": "ĐKHP",                  # Abbreviation
    "ma_chuong": "QD790_CH02",
    "full_text": "...",                      # Full article text
    "tom_tat": "..."                         # AI-generated summary
}
```

#### `CLAUSE` (Khoản)
Mỗi khoản trong một điều

**Properties**:
```python
{
    "ma_khoan": "QD790_ART14_CL01",          # Primary key
    "so_khoan": 1,                           # Khoản 1
    "ma_dieu": "QD790_ART14",
    "raw_text": "Trong học kỳ chính...",
    "normalized_text": "...",                # Cleaned text
    "has_conditions": true,                  # Flag if contains rules
    "condition_count": 2
}
```

#### `ITEM` (Optional - Gạch đầu dòng)
Items trong clause nếu cần detail cao

**Properties**:
```python
{
    "ma_item": "QD790_ART14_CL01_IT01",
    "ma_khoan": "QD790_ART14_CL01",
    "thu_tu": 1,                             # Order
    "noi_dung": "Đăng ký tối thiểu 14 TC"
}
```

---

### 1.2. Structural Relationships

```cypher
// Hierarchical structure
(Document)-[:HAS_CHAPTER]->(Chapter)
(Chapter)-[:HAS_ARTICLE]->(Article)
(Article)-[:HAS_CLAUSE]->(Clause)
(Clause)-[:HAS_ITEM]->(Item)

// Sequential navigation
(Article)-[:NEXT_ARTICLE]->(Article)
(Clause)-[:NEXT_CLAUSE]->(Clause)

// Cross-references
(Article)-[:REFERS_TO]->(Article)
(Clause)-[:CITES]->(Clause)
```

**Example**:
```cypher
// Điều 14 thuộc Chương 2
(doc:DOCUMENT {ma_van_ban: "790/QD-DHCNTT"})
  -[:HAS_CHAPTER]->
(ch2:CHAPTER {so_chuong: 2})
  -[:HAS_ARTICLE]->
(art14:ARTICLE {so_dieu: 14, tieu_de: "Đăng ký học phần"})
  -[:HAS_CLAUSE]->
(cl1:CLAUSE {so_khoan: 1})
```

---

## 🧠 LAYER 2: Semantic Nodes

### 2.1. Entity Nodes (Thực thể)

#### `STUDENT` (Sinh viên)
**Properties**: `ma_sv`, `ten`, `khoa`, `nganh`, `trang_thai`

#### `PROGRAM` (Chương trình đào tạo)
**Properties**: `ma_chuong_trinh`, `ten`, `bac_dao_tao`, `he_dao_tao`, `tin_chi_tot_nghiep`

#### `COURSE` (Học phần / Môn học)
**Properties**: `ma_mon`, `ten_mon`, `so_tin_chi`, `loai_mon`

#### `SEMESTER` (Học kỳ)
**Properties**: `ma_hoc_ky`, `ten`, `loai` (chính/hè), `nam_hoc`

#### `ACADEMIC_YEAR` (Năm học)
**Properties**: `nam_hoc`, `ngay_bat_dau`, `ngay_ket_thuc`

#### `COHORT` (Khóa học)
**Properties**: `ma_khoa`, `ten_khoa`, `nam_nhap_hoc`

#### `ADVISOR` (Cố vấn học tập)
**Properties**: `ma_giang_vien`, `ten`, `khoa`

#### `DEPARTMENT` (Khoa)
**Properties**: `ma_khoa`, `ten_khoa`

#### `TRAINING_FORM` (Hệ đào tạo)
**Properties**: `ma_he`, `ten_he` (Chính quy, VB1, VB2, Liên thông...)

---

### 2.2. Process Nodes (Quy trình)

Các process chính từ quy chế:

#### Academic Registration Processes
- `REGISTRATION` - Đăng ký học phần (Điều 14)
- `RETAKE_COURSE` - Học lại
- `IMPROVE_GRADE` - Học cải thiện
- `SUMMER_STUDY` - Học kỳ hè

#### Academic Status Processes
- `ACADEMIC_WARNING` - Cảnh báo học vụ (Điều 16)
- `SUSPENSION` - Đình chỉ học tập
- `EXPULSION` - Buộc thôi học

#### Student Mobility Processes
- `STOP_STUDY` - Thôi học (Điều 11)
- `LEAVE_OF_ABSENCE` - Tạm dừng học tập (Điều 17)
- `PROGRAM_TRANSFER` - Chuyển ngành/chương trình (Điều 19)
- `SCHOOL_TRANSFER` - Chuyển trường
- `DUAL_PROGRAM` - Học 2 chương trình đồng thời (Điều 18)

#### Graduation Processes
- `GRADUATION_REVIEW` - Xét tốt nghiệp (Điều 33)
- `DIPLOMA_ISSUE` - Cấp bằng tốt nghiệp (Điều 34)
- `DEGREE_CLASSIFICATION` - Xếp loại tốt nghiệp

**Process Properties**:
```python
{
    "ma_quy_trinh": "REG_MAIN_SEMESTER",
    "ten": "Đăng ký học kỳ chính",
    "mo_ta": "Quy trình đăng ký...",
    "dieu_lien_quan": ["QD790_ART14"],       # List of article IDs
    "doi_tuong": "STUDENT",                   # Who performs it
    "buoc_thuc_hien": ["step1", "step2"...]   # Process steps
}
```

---

### 2.3. Rule/Condition Nodes

Đây là **linh hồn của GraphRAG** - mỗi rule biểu diễn 1 điều kiện/ràng buộc cụ thể.

#### `RULE` Node

**Properties**:
```python
{
    "ma_rule": "RULE_MIN_MAX_CREDITS_MAIN",
    "ten": "Giới hạn tín chỉ học kỳ chính",
    "loai": "LIMIT",                         # LIMIT | PERMISSION | OBLIGATION | PROHIBITION
    "formula": "14 <= credits <= 24",        # Machine-readable
    "formula_extended": "if GPA >= 8.0: credits <= 30",
    "mo_ta": "SV đăng ký 14-24 TC/kỳ chính, tối đa 30 TC nếu ĐTBC ≥ 8.0",
    "source_article": "QD790_ART14",
    "source_clause": "QD790_ART14_CL01",
    "priority": 1,                           # For conflict resolution
    "active": true
}
```

**Rule Types**:
- `LIMIT` - Giới hạn (tín chỉ, điểm số)
- `PERMISSION` - Được phép làm gì
- `OBLIGATION` - Bắt buộc phải làm
- `PROHIBITION` - Cấm làm
- `CONDITION` - Điều kiện (if-then)

#### Example Rules

**Rule 1**: Min/Max Credits - Main Semester
```python
{
    "ma_rule": "RULE_MIN_MAX_CREDITS_MAIN",
    "loai": "LIMIT",
    "formula": "14 <= credits <= 24 OR (GPA >= 8.0 AND credits <= 30)",
    "source_article": "QD790_ART14",
    "source_clause": "QD790_ART14_CL01a"
}
```

**Rule 2**: Max Credits - Summer Semester
```python
{
    "ma_rule": "RULE_MAX_CREDITS_SUMMER",
    "loai": "LIMIT",
    "formula": "credits <= 12",
    "mo_ta": "Học kỳ hè tối đa 12 TC, chỉ học lại/cải thiện + NN",
    "source_article": "QD790_ART14",
    "source_clause": "QD790_ART14_CL01b"
}
```

**Rule 3**: Academic Warning Trigger
```python
{
    "ma_rule": "RULE_ACADEMIC_WARNING",
    "loai": "CONDITION",
    "formula": "GPA_semester < 3.0 OR (GPA_consecutive_2sem < 4.0)",
    "mo_ta": "Cảnh báo khi ĐTBHK < 3.0 hoặc 2 kỳ liên tiếp < 4.0",
    "source_article": "QD790_ART16",
    "triggers_process": "ACADEMIC_WARNING"
}
```

**Rule 4**: Expulsion Conditions
```python
{
    "ma_rule": "RULE_EXPULSION",
    "loai": "CONDITION",
    "formula": "GPA_consecutive_2sem == 0 OR max_years_exceeded OR repeated_warnings >= 3",
    "mo_ta": "Buộc thôi học khi: ĐTBHK 2 kỳ = 0, hết thời gian tối đa, hoặc cảnh báo nhiều lần",
    "source_article": "QD790_ART16",
    "triggers_process": "EXPULSION"
}
```

**Rule 5**: Leave of Absence Eligibility
```python
{
    "ma_rule": "RULE_LEAVE_REASON_MILITARY",
    "loai": "PERMISSION",
    "formula": "reason == 'military_duty'",
    "mo_ta": "Được tạm dừng khi: điều động lực lượng vũ trang",
    "source_article": "QD790_ART17",
    "allows_process": "LEAVE_OF_ABSENCE"
}
```

**Rule 6**: Dual Program Eligibility
```python
{
    "ma_rule": "RULE_DUAL_PROGRAM_ELIGIBILITY",
    "loai": "CONDITION",
    "formula": "completed_year >= 1 AND cumulative_GPA >= threshold_program2",
    "mo_ta": "Điều kiện học 2 chương trình: đã xong năm 1, ĐTBCTL đạt ngưỡng ngành 2",
    "source_article": "QD790_ART18",
    "allows_process": "DUAL_PROGRAM"
}
```

**Rule 7**: Program Transfer Eligibility
```python
{
    "ma_rule": "RULE_PROGRAM_TRANSFER_GPA",
    "loai": "CONDITION",
    "formula": "cumulative_GPA >= 6.0 AND completed_credits >= min_credits AND no_discipline",
    "mo_ta": "Chuyển ngành: ĐTBC ≥ 6.0, đủ TC, không bị kỷ luật",
    "source_article": "QD790_ART19"
}
```

---

### 2.4. Concept Nodes (Simplified version)

Nếu muốn đơn giản hơn, dùng **Concept** để nhóm các Article theo chủ đề:

#### `CONCEPT` Node

**Properties**:
```python
{
    "ma_concept": "CONCEPT_REGISTRATION",
    "ten": "Đăng ký học tập",
    "ten_en": "Course Registration",
    "mo_ta": "Các quy định về đăng ký học phần, học lại, cải thiện, học hè",
    "article_ids": ["QD790_ART14", "QD790_ART15"],
    "keywords": ["đăng ký", "học phần", "tín chỉ", "học lại"]
}
```

**Main Concepts**:
1. `CONCEPT_CREDITS_FEES` - Tín chỉ & Học phí (Điều 3-9)
2. `CONCEPT_REGISTRATION` - Đăng ký học tập (Điều 14-15)
3. `CONCEPT_ACADEMIC_STATUS` - Xử lý học vụ (Điều 16)
4. `CONCEPT_LEAVE_STOP` - Thôi học, tạm dừng (Điều 11, 17)
5. `CONCEPT_TRANSFER` - Chuyển ngành, chuyển trường (Điều 18-19)
6. `CONCEPT_ASSESSMENT` - Kiểm tra, thi, điểm (Điều 20-27)
7. `CONCEPT_GRADUATION` - Điều kiện tốt nghiệp (Điều 31-34)
8. `CONCEPT_INTERNSHIP` - Thực tập, khóa luận

---

## 🔗 LAYER 2: Semantic Relationships

### 3.1. Rule ↔ Article/Clause

```cypher
// Rule source tracking
(Rule)-[:DEFINED_IN]->(Clause)
(Clause)-[:HAS_RULE]->(Rule)
(Rule)-[:EXTRACTED_FROM]->(Article)

// Example:
(rule:RULE {ma_rule: "RULE_MIN_MAX_CREDITS_MAIN"})
  -[:DEFINED_IN]->
(clause:CLAUSE {ma_khoan: "QD790_ART14_CL01"})
  -[:BELONGS_TO]->
(article:ARTICLE {so_dieu: 14})
```

### 3.2. Rule ↔ Process/Entity

```cypher
// Rule application
(Rule)-[:APPLIES_TO]->(Student | Program | Process)
(Rule)-[:TRIGGERS]->(Process)  // When condition met
(Rule)-[:GRANTS]->(Permission)
(Rule)-[:RESTRICTS]->(Action)

// Examples:
(rule:RULE {ma_rule: "RULE_MIN_MAX_CREDITS_MAIN"})
  -[:APPLIES_TO]->
(proc:REGISTRATION)

(rule:RULE {ma_rule: "RULE_ACADEMIC_WARNING"})
  -[:TRIGGERS]->
(proc:ACADEMIC_WARNING)

(rule:RULE {ma_rule: "RULE_DUAL_PROGRAM_ELIGIBILITY"})
  -[:GRANTS]->
(perm:PERMISSION {type: "dual_program"})
```

### 3.3. Actor ↔ Process

```cypher
// Student actions
(Student)-[:PERFORMS]->(Registration | RetakeCourse | LeaveOfAbsence)
(Student)-[:ENROLLED_IN]->(Program)
(Student)-[:MEMBER_OF]->(Cohort)
(Student)-[:HAS_STATUS]->(Status {value: "Normal|Warning|Suspended"})
(Student)-[:ADVISED_BY]->(Advisor)

// Program requirements
(Program)-[:HAS_REQUIREMENT]->(Rule)
(Program)-[:OFFERS]->(Course)
(Program)-[:BELONGS_TO]->(Department)

// Example:
(student:STUDENT {ma_sv: "20520001"})
  -[:PERFORMS]->
(reg:REGISTRATION {ma_hoc_ky: "HK1_2024"})
  -[:SUBJECT_TO]->
(rule:RULE {ma_rule: "RULE_MIN_MAX_CREDITS_MAIN"})
```

### 3.4. Concept Relationships (Simplified)

```cypher
(Article)-[:ABOUT]->(Concept)
(Concept)-[:RELATED_TO]->(Concept)
(Article)-[:REFERS_TO]->(Article)

// Example:
(art14:ARTICLE {so_dieu: 14})
  -[:ABOUT]->
(concept:CONCEPT {ma_concept: "CONCEPT_REGISTRATION"})
  -[:RELATED_TO]->
(concept2:CONCEPT {ma_concept: "CONCEPT_ACADEMIC_STATUS"})
```

---

## 🎯 Use Cases for GraphRAG

### Use Case 1: "Điều kiện bị cảnh báo học vụ?"

**Query flow**:
```cypher
// 1. Find warning rules
MATCH (rule:RULE)-[:TRIGGERS]->(proc:ACADEMIC_WARNING)
WHERE rule.loai = 'CONDITION'

// 2. Get source article
MATCH (rule)-[:DEFINED_IN]->(clause)-[:BELONGS_TO]->(article)

// 3. Return answer with citation
RETURN 
  rule.mo_ta as condition,
  article.so_dieu as dieu,
  clause.raw_text as citation
```

**Answer**:
> Theo **Điều 16**, sinh viên bị cảnh báo học vụ khi:
> - ĐTBHK < 3.0, HOẶC
> - ĐTBHK 2 học kỳ liên tiếp < 4.0
> 
> (Trích: Khoản 1, Điều 16)

---

### Use Case 2: "Tôi có thể đăng ký tối đa bao nhiêu tín chỉ?"

**Query flow**:
```cypher
MATCH (rule:RULE)-[:APPLIES_TO]->(proc:REGISTRATION)
WHERE rule.loai = 'LIMIT' 
  AND rule.ten CONTAINS 'tín chỉ'
  
MATCH (rule)-[:DEFINED_IN]->(clause)-[:BELONGS_TO]->(article)

RETURN 
  rule.formula,
  rule.mo_ta,
  article.so_dieu,
  clause.so_khoan
```

**Answer**:
> Theo **Điều 14, Khoản 1**:
> - Học kỳ chính: 14-24 tín chỉ (tối đa 30 TC nếu ĐTBC ≥ 8.0)
> - Học kỳ hè: tối đa 12 tín chỉ

---

### Use Case 3: "Thủ tục chuyển ngành như thế nào?"

**Query flow**:
```cypher
// Find process
MATCH (proc:PROGRAM_TRANSFER)

// Get all rules
MATCH (rule:RULE)-[:APPLIES_TO]->(proc)

// Get procedure steps
MATCH (proc)-[:HAS_STEP]->(step)

// Get source articles
MATCH (rule)-[:DEFINED_IN]->(clause)-[:BELONGS_TO]->(article)

RETURN article, clause, rule, step
ORDER BY step.thu_tu
```

**Answer with structure**:
> ### Chuyển ngành (Điều 19)
> 
> **Điều kiện**:
> - ĐTBC ≥ 6.0
> - Đã hoàn thành đủ số tín chỉ quy định
> - Không bị kỷ luật
> 
> **Thủ tục**:
> 1. Nộp đơn xin chuyển ngành
> 2. Phỏng vấn/thi tuyển (nếu có)
> 3. ...
> 
> (Theo Điều 19, Quy chế 790/QD-ĐHCNTT)

---

## 📋 Implementation Priority

### Phase 1: Structure + Simple Concepts (CURRENT)
✅ DOCUMENT, CHAPTER, ARTICLE, CLAUSE  
✅ Hierarchical relationships  
⬜ CONCEPT nodes (6-8 concepts)  
⬜ (Article)-[:ABOUT]->(Concept)

### Phase 2: Rules Extraction
⬜ Extract RULE nodes from clauses  
⬜ (Rule)-[:DEFINED_IN]->(Clause)  
⬜ (Rule)-[:APPLIES_TO]->(Process/Entity)  
⬜ Parse formula fields

### Phase 3: Process & Entity Nodes
⬜ REGISTRATION, ACADEMIC_WARNING, etc.  
⬜ STUDENT, PROGRAM, COURSE (basic)  
⬜ (Student)-[:PERFORMS]->(Process)  
⬜ (Rule)-[:TRIGGERS]->(Process)

### Phase 4: Advanced Features
⬜ Cross-references: (Article)-[:REFERS_TO]->(Article)  
⬜ Rule conflict detection  
⬜ Temporal rules (effective dates)  
⬜ Multi-document support

---

## 🛠️ Next Steps

1. **Update extraction script** to create CLAUSE nodes
2. **Build CONCEPT taxonomy** (6-8 main concepts)
3. **Create rule extraction pipeline** using LLM
4. **Implement GraphRAG queries** for top 10 use cases

Bạn muốn tôi bắt đầu implement từ phase nào?
