# Sprint Planning Templates - GraphRAG Project

## 📋 Template cho GitHub Issues

### **Template 1: Team A - Infrastructure Task**

```markdown
### 🔵 [Team A] [Component] - Task Title

**Sprint:** Week X-Y | **Phase:** N | **Priority:** High/Medium/Low

#### 📝 Description
Brief description of what needs to be done.

#### 🎯 Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

#### 📦 Deliverables
- File/Module name
- Configuration file
- Test file

#### 🔗 Dependencies
- Depends on: #issue-number
- Blocks: #issue-number

#### 🧪 Testing Requirements
- [ ] Unit tests written (coverage > 80%)
- [ ] Integration tests pass
- [ ] Manual testing completed

#### 📚 Documentation
- [ ] Code comments added
- [ ] API documentation updated
- [ ] README updated if needed

#### ⏱️ Estimate
Story Points: X | Hours: Y

#### 🏷️ Labels
`team-a` `infrastructure` `sprint-X` `phase-X`
```

---

### **Template 2: Team B - NLP/ML Task**

```markdown
### 🟢 [Team B] [Component] - Task Title

**Sprint:** Week X-Y | **Phase:** N | **Priority:** High/Medium/Low

#### 📝 Description
Brief description of what needs to be done.

#### 🎯 Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

#### 📦 Deliverables
- Model/Module name
- Evaluation metrics
- Test dataset

#### 🔗 Dependencies
- Depends on: #issue-number
- Blocks: #issue-number

#### 🧪 Testing Requirements
- [ ] Unit tests written (coverage > 80%)
- [ ] Model evaluation completed
- [ ] Benchmark comparison done

#### 📊 Performance Metrics
- Target Accuracy: X%
- Target Latency: Yms
- Other metrics...

#### 📚 Documentation
- [ ] Model card created
- [ ] API documentation updated
- [ ] Example usage added

#### ⏱️ Estimate
Story Points: X | Hours: Y

#### 🏷️ Labels
`team-b` `nlp` `ml` `sprint-X` `phase-X`
```

---

## 🎫 PHASE 1 - Week 1-4 GitHub Issues

### **Week 1-2: Team A Tasks**

#### Issue #1: Neo4j Docker Setup with APOC + GDS

```markdown
### 🔵 [Team A] Infrastructure - Neo4j Docker Setup with APOC + GDS

**Sprint:** Week 1-2 | **Phase:** 1 | **Priority:** High

#### 📝 Description
Setup Neo4j Community Edition 5.15+ trong Docker với APOC và Graph Data Science plugins. Đây là foundation cho toàn bộ Knowledge Graph infrastructure.

#### 🎯 Acceptance Criteria
- [ ] Neo4j container chạy thành công trên port 7474 (Browser) và 7687 (Bolt)
- [ ] APOC plugin được cài đặt và test functions
- [ ] GDS plugin được cài đặt và test algorithms
- [ ] Authentication configured (neo4j/uitchatbot)
- [ ] Data persistence với volumes
- [ ] Health check endpoint working

#### 📦 Deliverables
- `services/rag_services/docker/docker-compose.neo4j.yml`
- `services/rag_services/docker/neo4j.env.example`
- `services/rag_services/scripts/test_neo4j_connection.py`
- `services/rag_services/docs/NEO4J_SETUP.md`

#### 🔗 Dependencies
- None (starting task)

#### 🧪 Testing Requirements
- [ ] Container starts without errors
- [ ] Can connect via Python neo4j-driver
- [ ] APOC functions accessible (test `apoc.version()`)
- [ ] GDS algorithms work (test `gds.version()`)
- [ ] Data persists after container restart

#### 📚 Documentation
- [ ] Document environment variables
- [ ] Add troubleshooting section
- [ ] Include APOC/GDS plugin verification steps

#### 💻 Technical Notes
```yaml
# Docker Compose structure
services:
  neo4j:
    image: neo4j:5.15-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/uitchatbot
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
```

#### ⏱️ Estimate
Story Points: 5 | Hours: 8-10

#### 🏷️ Labels
`team-a` `infrastructure` `docker` `sprint-1` `phase-1` `high-priority`
```

---

#### Issue #2: CatRAG Category Schema Design (UIT Domain)

```markdown
### 🔵 [Team A] Graph Schema - Design CatRAG Category Schema for UIT

**Sprint:** Week 1-2 | **Phase:** 1 | **Priority:** Critical

#### 📝 Description
Thiết kế schema đồ thị **phân cấp có danh mục** (Category-labeled KG) cho domain UIT theo CatRAG approach. Đây là core foundation cho toàn bộ GraphRAG system.

#### 🎯 Acceptance Criteria
- [ ] Định nghĩa đầy đủ Node Categories (8-12 types)
- [ ] Định nghĩa Relationship Types (10-15 types)
- [ ] Schema có phân cấp rõ ràng (hierarchical)
- [ ] Mỗi category có properties chuẩn hóa
- [ ] Schema được document trong Neo4j Browser
- [ ] Cypher scripts tạo constraints & indexes

#### 📦 Deliverables
- `services/rag_services/config/graph_schema_catrag.yaml`
- `services/rag_services/scripts/init_catrag_schema.cypher`
- `services/rag_services/docs/CATRAG_SCHEMA_DESIGN.md`
- Schema visualization diagram (PNG/SVG)

#### 🔗 Dependencies
- Depends on: #1 (Neo4j setup)

#### 🎯 CatRAG Category Schema (UIT Domain)

**Node Categories (Primary):**
```yaml
1. MonHoc (Môn học):
   - Properties: code (IT001), name, credits, type (bat_buoc/tu_chon)
   - Category: ACADEMIC_COURSE
   
2. QuyDinh (Quy định):
   - Properties: id, title, year, type (tuyen_sinh/tot_nghiep/hoc_vu)
   - Category: REGULATION
   
3. DieuKien (Điều kiện):
   - Properties: type (diem_so/tin_chi/mon_hoc), threshold, description
   - Category: REQUIREMENT
   
4. Khoa (Khoa):
   - Properties: code (CNTT/KHTN), name, dean
   - Category: DEPARTMENT
   
5. Nganh (Ngành):
   - Properties: code, name, type (dai_tra/cao_dang)
   - Category: MAJOR
   
6. ChuongTrinhDaoTao (Chương trình):
   - Properties: id, name, year, credits_required
   - Category: CURRICULUM
   
7. SinhVien (Đối tượng SV):
   - Properties: cohort (K2019/K2020), type (chinh_quy/lien_thong)
   - Category: STUDENT_TARGET
   
8. KyHoc (Kỳ học):
   - Properties: code (HK1/HK2/HK3), year, start_date, end_date
   - Category: SEMESTER
   
9. GiangVien (Giảng viên):
   - Properties: code, name, title, khoa_code
   - Category: INSTRUCTOR
   
10. HocPhi (Học phí):
    - Properties: type, amount, year, applies_to
    - Category: TUITION
```

**Relationship Types:**
```cypher
// Hierarchical Structure
(:Nganh)-[:THUOC_KHOA]->(:Khoa)
(:MonHoc)-[:THUOC_CHUONG_TRINH]->(:ChuongTrinhDaoTao)
(:ChuongTrinhDaoTao)-[:CUA_NGANH]->(:Nganh)

// Prerequisites & Requirements (CRITICAL for CatRAG)
(:MonHoc)-[:DIEU_KIEN_TIEN_QUYET {type: "bat_buoc/khuyen_nghi"}]->(:MonHoc)
(:MonHoc)-[:YEU_CAU_DIEU_KIEN]->(:DieuKien)
(:QuyDinh)-[:QUY_DINH_DIEU_KIEN]->(:DieuKien)

// Applicability
(:QuyDinh)-[:AP_DUNG_CHO]->(:SinhVien|Nganh|Khoa)
(:DieuKien)-[:AP_DUNG_CHO]->(:SinhVien|Nganh)

// Scheduling
(:MonHoc)-[:HOC_TRONG]->(:KyHoc)
(:GiangVien)-[:DAY {semester: "HK1-2024"}]->(:MonHoc)

// Financial
(:HocPhi)-[:AP_DUNG_CHO]->(:SinhVien|Nganh)
(:HocPhi)-[:THEO_QUY_DINH]->(:QuyDinh)

// Semantic Relations
(:MonHoc)-[:LIEN_QUAN_NOI_DUNG]->(:MonHoc)
(:QuyDinh)-[:THAY_THE]->(:QuyDinh)
(:QuyDinh)-[:BO_SUNG]->(:QuyDinh)
```

**Category Hierarchy:**
```
ACADEMIC
├── MonHoc (Course)
├── ChuongTrinhDaoTao (Curriculum)
└── KyHoc (Semester)

ADMINISTRATIVE
├── QuyDinh (Regulation)
├── DieuKien (Requirement)
└── HocPhi (Tuition)

ORGANIZATIONAL
├── Khoa (Department)
├── Nganh (Major)
├── GiangVien (Instructor)
└── SinhVien (Student Target)
```

#### 🧪 Testing Requirements
- [ ] Create 30-50 sample nodes covering all categories
- [ ] Create 50-100 sample relationships
- [ ] Validate schema constraints
- [ ] Test Cypher queries for each relationship type

#### 📚 Documentation
- [ ] Document rationale for each category
- [ ] Provide examples for each node type
- [ ] Include query examples for common use cases

#### 💡 CatRAG Alignment
This schema enables:
- **Intent-based routing**: Query về "tiên quyết" → Graph traversal
- **Category-specific retrieval**: Query về "mô tả môn" → Vector search
- **Multi-hop reasoning**: Traverse prerequisites chains
- **Structured Q&A**: "Điều kiện tốt nghiệp CNTT?" → traverse regulation graph

#### ⏱️ Estimate
Story Points: 8 | Hours: 12-16

#### 🏷️ Labels
`team-a` `graph-schema` `catrag` `critical` `sprint-1` `phase-1`
```

---

#### Issue #3: Neo4j Graph Adapter Implementation

```markdown
### 🔵 [Team A] Backend - Implement Neo4j Graph Adapter (Ports & Adapters)

**Sprint:** Week 1-2 | **Phase:** 1 | **Priority:** High

#### 📝 Description
Implement adapter pattern cho Neo4j operations theo clean architecture. Adapter này sẽ implement GraphRepository port và cung cấp interface sạch cho domain layer.

#### 🎯 Acceptance Criteria
- [ ] GraphRepository interface defined in ports
- [ ] Neo4jGraphAdapter implements GraphRepository
- [ ] Support CRUD operations cho nodes & relationships
- [ ] Support Cypher query execution
- [ ] Connection pooling & error handling
- [ ] Async operations support

#### 📦 Deliverables
- `services/rag_services/core/ports/graph_repository.py`
- `services/rag_services/adapters/neo4j_graph_adapter.py`
- `services/rag_services/core/domain/graph_models.py`
- `services/rag_services/tests/test_neo4j_adapter.py`

#### 🔗 Dependencies
- Depends on: #1 (Neo4j setup)
- Depends on: #2 (Schema design)

#### 🧪 Testing Requirements
- [ ] Unit tests for all adapter methods
- [ ] Integration tests with real Neo4j instance
- [ ] Test connection handling & retries
- [ ] Test transaction rollback

#### 💻 API Design
```python
class GraphRepository(ABC):
    async def add_node(self, category: str, properties: Dict) -> str
    async def add_relationship(self, source_id: str, rel_type: str, target_id: str, properties: Dict) -> bool
    async def get_node(self, node_id: str) -> Optional[Node]
    async def query(self, cypher: str, params: Dict) -> List[Dict]
    async def traverse(self, start_id: str, max_depth: int, relationship_types: List[str]) -> Graph
```

#### ⏱️ Estimate
Story Points: 8 | Hours: 12-16

#### 🏷️ Labels
`team-a` `backend` `adapter` `sprint-1` `phase-1`
```

---

### **Week 1-2: Team B Tasks**

#### Issue #4: Vietnamese NER Model Selection & Benchmarking

```markdown
### 🟢 [Team B] NLP - Vietnamese NER Model Selection

**Sprint:** Week 1-2 | **Phase:** 1 | **Priority:** High

#### 📝 Description
Research, benchmark và chọn best Vietnamese NER model cho entity extraction. Model phải support các entity types đã define trong CatRAG schema.

#### 🎯 Acceptance Criteria
- [ ] Benchmark 3-4 Vietnamese NER models
- [ ] Test trên UIT domain data (100 labeled sentences)
- [ ] Measure Precision, Recall, F1 for each entity type
- [ ] Select best model (accuracy vs speed tradeoff)
- [ ] Document benchmark results

#### 📦 Deliverables
- `services/rag_services/docs/NER_MODEL_BENCHMARK.md`
- `services/rag_services/tests/fixtures/ner_test_data_100.json`
- `services/rag_services/config/ner_model_config.yaml`

#### 🎯 Entity Types to Extract (aligned with CatRAG)
```yaml
ENTITY_TYPES:
  - MON_HOC: "IT001", "Nhập môn lập trình", "NMLT"
  - KHOA: "CNTT", "Khoa Công nghệ thông tin"
  - NGANH: "Công nghệ thông tin", "Khoa học máy tính"
  - QUY_DINH: "Quy chế 43/2024", "Quy định tốt nghiệp"
  - DIEM_SO: "GPA 2.0", "điểm trung bình 6.5"
  - TIN_CHI: "120 tín chỉ", "3 tín chỉ"
  - NAM_HOC: "năm học 2024-2025", "2024"
  - KY_HOC: "học kỳ 1", "HK2"
```

#### 🧪 Models to Benchmark
1. **PhoBERT-NER** (vinai/phobert-base)
2. **VnCoreNLP** (vncorenlp)
3. **XLM-RoBERTa-NER** (xlm-roberta-base fine-tuned)
4. **Custom BERT** (if needed)

#### 📊 Performance Metrics
- Precision@Entity_Type
- Recall@Entity_Type
- F1@Entity_Type
- Inference Latency (ms per document)
- Model Size (MB)

#### ⏱️ Estimate
Story Points: 5 | Hours: 10-12

#### 🏷️ Labels
`team-b` `nlp` `ner` `research` `sprint-1` `phase-1`
```

---

#### Issue #5: Category-Guided Entity Extractor Implementation

```markdown
### 🟢 [Team B] NLP - Implement Category-Guided Entity Extractor

**Sprint:** Week 1-2 | **Phase:** 1 | **Priority:** High

#### 📝 Description
Implement entity extractor với **category-guided approach** theo CatRAG. Thay vì bottom-up extraction, dùng predefined categories để guide extraction process.

#### 🎯 Acceptance Criteria
- [ ] EntityExtractor class implemented
- [ ] Support all 10 category types from schema
- [ ] Post-processing & normalization
- [ ] Confidence scoring for each entity
- [ ] Handle Vietnamese text correctly (diacritics, compound words)

#### 📦 Deliverables
- `services/rag_services/indexing/entity_extractor.py`
- `services/rag_services/indexing/entity_models.py`
- `services/rag_services/config/entity_extraction_config.yaml`
- `services/rag_services/tests/test_entity_extraction.py`

#### 🔗 Dependencies
- Depends on: #4 (NER model selection)
- Related to: #2 (CatRAG schema)

#### 💻 API Design (Category-Guided)
```python
class CategoryGuidedEntityExtractor:
    def __init__(self, model_name: str, categories: Dict[str, CategoryConfig]):
        """
        categories: Định nghĩa từ CatRAG schema
        {
            "MON_HOC": {
                "patterns": [...],
                "examples": ["IT001", "Nhập môn lập trình"],
                "validation_rules": [...]
            }
        }
        """
        
    def extract_by_category(
        self, 
        text: str, 
        target_categories: List[str]
    ) -> Dict[str, List[Entity]]:
        """
        Extract entities thuộc specific categories only.
        
        Example:
        >>> extract_by_category(text, ["MON_HOC", "DIEU_KIEN"])
        {
            "MON_HOC": [Entity("IT001", type="MON_HOC", confidence=0.95)],
            "DIEU_KIEN": [Entity("120 tín chỉ", type="TIN_CHI", confidence=0.88)]
        }
        """
```

#### 🧪 Testing Requirements
- [ ] Test extraction for each category type
- [ ] Test Vietnamese diacritics handling
- [ ] Test compound words (e.g., "công nghệ thông tin")
- [ ] Test abbreviation matching (e.g., "CNTT" = "Công nghệ thông tin")
- [ ] Achieve F1 > 0.85 on test set

#### 📊 Performance Targets
- F1 Score: > 0.85 (per category)
- Latency: < 100ms per document (avg)
- False Positive Rate: < 5%

#### 💡 CatRAG Alignment
- Guided extraction ensures entities match schema categories
- Enables intent-based routing (extract only needed categories)
- Improves precision by constraining entity types

#### ⏱️ Estimate
Story Points: 8 | Hours: 14-16

#### 🏷️ Labels
`team-b` `nlp` `entity-extraction` `catrag` `sprint-1` `phase-1`
```

---

## 🎫 Jira Epic Structure

### **Epic 1: GraphRAG Foundation [Phase 1]**

```
Epic: GraphRAG Foundation Setup
Timeline: Week 1-4
Teams: A + B

Stories:
├─ GRAPH-1: Neo4j Infrastructure Setup [Team A]
├─ GRAPH-2: CatRAG Schema Design [Team A] 🔥
├─ GRAPH-3: Graph Adapter Implementation [Team A]
├─ GRAPH-4: Data Ingestion Pipeline [Team A]
├─ GRAPH-5: NER Model Selection [Team B]
├─ GRAPH-6: Category-Guided Entity Extractor [Team B] 🔥
├─ GRAPH-7: LLM-Guided Relation Extractor [Team B] 🔥
└─ GRAPH-8: Graph Builder Integration [A+B]

Labels: phase-1, foundation, catrag
```

---

### **Epic 2: Intent Router & Category-Based Retrieval [Phase 1-2]**

```
Epic: Implement CatRAG Intent Router
Timeline: Week 3-8
Teams: A + B + Orchestrator

Stories:
├─ ROUTER-1: Define Query Intent Categories [Team B] 🔥
├─ ROUTER-2: Intent Classifier Implementation [Team B] 🔥
├─ ROUTER-3: Planner Agent → Router Agent Migration [Orchestrator] 🔥
├─ ROUTER-4: Category-Based Retrieval Strategies [Team A]
├─ ROUTER-5: Graph Traversal Service [Team A]
├─ ROUTER-6: Vector Search Service (unchanged) [Team A]
└─ ROUTER-7: Routing Integration Testing [A+B]

Labels: phase-2, routing, catrag, critical
```

---

## 📊 Sprint Board Setup (GitHub Projects or Jira)

### **Columns:**
```
1. 📋 Backlog
2. 🔜 Todo (This Sprint)
3. 🏗️ In Progress (WIP limit: 3 per person)
4. 👀 In Review
5. 🧪 Testing
6. ✅ Done
7. 🚫 Blocked
```

### **Swim Lanes:**
```
- Team A (Infrastructure)
- Team B (NLP/ML)
- Cross-Team (Integration)
- Orchestrator (Routing)
```

---

## 🏷️ Label System

### **Team Labels:**
- `team-a` - Team A tasks
- `team-b` - Team B tasks
- `cross-team` - Integration tasks
- `orchestrator` - Orchestrator service tasks

### **Priority Labels:**
- `critical` - Must have for CatRAG
- `high-priority` - Important for phase success
- `medium-priority` - Nice to have
- `low-priority` - Can defer

### **Type Labels:**
- `infrastructure` - DevOps, Docker, K8s
- `backend` - Python backend code
- `nlp` - NLP/NER tasks
- `ml` - Machine learning tasks
- `graph` - Graph database related
- `catrag` - CatRAG specific features 🔥

### **Phase Labels:**
- `phase-1` - Foundation (Week 1-4)
- `phase-2` - Retrieval (Week 5-12)
- `phase-3` - Auto-construction (Week 13-18)
- `phase-4` - Production (Week 19-24)

---

## 📝 Issue Template cho CatRAG Features

### **Template 3: CatRAG-Specific Feature**

```markdown
### 🌟 [CatRAG] [Component] - Feature Title

**Sprint:** Week X-Y | **Phase:** N | **Priority:** Critical

#### 📝 Description
Brief description emphasizing CatRAG approach.

#### 🎯 CatRAG Rationale
Why this is important for CatRAG:
- How it uses category-labeled graph
- How it enables intent routing
- Impact on retrieval accuracy

#### 🎯 Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
- [ ] Aligns with CatRAG paper approach

#### 📦 Deliverables
- Component files
- Category definitions
- Routing logic

#### 🔗 Dependencies
- Depends on CatRAG schema (#2)
- Related to Intent Router

#### 🧪 Testing Requirements
- [ ] Test with category-based queries
- [ ] Validate routing decisions
- [ ] Measure accuracy improvement

#### 📊 Performance Metrics (CatRAG)
- Intent Classification Accuracy: > 90%
- Routing Precision: > 95%
- End-to-end Latency: < 500ms

#### 💡 Example Queries
```
# Category: TIEN_QUYET (Graph traversal)
Q: "Môn tiên quyết của IT003 là gì?"
Route: GraphRAG → Neo4j traversal

# Category: MO_TA_MON (Vector search)
Q: "IT003 học về gì?"
Route: VectorRAG → Weaviate semantic search

# Category: DIEU_KIEN_TOT_NGHIEP (Multi-hop graph)
Q: "Điều kiện tốt nghiệp ngành CNTT?"
Route: GraphRAG → Complex Cypher query
```

#### ⏱️ Estimate
Story Points: X | Hours: Y

#### 🏷️ Labels
`catrag` `critical` `routing` `sprint-X` `phase-X`
```

---

## 🔄 Sprint Workflow

### **Sprint Kickoff (Every 2 weeks)**
1. Review backlog
2. Estimate story points
3. Assign tasks
4. Identify dependencies
5. Set sprint goals

### **Daily Standup (15 min)**
```
Template:
1. What I did yesterday
2. What I'll do today
3. Any blockers?
4. Need help from other team?
```

### **Mid-Sprint Sync (Week 1 Wednesday)**
- Check progress
- Adjust if needed
- Cross-team alignment

### **Sprint Review (Last Friday)**
- Demo completed features
- Stakeholder feedback
- Update metrics

### **Sprint Retrospective (Last Friday)**
- What went well?
- What can improve?
- Action items for next sprint

---

## 📈 Metrics Dashboard

### **Velocity Tracking**
```
Sprint 1: X points completed
Sprint 2: Y points completed
Average velocity: Z points/sprint
```

### **Burn-down Chart**
Track story points remaining each day.

### **CatRAG-Specific Metrics**
```
- Categories defined: X/10
- Routing rules implemented: Y/15
- Intent classification accuracy: Z%
- Graph coverage: N nodes, M edges
```

---

## 🎯 Quick Reference: First Week Tasks

### **Team A - Week 1**
1. Monday-Tuesday: Setup Neo4j (#1)
2. Wednesday-Friday: Design CatRAG Schema (#2)
3. Weekend: Start Graph Adapter (#3)

### **Team B - Week 1**
1. Monday-Tuesday: NER Model Research (#4)
2. Wednesday-Thursday: Benchmark models
3. Friday: Start Entity Extractor (#6)

### **Cross-Team - Week 1**
- Daily standup at 9 AM
- Wednesday sync: Schema review
- Friday: Week 1 demo prep

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Owner:** GraphRAG Project Team
