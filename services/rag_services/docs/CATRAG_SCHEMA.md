# CatRAG Schema Design - Week 1 Task A2

**Created:** November 14, 2025  
**Owner:** Data Architect + Senior Developer  
**Status:** ✅ Complete

---

## Overview

This document defines the **Category-Labeled Schema** for CatRAG (Category-guided Graph RAG) - **Principle #1** of the CatRAG approach.

The schema is designed top-down to align with UIT's academic domain, focusing on courses, prerequisites, regulations, and academic programs.

---

## Node Categories (10 Types)

### 1. MON_HOC (Course)
**Purpose:** Represents individual courses  
**Properties:**
- `ma_mon` (string, UNIQUE): Course code (e.g., "IT001", "SE104")
- `ten_mon` (string): Course name in Vietnamese
- `ten_mon_en` (string, optional): Course name in English
- `so_tin_chi` (integer): Number of credits
- `khoa` (string): Department code
- `hoc_ky` (integer, optional): Recommended semester
- `mo_ta` (text): Course description
- `noi_dung` (text, optional): Detailed syllabus content
- `created_at` (datetime): Timestamp
- `updated_at` (datetime): Timestamp

**Example:**
```cypher
(:MON_HOC {
  ma_mon: "IT003",
  ten_mon: "Cấu trúc dữ liệu và giải thuật",
  ten_mon_en: "Data Structures and Algorithms",
  so_tin_chi: 4,
  khoa: "CNTT",
  hoc_ky: 3,
  mo_ta: "Học về các cấu trúc dữ liệu cơ bản và giải thuật",
  created_at: datetime(),
  updated_at: datetime()
})
```

---

### 2. CHUONG_TRINH_DAO_TAO (Academic Program)
**Purpose:** Represents degree programs (Bachelor, Master, etc.)  
**Properties:**
- `ma_chuong_trinh` (string, UNIQUE): Program code
- `ten_chuong_trinh` (string): Program name
- `khoa` (string): Department code
- `bac_dao_tao` (string): Degree level (Cử nhân, Thạc sĩ, etc.)
- `nam_bat_dau` (integer): Year started
- `tong_tin_chi` (integer): Total credits required
- `mo_ta` (text): Program description
- `created_at` (datetime)
- `updated_at` (datetime)

**Example:**
```cypher
(:CHUONG_TRINH_DAO_TAO {
  ma_chuong_trinh: "CNTT2023",
  ten_chuong_trinh: "Công nghệ thông tin",
  khoa: "CNTT",
  bac_dao_tao: "Cử nhân",
  nam_bat_dau: 2023,
  tong_tin_chi: 140,
  mo_ta: "Chương trình đào tạo kỹ sư CNTT"
})
```

---

### 3. KHOA (Department/Faculty)
**Purpose:** Represents academic departments  
**Properties:**
- `ma_khoa` (string, UNIQUE): Department code
- `ten_khoa` (string): Department name
- `ten_khoa_en` (string, optional): English name
- `website` (string, optional): Department website
- `email` (string, optional): Contact email
- `phone` (string, optional): Contact phone
- `truong_khoa` (string, optional): Dean name
- `created_at` (datetime)
- `updated_at` (datetime)

**Example:**
```cypher
(:KHOA {
  ma_khoa: "CNTT",
  ten_khoa: "Khoa Công nghệ thông tin",
  ten_khoa_en: "Faculty of Information Technology",
  website: "https://fit.uit.edu.vn",
  email: "fit@uit.edu.vn"
})
```

---

### 4. GIANG_VIEN (Lecturer)
**Purpose:** Represents teaching staff  
**Properties:**
- `ma_gv` (string, UNIQUE): Lecturer ID
- `ten_gv` (string): Full name
- `khoa` (string): Department code
- `email` (string, optional): Email address
- `chuyen_nganh` (string, optional): Specialization
- `hoc_vi` (string, optional): Academic degree (TS, PGS, GS)
- `created_at` (datetime)
- `updated_at` (datetime)

**Example:**
```cypher
(:GIANG_VIEN {
  ma_gv: "GV001",
  ten_gv: "Nguyễn Văn A",
  khoa: "CNTT",
  email: "nva@uit.edu.vn",
  hoc_vi: "Tiến sĩ"
})
```

---

### 5. DIEU_KIEN (Requirement/Condition)
**Purpose:** Represents conditions and requirements  
**Properties:**
- `loai` (string): Type (tien_quyet, song_hanh, diem_toi_thieu, etc.)
- `mo_ta` (string): Description
- `gia_tri` (string, optional): Value (e.g., "5.0" for minimum grade)
- `logic` (string, optional): Logic operator (AND, OR)
- `created_at` (datetime)

**Example:**
```cypher
(:DIEU_KIEN {
  loai: "tien_quyet",
  mo_ta: "Hoàn thành IT001 và IT002 với điểm >= 5.0",
  gia_tri: "5.0",
  logic: "AND"
})
```

---

### 6. QUY_DINH (Regulation)
**Purpose:** Represents university regulations and policies  
**Properties:**
- `ma_quy_dinh` (string, UNIQUE): Regulation code
- `tieu_de` (string): Title
- `noi_dung` (text): Full content
- `loai` (string): Type (dao_tao, thi_cu, hoc_phi, etc.)
- `nam_ap_dung` (integer): Year of application
- `trang_thai` (string): Status (hieu_luc, het_hieu_luc)
- `created_at` (datetime)
- `updated_at` (datetime)

**Example:**
```cypher
(:QUY_DINH {
  ma_quy_dinh: "QD123/2023",
  tieu_de: "Quy định về điều kiện tốt nghiệp",
  noi_dung: "Sinh viên phải hoàn thành tối thiểu 140 tín chỉ...",
  loai: "dao_tao",
  nam_ap_dung: 2023,
  trang_thai: "hieu_luc"
})
```

---

### 7. HOC_KY (Semester)
**Purpose:** Represents academic semesters  
**Properties:**
- `ma_hk` (string, UNIQUE): Semester code (e.g., "HK1_2023")
- `ten_hk` (string): Semester name (Học kỳ 1, Học kỳ 2)
- `nam_hoc` (string): Academic year (2023-2024)
- `ngay_bat_dau` (date): Start date
- `ngay_ket_thuc` (date): End date
- `created_at` (datetime)

**Example:**
```cypher
(:HOC_KY {
  ma_hk: "HK1_2023",
  ten_hk: "Học kỳ 1",
  nam_hoc: "2023-2024",
  ngay_bat_dau: date("2023-09-01"),
  ngay_ket_thuc: date("2024-01-15")
})
```

---

### 8. CATEGORY (Metadata Category)
**Purpose:** Category labels for classification  
**Properties:**
- `name` (string, UNIQUE): Category name
- `description` (string): Description
- `parent_category` (string, optional): Parent category
- `created_at` (datetime)

**Example:**
```cypher
(:CATEGORY {
  name: "CO_SO",
  description: "Môn học cơ sở",
  parent_category: "MON_HOC"
})
```

---

### 9. TAG (Tag/Label)
**Purpose:** Flexible tagging system  
**Properties:**
- `name` (string): Tag name
- `type` (string): Tag type (skill, topic, difficulty, etc.)
- `created_at` (datetime)

**Example:**
```cypher
(:TAG {
  name: "lap_trinh",
  type: "skill"
})
```

---

### 10. ENTITY_MENTION (Entity Reference)
**Purpose:** Links to original documents where entities are mentioned  
**Properties:**
- `text` (string): Original text snippet
- `source_doc` (string): Source document ID
- `confidence` (float): Extraction confidence (0.0-1.0)
- `start_pos` (integer, optional): Start position in document
- `end_pos` (integer, optional): End position in document
- `created_at` (datetime)

**Example:**
```cypher
(:ENTITY_MENTION {
  text: "Môn IT003 cần học IT002 trước",
  source_doc: "doc_123",
  confidence: 0.95,
  start_pos: 150,
  end_pos: 180
})
```

---

## Relationship Types (12 Types)

### Critical Relationships (For Graph Traversal)

#### 1. DIEU_KIEN_TIEN_QUYET (Prerequisite)
**Direction:** `(MON_HOC)-[:DIEU_KIEN_TIEN_QUYET]->(MON_HOC)`  
**Purpose:** Define prerequisite requirements  
**Properties:**
- `loai` (string): Type (bat_buoc, khuyen_nghi)
- `diem_toi_thieu` (float, optional): Minimum grade required
- `ghi_chu` (string, optional): Notes
- `created_at` (datetime)

**Example:**
```cypher
(IT003)-[:DIEU_KIEN_TIEN_QUYET {
  loai: "bat_buoc",
  diem_toi_thieu: 5.0,
  ghi_chu: "Phải hoàn thành trước khi đăng ký IT003"
}]->(IT002)
```

---

#### 2. DIEU_KIEN_SONG_HANH (Co-requisite)
**Direction:** `(MON_HOC)-[:DIEU_KIEN_SONG_HANH]->(MON_HOC)`  
**Purpose:** Courses that must be taken together  
**Properties:**
- `ghi_chu` (string, optional)
- `created_at` (datetime)

**Example:**
```cypher
(IT005)-[:DIEU_KIEN_SONG_HANH]->(IT006)
```

---

### Hierarchical Relationships

#### 3. THUOC_CHUONG_TRINH (Belongs to Program)
**Direction:** `(MON_HOC)-[:THUOC_CHUONG_TRINH]->(CHUONG_TRINH_DAO_TAO)`  
**Purpose:** Course belongs to academic program  
**Properties:**
- `loai_mon` (string): Type (bat_buoc, tu_chon, tu_chon_tu_do)
- `hoc_ky_khuyen_nghi` (integer, optional): Recommended semester
- `created_at` (datetime)

---

#### 4. THUOC_KHOA (Belongs to Department)
**Direction:** `(MON_HOC)-[:THUOC_KHOA]->(KHOA)`  
**Purpose:** Course belongs to department  
**Properties:**
- `created_at` (datetime)

---

#### 5. QUAN_LY (Manages)
**Direction:** `(KHOA)-[:QUAN_LY]->(CHUONG_TRINH_DAO_TAO)`  
**Purpose:** Department manages program  
**Properties:**
- `created_at` (datetime)

---

### Teaching Relationships

#### 6. DUOC_DAY_BOI (Taught by)
**Direction:** `(MON_HOC)-[:DUOC_DAY_BOI]->(GIANG_VIEN)`  
**Purpose:** Course taught by lecturer  
**Properties:**
- `hoc_ky` (string, optional): Semester
- `vai_tro` (string): Role (giang_vien_chinh, tro_giang)
- `created_at` (datetime)

---

### Content Relationships

#### 7. MO_TA_BOI (Described by)
**Direction:** `(MON_HOC)-[:MO_TA_BOI]->(ENTITY_MENTION)`  
**Purpose:** Link to original text mentions  
**Properties:**
- `relevance_score` (float): Relevance score
- `created_at` (datetime)

---

#### 8. AP_DUNG_QUY_DINH (Applies Regulation)
**Direction:** `(CHUONG_TRINH_DAO_TAO)-[:AP_DUNG_QUY_DINH]->(QUY_DINH)`  
**Purpose:** Program applies regulation  
**Properties:**
- `bat_dau` (date, optional): Start date
- `ket_thuc` (date, optional): End date
- `created_at` (datetime)

---

### Semantic Relationships

#### 9. LIEN_QUAN (Related to)
**Direction:** `(MON_HOC)-[:LIEN_QUAN]->(MON_HOC)`  
**Purpose:** Semantically related courses  
**Properties:**
- `do_tuong_tu` (float): Similarity score (0.0-1.0)
- `ly_do` (string, optional): Reason for relation
- `created_at` (datetime)

---

#### 10. TAGGED_AS (Tagged as)
**Direction:** `(MON_HOC)-[:TAGGED_AS]->(TAG)`  
**Purpose:** Course tagged with label  
**Properties:**
- `created_at` (datetime)

---

#### 11. THUOC_DANH_MUC (Belongs to Category)
**Direction:** `(MON_HOC)-[:THUOC_DANH_MUC]->(CATEGORY)`  
**Purpose:** Course belongs to category  
**Properties:**
- `created_at` (datetime)

---

#### 12. MO_TA_DIEU_KIEN (Describes Condition)
**Direction:** `(MON_HOC)-[:MO_TA_DIEU_KIEN]->(DIEU_KIEN)`  
**Purpose:** Course has specific conditions  
**Properties:**
- `created_at` (datetime)

---

## CatRAG Routing Annotations

Each relationship type has routing implications for the Router Agent (Week 3):

| Relationship | Primary Retrieval | Secondary | Rerank |
|--------------|------------------|-----------|--------|
| DIEU_KIEN_TIEN_QUYET | Graph Traversal | None | No |
| DIEU_KIEN_SONG_HANH | Graph Traversal | None | No |
| THUOC_CHUONG_TRINH | Graph Traversal | Vector | Yes |
| LIEN_QUAN | Vector Search | Graph | Yes |
| MO_TA_BOI | Vector Search | None | Yes |
| AP_DUNG_QUY_DINH | Hybrid Search | None | Yes |

---

## Schema Constraints & Indexes

See `/services/rag_services/scripts/cypher/01_create_constraints.cypher` for implementation.

**Key Constraints:**
- Unique IDs for all core entities (ma_mon, ma_khoa, ma_chuong_trinh)
- Unique node keys for proper deduplication

**Key Indexes:**
- Search indexes on names (ten_mon, ten_khoa)
- Composite indexes for filtering (ma_mon + khoa)
- Full-text indexes for content search

---

## Example Graph Patterns

### Pattern 1: Prerequisite Chain
```cypher
// Find full prerequisite chain for IT005
MATCH path = (target:MON_HOC {ma_mon: 'IT005'})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq:MON_HOC)
RETURN path
ORDER BY length(path) DESC
```

### Pattern 2: Department Courses
```cypher
// Find all courses in CNTT department
MATCH (course:MON_HOC)-[:THUOC_KHOA]->(dept:KHOA {ma_khoa: 'CNTT'})
RETURN course.ma_mon, course.ten_mon
ORDER BY course.ma_mon
```

### Pattern 3: Program Requirements
```cypher
// Find all required courses for a program
MATCH (course:MON_HOC)-[r:THUOC_CHUONG_TRINH {loai_mon: 'bat_buoc'}]->(program:CHUONG_TRINH_DAO_TAO {ma_chuong_trinh: 'CNTT2023'})
RETURN course.ma_mon, course.ten_mon, r.hoc_ky_khuyen_nghi
ORDER BY r.hoc_ky_khuyen_nghi
```

---

## Schema Validation Checklist

- [x] All 10 node categories defined
- [x] All 12 relationship types defined  
- [x] Properties specified for each node type
- [x] Unique constraints identified
- [x] Index requirements documented
- [x] Routing annotations added
- [x] Example queries provided

---

## Next Steps

1. ✅ Task A3: Implement Cypher scripts for this schema
2. ✅ Task A3: Create sample data based on UIT courses
3. ✅ Week 2: Populate graph with real data using LLM extraction

---

**Schema Status:** ✅ Approved and ready for implementation  
**Reviewed by:** Data Architect  
**Last Updated:** November 14, 2025
