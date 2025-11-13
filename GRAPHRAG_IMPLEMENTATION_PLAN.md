# GraphRAG Implementation Plan - Long-term (5-6 tháng)

## 📋 Tổng Quan Dự Án

**Mục tiêu:** Xây dựng hệ thống GraphRAG hoàn chỉnh tích hợp Knowledge Graph vào RAG pipeline hiện tại

**Timeline:** 5-6 tháng (20-24 tuần)

**Nhân sự:** 2 nhóm (Team A & Team B) - làm việc song song

**Kiến trúc mục tiêu:**
```
┌─────────────────────────────────────────────────────┐
│              ORCHESTRATOR (Multi-Agent)             │
└─────────────────────┬───────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│         GraphRAG Service (Enhanced RAG)             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Graph Query  │  │ Vector Search│  │  Hybrid   │ │
│  │  (Neo4j)     │  │  (Weaviate)  │  │  Rerank   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│            Data Layer & Indexing                    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Neo4j DB   │  │   Weaviate   │  │ OpenSearch│ │
│  │  (Graph KG)  │  │   (Vector)   │  │ (Keyword) │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Phân Công 2 Nhóm - Song Song

### **TEAM A: Infrastructure & Graph Foundation**
**Focus:** Xây dựng nền tảng Knowledge Graph, Data Pipeline, và Graph Database

**Lead Skills Required:** Backend, Database, DevOps

### **TEAM B: NLP & Retrieval Enhancement**
**Focus:** Entity/Relation Extraction, Graph-enhanced Search, và Reranking

**Lead Skills Required:** NLP, Machine Learning, RAG Engineering

---

## 🌟 CATRAG APPROACH - Core Principles

**CRITICAL UPDATE:** Hệ thống được xây dựng theo **CatRAG (Category-guided Graph RAG)** approach:

### **1️⃣ Định nghĩa "Danh Mục" (Categories) cho Graph**

**Nguyên tắc:** Thay vì bottom-up extraction, chúng ta định nghĩa trước schema đồ thị có phân cấp và nhãn danh mục.

**Các danh mục Node (Category-labeled):**
- 🎓 **MON_HOC** (Môn học): IT001, IT002, IT003
- 📋 **QUY_DINH** (Quy định): Quy chế 43/2024, Quy định tốt nghiệp
- ✅ **DIEU_KIEN** (Điều kiện): GPA >= 2.0, 120 tín chỉ
- 🏛️ **KHOA** (Khoa): CNTT, KHMT, KHTN
- 🎯 **NGANH** (Ngành): Công nghệ thông tin
- 📚 **CHUONG_TRINH_DAO_TAO** (Chương trình)
- 👨‍🎓 **SINH_VIEN** (Đối tượng sinh viên): K2024, K2023
- 📅 **KY_HOC** (Kỳ học): HK1, HK2, HK3

**Các mối quan hệ (Relationships):**
- 🔗 **DIEU_KIEN_TIEN_QUYET**: Môn A yêu cầu môn B (CRITICAL for routing)
- 🔗 **YEU_CAU_DIEU_KIEN**: Môn học/Quy định yêu cầu điều kiện
- 🔗 **AP_DUNG_CHO**: Quy định áp dụng cho đối tượng
- 🔗 **THUOC_KHOA**: Ngành thuộc Khoa (hierarchical)

**Tại sao quan trọng:**
✅ Giúp Router Agent phân loại intent chính xác
✅ Cho phép graph traversal có hướng
✅ Tạo nền tảng cho LLM-guided population

---

### **2️⃣ Dùng LLM để điền vào Graph có "Danh Mục"**

**Nguyên tắc:** Thay vì để LLM "tự động trích xuất" (bottom-up), dùng LLM với nhiệm vụ cụ thể là populate các danh mục đã định nghĩa.

**Cách làm:**

```python
# ❌ SAI: Bottom-up extraction
prompt = "Trích xuất tất cả entities từ văn bản này"

# ✅ ĐÚNG: Category-guided extraction
prompt = """
Từ văn bản sau, tìm:
1. Entities thuộc danh mục MON_HOC (mã môn học)
2. Entities thuộc danh mục DIEU_KIEN (điều kiện học)
3. Relationships DIEU_KIEN_TIEN_QUYET giữa các môn học

Văn bản: "{text}"
"""
```

**Lợi ích:**
✅ Graph có cấu trúc chặt chẽ, sạch sẽ
✅ Đúng với nghiệp vụ domain (UIT)
✅ Dễ validate và debug
✅ Tăng độ chính xác của graph queries

**Implementation:** Week 3-4 (Phase 1)

---

### **3️⃣ Nâng cấp Planner Agent → "Router Agent"**

**CRITICAL:** Đây là bước quan trọng nhất để cải thiện hiệu suất!

**Nhiệm vụ mới của Planner Agent:**

```
User Query → Router Agent → Routing Decision
                    ↓
            ┌───────┴────────┐
            ↓                ↓
    Graph Traversal    Vector Search
    (Prerequisites)    (Descriptions)
```

**Router Agent hoạt động:**

1. **Nhận câu hỏi** từ người dùng
2. **Phân loại intent** dựa trên categories:
   - TIEN_QUYET (Tiên quyết) → Graph traversal
   - MO_TA_MON_HOC (Mô tả môn) → Vector search
   - DIEU_KIEN_TOT_NGHIEP (Tốt nghiệp) → Multi-hop graph
   - CHUONG_TRINH_DAO_TAO → Graph traversal
   - QUY_DINH_HOC_VU → Hybrid search

3. **Điều hướng (Route) thông minh:**
   ```python
   if intent == "TIEN_QUYET":
       return route_to_graph_traversal()  # Neo4j
   elif intent == "MO_TA_MON_HOC":
       return route_to_vector_search()    # Weaviate
   elif intent == "DIEU_KIEN_TOT_NGHIEP":
       return route_to_multi_hop_graph()  # Complex Neo4j
   else:
       return route_to_hybrid_search()    # All sources
   ```

**Example Routing:**

| Query | Intent | Route To | Why |
|-------|--------|----------|-----|
| "Môn tiên quyết của IT003?" | TIEN_QUYET | Graph Traversal | Cần traverse prerequisite chain |
| "IT003 học về gì?" | MO_TA_MON_HOC | Vector Search | Semantic similarity on descriptions |
| "Điều kiện tốt nghiệp CNTT?" | DIEU_KIEN_TOT_NGHIEP | Multi-hop Graph | Traverse regulations → requirements → courses |
| "Học phí ngành CNTT?" | HOC_PHI | Hybrid Search | Needs both structure (graph) and text (vector) |

**Implementation:** Week 8-10 (Phase 2)

**Benefits:**
- ⚡ 30-50% faster (skip unnecessary vector search)
- 🎯 Higher precision (use right tool for right job)
- 💰 Lower cost (fewer LLM calls)
- 📊 Better explainability

---

## 📅 PHASE 1: Foundation Setup (Tuần 1-4)

### **🔵 TEAM A - Nhiệm vụ Phase 1**

#### **Sprint 1.1: CatRAG Schema Design & Neo4j Setup (Tuần 1-2)**

**🌟 UPDATED with CatRAG approach**

**Deliverables:**
- [ ] Neo4j Docker setup với APOC + GDS plugins
- [ ] Initial schema design cho UIT domain
- [ ] Basic CRUD operations
- [ ] Connection adapter pattern implementation

**Chi tiết công việc:**

```yaml
Week 1:
  - Day 1-2: 
      - Setup Neo4j container (docker-compose.neo4j.yml)
      - Configure authentication & security
      - Install APOC, GDS plugins
      - Test connection từ Python
  
  - Day 3-5:
      - Design schema v1.0:
          * Node types: Khoa, Nganh, MonHoc, QuyDinh, GiangVien
          * Relationship types: THUOC_KHOA, DIEU_KIEN_TIEN_QUYET, AP_DUNG_CHO
      - Create Cypher scripts cho schema initialization
      - Document schema trong Neo4j Browser

Week 2:
  - Day 1-3:
      - Implement neo4j_graph_adapter.py
          * Interface: GraphRepository (ports pattern)
          * Methods: add_node, add_relationship, query, traverse
      - Unit tests cho adapter
  
  - Day 4-5:
      - Create sample data (20-30 nodes)
      - Test basic graph queries
      - Performance baseline measurement
      - PR Review & merge
```

**Files to create:**
```
services/rag_services/
├── docker/
│   └── docker-compose.neo4j.yml          # NEW
├── adapters/
│   └── neo4j_graph_adapter.py            # NEW
├── core/
│   ├── domain/
│   │   └── graph_models.py               # NEW
│   └── ports/
│       └── graph_repository.py           # NEW
└── scripts/
    ├── init_neo4j_schema.py              # NEW
    └── seed_graph_data.py                # NEW
```

#### **Sprint 1.2: Data Ingestion Pipeline (Tuần 3-4)**

**Deliverables:**
- [ ] Document crawler/parser cho data sources
- [ ] ETL pipeline: Documents → Graph
- [ ] Batch processing với error handling
- [ ] Data validation & quality checks

**Chi tiết công việc:**

```yaml
Week 3:
  - Day 1-2:
      - Analyze existing data sources:
          * services/rag_services/data/quy_dinh/
          * services/rag_services/data/docs/
          * services/rag_services/data/crawled_programs/
      - Design ingestion manifest format
  
  - Day 3-5:
      - Implement graph_data_loader.py:
          * Parse PDF/DOCX to extract structured data
          * Map to graph entities
          * Batch insert to Neo4j
      - Handle duplicates & updates

Week 4:
  - Day 1-3:
      - Create indexing/graph_builder.py:
          * Orchestrate document → graph pipeline
          * Progress tracking & logging
          * Rollback on failures
  
  - Day 4-5:
      - Ingest first 100 documents into graph
      - Validate graph structure
      - Performance tuning (batch size, indexes)
      - Documentation & handoff to Team B
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── graph_builder.py                  # NEW
│   ├── graph_data_loader.py              # NEW
│   └── graph_validators.py               # NEW
└── scripts/
    ├── index_to_graph.py                 # NEW
    └── validate_graph_data.py            # NEW
```

---

### **🟢 TEAM B - Nhiệm vụ Phase 1**

#### **Sprint 1.1: NER & Entity Extraction Setup (Tuần 1-2)**

**Deliverables:**
- [ ] Vietnamese NER model selection/training
- [ ] Entity extraction pipeline
- [ ] Entity type classification
- [ ] Evaluation dataset preparation

**Chi tiết công việc:**

```yaml
Week 1:
  - Day 1-2:
      - Research Vietnamese NER models:
          * PhoBERT-NER
          * VnCoreNLP
          * Underthesea
          * Custom transformer models
      - Benchmark 3-4 models trên sample UIT data
  
  - Day 3-5:
      - Select best model (accuracy vs speed tradeoff)
      - Setup model inference pipeline
      - Create entity_extractor.py interface

Week 2:
  - Day 1-3:
      - Implement VietnameseEntityExtractor:
          * Input: text string
          * Output: List[Entity(text, type, span, confidence)]
          * Entity types: KHOA, NGANH, MON_HOC, QUY_DINH, NAM_HOC
      - Post-processing & normalization
  
  - Day 4-5:
      - Create evaluation dataset (100 labeled sentences)
      - Measure Precision/Recall/F1
      - Optimize threshold & filters
      - Document API & examples
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── entity_extractor.py               # NEW
│   ├── entity_models.py                  # NEW
│   └── entity_config.yaml                # NEW
└── tests/
    ├── test_entity_extraction.py         # NEW
    └── fixtures/
        └── entity_test_data.json         # NEW
```

#### **Sprint 1.2: Relation Extraction (Tuần 3-4)**

**Deliverables:**
- [ ] Relation extraction patterns/model
- [ ] Relation type classification
- [ ] Entity linking & resolution
- [ ] Integration với Graph Builder

**Chi tiết công việc:**

```yaml
Week 3:
  - Day 1-2:
      - Design relation extraction approach:
          * Option 1: Rule-based with regex patterns
          * Option 2: LLM-based extraction (GPT/Claude API)
          * Option 3: Fine-tuned transformer model
      - Decide based on accuracy needs & budget
  
  - Day 3-5:
      - Implement relation_extractor.py:
          * Input: text + List[Entity]
          * Output: List[Relation(source, type, target, confidence)]
          * Relation types: THUOC_KHOA, DIEU_KIEN, AP_DUNG_CHO, etc.

Week 4:
  - Day 1-3:
      - Entity resolution & linking:
          * "CNTT" = "Công nghệ thông tin" = "Khoa CNTT"
          * "IT001" = "Nhập môn lập trình"
      - Create entity_linker.py
  
  - Day 4-5:
      - Integration test với Team A's Graph Builder
      - End-to-end test: Document → Entities → Relations → Graph
      - Performance measurement
      - PR review & documentation
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── relation_extractor.py             # NEW
│   ├── relation_patterns.py              # NEW
│   └── entity_linker.py                  # NEW
└── tests/
    ├── test_relation_extraction.py       # NEW
    └── fixtures/
        └── relation_test_data.json       # NEW
```

---

## 📅 PHASE 2: Graph-Enhanced Retrieval (Tuần 5-12)

### **🔵 TEAM A - Nhiệm vụ Phase 2**

#### **Sprint 2.1: Graph Query Service (Tuần 5-7)**

**Deliverables:**
- [ ] Graph traversal algorithms
- [ ] Cypher query templates
- [ ] Graph search API
- [ ] Performance optimization

**Chi tiết công việc:**

```yaml
Week 5-6:
  - Implement graph_query_service.py:
      * find_related_entities(entity_id, max_depth=2)
      * get_shortest_path(source, target)
      * find_all_paths(source, target, max_length=5)
      * subgraph_search(entity_ids, expand_depth=1)
  
  - Create Cypher template library:
      * Template: Find prerequisites for course
      * Template: Get regulations for student cohort
      * Template: Find related documents by faculty

Week 7:
  - Performance optimization:
      * Add Neo4j indexes on frequently queried properties
      * Implement query result caching (Redis)
      * Batch query optimization
  
  - API endpoint implementation:
      * POST /v1/graph/search
      * POST /v1/graph/traverse
      * GET /v1/graph/entity/{id}
```

**Files to create:**
```
services/rag_services/
├── core/
│   └── domain/
│       └── graph_query_service.py        # NEW
├── adapters/
│   ├── graph_cache_adapter.py            # NEW (Redis)
│   └── cypher_templates.py               # NEW
└── app/
    └── api/
        └── v1/
            └── graph_routes.py           # NEW
```

#### **Sprint 2.2: Hybrid Storage Integration (Tuần 8-10)**

**Deliverables:**
- [ ] Graph + Vector unified interface
- [ ] Cross-database query coordination
- [ ] Result fusion strategies
- [ ] Consistency management

**Chi tiết công việc:**

```yaml
Week 8:
  - Design unified search interface:
      * HybridSearchService class
      * Coordinate Graph + Vector + BM25 queries
      * Handle partial failures gracefully
  
  - Implement result fusion:
      * Merge results from multiple sources
      * Deduplicate by doc_id
      * Preserve provenance metadata

Week 9-10:
  - Create graph_vector_sync_service.py:
      * Ensure doc_id consistency across databases
      * Update graph when documents change
      * Cascade delete operations
  
  - Implement hybrid_search_adapter.py:
      * Parallel query execution
      * Timeout handling
      * Result ranking pipeline
  
  - Testing & validation:
      * Test 1000+ queries
      * Compare with baseline (no graph)
      * Measure latency impact
```

**Files to create:**
```
services/rag_services/
├── adapters/
│   ├── hybrid_search_adapter.py          # NEW
│   └── graph_vector_sync_service.py      # NEW
├── core/
│   └── domain/
│       └── unified_search_service.py     # NEW
└── tests/
    └── test_hybrid_search.py             # NEW
```

#### **Sprint 2.3: Infrastructure & Monitoring (Tuần 11-12)**

**Deliverables:**
- [ ] Monitoring dashboards
- [ ] Performance metrics collection
- [ ] Alerting system
- [ ] Auto-scaling configuration

**Chi tiết công việc:**

```yaml
Week 11:
  - Setup Prometheus + Grafana:
      * Neo4j metrics (query latency, node count)
      * Graph query performance
      * Cache hit rates
  
  - Create monitoring dashboards:
      * Graph database health
      * Query performance over time
      * Error rates & types

Week 12:
  - Implement health checks:
      * Neo4j connectivity
      * Graph data quality checks
      * Automated alerts for issues
  
  - Load testing:
      * Simulate 100 concurrent users
      * Identify bottlenecks
      * Optimize resource allocation
  
  - Documentation:
      * Operations manual
      * Troubleshooting guide
      * Runbook for common issues
```

**Files to create:**
```
services/rag_services/
├── docker/
│   └── docker-compose.monitoring.yml     # NEW
├── monitoring/
│   ├── prometheus.yml                    # NEW
│   ├── grafana/
│   │   └── dashboards/
│   │       └── graphrag_dashboard.json   # NEW
│   └── health_checks.py                  # NEW
└── docs/
    └── OPERATIONS_MANUAL.md              # NEW
```

---

### **🟢 TEAM B - Nhiệm vụ Phase 2**

#### **Sprint 2.1: Graph-Aware Reranking (Tuần 5-7)**

**Deliverables:**
- [ ] Graph relevance scoring
- [ ] Multi-signal reranking algorithm
- [ ] Integration với existing reranker
- [ ] A/B testing framework

**Chi tiết công việc:**

```yaml
Week 5:
  - Design graph relevance metrics:
      * Metric 1: Is result in query entity subgraph?
      * Metric 2: Graph distance from query entities
      * Metric 3: Entity overlap score
      * Metric 4: Relation path confidence
  
  - Implement graph_relevance_scorer.py:
      * Input: SearchResult + QueryEntities + Graph
      * Output: GraphRelevanceScore(0.0-1.0)

Week 6-7:
  - Create GraphAwareReranker:
      * Combine CrossEncoder + GraphRelevance + PathDistance
      * Formula: α·semantic + β·graph + γ·path
      * Tune α, β, γ weights using validation set
  
  - Integration:
      * Extend existing CrossEncoderRerankingService
      * Add graph_aware_rerank() method
      * Backward compatible with non-graph mode
  
  - A/B testing setup:
      * Create test query sets (200 queries)
      * Measure before/after metrics
      * Statistical significance testing
```

**Files to create:**
```
services/rag_services/
├── adapters/
│   ├── graph_aware_reranker.py           # NEW
│   └── graph_relevance_scorer.py         # NEW
├── core/
│   └── domain/
│       └── multi_signal_ranking.py       # NEW
└── tests/
    ├── test_graph_reranking.py           # NEW
    └── fixtures/
        └── reranking_test_queries.json   # NEW
```

#### **Sprint 2.2: Query Understanding & Expansion (Tuần 8-10)**

**Deliverables:**
- [ ] Query entity extraction
- [ ] Graph-based query expansion
- [ ] Semantic query rewriting
- [ ] Context-aware search

**Chi tiết công việc:**

```yaml
Week 8:
  - Implement query_analyzer.py:
      * Extract entities from user query
      * Classify query intent (factual, procedural, etc.)
      * Identify query complexity (single-hop vs multi-hop)
  
  - Create graph_query_expander.py:
      * Find synonyms from graph
      * Expand with related entities
      * Example: "CNTT" → add "Công nghệ thông tin", "Khoa CNTT"

Week 9:
  - Implement multi_hop_query_handler.py:
      * Detect multi-hop queries
      * Decompose into sub-queries
      * Execute graph traversal
      * Combine results
  
  - Example query: "Điều kiện tốt nghiệp và môn tiên quyết của CNTT"
      * Sub-query 1: Điều kiện tốt nghiệp CNTT (graph)
      * Sub-query 2: Môn tiên quyết (graph traversal)
      * Combine & rank results

Week 10:
  - Context-aware search:
      * Maintain conversation context
      * Resolve pronouns & references
      * Example: "Thế còn ngành KHMT?" (refers to previous query)
  
  - Integration testing:
      * Test 50 complex queries
      * Validate answer quality
      * Compare with baseline
```

**Files to create:**
```
services/rag_services/
├── core/
│   └── domain/
│       ├── query_analyzer.py             # NEW
│       ├── graph_query_expander.py       # NEW
│       └── multi_hop_query_handler.py    # NEW
└── tests/
    ├── test_query_understanding.py       # NEW
    └── fixtures/
        └── complex_queries.json          # NEW
```

#### **Sprint 2.3: Enhanced Search Service (Tuần 11-12)**

**Deliverables:**
- [ ] GraphRAG search pipeline
- [ ] Fallback strategies
- [ ] Result explanation generation
- [ ] Performance benchmarking

**Chi tiết công việc:**

```yaml
Week 11:
  - Implement GraphRAGSearchService:
      * Stage 1: Query understanding (entities, intent)
      * Stage 2: Parallel retrieval (graph + vector + BM25)
      * Stage 3: Result fusion & deduplication
      * Stage 4: Graph-aware reranking
      * Stage 5: Context enrichment
  
  - Add fallback mechanisms:
      * If graph query fails → fallback to vector only
      * If no entities found → skip graph traversal
      * Graceful degradation

Week 12:
  - Result explanation:
      * Why this result is relevant?
      * Graph path visualization data
      * Entity highlighting in results
  
  - Benchmarking:
      * Create test suite: 500 queries
      * Metrics: Precision@K, Recall@K, MRR, NDCG
      * Compare GraphRAG vs Baseline RAG
      * Document improvements
  
  - Integration with Orchestrator:
      * Update RAG adapter in orchestrator service
      * Test multi-agent flow
      * End-to-end validation
```

**Files to create:**
```
services/rag_services/
├── core/
│   └── domain/
│       ├── graphrag_search_service.py    # NEW
│       └── result_explainer.py           # NEW
├── tests/
│   ├── test_graphrag_pipeline.py         # NEW
│   └── benchmarks/
│       ├── benchmark_suite.py            # NEW
│       └── test_queries_500.json         # NEW
└── docs/
    └── GRAPHRAG_PERFORMANCE.md           # NEW
```

---

## 📅 PHASE 3: Auto Graph Construction (Tuần 13-18)

### **🔵 TEAM A - Nhiệm vụ Phase 3**

#### **Sprint 3.1: Incremental Graph Updates (Tuần 13-15)**

**Deliverables:**
- [ ] Real-time document ingestion
- [ ] Incremental graph update pipeline
- [ ] Conflict resolution strategies
- [ ] Version control for graph data

**Chi tiết công việc:**

```yaml
Week 13:
  - Design incremental update architecture:
      * Event-driven updates (document added/modified/deleted)
      * Message queue (RabbitMQ or Redis Streams)
      * Worker pool for processing
  
  - Implement document_change_detector.py:
      * Watch data directories
      * Detect new/modified files
      * Emit update events

Week 14-15:
  - Create incremental_graph_updater.py:
      * Process update events
      * Extract new entities/relations
      * Merge with existing graph
      * Handle conflicts (same entity, different attributes)
  
  - Implement graph versioning:
      * Track graph schema version
      * Support rollback to previous state
      * Audit log for all changes
  
  - Testing:
      * Simulate 1000 document updates
      * Validate graph consistency
      * Performance under load
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── incremental_graph_updater.py      # NEW
│   ├── document_change_detector.py       # NEW
│   └── graph_version_manager.py          # NEW
├── infrastructure/
│   └── messaging/
│       └── update_queue.py               # NEW
└── tests/
    └── test_incremental_updates.py       # NEW
```

#### **Sprint 3.2: Graph Quality Assurance (Tuần 16-18)**

**Deliverables:**
- [ ] Automated graph validation
- [ ] Data quality metrics
- [ ] Anomaly detection
- [ ] Cleanup & maintenance tools

**Chi tiết công việc:**

```yaml
Week 16:
  - Implement graph_validator.py:
      * Check for orphaned nodes
      * Validate relationship integrity
      * Detect duplicate entities
      * Find missing required properties
  
  - Create quality metrics dashboard:
      * Entity count by type
      * Relationship distribution
      * Graph connectivity metrics
      * Data completeness scores

Week 17:
  - Anomaly detection:
      * Detect unusual patterns
      * Find inconsistent data
      * Alert on quality degradation
  
  - Implement graph_cleanup_service.py:
      * Merge duplicate entities
      * Remove orphaned nodes
      * Fix broken relationships
      * Normalize entity names

Week 18:
  - Maintenance automation:
      * Scheduled quality checks
      * Auto-cleanup tasks
      * Generate quality reports
  
  - Documentation:
      * Graph maintenance guide
      * Quality standards document
      * Troubleshooting procedures
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── graph_validator.py                # NEW
│   ├── graph_cleanup_service.py          # NEW
│   └── quality_metrics.py                # NEW
├── monitoring/
│   └── grafana/
│       └── dashboards/
│           └── graph_quality.json        # NEW
└── docs/
    └── GRAPH_QUALITY_STANDARDS.md        # NEW
```

---

### **🟢 TEAM B - Nhiệm vụ Phase 3**

#### **Sprint 3.1: Advanced Entity Resolution (Tuần 13-15)**

**Deliverables:**
- [ ] Entity deduplication
- [ ] Fuzzy matching algorithms
- [ ] Entity merging strategies
- [ ] Cross-document entity linking

**Chi tiết công việc:**

```yaml
Week 13:
  - Implement entity_deduplicator.py:
      * String similarity (Levenshtein, Jaro-Winkler)
      * Phonetic matching for Vietnamese
      * Embedding-based similarity
  
  - Create entity matching rules:
      * "CNTT" = "Công nghệ thông tin"
      * "IT001" = "Nhập môn lập trình" = "NMLT"
      * Handle abbreviations & variations

Week 14-15:
  - Cross-document entity linking:
      * Link same entities across multiple docs
      * Build entity co-reference chains
      * Update graph with merged entities
  
  - Implement entity_merger.py:
      * Merge entity attributes
      * Preserve provenance (which doc mentioned it)
      * Handle conflicting information
  
  - Validation:
      * Test on 500 documents
      * Measure precision/recall of entity linking
      * Manual review of sample merges
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── entity_deduplicator.py            # NEW
│   ├── entity_merger.py                  # NEW
│   └── entity_similarity.py              # NEW
└── tests/
    └── test_entity_resolution.py         # NEW
```

#### **Sprint 3.2: LLM-Powered Graph Enrichment (Tuần 16-18)**

**Deliverables:**
- [ ] LLM-based relation extraction
- [ ] Attribute inference
- [ ] Missing data completion
- [ ] Graph quality improvement

**Chi tiết công việc:**

```yaml
Week 16:
  - Setup LLM integration:
      * OpenRouter API or self-hosted LLM
      * Prompt engineering for Vietnamese
      * Batch processing for cost efficiency
  
  - Implement llm_relation_extractor.py:
      * Extract complex relations LLMs can understand
      * Example: "Điều kiện", "Yêu cầu", "Quy định áp dụng"
      * Validate LLM outputs

Week 17:
  - Attribute inference:
      * Infer missing entity attributes using LLM
      * Example: Extract year from document content
      * Fill in entity descriptions
  
  - Create graph_enrichment_service.py:
      * Identify incomplete entities
      * Use LLM to enrich data
      * Validate & merge enrichments

Week 18:
  - Quality improvement loop:
      * Identify low-confidence entities/relations
      * Use LLM to re-extract or validate
      * Human-in-the-loop for corrections
  
  - Performance optimization:
      * Batch LLM requests
      * Cache LLM responses
      * Cost monitoring & limits
  
  - Evaluation:
      * Compare LLM vs rule-based extraction
      * Measure accuracy improvements
      * Cost-benefit analysis
```

**Files to create:**
```
services/rag_services/
├── indexing/
│   ├── llm_relation_extractor.py         # NEW
│   ├── llm_attribute_inferrer.py         # NEW
│   └── graph_enrichment_service.py       # NEW
├── core/
│   └── ports/
│       └── llm_service.py                # NEW
└── tests/
    └── test_llm_enrichment.py            # NEW
```

---

## 📅 PHASE 4: Production Deployment (Tuần 19-24)

### **🔵 TEAM A - Nhiệm vụ Phase 4**

#### **Sprint 4.1: Production Infrastructure (Tuần 19-21)**

**Deliverables:**
- [ ] Production-ready Docker setup
- [ ] Kubernetes deployment configs
- [ ] High availability configuration
- [ ] Backup & disaster recovery

**Chi tiết công việc:**

```yaml
Week 19:
  - Production Docker images:
      * Multi-stage builds for smaller images
      * Security scanning
      * Optimized for performance
  
  - Kubernetes manifests:
      * Deployments for all services
      * Services & Ingress
      * ConfigMaps & Secrets
      * PersistentVolumeClaims

Week 20:
  - High availability setup:
      * Neo4j clustering (3-5 nodes)
      * Load balancing
      * Auto-scaling rules
      * Health checks & readiness probes
  
  - Implement circuit breakers:
      * Graceful degradation
      * Retry logic with backoff
      * Failover mechanisms

Week 21:
  - Backup strategy:
      * Automated daily Neo4j backups
      * Point-in-time recovery
      * Backup verification tests
  
  - Disaster recovery:
      * DR runbook
      * Failover procedures
      * Recovery time objectives (RTO)
      * Recovery point objectives (RPO)
```

**Files to create:**
```
services/rag_services/
├── docker/
│   ├── Dockerfile.production             # NEW
│   └── docker-compose.production.yml     # NEW
├── k8s/
│   ├── deployments/
│   │   ├── neo4j-statefulset.yaml       # NEW
│   │   ├── rag-service-deployment.yaml  # NEW
│   │   └── orchestrator-deployment.yaml # NEW
│   ├── services/
│   │   └── *.yaml                       # NEW
│   ├── configmaps/
│   │   └── *.yaml                       # NEW
│   └── ingress/
│       └── ingress.yaml                 # NEW
└── docs/
    ├── DEPLOYMENT_GUIDE.md              # NEW
    └── DISASTER_RECOVERY.md             # NEW
```

#### **Sprint 4.2: Performance Optimization (Tuần 22-24)**

**Deliverables:**
- [ ] Query optimization
- [ ] Caching strategies
- [ ] Resource tuning
- [ ] Load testing results

**Chi tiết công việc:**

```yaml
Week 22:
  - Query optimization:
      * Analyze slow Cypher queries
      * Add appropriate indexes
      * Rewrite inefficient queries
      * Query plan analysis
  
  - Caching implementation:
      * Multi-level caching (Redis)
      * Query result cache
      * Entity/relation cache
      * Cache invalidation strategy

Week 23:
  - Resource tuning:
      * Neo4j memory configuration
      * JVM tuning
      * Database connection pools
      * Thread pool optimization
  
  - Load testing:
      * Simulate production load
      * Identify bottlenecks
      * Stress test failure scenarios
      * Document performance characteristics

Week 24:
  - Final optimization:
      * Apply lessons from load testing
      * Fine-tune all parameters
      * Create performance baselines
  
  - Launch preparation:
      * Production checklist
      * Monitoring setup verification
      * Alert configuration
      * On-call procedures
```

**Files to create:**
```
services/rag_services/
├── config/
│   ├── neo4j.production.conf             # NEW
│   └── cache_config.yaml                 # NEW
├── tests/
│   └── load_tests/
│       ├── locustfile.py                 # NEW
│       └── load_test_scenarios.py        # NEW
└── docs/
    ├── PERFORMANCE_TUNING.md             # NEW
    └── PRODUCTION_CHECKLIST.md           # NEW
```

---

### **🟢 TEAM B - Nhiệm vụ Phase 4**

#### **Sprint 4.1: Graph Visualization & UI (Tuần 19-21)**

**Deliverables:**
- [ ] Graph visualization API
- [ ] Interactive graph explorer
- [ ] Query result visualization
- [ ] Frontend integration

**Chi tiết công việc:**

```yaml
Week 19:
  - Implement graph_visualization_service.py:
      * Generate graph data for visualization
      * Format: Nodes + Edges JSON
      * Support filtering & sampling
  
  - API endpoints:
      * GET /v1/graph/visualize/{entity_id}
      * POST /v1/graph/subgraph
      * GET /v1/graph/stats

Week 20-21:
  - Frontend integration:
      * Add Graph View component to frontend
      * Use D3.js or Cytoscape.js
      * Interactive features:
          - Click to expand nodes
          - Filter by node type
          - Highlight paths
          - Export to PNG/SVG
  
  - Search result enhancements:
      * Show entity tags in results
      * Display graph paths inline
      * "Why this result?" explanation
      * Related entities sidebar
```

**Files to create:**
```
services/rag_services/
├── adapters/
│   └── graph_visualization_service.py    # NEW
├── app/
│   └── api/
│       └── v1/
│           └── visualization_routes.py   # NEW
└── frontend/
    └── src/
        └── components/
            ├── GraphVisualization.jsx    # NEW
            ├── EntityHighlight.jsx       # NEW
            └── ResultExplanation.jsx     # NEW
```

#### **Sprint 4.2: Evaluation & Documentation (Tuần 22-24)**

**Deliverables:**
- [ ] Comprehensive evaluation
- [ ] User documentation
- [ ] API documentation
- [ ] Training materials

**Chi tiết công việc:**

```yaml
Week 22:
  - System evaluation:
      * Create gold standard dataset (200 Q&A pairs)
      * Measure GraphRAG vs Baseline:
          - Precision@1,3,5,10
          - Recall@10
          - MRR
          - NDCG
          - Answer correctness
      * Statistical significance tests
  
  - Prepare evaluation report:
      * Quantitative results
      * Qualitative analysis
      * Error analysis
      * Improvement recommendations

Week 23:
  - Documentation:
      * User guide: How to use GraphRAG features
      * API reference: All endpoints documented
      * Developer guide: Architecture & codebase
      * Admin guide: Operations & maintenance
  
  - Create tutorials:
      * Getting started with GraphRAG
      * Advanced query techniques
      * Troubleshooting common issues
      * Best practices

Week 24:
  - Knowledge transfer:
      * Team training sessions
      * Demo presentations
      * Q&A documentation
      * Handoff materials
  
  - Launch preparation:
      * Beta testing with select users
      * Gather feedback
      * Final bug fixes
      * Release notes
```

**Files to create:**
```
services/rag_services/
├── tests/
│   └── evaluation/
│       ├── gold_standard_qa.json         # NEW
│       ├── evaluation_suite.py           # NEW
│       └── evaluation_report.md          # NEW
└── docs/
    ├── USER_GUIDE.md                     # NEW
    ├── API_REFERENCE.md                  # NEW
    ├── DEVELOPER_GUIDE.md                # NEW
    ├── ADMIN_GUIDE.md                    # NEW
    ├── TUTORIALS.md                      # NEW
    └── RELEASE_NOTES.md                  # NEW
```

---

## 📊 Deliverables Summary

### **Code Deliverables**

**Team A (Infrastructure):**
- 25+ Python modules
- 15+ configuration files
- 10+ Docker/K8s manifests
- 8+ database scripts

**Team B (NLP/ML):**
- 20+ Python modules
- 3+ Frontend components
- 15+ test suites
- 5+ evaluation datasets

### **Documentation Deliverables**

- 12+ Technical documentation files
- 5+ Runbooks & guides
- 10+ Test reports
- 1 Comprehensive evaluation report

---

## 🎯 Success Metrics

### **Technical Metrics**

```
Graph Coverage:
├─ Entities indexed: > 5,000 nodes
├─ Relationships: > 10,000 edges
└─ Documents in graph: > 1,000

Performance:
├─ Graph query latency: < 100ms (p95)
├─ End-to-end search: < 500ms (p95)
└─ Throughput: > 100 queries/sec

Quality:
├─ Entity extraction F1: > 0.85
├─ Relation extraction F1: > 0.75
└─ Graph consistency: > 95%

Retrieval Accuracy:
├─ Precision@5: 84% → 92% (+8%)
├─ Recall@10: 78% → 88% (+10%)
├─ MRR: 0.72 → 0.85 (+18%)
└─ NDCG@10: 0.78 → 0.88 (+13%)
```

### **Business Metrics**

```
User Satisfaction:
├─ Answer correctness: +20%
├─ Response completeness: +25%
└─ User trust score: +15%

System Reliability:
├─ Uptime: > 99.5%
├─ Error rate: < 0.1%
└─ Mean time to recovery: < 15 min
```

---

## 🚀 Risk Mitigation

### **Technical Risks**

| Risk | Impact | Mitigation | Owner |
|------|--------|------------|-------|
| Neo4j performance issues | High | Load testing early, optimize queries, add caching | Team A |
| Entity extraction accuracy low | High | Use multiple models, LLM fallback, human validation | Team B |
| Graph data quality poor | Medium | Automated validation, cleanup tools, monitoring | Team A |
| Integration complexity | Medium | Incremental integration, extensive testing | Both |
| LLM API costs high | Medium | Batch processing, caching, cost monitoring | Team B |

### **Project Risks**

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep | High | Strict sprint planning, change control process |
| Resource unavailability | Medium | Cross-training, documentation, backup resources |
| Timeline delays | Medium | Buffer time in schedule, weekly progress reviews |
| Knowledge silos | Low | Code reviews, pair programming, documentation |

---

## 📅 Milestones & Checkpoints

```
Month 1 (Week 1-4):
├─ Checkpoint 1.1: Neo4j setup complete ✓
├─ Checkpoint 1.2: Entity extraction working ✓
└─ Demo: Show 100 entities in graph

Month 2 (Week 5-8):
├─ Checkpoint 2.1: Graph query API live ✓
├─ Checkpoint 2.2: Graph-aware reranking ✓
└─ Demo: Compare GraphRAG vs Baseline on 50 queries

Month 3 (Week 9-12):
├─ Checkpoint 3.1: Hybrid search integrated ✓
├─ Checkpoint 3.2: Monitoring dashboard ✓
└─ Demo: Full pipeline with 200+ queries

Month 4 (Week 13-16):
├─ Checkpoint 4.1: Incremental updates working ✓
├─ Checkpoint 4.2: LLM enrichment pipeline ✓
└─ Demo: 1000+ documents in graph

Month 5 (Week 17-20):
├─ Checkpoint 5.1: Production deployment ready ✓
├─ Checkpoint 5.2: Graph visualization UI ✓
└─ Demo: Beta release to select users

Month 6 (Week 21-24):
├─ Checkpoint 6.1: Performance optimized ✓
├─ Checkpoint 6.2: Documentation complete ✓
└─ **LAUNCH: GraphRAG v1.0** 🚀
```

---

## 🛠️ Tools & Technologies

### **Required Tools**

```yaml
Databases:
  - Neo4j 5.15+ (Community or Enterprise)
  - Weaviate 1.24+ (Vector DB)
  - OpenSearch 2.x (Keyword search)
  - Redis 7.x (Caching)

NLP/ML:
  - PhoBERT or XLM-RoBERTa (NER)
  - Sentence Transformers (Embeddings)
  - Cross-Encoder models (Reranking)
  - OpenRouter API or self-hosted LLM

Development:
  - Python 3.11+
  - Docker & Docker Compose
  - Kubernetes 1.28+
  - Git & GitHub

Monitoring:
  - Prometheus
  - Grafana
  - ELK Stack (optional)

Testing:
  - pytest
  - locust (load testing)
  - coverage.py
```

### **Python Libraries**

```txt
# Graph & Knowledge
neo4j==5.15.0
networkx==3.2.1
node2vec==0.4.6

# NLP - Vietnamese
underthesea==6.7.0
vncorenlp==1.0.3
py_vncorenlp

# NLP - General
transformers==4.36.0
sentence-transformers==2.3.0
spacy==3.7.0

# LlamaIndex
llama-index==0.9.48
llama-index-graph-stores-neo4j==0.2.0

# ML
scikit-learn==1.4.0
numpy==1.26.0
pandas==2.1.0

# API & Services
fastapi==0.108.0
uvicorn==0.25.0
pydantic==2.5.0
redis==5.0.0
```

---

## 📚 Learning Resources for Teams

### **For Team A**

- Neo4j Graph Academy (free courses)
- Cypher Query Language documentation
- Kubernetes documentation
- Docker best practices
- System design patterns

### **For Team B**

- Vietnamese NLP resources (VnCoreNLP docs)
- PhoBERT paper & implementation
- LlamaIndex documentation
- Cross-encoder training guides
- Evaluation metrics (MRR, NDCG)

---

## 🤝 Communication & Collaboration

### **Daily Standups**
- Time: 9:00 AM
- Duration: 15 minutes
- Format: What did you do? What will you do? Any blockers?

### **Weekly Sync**
- Time: Friday 3:00 PM
- Duration: 1 hour
- Agenda: Demo progress, discuss issues, plan next week

### **Sprint Planning**
- Every 2 weeks
- Duration: 2 hours
- Participants: Both teams + stakeholders

### **Code Reviews**
- All PRs require 1 approval from same team + 1 from other team
- Review SLA: 24 hours
- Use PR templates

### **Documentation**
- Update docs with code changes
- Weekly documentation review
- Maintain changelog

---

## 📞 Contact & Escalation

**Team A Lead:**
- Responsibilities: Infrastructure, Graph DB, DevOps
- Escalation path: CTO → Tech Lead

**Team B Lead:**
- Responsibilities: NLP, ML, Search Quality
- Escalation path: ML Lead → CTO

**Cross-team Issues:**
- Daily standup for immediate issues
- Slack channel: #graphrag-project
- Email: graphrag-team@uit.edu.vn

---

## ✅ Definition of Done

A feature is "Done" when:
- [ ] Code is written and passes all tests
- [ ] Unit tests coverage > 80%
- [ ] Integration tests pass
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] Demo prepared
- [ ] Performance benchmarked
- [ ] Deployed to staging
- [ ] Stakeholder approval received

---

**Document Version:** 1.0  
**Last Updated:** November 13, 2025  
**Owner:** GraphRAG Project Team  
**Status:** Active Planning

