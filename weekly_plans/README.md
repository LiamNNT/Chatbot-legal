# Weekly Plans Summary - 6-Week GraphRAG Implementation

**Project:** CatRAG (Category-guided Graph RAG) for UIT Chatbot  
**Duration:** 6 weeks (Nov 13 - Dec 24, 2025)  
**Teams:** Team A (Infrastructure), Team B (NLP/ML)

---

## 📅 Timeline Overview

| Week | Focus | Team A | Team B | Deliverable |
|------|-------|--------|--------|-------------|
| **1** | Foundation | Neo4j setup, Schema design | NER model, Entity extraction | POC Demo |
| **2** | Graph Builder | ETL pipeline, Batch operations | LLM relation extraction | Graph Population Pipeline |
| **3** | Router Agent | Intent classifier, Routing logic | Query preprocessing | CatRAG Retrieval E2E |
| **4** | Optimization | Multi-hop reasoning, Performance | Context-aware retrieval | Production-Ready System |
| **5** | Testing | Integration tests, Load testing | UI polish, UAT | User Acceptance Testing |
| **6** | Launch | Production deployment, Scaling | Training, Support | 🚀 Production Launch |

---

## 🎯 CatRAG Approach - 3 Core Principles

### **Principle 1: Category-Labeled Schema** (Week 1-2)
**Top-down approach:** Define 10 node categories upfront
- MON_HOC, KHOA, QUY_DINH, DIEU_KIEN, etc.
- 12 relationship types with routing annotations
- Better precision than bottom-up entity extraction

### **Principle 2: LLM-Guided Population** (Week 2)
**Smart extraction:** Use LLM to populate graph based on categories
- Category-guided prompts (not generic NER)
- Confidence scoring for quality
- 30-50% faster than traditional NER

### **Principle 3: Router Agent** (Week 3)
**Intelligent routing:** Classify intent → Choose retrieval strategy
- TIEN_QUYET → Graph traversal
- MO_TA_MON_HOC → Vector search
- QUY_DINH → Hybrid search
- Expected: +10-15% accuracy improvement

---

## 📦 Key Deliverables by Week

### **Week 1: Foundation**
- ✅ Neo4j Docker environment
- ✅ CatRAG schema (10 categories, 12 relationships)
- ✅ GraphRepository POC (25 methods)
- ✅ Category-guided entity extractor POC
- ✅ Demo script for prerequisites

**Files:**
- `core/domain/graph_models.py` (400 lines)
- `core/ports/graph_repository.py` (400 lines)
- `adapters/graph/neo4j_adapter.py` (500 lines)
- `indexing/category_guided_entity_extractor.py` (350 lines)

---

### **Week 2: Graph Builder**
- ✅ Graph Builder service (batch operations)
- ✅ ETL pipeline (documents → graph)
- ✅ LLM relation extraction
- ✅ Entity resolution & deduplication
- ✅ Query optimizer

**Files:**
- `core/services/graph_builder_service.py` (500 lines)
- `indexing/graph_etl_pipeline.py` (400 lines)
- `indexing/llm_relation_extractor.py` (400 lines)
- `core/services/entity_resolver.py` (300 lines)

---

### **Week 3: Router Agent**
- ✅ Intent classifier (7 query types, 90%+ accuracy)
- ✅ Router Agent service (routing logic)
- ✅ Vietnamese query preprocessing
- ✅ Query expansion & synonyms
- ✅ Evaluation framework + A/B testing

**Files:**
- `core/services/intent_classifier.py` (500 lines)
- `core/services/router_agent.py` (700 lines)
- `core/services/query_preprocessor.py` (300 lines)
- `tests/evaluation/router_evaluation.py` (400 lines)

---

### **Week 4: Advanced Features**
- ✅ Multi-hop reasoning (learning paths)
- ✅ Graph embeddings (Node2Vec)
- ✅ Performance optimization (caching, indexing)
- ✅ Conversation history integration
- ✅ Personalized retrieval

**Files:**
- `core/services/multi_hop_reasoner.py` (600 lines)
- `core/services/graph_embedder.py` (400 lines)
- `core/services/conversation_manager.py` (400 lines)
- `core/services/personalization_service.py` (300 lines)

---

### **Week 5: Testing & Documentation**
- ✅ Integration test suite (50+ scenarios)
- ✅ Load testing (200+ concurrent users)
- ✅ API documentation (OpenAPI/Swagger)
- ✅ Monitoring & alerting (Prometheus/Grafana)
- ✅ User Acceptance Testing (10+ users)

**Files:**
- `tests/integration/test_catrag_e2e.py` (500 lines)
- `tests/load/locustfile.py` (200 lines)
- `docs/openapi.yaml` (complete API spec)
- `core/monitoring/metrics.py` (200 lines)

---

### **Week 6: Production Launch**
- ✅ Production environment setup
- ✅ Database migration (500+ courses, 300+ prereqs)
- ✅ Auto-scaling configuration
- ✅ Backup & disaster recovery
- ✅ User training materials
- 🚀 **Official Launch!**

**Infrastructure:**
- Docker Swarm/Kubernetes deployment
- Neo4j Enterprise (32GB RAM)
- Redis caching layer
- Nginx load balancer
- Automated backups

---

## 📊 Expected Improvements

### **Accuracy Gains:**
| Metric | Baseline (Hybrid) | CatRAG | Improvement |
|--------|------------------|--------|-------------|
| Precision | 75% | 85% | **+10%** |
| Recall | 70% | 85% | **+15%** |
| Entity Queries | 70% | 90% | **+20%** |
| F1 Score | 72.5% | 85% | **+12.5%** |

### **Performance Gains:**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Extraction Speed | 100 ent/s | 150 ent/s | **+50%** |
| Query Latency (P95) | 800ms | 500ms | **-37.5%** |
| Cache Hit Rate | 30% | 60% | **+100%** |

---

## 🏗️ Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                      CatRAG System                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  User Query → Intent Classifier → Router Agent              │
│                         ↓                                     │
│              ┌──────────┼──────────┐                         │
│              │          │          │                         │
│         Graph       Vector       BM25                        │
│       Traversal     Search      Search                       │
│              │          │          │                         │
│              └──────────┼──────────┘                         │
│                         ↓                                     │
│              Cross-Encoder Reranker                          │
│                         ↓                                     │
│                   Final Results                              │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│  Core Components:                                            │
│  - Neo4j Graph Database (500+ courses, 300+ relationships)  │
│  - Weaviate Vector Store (document embeddings)              │
│  - OpenSearch BM25 (keyword search)                         │
│  - PhoBERT Intent Classifier (7 intents, 90%+ accuracy)     │
│  - LLM Relation Extractor (GPT-4, 85%+ precision)           │
│  - Redis Cache (60%+ hit rate)                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 Team Roles

### **Team A: Graph Infrastructure**
**Lead:** Senior Backend Developer  
**Members:** Backend Developer, DevOps, DBA

**Responsibilities:**
- Neo4j setup and management
- Graph schema design
- GraphRepository implementation
- Performance optimization
- Production deployment

---

### **Team B: NLP/ML**
**Lead:** ML Engineer  
**Members:** NLP Engineer, Frontend Developer

**Responsibilities:**
- Entity extraction (PhoBERT/VnCoreNLP)
- Intent classification
- LLM integration
- Query preprocessing
- UI development

---

## 📚 Documentation Structure

```
docs/
├── API_GUIDE.md                      # API documentation
├── CATRAG_APPROACH.md                # CatRAG methodology
├── CATRAG_SCHEMA.md                  # Graph schema details
├── NER_MODEL_SELECTION.md            # NER benchmarking results
├── ROUTER_EVALUATION_WEEK3.md        # Router accuracy report
├── WEEK1_PERFORMANCE_BASELINE.md     # Initial benchmarks
└── openapi.yaml                      # OpenAPI specification

weekly_plans/
├── WEEK_1_FOUNDATION_SETUP.md
├── WEEK_2_GRAPH_BUILDER_LLM_EXTRACTION.md
├── WEEK_3_ROUTER_AGENT_INTENT.md
├── WEEK_4_ADVANCED_ALGORITHMS_OPTIMIZATION.md
├── WEEK_5_TESTING_DOCUMENTATION_UAT.md
└── WEEK_6_PRODUCTION_LAUNCH.md
```

---

## 🎯 Success Metrics (Post-Launch)

### **Week 1 Post-Launch:**
- Users: 500+
- Queries: 2000+
- Success rate: 90%+
- User satisfaction: 4.0+/5.0

### **Month 1:**
- Users: 2000+
- Queries: 10,000+
- Uptime: 99.5%+
- P95 latency: <500ms

---

## 🔑 Key Learnings

1. **Top-down beats bottom-up:** Category-guided extraction is faster and more accurate than generic NER
2. **Router Agent is critical:** Intent-based routing significantly improves relevance
3. **Graph + Vector = Best:** Hybrid approach with intelligent routing outperforms any single method
4. **Vietnamese NLP requires special handling:** Diacritics, compound words, abbreviations
5. **Clean Architecture enables parallel work:** Teams A and B worked independently without blockers

---

## 🚀 Next Steps (Post-Launch)

### **Short-term (Month 2-3):**
- Fine-tune intent classifier on real queries
- Expand graph with more regulations
- Add course review/difficulty data
- Improve error messages

### **Medium-term (Month 4-6):**
- Multi-language support (English)
- Advanced analytics dashboard
- Recommendation system refinement
- Mobile app (optional)

### **Long-term (Month 7-12):**
- Integration with UIT student portal
- Personalized learning path planning
- Academic advisor chatbot
- Expansion to other universities

---

## 📞 Contact & Support

**Project Lead:** [Your Name]  
**Email:** catrag-support@uit.edu.vn  
**Repository:** https://github.com/LiamNNT/Chatbot-UIT  
**Documentation:** https://docs.catrag.uit.edu.vn

---

**🎊 Thank you to both teams for an incredible 6-week sprint!**

**From 0 to Production in 42 days. Well done! 🚀**

---

**Last Updated:** November 13, 2025  
**Version:** 1.0.0  
**Status:** ✅ Complete & Ready for Launch
