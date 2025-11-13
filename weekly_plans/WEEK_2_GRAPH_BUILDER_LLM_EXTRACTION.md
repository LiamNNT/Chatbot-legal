# Week 2: Graph Builder Service & LLM-Guided Extraction

**Duration:** Week 2 (Nov 20-26, 2025)  
**Phase:** Core Development  
**Objective:** Build graph population service, implement LLM-guided entity/relation extraction

---

## 🎯 Week Goals

### Team A (Graph Builder Service)
- 🔨 Implement Graph Builder service with batch operations
- 🔨 Create ETL pipeline: Documents → Graph nodes
- 🔨 Query optimizer for complex traversals
- 🔨 Graph versioning and migration tools
- 🔨 Monitoring and health checks

### Team B (LLM-Guided Extraction)
- 🤖 Implement LLM-guided relation extraction (CatRAG Principle #2)
- 🤖 Entity resolution and deduplication
- 🤖 Confidence scoring for extracted entities
- 🤖 Prompt engineering for Vietnamese academic text
- 🤖 Validation pipeline

### Integration Goal
- **Friday:** Graph population pipeline: Text → LLM extraction → Graph Builder → Neo4j

---

## 📋 Detailed Tasks

### **Team A: Graph Builder Service**

#### Task A1: Graph Builder Core Service (Monday-Tuesday - 10h)
**Owner:** Senior Backend Developer  
**Priority:** P0 (Critical)

**Architecture:**
```
GraphBuilderService
├── EntityProcessor (validates & transforms entities)
├── RelationshipProcessor (creates relationships)
├── BatchProcessor (handles large-scale operations)
└── ConflictResolver (handles duplicates)
```

**Implementation:**

```python
# services/rag_services/core/services/graph_builder_service.py

class GraphBuilderService:
    """Service for building and populating knowledge graph"""
    
    def __init__(
        self,
        graph_repo: GraphRepository,
        entity_extractor: CategoryGuidedEntityExtractor,
        config: GraphBuilderConfig
    ):
        self.graph_repo = graph_repo
        self.entity_extractor = entity_extractor
        self.config = config
        self.batch_size = config.batch_size
    
    async def build_from_documents(
        self,
        documents: List[Document],
        category_hints: Optional[List[NodeCategory]] = None
    ) -> GraphBuildResult:
        """Build graph from document collection"""
        
        results = GraphBuildResult()
        
        # Phase 1: Extract all entities
        all_entities = []
        for doc in documents:
            entities = self.entity_extractor.extract(
                doc.content,
                categories=category_hints
            )
            all_entities.extend(entities)
        
        # Phase 2: Deduplicate and resolve entities
        resolved_entities = await self._resolve_entities(all_entities)
        
        # Phase 3: Create nodes in batches
        node_ids = await self._batch_create_nodes(resolved_entities)
        results.created_nodes = len(node_ids)
        
        # Phase 4: Extract and create relationships
        relationships = await self._extract_relationships(documents)
        rel_ids = await self._batch_create_relationships(relationships)
        results.created_relationships = len(rel_ids)
        
        return results
    
    async def _batch_create_nodes(
        self,
        entities: List[Entity],
        batch_size: int = 100
    ) -> List[str]:
        """Create nodes in batches for performance"""
        
        node_ids = []
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i+batch_size]
            
            # Convert entities to GraphNode objects
            nodes = [self._entity_to_node(e) for e in batch]
            
            # Batch insert
            batch_ids = await self.graph_repo.batch_add_nodes(nodes)
            node_ids.extend(batch_ids)
            
            # Progress tracking
            logger.info(f"Created {len(batch_ids)} nodes (batch {i//batch_size + 1})")
        
        return node_ids
    
    async def _resolve_entities(
        self,
        entities: List[Entity]
    ) -> List[Entity]:
        """Deduplicate and resolve entity references"""
        
        # Group by category and normalize
        grouped = defaultdict(list)
        for entity in entities:
            key = self._entity_key(entity)
            grouped[key].append(entity)
        
        # Merge duplicates
        resolved = []
        for key, group in grouped.items():
            merged = self._merge_entity_group(group)
            resolved.append(merged)
        
        return resolved
    
    async def _extract_relationships(
        self,
        documents: List[Document]
    ) -> List[Relationship]:
        """Extract relationships from documents (Week 2 stub)"""
        # TODO: Implement LLM-guided relation extraction
        pass
```

**Deliverables:**
- ✅ `core/services/graph_builder_service.py` (500+ lines)
- ✅ `core/services/graph_builder_config.py` (config dataclass)
- ✅ Unit tests with 85%+ coverage
- ✅ Integration test with Neo4j

**Acceptance Criteria:**
- [ ] Build graph from 100 documents successfully
- [ ] Batch operations: 10,000 nodes in <60s
- [ ] Deduplication reduces duplicates by >95%
- [ ] Memory usage: <500MB for 10k nodes

---

#### Task A2: ETL Pipeline Implementation (Tuesday-Wednesday - 8h)
**Owner:** Backend Developer  
**Priority:** P1

**Pipeline Stages:**

```python
# indexing/graph_etl_pipeline.py

class GraphETLPipeline:
    """ETL pipeline: Documents → Graph"""
    
    async def run(self, source_path: str) -> ETLResult:
        # Stage 1: Extract (Load documents)
        documents = await self._load_documents(source_path)
        
        # Stage 2: Transform (Extract entities, enrich)
        enriched = await self._transform_documents(documents)
        
        # Stage 3: Load (Build graph)
        result = await self.graph_builder.build_from_documents(enriched)
        
        return result
    
    async def _load_documents(self, source_path: str) -> List[Document]:
        """Load from various sources"""
        loaders = {
            '.pdf': PDFLoader(),
            '.docx': DocxLoader(),
            '.json': JSONLoader(),
            '.md': MarkdownLoader()
        }
        # ... loading logic
    
    async def _transform_documents(
        self,
        documents: List[Document]
    ) -> List[EnrichedDocument]:
        """Enrich documents with metadata and preprocessing"""
        
        enriched = []
        for doc in documents:
            # Preprocessing
            clean_text = self.preprocessor.clean(doc.content)
            
            # Extract metadata
            metadata = self._extract_metadata(doc)
            
            # Category detection
            categories = self._detect_categories(clean_text)
            
            enriched.append(EnrichedDocument(
                content=clean_text,
                metadata=metadata,
                detected_categories=categories,
                source=doc.source
            ))
        
        return enriched
```

**Data Sources:**
- `/data/crawled_programs/*.json` - Course programs
- `/data/quy_dinh/*.pdf` - Regulations
- `/data/docs/*.md` - Documentation

**Deliverables:**
- ✅ `indexing/graph_etl_pipeline.py`
- ✅ Source-specific loaders (PDF, DOCX, JSON, MD)
- ✅ ETL configuration: `config/etl_config.yaml`
- ✅ CLI tool: `scripts/run_etl.py`

**Acceptance Criteria:**
- [ ] Load 500+ documents without errors
- [ ] Handle all 4 file formats
- [ ] Progress tracking and logging
- [ ] Rollback on errors

---

#### Task A3: Query Optimizer (Wednesday-Thursday - 6h)
**Owner:** Senior Backend Developer  
**Priority:** P2

**Optimization Strategies:**

1. **Query Plan Analysis:**
   ```python
   async def explain_query(self, cypher: str) -> QueryPlan:
       """Analyze query execution plan"""
       result = await self.driver.execute_query(
           f"EXPLAIN {cypher}"
       )
       return self._parse_plan(result)
   ```

2. **Index Recommendations:**
   ```python
   def recommend_indexes(self, query_patterns: List[str]) -> List[str]:
       """Recommend indexes based on query patterns"""
       # Analyze common WHERE clauses
       # Suggest composite indexes
   ```

3. **Query Caching:**
   ```python
   @lru_cache(maxsize=1000)
   async def cached_query(self, cypher: str, params: dict) -> List[dict]:
       """Cache frequent queries"""
   ```

**Deliverables:**
- ✅ `adapters/graph/query_optimizer.py`
- ✅ Performance analysis tools
- ✅ Index recommendation report

**Acceptance Criteria:**
- [ ] Query performance improvement: >30%
- [ ] Cache hit rate: >60% on common queries
- [ ] Index recommendations validated

---

#### Task A4: Monitoring & Health Checks (Thursday-Friday - 4h)
**Owner:** DevOps + Backend Developer  
**Priority:** P2

**Monitoring Components:**

1. **Health Check Endpoint:**
   ```python
   @router.get("/graph/health")
   async def graph_health():
       return {
           "neo4j_connection": await check_neo4j(),
           "node_count": await get_node_count(),
           "relationship_count": await get_rel_count(),
           "index_status": await check_indexes()
       }
   ```

2. **Metrics Collection:**
   - Query latency (p50, p95, p99)
   - Node/relationship counts
   - Memory usage
   - Connection pool status

**Deliverables:**
- ✅ Health check endpoints
- ✅ Grafana dashboard config (optional)
- ✅ Alert rules for critical metrics

**Acceptance Criteria:**
- [ ] Health checks respond <100ms
- [ ] Metrics exported to Prometheus (optional)
- [ ] Dashboard shows real-time stats

---

### **Team B: LLM-Guided Extraction**

#### Task B1: LLM Relation Extraction (Monday-Wednesday - 12h)
**Owner:** ML Engineer + NLP Engineer  
**Priority:** P0 (Critical - CatRAG Principle #2)

**Concept:**
Use LLM to extract relationships between entities, guided by category schema.

**Prompt Engineering:**

```python
# indexing/llm_relation_extractor.py

class LLMRelationExtractor:
    """LLM-guided relation extraction for CatRAG"""
    
    RELATION_EXTRACTION_PROMPT = """
Bạn là chuyên gia phân tích văn bản học thuật của Đại học UIT.

**Danh mục quan hệ được phép:**
1. DIEU_KIEN_TIEN_QUYET: Môn học A yêu cầu hoàn thành môn B trước
2. DIEU_KIEN_SONG_HANH: Môn A và môn B phải học cùng kỳ
3. THUOC_CHUONG_TRINH: Môn học thuộc chương trình đào tạo
4. THUOC_KHOA: Môn học thuộc khoa
5. LIEN_QUAN: Môn học có nội dung liên quan

**Văn bản phân tích:**
{text}

**Nhiệm vụ:**
Trích xuất tất cả quan hệ từ văn bản trên theo định dạng JSON:
```json
[
  {
    "source_entity": "IT003",
    "source_category": "MON_HOC",
    "relation_type": "DIEU_KIEN_TIEN_QUYET",
    "target_entity": "IT002",
    "target_category": "MON_HOC",
    "confidence": 0.95,
    "evidence": "Văn bản gốc: 'Môn IT003 cần hoàn thành IT002 trước'"
  }
]
```

**Lưu ý:**
- Chỉ trích xuất quan hệ có confidence >= 0.7
- Phải cung cấp evidence từ văn bản gốc
- Sử dụng đúng category schema đã định nghĩa
"""
    
    async def extract_relations(
        self,
        text: str,
        entities: List[Entity],
        llm_client: LLMClient
    ) -> List[Relation]:
        """Extract relations using LLM"""
        
        # Build prompt with context
        prompt = self.RELATION_EXTRACTION_PROMPT.format(text=text)
        
        # Add entity context
        entity_context = self._build_entity_context(entities)
        prompt += f"\n\n**Entities đã phát hiện:**\n{entity_context}"
        
        # Call LLM
        response = await llm_client.complete(
            prompt=prompt,
            temperature=0.1,  # Low temp for deterministic extraction
            max_tokens=2000
        )
        
        # Parse JSON response
        relations = self._parse_llm_response(response)
        
        # Validate and filter
        validated = [r for r in relations if self._validate_relation(r)]
        
        return validated
    
    def _validate_relation(self, relation: Relation) -> bool:
        """Validate extracted relation"""
        checks = [
            relation.confidence >= 0.7,
            relation.relation_type in RelationshipType.__members__,
            relation.source_category in NodeCategory.__members__,
            relation.target_category in NodeCategory.__members__,
            len(relation.evidence) > 10
        ]
        return all(checks)
```

**LLM Providers:**
- **Primary:** OpenAI GPT-4 (via API)
- **Fallback:** Gemini Pro (Google)
- **Local option:** Llama 3 (via Ollama) for testing

**Deliverables:**
- ✅ `indexing/llm_relation_extractor.py` (400+ lines)
- ✅ Prompt templates: `config/prompts/relation_extraction.yaml`
- ✅ LLM client wrapper: `adapters/llm_client.py`
- ✅ Tests with mock LLM responses

**Acceptance Criteria:**
- [ ] Extract relations with precision > 0.85
- [ ] Extract relations with recall > 0.75
- [ ] Handle Vietnamese text correctly
- [ ] Cost: <$0.01 per document (GPT-4)

---

#### Task B2: Entity Resolution & Deduplication (Tuesday-Wednesday - 6h)
**Owner:** ML Engineer  
**Priority:** P1

**Entity Resolution Strategies:**

1. **Fuzzy Matching:**
   ```python
   from fuzzywuzzy import fuzz
   
   def are_same_entity(e1: Entity, e2: Entity) -> bool:
       if e1.category != e2.category:
           return False
       
       # Normalize text
       text1 = normalize_vietnamese(e1.text)
       text2 = normalize_vietnamese(e2.text)
       
       # Fuzzy match
       ratio = fuzz.ratio(text1, text2)
       return ratio >= 90  # 90% similarity threshold
   ```

2. **Embedding-based Similarity:**
   ```python
   async def compute_similarity(e1: Entity, e2: Entity) -> float:
       """Use PhoBERT embeddings for semantic similarity"""
       emb1 = await self.encoder.encode(e1.text)
       emb2 = await self.encoder.encode(e2.text)
       return cosine_similarity(emb1, emb2)
   ```

3. **Entity Linking:**
   ```python
   async def link_to_graph(self, entity: Entity) -> Optional[str]:
       """Link extracted entity to existing graph node"""
       candidates = await self.graph_repo.search_nodes(
           category=entity.category,
           text_query=entity.text
       )
       
       if candidates:
           best_match = max(candidates, key=lambda c: c.similarity)
           if best_match.similarity > 0.85:
               return best_match.node_id
       
       return None  # Create new node
   ```

**Deliverables:**
- ✅ `core/services/entity_resolver.py`
- ✅ Deduplication benchmarks
- ✅ Entity linking accuracy report

**Acceptance Criteria:**
- [ ] Deduplication accuracy > 95%
- [ ] False positive rate < 5%
- [ ] Processing: 1000 entities/second

---

#### Task B3: Confidence Scoring (Wednesday-Thursday - 4h)
**Owner:** ML Engineer  
**Priority:** P2

**Confidence Score Components:**

```python
class ConfidenceScorer:
    """Multi-factor confidence scoring for extractions"""
    
    def score_entity(self, entity: Entity, context: str) -> float:
        """Calculate confidence score for extracted entity"""
        
        scores = {
            'pattern_match': self._pattern_confidence(entity),
            'context_relevance': self._context_score(entity, context),
            'llm_confidence': entity.llm_confidence if hasattr(entity, 'llm_confidence') else 0.5,
            'frequency': self._frequency_score(entity),
        }
        
        # Weighted average
        weights = {
            'pattern_match': 0.3,
            'context_relevance': 0.3,
            'llm_confidence': 0.3,
            'frequency': 0.1
        }
        
        confidence = sum(scores[k] * weights[k] for k in scores)
        return min(confidence, 1.0)
    
    def score_relation(self, relation: Relation) -> float:
        """Calculate confidence for extracted relation"""
        
        factors = [
            relation.llm_confidence,
            self._evidence_quality(relation.evidence),
            self._entity_confidence(relation.source_entity),
            self._entity_confidence(relation.target_entity),
        ]
        
        return np.mean(factors)
```

**Deliverables:**
- ✅ `core/services/confidence_scorer.py`
- ✅ Calibration on validation set
- ✅ Confidence threshold recommendations

**Acceptance Criteria:**
- [ ] Well-calibrated (predicted vs actual confidence)
- [ ] Filters out low-quality extractions (threshold 0.7)

---

#### Task B4: Validation Pipeline (Thursday-Friday - 6h)
**Owner:** Both Teams  
**Priority:** P1

**Validation Steps:**

1. **Schema Validation:**
   ```python
   def validate_extraction_schema(result: ExtractionResult) -> ValidationReport:
       """Validate against CatRAG schema"""
       
       errors = []
       
       # Check entity categories
       for entity in result.entities:
           if entity.category not in NodeCategory:
               errors.append(f"Invalid category: {entity.category}")
       
       # Check relationship types
       for relation in result.relations:
           if relation.type not in RelationshipType:
               errors.append(f"Invalid relation: {relation.type}")
       
       return ValidationReport(errors=errors)
   ```

2. **Consistency Checks:**
   - No self-referencing relationships
   - Relationship types match entity categories
   - No duplicate entities

3. **Human-in-the-Loop Review:**
   - Flag low-confidence extractions (<0.7)
   - Review interface for corrections

**Deliverables:**
- ✅ `core/services/extraction_validator.py`
- ✅ Validation report generator
- ✅ Review interface (simple web UI - optional)

**Acceptance Criteria:**
- [ ] Catches 100% of schema violations
- [ ] False alarm rate < 10%
- [ ] Validation time: <100ms per extraction

---

## 🎬 Friday Integration Demo

### **Demo Flow:**

**1. ETL Pipeline (Team A):**
```bash
# Load sample documents
python scripts/run_etl.py \
  --source data/crawled_programs/cntt_curriculum.json \
  --mode full

# Show graph statistics
curl http://localhost:8000/graph/health
```

**2. LLM Extraction (Team B):**
```bash
# Extract from sample text
python scripts/demo_llm_extraction.py \
  --input "Môn IT003 - Cấu trúc dữ liệu cần hoàn thành IT002 và IT001 trước"

# Output: Relations with confidence scores
```

**3. Full Pipeline:**
```bash
# Text → LLM extraction → Entity resolution → Graph Builder → Neo4j
python scripts/demo_full_pipeline.py
```

---

## 📊 Success Metrics

### **Team A:**
- ✅ Graph Builder handles 10k+ nodes
- ✅ ETL pipeline processes 500+ documents
- ✅ Query performance improved 30%+
- ✅ Health monitoring operational

### **Team B:**
- ✅ LLM extraction precision > 0.85
- ✅ Entity resolution accuracy > 0.95
- ✅ Confidence calibration validated
- ✅ Validation pipeline catches errors

### **Integration:**
- ✅ E2E pipeline: Text → Graph
- ✅ Processing time: <1s per document
- ✅ Data quality > 90% accurate

---

## 🚧 Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM API costs | Use caching, batch requests, local fallback |
| Extraction quality | Prompt engineering, validation pipeline |
| Performance bottleneck | Async processing, batch operations |
| Schema drift | Version control for schema, migration tools |

---

## 🔜 Week 3 Preview

**Team A:** Router Agent implementation, intent classification  
**Team B:** Advanced query understanding, multi-hop reasoning  
**Integration:** CatRAG retrieval pipeline end-to-end

---

**Last Updated:** November 13, 2025  
**Status:** 📝 Ready for Week 2
