# Week 1: Foundation & Environment Setup (CatRAG Schema Design)

**Duration:** Week 1 (Nov 13-19, 2025)  
**Phase:** Foundation  
**Objective:** Setup infrastructure, design CatRAG schema, create POC demonstrations

---

## 🎯 Week Goals

### Team A (Graph Infrastructure)
- ✅ Setup Neo4j database (Docker + Local)
- ✅ Design CatRAG category-labeled schema
- ✅ Create Cypher initialization scripts
- ✅ Implement basic GraphRepository POC
- ✅ Performance baseline testing

### Team B (NLP & Entity Extraction)
- ✅ NER model selection & benchmarking
- ✅ Implement category-guided entity extractor
- ✅ Create Vietnamese regex patterns
- ✅ Entity normalization logic
- ✅ Integration testing with sample data

### Integration Goal
- **Friday Demo:** Working POC showing graph traversal + entity extraction

---

## 📋 Detailed Tasks

### **Team A: Graph Infrastructure Tasks**

#### Task A1: Neo4j Environment Setup (Monday - 4h)
**Owner:** Senior Backend Developer  
**Priority:** P0 (Blocker)

**Subtasks:**
1. Install Neo4j 5.15 Community Edition via Docker
   ```bash
   docker pull neo4j:5.15-community
   docker run -d \
     --name neo4j-catrag \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/uitchatbot \
     -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
     neo4j:5.15-community
   ```

2. Verify installation:
   - Access Neo4j Browser: http://localhost:7474
   - Run test query: `MATCH (n) RETURN count(n)`
   - Check APOC: `CALL apoc.help("text")`

3. Create docker-compose.neo4j.yml for team replication

**Deliverables:**
- ✅ Working Neo4j instance (localhost:7687)
- ✅ docker-compose.neo4j.yml file
- ✅ Connection test script: `scripts/test_neo4j_connection.py`

**Acceptance Criteria:**
- [ ] Neo4j Browser accessible at localhost:7474
- [ ] Python can connect via `neo4j-driver`
- [ ] APOC and GDS plugins loaded successfully
- [ ] Docker container auto-restarts

---

#### Task A2: CatRAG Schema Design (Monday-Tuesday - 6h)
**Owner:** Data Architect + Senior Developer  
**Priority:** P0 (Critical)

**Context:**
Design the **category-labeled schema** (CatRAG Principle #1) aligned with UIT domain.

**Schema Requirements:**

**1. Node Categories (10 types):**
```cypher
// Core academic entities
(:MON_HOC {ma_mon, ten_mon, so_tin_chi, khoa, hoc_ky, mo_ta})
(:CHUONG_TRINH_DAO_TAO {ma_chuong_trinh, ten_chuong_trinh, khoa, nam_bat_dau})
(:KHOA {ma_khoa, ten_khoa, website, email})
(:GIANG_VIEN {ma_gv, ten_gv, khoa, email})

// Requirements & regulations
(:DIEU_KIEN {loai, mo_ta, gia_tri})
(:QUY_DINH {ma_quy_dinh, tieu_de, noi_dung, nam_ap_dung})
(:HOC_KY {ma_hk, ten_hk, nam_hoc, ngay_bat_dau, ngay_ket_thuc})

// Metadata
(:CATEGORY {name, description})
(:TAG {name, type})
(:ENTITY_MENTION {text, source_doc, confidence})
```

**2. Relationship Types (12 types):**
```cypher
// Critical relationships
(MON_HOC)-[:DIEU_KIEN_TIEN_QUYET]->(MON_HOC)       // For graph traversal
(MON_HOC)-[:DIEU_KIEN_SONG_HANH]->(MON_HOC)        // Co-requisites
(MON_HOC)-[:THUOC_CHUONG_TRINH]->(CHUONG_TRINH_DAO_TAO)
(MON_HOC)-[:THUOC_KHOA]->(KHOA)
(MON_HOC)-[:DUOC_DAY_BOI]->(GIANG_VIEN)
(MON_HOC)-[:MO_TA_BOI]->(ENTITY_MENTION)

// Hierarchical
(KHOA)-[:QUAN_LY]->(CHUONG_TRINH_DAO_TAO)
(CHUONG_TRINH_DAO_TAO)-[:AP_DUNG_QUY_DINH]->(QUY_DINH)

// Semantic
(MON_HOC)-[:LIEN_QUAN]->(MON_HOC)
(MON_HOC)-[:TAGGED_AS]->(TAG)
```

**Deliverables:**
- ✅ `config/graph_schema_catrag.yaml` - Category definitions
- ✅ `scripts/create_schema_constraints.cypher` - Constraints & indexes
- ✅ Schema diagram (draw.io or Mermaid)
- ✅ Documentation: CATRAG_SCHEMA.md

**Acceptance Criteria:**
- [ ] All 10 node categories defined with properties
- [ ] All 12 relationship types defined
- [ ] Constraints for unique IDs (ma_mon, ma_khoa, etc.)
- [ ] Indexes on search properties (ten_mon, ma_mon)
- [ ] Schema validated by team lead

---

#### Task A3: Graph Initialization Scripts (Tuesday-Wednesday - 4h)
**Owner:** Backend Developer  
**Priority:** P1

**Create Cypher Scripts:**

**1. Schema constraints:**
```cypher
// scripts/01_create_constraints.cypher
CREATE CONSTRAINT mon_hoc_ma IF NOT EXISTS 
FOR (m:MON_HOC) REQUIRE m.ma_mon IS UNIQUE;

CREATE CONSTRAINT khoa_ma IF NOT EXISTS 
FOR (k:KHOA) REQUIRE k.ma_khoa IS UNIQUE;

// ... constraints for all 10 node types
```

**2. Indexes for performance:**
```cypher
// scripts/02_create_indexes.cypher
CREATE INDEX mon_hoc_ten IF NOT EXISTS 
FOR (m:MON_HOC) ON (m.ten_mon);

CREATE INDEX mon_hoc_search IF NOT EXISTS 
FOR (m:MON_HOC) ON (m.ma_mon, m.ten_mon);

// Full-text search index
CALL db.index.fulltext.createNodeIndex(
  'mon_hoc_fulltext', 
  ['MON_HOC'], 
  ['ten_mon', 'mo_ta']
);
```

**3. Sample data loader:**
```cypher
// scripts/03_load_sample_data.cypher
// Create sample courses (IT Department)
CREATE (it001:MON_HOC {
  ma_mon: 'IT001',
  ten_mon: 'Nhập môn lập trình',
  so_tin_chi: 4,
  khoa: 'CNTT',
  mo_ta: 'Lập trình C/C++ cơ bản'
});

CREATE (it002:MON_HOC {
  ma_mon: 'IT002',
  ten_mon: 'Cấu trúc dữ liệu và giải thuật',
  so_tin_chi: 4,
  khoa: 'CNTT'
});

// Create prerequisite relationships
MATCH (it003:MON_HOC {ma_mon: 'IT003'})
MATCH (it002:MON_HOC {ma_mon: 'IT002'})
CREATE (it003)-[:DIEU_KIEN_TIEN_QUYET]->(it002);
```

**Deliverables:**
- ✅ `scripts/01_create_constraints.cypher`
- ✅ `scripts/02_create_indexes.cypher`
- ✅ `scripts/03_load_sample_data.cypher`
- ✅ `scripts/run_all_init.sh` - Batch runner

**Acceptance Criteria:**
- [ ] Scripts run without errors
- [ ] Constraints prevent duplicate nodes
- [ ] Indexes improve query performance (verify with EXPLAIN)
- [ ] Sample data creates 20+ nodes, 15+ relationships

---

#### Task A4: GraphRepository POC Implementation (Wednesday-Thursday - 8h)
**Owner:** Senior Backend Developer  
**Priority:** P1

**Already Created (Review & Enhance):**
- ✅ `core/domain/graph_models.py` (400 lines)
- ✅ `core/ports/graph_repository.py` (400 lines)
- ✅ `adapters/graph/neo4j_adapter.py` (500 lines POC)

**Enhancement Tasks:**
1. **Complete stub methods:**
   - `update_node()` - Update node properties
   - `delete_node()` - Soft delete with timestamp
   - `find_shortest_path()` - Dijkstra for course prerequisites

2. **Add batch operations:**
   ```python
   async def batch_add_nodes(
       self, 
       nodes: List[GraphNode],
       batch_size: int = 100
   ) -> List[str]:
       """Add nodes in batches for performance"""
   ```

3. **Add CatRAG-specific queries:**
   ```python
   async def find_prerequisites_chain(
       self, 
       course_code: str,
       max_depth: int = 5
   ) -> GraphPath:
       """Find full prerequisite chain for a course"""
   ```

4. **Connection pooling & retry logic:**
   - Max pool size: 50
   - Connection timeout: 30s
   - Retry on transient errors (3 attempts)

**Deliverables:**
- ✅ Enhanced `neo4j_adapter.py` with all methods implemented
- ✅ Unit tests: `tests/test_neo4j_adapter.py`
- ✅ Integration test: `tests/integration/test_graph_operations.py`

**Acceptance Criteria:**
- [ ] All GraphRepository methods implemented (25/25)
- [ ] Unit test coverage > 80%
- [ ] Integration tests pass against live Neo4j
- [ ] Performance: <50ms for single node operations
- [ ] Performance: <200ms for traversal queries (depth 3)

---

#### Task A5: Performance Baseline (Thursday-Friday - 4h)
**Owner:** DevOps + Backend Developer  
**Priority:** P2

**Benchmark Scenarios:**

1. **Node Operations:**
   - Add 1000 nodes: Target <5s
   - Batch add 10000 nodes: Target <30s
   - Query single node by ID: Target <10ms

2. **Relationship Operations:**
   - Add 1000 relationships: Target <8s
   - Query relationships (depth 2): Target <50ms
   - Query relationships (depth 5): Target <200ms

3. **Traversal Queries:**
   - Find prerequisites (depth 3): Target <100ms
   - Find all courses in program: Target <150ms
   - Shortest path between 2 courses: Target <80ms

**Tools:**
- `scripts/benchmark_graph_operations.py`
- `locust` for load testing (optional)

**Deliverables:**
- ✅ Benchmark results: `docs/WEEK1_PERFORMANCE_BASELINE.md`
- ✅ Performance optimization notes
- ✅ Recommended Neo4j config tweaks

**Acceptance Criteria:**
- [ ] All benchmarks documented
- [ ] Performance meets or exceeds targets
- [ ] Bottlenecks identified and documented
- [ ] Optimization plan for Week 2

---

### **Team B: NLP & Entity Extraction Tasks**

#### Task B1: NER Model Selection & Benchmarking (Monday-Tuesday - 8h)
**Owner:** NLP Engineer + ML Engineer  
**Priority:** P0 (Critical)

**Models to Evaluate:**

1. **PhoBERT-NER** (Recommended)
   - Pre-trained on Vietnamese corpus
   - Fine-tune on UIT-specific entities
   - Expected F1: 0.85-0.90

2. **VnCoreNLP**
   - Rule-based + CRF
   - Fast inference (<50ms)
   - Expected F1: 0.75-0.80

3. **Underthesea**
   - Lightweight, easy integration
   - Expected F1: 0.70-0.75

**Evaluation Dataset:**
Create 100 labeled sentences covering:
- Course codes: IT001, IT002, SE101, etc. (30 sentences)
- Department names: CNTT, KHMT, etc. (20 sentences)
- Regulation references: QĐ 123/2023, etc. (20 sentences)
- Requirements: điều kiện, tiên quyết, etc. (30 sentences)

**Metrics:**
- Precision, Recall, F1 per entity category
- Inference speed (sentences/sec)
- Memory usage

**Deliverables:**
- ✅ Evaluation dataset: `data/ner_evaluation_dataset.json`
- ✅ Benchmark script: `scripts/benchmark_ner_models.py`
- ✅ Results report: `docs/NER_MODEL_SELECTION.md`
- ✅ Recommendation with rationale

**Acceptance Criteria:**
- [ ] 3 models benchmarked
- [ ] Results documented with metrics
- [ ] Model recommendation approved by team lead
- [ ] Selected model integrated into codebase

---

#### Task B2: Category-Guided Entity Extractor (Tuesday-Wednesday - 6h)
**Owner:** NLP Engineer  
**Priority:** P1

**Already Created (Review & Enhance):**
- ✅ `indexing/category_guided_entity_extractor.py` (350 lines POC)

**Enhancement Tasks:**

1. **Add more entity patterns:**
   ```python
   CATEGORY_PATTERNS = {
       "MON_HOC": [
           r'\b[A-Z]{2,4}\d{3}[A-Z]?\b',  # IT001, SE101A
           r'(?i)môn\s+([A-ZĐ][a-zđ\s]+)',  # Môn Lập trình
       ],
       "KHOA": [
           r'(?i)khoa\s+([A-ZĐ][a-zđ\s]+)',
           r'\b(?:CNTT|KHMT|KTMT|HTTT)\b',  # Abbreviations
       ],
       "DIEU_KIEN": [
           r'(?i)(điều\s+kiện|tiên\s+quyết|yêu\s+cầu)',
           r'(?i)cần\s+(học|hoàn\s+thành|đạt)',
       ],
       # ... add 5+ more categories
   }
   ```

2. **Implement intent-based extraction:**
   ```python
   def extract_for_intent(
       self, 
       text: str, 
       intent: QueryIntent
   ) -> Dict[str, List[Entity]]:
       """Extract only categories relevant to query intent"""
       
       # Map intent to relevant categories
       if intent == QueryIntent.TIEN_QUYET:
           categories = ["MON_HOC", "DIEU_KIEN"]
       elif intent == QueryIntent.THONG_TIN_KHOA:
           categories = ["KHOA", "CHUONG_TRINH_DAO_TAO"]
       # ... more mappings
       
       return self.extract_categories(text, categories)
   ```

3. **Normalization maps:**
   ```python
   NORMALIZATION_MAPS = {
       "MON_HOC": {
           "CNTT": "Công nghệ thông tin",
           "KTMT": "Kỹ thuật máy tính",
           "lập trình": "Lập trình",  # Capitalize
       },
       "KHOA": {
           "CNTT": "Công nghệ thông tin",
           "CS": "Khoa học máy tính",
       }
   }
   ```

**Deliverables:**
- ✅ Enhanced `category_guided_entity_extractor.py`
- ✅ Unit tests: `tests/test_entity_extractor.py`
- ✅ Test coverage > 85%

**Acceptance Criteria:**
- [ ] 8+ entity categories supported
- [ ] Intent-based extraction implemented
- [ ] Normalization for Vietnamese text
- [ ] F1 score > 0.80 on test dataset

---

#### Task B3: Vietnamese Text Preprocessing (Wednesday-Thursday - 4h)
**Owner:** NLP Engineer  
**Priority:** P2

**Preprocessing Pipeline:**

1. **Text normalization:**
   - Unicode normalization (NFC)
   - Remove extra whitespace
   - Handle Vietnamese diacritics

2. **Tokenization:**
   - Use VnCoreNLP or Underthesea
   - Handle compound words (e.g., "công nghệ thông tin")

3. **Stopword removal:**
   - Custom stopword list for academic Vietnamese
   - Preserve important keywords (tiên quyết, yêu cầu, etc.)

**Deliverables:**
- ✅ `indexing/preprocess/vietnamese_preprocessor.py`
- ✅ Stopword list: `data/vietnamese_stopwords.txt`
- ✅ Tests: `tests/test_vietnamese_preprocessor.py`

**Acceptance Criteria:**
- [ ] Handles all Vietnamese diacritics correctly
- [ ] Preserves entity boundaries during tokenization
- [ ] Preprocessing time: <10ms per sentence

---

#### Task B4: Integration Testing (Thursday-Friday - 6h)
**Owner:** Both Teams  
**Priority:** P1

**Integration Scenarios:**

1. **Entity Extraction → Graph Population:**
   ```python
   # Extract entities from text
   text = "Môn IT003 cần học IT002 trước"
   entities = extractor.extract_for_intent(text, QueryIntent.TIEN_QUYET)
   
   # Populate graph
   for entity in entities["MON_HOC"]:
       node = create_mon_hoc_node(entity)
       await graph_adapter.add_node(node)
   ```

2. **Graph Traversal → Results:**
   ```python
   # Query prerequisites
   prerequisites = await graph_adapter.find_prerequisites_chain("IT003")
   
   # Verify results
   assert "IT002" in prerequisites.node_ids
   assert "IT001" in prerequisites.node_ids
   ```

**Test Cases:**
- Extract 10 courses → Add to graph → Verify count
- Create prerequisite chain → Traverse → Verify path
- Batch add 100 nodes → Query all → Verify integrity

**Deliverables:**
- ✅ Integration tests: `tests/integration/test_e2e_catrag.py`
- ✅ Test data: `tests/fixtures/sample_course_data.json`
- ✅ CI/CD pipeline config (optional)

**Acceptance Criteria:**
- [ ] All integration tests pass
- [ ] E2E workflow completes successfully
- [ ] No data loss during entity → graph pipeline
- [ ] Performance: Full pipeline <500ms for 10 entities

---

## 🎬 Friday Demo Script

### **Presentation Flow (30 minutes):**

**1. Introduction (5 min)**
- Overview of CatRAG approach
- Week 1 objectives recap

**2. Team A Demo (10 min)**
```bash
# Show Neo4j Browser
# Navigate to localhost:7474

# Run prerequisite query
MATCH path = (course:MON_HOC {ma_mon: 'IT003'})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq:MON_HOC)
RETURN path

# Show schema
CALL db.schema.visualization()

# Run Python adapter
python scripts/demo_graphrag_poc.py
```

**3. Team B Demo (10 min)**
```bash
# Run entity extraction
python indexing/category_guided_entity_extractor.py

# Show intent-based extraction
python scripts/demo_intent_extraction.py
```

**4. Integration Demo (5 min)**
```bash
# Show E2E pipeline
python tests/integration/test_e2e_catrag.py -v
```

**5. Q&A + Next Steps (5 min)**

---

## 📊 Success Metrics

### **Team A:**
- ✅ Neo4j accessible and stable
- ✅ Schema designed with 10 node categories
- ✅ 25/25 GraphRepository methods implemented
- ✅ Performance baselines documented
- ✅ Demo working smoothly

### **Team B:**
- ✅ NER model selected and benchmarked
- ✅ Entity extractor F1 > 0.80
- ✅ 8+ entity categories supported
- ✅ Intent-based extraction working
- ✅ Demo extraction accurate

### **Integration:**
- ✅ E2E pipeline functional
- ✅ No critical bugs
- ✅ Documentation complete

---

## 🚧 Known Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Neo4j Docker issues | Medium | High | Provide troubleshooting guide, backup local install |
| NER model low accuracy | Low | Medium | Use ensemble of models, add rule-based fallback |
| Integration complexity | Medium | Medium | Daily sync meetings, shared test data |
| Timeline slip | Low | Low | Buffer tasks on Friday, clear priorities |

---

## 📝 Checklist

### **Team A Checklist:**
- [ ] Neo4j Docker running (Task A1)
- [ ] Schema designed and approved (Task A2)
- [ ] Cypher scripts tested (Task A3)
- [ ] GraphRepository 100% implemented (Task A4)
- [ ] Performance benchmarks done (Task A5)
- [ ] Demo script ready

### **Team B Checklist:**
- [ ] NER models benchmarked (Task B1)
- [ ] Entity extractor enhanced (Task B2)
- [ ] Vietnamese preprocessing done (Task B3)
- [ ] Integration tests passing (Task B4)
- [ ] Demo script ready

### **Documentation:**
- [ ] CATRAG_SCHEMA.md
- [ ] NER_MODEL_SELECTION.md
- [ ] WEEK1_PERFORMANCE_BASELINE.md
- [ ] Code comments and docstrings

---

## 🔜 Week 2 Preview

**Team A:** Graph Builder service, batch operations, query optimizer  
**Team B:** LLM-guided relation extraction, entity resolution, confidence scoring  
**Integration:** Router Agent POC, intent classification

---

**Last Updated:** November 13, 2025  
**Status:** ✅ Ready for Kickoff
