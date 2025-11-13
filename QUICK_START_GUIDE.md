# Quick Start Guide - Week 1

## 🚀 Quick Start cho Team A (Infrastructure)

### **Mục tiêu Week 1**
- Setup Neo4j infrastructure
- Design CatRAG category schema
- Implement basic Graph Adapter

---

### **Day 1-2: Neo4j Setup**

#### **Prerequisites**
```bash
# Check installations
docker --version    # >= 20.x
docker-compose --version  # >= 2.x
python --version    # 3.11+

# Activate environment
conda activate chatbot-UIT
```

#### **Step 1: Create Neo4j Docker Configuration**

```bash
cd /home/kien/Kien/study/SE363.Q11/Chatbot-UIT/services/rag_services

# Create docker compose file
cat > docker/docker-compose.neo4j.yml << 'EOF'
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: neo4j-graphrag
    ports:
      - "7474:7474"  # HTTP (Browser)
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/uitchatbot
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=512m
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p uitchatbot 'RETURN 1'"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:
EOF
```

#### **Step 2: Start Neo4j**

```bash
# Start container
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Check logs
docker logs neo4j-graphrag

# Wait for Neo4j to start (30-60 seconds)
# You should see: "Started"
```

#### **Step 3: Verify Installation**

```bash
# Install Python driver
pip install neo4j==5.15.0

# Test connection
cat > scripts/test_neo4j_connection.py << 'EOF'
from neo4j import GraphDatabase
import sys

def test_connection():
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "uitchatbot"))
    
    try:
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as num")
            record = result.single()
            print(f"✓ Connection successful! Result: {record['num']}")
        
        # Test APOC
        with driver.session() as session:
            result = session.run("RETURN apoc.version() as version")
            record = result.single()
            print(f"✓ APOC available! Version: {record['version']}")
        
        # Test GDS
        with driver.session() as session:
            result = session.run("RETURN gds.version() as version")
            record = result.single()
            print(f"✓ GDS available! Version: {record['version']}")
        
        print("\n✅ All tests passed! Neo4j is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        driver.close()

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
EOF

python scripts/test_neo4j_connection.py
```

#### **Step 4: Access Neo4j Browser**

1. Open browser: http://localhost:7474
2. Login credentials:
   - Username: `neo4j`
   - Password: `uitchatbot`
3. Test query: `RETURN "Hello GraphRAG!" as message`

---

### **Day 3-5: CatRAG Schema Design**

#### **Step 1: Create Schema Configuration**

```bash
# Create config file
mkdir -p config
cat > config/graph_schema_catrag.yaml << 'EOF'
# CatRAG Category Schema for UIT Domain
# Based on: Category-guided Graph RAG approach

categories:
  # Academic Categories
  MON_HOC:
    label: "MonHoc"
    description: "Môn học / Course"
    properties:
      - name: code
        type: string
        required: true
        unique: true
        examples: ["IT001", "IT003", "CS101"]
      - name: name
        type: string
        required: true
        examples: ["Nhập môn lập trình", "Cấu trúc dữ liệu"]
      - name: credits
        type: integer
        required: true
        examples: [3, 4, 2]
      - name: type
        type: string
        enum: ["bat_buoc", "tu_chon", "tu_chon_tu_do"]
      - name: description
        type: string
        required: false
    indexes:
      - fields: [code]
        type: unique
      - fields: [name]
        type: fulltext

  QUY_DINH:
    label: "QuyDinh"
    description: "Quy định / Regulation"
    properties:
      - name: id
        type: string
        required: true
        unique: true
      - name: title
        type: string
        required: true
      - name: year
        type: integer
        required: true
      - name: type
        type: string
        enum: ["tuyen_sinh", "tot_nghiep", "hoc_vu", "tai_chinh", "khac"]
      - name: content
        type: string
        required: false
      - name: effective_date
        type: date
        required: false
    indexes:
      - fields: [id]
        type: unique
      - fields: [title]
        type: fulltext

  DIEU_KIEN:
    label: "DieuKien"
    description: "Điều kiện / Requirement"
    properties:
      - name: id
        type: string
        required: true
      - name: type
        type: string
        enum: ["diem_so", "tin_chi", "mon_hoc", "thoi_gian", "khac"]
      - name: threshold
        type: float
        required: false
      - name: description
        type: string
        required: true
    indexes:
      - fields: [id]
        type: unique

  KHOA:
    label: "Khoa"
    description: "Khoa / Department"
    properties:
      - name: code
        type: string
        required: true
        unique: true
        examples: ["CNTT", "KHTN", "KHMT"]
      - name: name
        type: string
        required: true
      - name: dean
        type: string
        required: false
    indexes:
      - fields: [code]
        type: unique

  NGANH:
    label: "Nganh"
    description: "Ngành / Major"
    properties:
      - name: code
        type: string
        required: true
        unique: true
      - name: name
        type: string
        required: true
      - name: type
        type: string
        enum: ["dai_tra", "cao_dang", "lien_thong"]
    indexes:
      - fields: [code]
        type: unique

  CHUONG_TRINH_DAO_TAO:
    label: "ChuongTrinhDaoTao"
    description: "Chương trình đào tạo / Curriculum"
    properties:
      - name: id
        type: string
        required: true
      - name: name
        type: string
        required: true
      - name: year
        type: integer
        required: true
      - name: credits_required
        type: integer
        required: true
    indexes:
      - fields: [id]
        type: unique

  SINH_VIEN:
    label: "SinhVien"
    description: "Đối tượng sinh viên / Student Target Group"
    properties:
      - name: cohort
        type: string
        required: true
        examples: ["K2019", "K2020", "K2021"]
      - name: type
        type: string
        enum: ["chinh_quy", "lien_thong", "chat_luong_cao"]
    indexes:
      - fields: [cohort]
        type: unique

  KY_HOC:
    label: "KyHoc"
    description: "Kỳ học / Semester"
    properties:
      - name: code
        type: string
        required: true
        examples: ["HK1", "HK2", "HK3"]
      - name: year
        type: string
        required: true
      - name: start_date
        type: date
        required: false
      - name: end_date
        type: date
        required: false

relationships:
  # Hierarchical relationships
  THUOC_KHOA:
    from: NGANH
    to: KHOA
    description: "Ngành thuộc Khoa"
    properties: []

  CUA_NGANH:
    from: CHUONG_TRINH_DAO_TAO
    to: NGANH
    description: "Chương trình của Ngành"
    properties: []

  THUOC_CHUONG_TRINH:
    from: MON_HOC
    to: CHUONG_TRINH_DAO_TAO
    description: "Môn học thuộc Chương trình"
    properties:
      - name: is_required
        type: boolean
      - name: semester_recommended
        type: integer

  # Prerequisites (CRITICAL for CatRAG routing)
  DIEU_KIEN_TIEN_QUYET:
    from: MON_HOC
    to: MON_HOC
    description: "Môn A là điều kiện tiên quyết của môn B"
    properties:
      - name: type
        type: string
        enum: ["bat_buoc", "khuyen_nghi"]
      - name: can_study_parallel
        type: boolean
        default: false

  YEU_CAU_DIEU_KIEN:
    from: MON_HOC
    to: DIEU_KIEN
    description: "Môn học yêu cầu điều kiện"
    properties: []

  QUY_DINH_DIEU_KIEN:
    from: QUY_DINH
    to: DIEU_KIEN
    description: "Quy định yêu cầu điều kiện"
    properties: []

  # Applicability
  AP_DUNG_CHO:
    from: QUY_DINH
    to: [SINH_VIEN, NGANH, KHOA]
    description: "Quy định áp dụng cho đối tượng"
    properties:
      - name: effective_from
        type: date
      - name: effective_to
        type: date

  # Semantic relations
  LIEN_QUAN_NOI_DUNG:
    from: MON_HOC
    to: MON_HOC
    description: "Môn học có nội dung liên quan"
    properties:
      - name: similarity_score
        type: float
        range: [0.0, 1.0]

# Query Intent Categories (for Router Agent)
query_intents:
  TIEN_QUYET:
    description: "Hỏi về môn tiên quyết"
    keywords: ["tiên quyết", "học trước", "điều kiện học"]
    route_to: "graph_traversal"
    example_queries:
      - "Môn tiên quyết của IT003 là gì?"
      - "Tôi cần học gì trước khi học Cấu trúc dữ liệu?"

  MO_TA_MON_HOC:
    description: "Hỏi về mô tả, nội dung môn học"
    keywords: ["học về gì", "nội dung", "mô tả môn"]
    route_to: "vector_search"
    example_queries:
      - "IT001 học về gì?"
      - "Nội dung môn Nhập môn lập trình là gì?"

  DIEU_KIEN_TOT_NGHIEP:
    description: "Hỏi về điều kiện tốt nghiệp"
    keywords: ["tốt nghiệp", "điều kiện ra trường", "yêu cầu tốt nghiệp"]
    route_to: "graph_multi_hop"
    example_queries:
      - "Điều kiện tốt nghiệp ngành CNTT?"
      - "Tôi cần bao nhiêu tín chỉ để tốt nghiệp?"

  CHUONG_TRINH_DAO_TAO:
    description: "Hỏi về chương trình đào tạo"
    keywords: ["chương trình", "khung chương trình", "danh sách môn"]
    route_to: "graph_traversal"
    example_queries:
      - "Chương trình đào tạo CNTT gồm những môn nào?"
      - "Danh sách môn bắt buộc ngành KHMT?"

  QUY_DINH_HOC_VU:
    description: "Hỏi về quy định học vụ"
    keywords: ["quy định", "quy chế", "chính sách"]
    route_to: "hybrid_search"
    example_queries:
      - "Quy định về điểm danh là gì?"
      - "Chính sách miễn giảm học phí?"

  HOC_PHI:
    description: "Hỏi về học phí"
    keywords: ["học phí", "chi phí", "đóng tiền"]
    route_to: "hybrid_search"
    example_queries:
      - "Học phí ngành CNTT bao nhiêu?"
      - "Cách thức đóng học phí?"
EOF
```

#### **Step 2: Create Cypher Schema Script**

```bash
cat > scripts/init_catrag_schema.cypher << 'EOF'
// CatRAG Schema Initialization Script
// Run this in Neo4j Browser or via Python driver

// 1. Create constraints for unique identifiers
CREATE CONSTRAINT mon_hoc_code IF NOT EXISTS FOR (m:MonHoc) REQUIRE m.code IS UNIQUE;
CREATE CONSTRAINT quy_dinh_id IF NOT EXISTS FOR (q:QuyDinh) REQUIRE q.id IS UNIQUE;
CREATE CONSTRAINT dieu_kien_id IF NOT EXISTS FOR (d:DieuKien) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT khoa_code IF NOT EXISTS FOR (k:Khoa) REQUIRE k.code IS UNIQUE;
CREATE CONSTRAINT nganh_code IF NOT EXISTS FOR (n:Nganh) REQUIRE n.code IS UNIQUE;
CREATE CONSTRAINT chuong_trinh_id IF NOT EXISTS FOR (ct:ChuongTrinhDaoTao) REQUIRE ct.id IS UNIQUE;

// 2. Create indexes for performance
CREATE INDEX mon_hoc_name IF NOT EXISTS FOR (m:MonHoc) ON (m.name);
CREATE INDEX quy_dinh_title IF NOT EXISTS FOR (q:QuyDinh) ON (q.title);
CREATE INDEX quy_dinh_year IF NOT EXISTS FOR (q:QuyDinh) ON (q.year);

// 3. Create fulltext indexes for semantic search
CALL db.index.fulltext.createNodeIndex(
  'monHocFulltext',
  ['MonHoc'],
  ['name', 'description'],
  {eventually_consistent: 'true'}
);

CALL db.index.fulltext.createNodeIndex(
  'quyDinhFulltext',
  ['QuyDinh'],
  ['title', 'content'],
  {eventually_consistent: 'true'}
);

// 4. Create sample data (for testing)

// Sample Khoa
CREATE (cntt:Khoa {code: 'CNTT', name: 'Khoa Công nghệ thông tin', dean: 'PGS.TS Nguyễn Văn A'});
CREATE (khmt:Khoa {code: 'KHMT', name: 'Khoa Khoa học máy tính', dean: 'PGS.TS Trần Văn B'});

// Sample Nganh
CREATE (nganh_cntt:Nganh {code: 'CNTT_DT', name: 'Công nghệ thông tin', type: 'dai_tra'});
CREATE (nganh_cntt)-[:THUOC_KHOA]->(cntt);

// Sample Chuong Trinh
CREATE (ct_2024:ChuongTrinhDaoTao {
  id: 'CNTT_2024', 
  name: 'Chương trình đào tạo CNTT 2024', 
  year: 2024, 
  credits_required: 120
});
CREATE (ct_2024)-[:CUA_NGANH]->(nganh_cntt);

// Sample Mon Hoc
CREATE (it001:MonHoc {
  code: 'IT001', 
  name: 'Nhập môn lập trình', 
  credits: 4, 
  type: 'bat_buoc',
  description: 'Môn học cung cấp kiến thức cơ bản về lập trình C/C++'
});

CREATE (it002:MonHoc {
  code: 'IT002', 
  name: 'Lập trình hướng đối tượng', 
  credits: 4, 
  type: 'bat_buoc',
  description: 'Môn học về OOP với C++'
});

CREATE (it003:MonHoc {
  code: 'IT003', 
  name: 'Cấu trúc dữ liệu và giải thuật', 
  credits: 4, 
  type: 'bat_buoc',
  description: 'Môn học về CTDL và GT cơ bản'
});

// Prerequisites relationships
CREATE (it002)-[:DIEU_KIEN_TIEN_QUYET {type: 'bat_buoc', can_study_parallel: false}]->(it001);
CREATE (it003)-[:DIEU_KIEN_TIEN_QUYET {type: 'bat_buoc', can_study_parallel: false}]->(it002);

// Thuoc chuong trinh
CREATE (it001)-[:THUOC_CHUONG_TRINH {is_required: true, semester_recommended: 1}]->(ct_2024);
CREATE (it002)-[:THUOC_CHUONG_TRINH {is_required: true, semester_recommended: 2}]->(ct_2024);
CREATE (it003)-[:THUOC_CHUONG_TRINH {is_required: true, semester_recommended: 3}]->(ct_2024);

// Sample Dieu Kien
CREATE (dk_gpa:DieuKien {
  id: 'DK_GPA_TOT_NGHIEP',
  type: 'diem_so',
  threshold: 2.0,
  description: 'GPA tối thiểu để tốt nghiệp'
});

CREATE (dk_credits:DieuKien {
  id: 'DK_TIN_CHI_TOT_NGHIEP',
  type: 'tin_chi',
  threshold: 120.0,
  description: 'Số tín chỉ tối thiểu để tốt nghiệp'
});

// Sample Quy Dinh
CREATE (qd_tn:QuyDinh {
  id: 'QD_43_2024',
  title: 'Quy chế tốt nghiệp 2024',
  year: 2024,
  type: 'tot_nghiep',
  content: 'Quy định về điều kiện và thủ tục tốt nghiệp...'
});

CREATE (qd_tn)-[:QUY_DINH_DIEU_KIEN]->(dk_gpa);
CREATE (qd_tn)-[:QUY_DINH_DIEU_KIEN]->(dk_credits);

// Sample Sinh Vien target
CREATE (sv_k2024:SinhVien {cohort: 'K2024', type: 'chinh_quy'});
CREATE (qd_tn)-[:AP_DUNG_CHO]->(sv_k2024);

// Verification queries
MATCH (n) RETURN labels(n) as NodeType, count(n) as Count;
MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count;
EOF
```

#### **Step 3: Initialize Schema**

```bash
# Run via Python
cat > scripts/init_schema.py << 'EOF'
from neo4j import GraphDatabase

def init_schema():
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "uitchatbot"))
    
    # Read Cypher script
    with open('scripts/init_catrag_schema.cypher', 'r', encoding='utf-8') as f:
        cypher_script = f.read()
    
    # Execute each statement
    with driver.session() as session:
        for statement in cypher_script.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('//'):
                try:
                    session.run(statement)
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"⚠ Skipped: {e}")
    
    print("\n✅ Schema initialized!")
    driver.close()

if __name__ == "__main__":
    init_schema()
EOF

python scripts/init_schema.py
```

#### **Step 4: Verify Schema in Browser**

Open Neo4j Browser (http://localhost:7474) and run:

```cypher
// See all node types
MATCH (n) RETURN labels(n) as NodeType, count(n) as Count;

// See all relationship types  
MATCH ()-[r]->() RETURN type(r) as RelationType, count(r) as Count;

// Test prerequisite chain
MATCH path = (start:MonHoc {code: 'IT003'})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq:MonHoc)
RETURN start.name, 
       [node in nodes(path) | node.name] as prerequisite_chain;

// Visualize schema
CALL db.schema.visualization();
```

---

### **Day 5: Basic Graph Adapter POC**

See POC code section below.

---

## 🚀 Quick Start cho Team B (NLP/ML)

### **Mục tiêu Week 1**
- Research Vietnamese NER models
- Benchmark entity extraction
- Implement category-guided entity extractor

---

### **Day 1-2: NER Model Research**

#### **Step 1: Setup Vietnamese NLP Tools**

```bash
# Install dependencies
pip install underthesea vncorenlp transformers sentence-transformers

# Download PhoBERT
python -c "from transformers import AutoModel; AutoModel.from_pretrained('vinai/phobert-base')"

# Download VnCoreNLP (if using)
# Follow: https://github.com/vncorenlp/VnCoreNLP
```

#### **Step 2: Create Test Dataset**

```bash
mkdir -p tests/fixtures

cat > tests/fixtures/ner_test_data.json << 'EOF'
[
  {
    "text": "Môn IT001 - Nhập môn lập trình là môn cơ bản của ngành CNTT.",
    "entities": [
      {"text": "IT001", "type": "MON_HOC", "start": 4, "end": 9},
      {"text": "Nhập môn lập trình", "type": "MON_HOC", "start": 12, "end": 30},
      {"text": "CNTT", "type": "KHOA", "start": 55, "end": 59}
    ]
  },
  {
    "text": "Quy chế 43/2024 quy định sinh viên K2024 cần GPA tối thiểu 2.0 để tốt nghiệp.",
    "entities": [
      {"text": "Quy chế 43/2024", "type": "QUY_DINH", "start": 0, "end": 15},
      {"text": "K2024", "type": "SINH_VIEN", "start": 38, "end": 43},
      {"text": "GPA tối thiểu 2.0", "type": "DIEU_KIEN", "start": 49, "end": 66}
    ]
  }
]
EOF
```

#### **Step 3: Benchmark Script**

See POC code section below.

---

### **Day 3-5: Category-Guided Entity Extractor**

See POC code section below.

---

## 📚 Resources

### **For Team A**
- Neo4j Documentation: https://neo4j.com/docs/
- Cypher Manual: https://neo4j.com/docs/cypher-manual/
- APOC Documentation: https://neo4j.com/labs/apoc/
- GDS Documentation: https://neo4j.com/docs/graph-data-science/

### **For Team B**
- PhoBERT: https://github.com/VinAIResearch/PhoBERT
- VnCoreNLP: https://github.com/vncorenlp/VnCoreNLP
- Underthesea: https://github.com/undertheseanlp/underthesea
- Transformers: https://huggingface.co/docs/transformers

---

## 🆘 Troubleshooting

### **Neo4j Issues**

**Problem:** Container won't start
```bash
# Check logs
docker logs neo4j-graphrag

# Common fix: Remove old data
docker-compose -f docker/docker-compose.neo4j.yml down -v
docker-compose -f docker/docker-compose.neo4j.yml up -d
```

**Problem:** APOC/GDS not available
```bash
# Verify plugins
docker exec neo4j-graphrag ls /plugins

# Reinstall if needed
docker-compose -f docker/docker-compose.neo4j.yml down
docker-compose -f docker/docker-compose.neo4j.yml up -d
```

### **Python Connection Issues**

**Problem:** Can't connect from Python
```python
# Test with explicit error handling
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

try:
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "uitchatbot"))
    driver.verify_connectivity()
    print("✓ Connected!")
except ServiceUnavailable:
    print("❌ Neo4j not running or wrong credentials")
```

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Team:** GraphRAG Project
