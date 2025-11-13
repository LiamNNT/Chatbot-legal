# Week 3: Router Agent & Intent Classification (CatRAG Principle #3)

**Duration:** Week 3 (Nov 27 - Dec 3, 2025)  
**Phase:** Core Development - CatRAG Intelligence  
**Objective:** Implement Router Agent for intelligent query routing based on intent

---

## 🎯 Week Goals

### Team A (Router Agent Infrastructure)
- 🧠 Implement Router Agent service
- 🧠 Intent classification model (7 query types)
- 🧠 Routing decision logic with confidence thresholds
- 🧠 Fallback strategies for ambiguous queries
- 🧠 A/B testing framework for routing strategies

### Team B (Query Understanding)
- 🔍 Advanced query preprocessing for Vietnamese
- 🔍 Query expansion and synonym handling
- 🔍 Entity disambiguation in queries
- 🔍 Multi-intent query handling
- 🔍 Query reformulation for graph traversal

### Integration Goal
- **Friday:** CatRAG retrieval pipeline: Query → Router → Graph/Vector/Hybrid → Ranked Results

---

## 📋 Detailed Tasks

### **Team A: Router Agent Implementation**

#### Task A1: Intent Classifier Model (Monday-Tuesday - 10h)
**Owner:** ML Engineer + NLP Engineer  
**Priority:** P0 (Critical - CatRAG Core)

**Intent Categories (7 types):**

```python
class QueryIntent(Enum):
    """CatRAG query intent classification"""
    
    # Graph-routed intents
    TIEN_QUYET = "tien_quyet"              # Prerequisites: Use graph traversal
    DIEU_KIEN_HOC_TAP = "dieu_kien_hoc_tap"  # Requirements: Use graph + rules
    
    # Vector-routed intents
    MO_TA_MON_HOC = "mo_ta_mon_hoc"        # Course description: Use vector
    TIM_KIEM_NOI_DUNG = "tim_kiem_noi_dung"  # Content search: Use vector
    
    # Hybrid-routed intents
    QUY_DINH = "quy_dinh"                  # Regulations: Hybrid search
    THONG_TIN_KHOA = "thong_tin_khoa"      # Department info: Hybrid
    
    # Complex routing
    TU_VAN_HOC_TAP = "tu_van_hoc_tap"      # Academic advisory: Multi-strategy
```

**Model Architecture:**

```python
# core/services/intent_classifier.py

class IntentClassifier:
    """Classify user query intent for routing"""
    
    def __init__(self, model_type: str = "phobert"):
        if model_type == "phobert":
            self.model = self._load_phobert_classifier()
        elif model_type == "lightweight":
            self.model = self._load_fasttext_classifier()
    
    def _load_phobert_classifier(self):
        """PhoBERT-based classifier (high accuracy)"""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        
        model = AutoModelForSequenceClassification.from_pretrained(
            "vinai/phobert-base",
            num_labels=7  # 7 intent categories
        )
        tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
        
        return {"model": model, "tokenizer": tokenizer}
    
    async def classify(self, query: str) -> IntentPrediction:
        """Classify query intent with confidence"""
        
        # Preprocess Vietnamese query
        processed = self._preprocess_query(query)
        
        # Get model predictions
        logits = await self._get_model_predictions(processed)
        
        # Softmax for probabilities
        probs = softmax(logits)
        
        # Top intent
        top_idx = np.argmax(probs)
        top_intent = QueryIntent(list(QueryIntent)[top_idx].value)
        confidence = probs[top_idx]
        
        # Alternative intents (for multi-intent queries)
        alternatives = [
            (QueryIntent(list(QueryIntent)[i].value), probs[i])
            for i in np.argsort(probs)[-3:-1]  # Top 2 alternatives
            if probs[i] > 0.15  # Only if > 15% probability
        ]
        
        return IntentPrediction(
            primary_intent=top_intent,
            confidence=float(confidence),
            alternatives=alternatives,
            reasoning=self._explain_prediction(query, top_intent)
        )
    
    def _preprocess_query(self, query: str) -> str:
        """Vietnamese query preprocessing"""
        # Lowercase
        query = query.lower()
        
        # Normalize keywords
        query = query.replace("môn học", "monhoc")
        query = query.replace("tiên quyết", "tienquyet")
        query = query.replace("điều kiện", "dieukien")
        
        return query
    
    def _explain_prediction(self, query: str, intent: QueryIntent) -> str:
        """Explain why this intent was chosen"""
        
        triggers = {
            QueryIntent.TIEN_QUYET: ["tiên quyết", "học trước", "cần học"],
            QueryIntent.MO_TA_MON_HOC: ["mô tả", "nội dung", "học gì"],
            QueryIntent.QUY_DINH: ["quy định", "quy chế", "điều"],
        }
        
        matched_keywords = [
            kw for kw in triggers.get(intent, [])
            if kw in query.lower()
        ]
        
        if matched_keywords:
            return f"Detected keywords: {', '.join(matched_keywords)}"
        return "Classified by semantic understanding"
```

**Training Data Creation:**

```python
# Create training dataset (500+ examples)
training_data = [
    # TIEN_QUYET examples (100)
    ("Môn IT003 cần học gì trước?", QueryIntent.TIEN_QUYET),
    ("IT005 có môn tiên quyết không?", QueryIntent.TIEN_QUYET),
    ("Điều kiện để học SE104 là gì?", QueryIntent.TIEN_QUYET),
    
    # MO_TA_MON_HOC examples (100)
    ("Môn IT003 học về gì?", QueryIntent.MO_TA_MON_HOC),
    ("Nội dung môn Cấu trúc dữ liệu?", QueryIntent.MO_TA_MON_HOC),
    ("IT001 có khó không?", QueryIntent.MO_TA_MON_HOC),
    
    # QUY_DINH examples (100)
    ("Quy định về điểm rớt?", QueryIntent.QUY_DINH),
    ("Điều 15 quy chế đào tạo nói gì?", QueryIntent.QUY_DINH),
    
    # ... 400+ more examples
]
```

**Deliverables:**
- ✅ `core/services/intent_classifier.py` (500+ lines)
- ✅ Training dataset: `data/intent_training_data.json`
- ✅ Trained model: `models/intent_classifier_phobert.pth`
- ✅ Evaluation metrics report

**Acceptance Criteria:**
- [ ] Accuracy > 0.90 on test set (100 examples)
- [ ] Inference time: <50ms per query
- [ ] Handles Vietnamese correctly (diacritics, compound words)
- [ ] Confidence calibration: predicted ≈ actual

---

#### Task A2: Router Agent Service (Tuesday-Wednesday - 10h)
**Owner:** Senior Backend Developer  
**Priority:** P0 (Critical)

**Router Agent Architecture:**

```python
# core/services/router_agent.py

class RouterAgent:
    """CatRAG Router Agent - Intelligence layer for retrieval routing"""
    
    # Routing Table (CatRAG Principle #3)
    ROUTING_TABLE = {
        QueryIntent.TIEN_QUYET: {
            "primary": "graph_traversal",
            "secondary": None,
            "rerank": False,
            "params": {"max_depth": 5, "direction": "incoming"}
        },
        QueryIntent.DIEU_KIEN_HOC_TAP: {
            "primary": "graph_traversal",
            "secondary": "vector_search",
            "rerank": True,
            "params": {"max_depth": 3}
        },
        QueryIntent.MO_TA_MON_HOC: {
            "primary": "vector_search",
            "secondary": "bm25",
            "rerank": True,
            "params": {"top_k": 10}
        },
        QueryIntent.QUY_DINH: {
            "primary": "hybrid",
            "secondary": "graph_traversal",
            "rerank": True,
            "params": {"alpha": 0.7}  # 70% vector, 30% BM25
        },
        QueryIntent.TU_VAN_HOC_TAP: {
            "primary": "multi_strategy",
            "secondary": None,
            "rerank": True,
            "params": {"strategies": ["graph", "vector", "bm25"]}
        }
    }
    
    def __init__(
        self,
        intent_classifier: IntentClassifier,
        graph_repo: GraphRepository,
        vector_adapter: WeaviateVectorAdapter,
        bm25_adapter: OpenSearchKeywordAdapter,
        reranker: CrossEncoderReranker
    ):
        self.intent_classifier = intent_classifier
        self.graph_repo = graph_repo
        self.vector_adapter = vector_adapter
        self.bm25_adapter = bm25_adapter
        self.reranker = reranker
    
    async def route_query(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> RoutingDecision:
        """Main routing logic - CatRAG intelligence"""
        
        # Step 1: Classify intent
        intent_pred = await self.intent_classifier.classify(query)
        
        # Step 2: Get routing config
        routing_config = self.ROUTING_TABLE.get(
            intent_pred.primary_intent,
            self._get_default_routing()
        )
        
        # Step 3: Check confidence threshold
        if intent_pred.confidence < 0.75:
            # Low confidence → Use fallback strategy
            routing_config = self._get_fallback_routing(intent_pred)
        
        # Step 4: Create routing decision
        decision = RoutingDecision(
            intent=intent_pred.primary_intent,
            confidence=intent_pred.confidence,
            route_to=routing_config["primary"],
            secondary_route=routing_config["secondary"],
            use_reranking=routing_config["rerank"],
            params=routing_config["params"],
            reasoning=self._build_reasoning(intent_pred, routing_config)
        )
        
        return decision
    
    async def execute_routing(
        self,
        query: str,
        decision: RoutingDecision,
        top_k: int = 5
    ) -> RetrievalResult:
        """Execute retrieval based on routing decision"""
        
        results = []
        
        # Primary retrieval
        if decision.route_to == "graph_traversal":
            results = await self._graph_retrieval(query, decision.params)
        
        elif decision.route_to == "vector_search":
            results = await self._vector_retrieval(query, decision.params)
        
        elif decision.route_to == "bm25":
            results = await self._bm25_retrieval(query, decision.params)
        
        elif decision.route_to == "hybrid":
            results = await self._hybrid_retrieval(query, decision.params)
        
        elif decision.route_to == "multi_strategy":
            results = await self._multi_strategy_retrieval(query, decision.params)
        
        # Secondary retrieval (if specified)
        if decision.secondary_route and len(results) < top_k:
            secondary_results = await self._execute_secondary(
                query, 
                decision.secondary_route,
                top_k - len(results)
            )
            results.extend(secondary_results)
        
        # Reranking
        if decision.use_reranking:
            results = await self.reranker.rerank(query, results)
        
        # Limit to top_k
        results = results[:top_k]
        
        return RetrievalResult(
            results=results,
            routing_decision=decision,
            total_retrieved=len(results)
        )
    
    async def _graph_retrieval(
        self,
        query: str,
        params: Dict
    ) -> List[Document]:
        """Graph traversal retrieval"""
        
        # Extract course code from query
        entities = self.entity_extractor.extract(query)
        course_codes = [e.text for e in entities if e.category == NodeCategory.MON_HOC]
        
        if not course_codes:
            return []
        
        # Traverse graph
        results = []
        for code in course_codes:
            subgraph = await self.graph_repo.traverse(
                start_node_id=code,
                relationship_types=[RelationshipType.DIEU_KIEN_TIEN_QUYET],
                max_depth=params.get("max_depth", 5),
                direction=params.get("direction", "both")
            )
            
            # Convert subgraph to documents
            docs = self._subgraph_to_documents(subgraph)
            results.extend(docs)
        
        return results
    
    async def _multi_strategy_retrieval(
        self,
        query: str,
        params: Dict
    ) -> List[Document]:
        """Execute multiple retrieval strategies and merge"""
        
        strategies = params.get("strategies", ["graph", "vector"])
        all_results = []
        
        # Execute in parallel
        tasks = []
        for strategy in strategies:
            if strategy == "graph":
                tasks.append(self._graph_retrieval(query, {}))
            elif strategy == "vector":
                tasks.append(self._vector_retrieval(query, {}))
            elif strategy == "bm25":
                tasks.append(self._bm25_retrieval(query, {}))
        
        strategy_results = await asyncio.gather(*tasks)
        
        # Merge and deduplicate
        seen_ids = set()
        for results in strategy_results:
            for doc in results:
                if doc.id not in seen_ids:
                    all_results.append(doc)
                    seen_ids.add(doc.id)
        
        return all_results
```

**Deliverables:**
- ✅ `core/services/router_agent.py` (700+ lines)
- ✅ Routing configuration: `config/routing_config.yaml`
- ✅ Unit tests with mock retrievers
- ✅ Integration tests with all retrievers

**Acceptance Criteria:**
- [ ] Correctly routes 95%+ queries
- [ ] Fallback strategy handles edge cases
- [ ] Multi-strategy merging works
- [ ] End-to-end latency: <500ms

---

#### Task A3: Routing Evaluation & A/B Testing (Wednesday-Thursday - 6h)
**Owner:** ML Engineer + Senior Developer  
**Priority:** P1

**Evaluation Framework:**

```python
# tests/evaluation/router_evaluation.py

class RouterEvaluator:
    """Evaluate routing decisions"""
    
    async def evaluate_routing_accuracy(
        self,
        test_queries: List[QueryWithGroundTruth]
    ) -> EvaluationMetrics:
        """Compare routing decisions vs ground truth"""
        
        correct_routes = 0
        total = len(test_queries)
        
        confusion_matrix = defaultdict(lambda: defaultdict(int))
        
        for query_item in test_queries:
            decision = await self.router.route_query(query_item.query)
            
            if decision.route_to == query_item.expected_route:
                correct_routes += 1
            
            confusion_matrix[query_item.expected_route][decision.route_to] += 1
        
        accuracy = correct_routes / total
        
        return EvaluationMetrics(
            accuracy=accuracy,
            confusion_matrix=dict(confusion_matrix),
            per_intent_accuracy=self._compute_per_intent(confusion_matrix)
        )
    
    async def evaluate_retrieval_quality(
        self,
        test_queries: List[QueryWithRelevance]
    ) -> RetrievalMetrics:
        """Evaluate end-to-end retrieval quality"""
        
        total_precision = 0
        total_recall = 0
        total_ndcg = 0
        
        for query_item in test_queries:
            result = await self.router.execute_routing(query_item.query)
            
            # Compute metrics
            precision = self._compute_precision(result, query_item.relevant_docs)
            recall = self._compute_recall(result, query_item.relevant_docs)
            ndcg = self._compute_ndcg(result, query_item.relevance_scores)
            
            total_precision += precision
            total_recall += recall
            total_ndcg += ndcg
        
        n = len(test_queries)
        return RetrievalMetrics(
            precision=total_precision / n,
            recall=total_recall / n,
            ndcg=total_ndcg / n,
            f1=(2 * total_precision * total_recall) / (total_precision + total_recall) / n
        )
```

**A/B Testing Setup:**

```python
# Experiment: CatRAG Router vs Baseline (always hybrid)
class ABTestRunner:
    """Run A/B tests on routing strategies"""
    
    async def run_experiment(
        self,
        queries: List[str],
        treatment_pct: float = 0.5
    ):
        """Split traffic between CatRAG and baseline"""
        
        results = {"catrag": [], "baseline": []}
        
        for query in queries:
            # Random assignment
            if random.random() < treatment_pct:
                # Treatment: CatRAG Router
                result = await self.catrag_router.execute_routing(query)
                results["catrag"].append(result)
            else:
                # Control: Always hybrid
                result = await self.baseline_hybrid_search(query)
                results["baseline"].append(result)
        
        # Compare metrics
        comparison = self._compare_results(results)
        return comparison
```

**Deliverables:**
- ✅ `tests/evaluation/router_evaluation.py`
- ✅ Evaluation dataset: 200+ queries with ground truth
- ✅ A/B testing framework
- ✅ Results report: `docs/ROUTER_EVALUATION_WEEK3.md`

**Acceptance Criteria:**
- [ ] Routing accuracy > 90%
- [ ] CatRAG outperforms baseline by 10%+ (precision/recall)
- [ ] Statistical significance (p < 0.05)

---

### **Team B: Query Understanding**

#### Task B1: Vietnamese Query Preprocessing (Monday-Tuesday - 6h)
**Owner:** NLP Engineer  
**Priority:** P1

**Advanced Preprocessing:**

```python
# core/services/query_preprocessor.py

class VietnameseQueryPreprocessor:
    """Advanced query preprocessing for Vietnamese"""
    
    def preprocess(self, query: str) -> ProcessedQuery:
        """Full preprocessing pipeline"""
        
        # Step 1: Normalize
        normalized = self._normalize_unicode(query)
        normalized = self._normalize_whitespace(normalized)
        
        # Step 2: Spell correction (optional)
        corrected = self._spell_correct(normalized)
        
        # Step 3: Tokenize
        tokens = self._tokenize_vietnamese(corrected)
        
        # Step 4: Remove stopwords (but keep important ones)
        filtered_tokens = self._filter_stopwords(tokens)
        
        # Step 5: Normalize compound words
        normalized_tokens = self._normalize_compounds(filtered_tokens)
        
        return ProcessedQuery(
            original=query,
            normalized=corrected,
            tokens=normalized_tokens,
            entities=self._extract_entities(query)
        )
    
    def _normalize_compounds(self, tokens: List[str]) -> List[str]:
        """Handle Vietnamese compound words"""
        
        compounds = {
            ("công", "nghệ", "thông", "tin"): "công_nghệ_thông_tin",
            ("cấu", "trúc", "dữ", "liệu"): "cấu_trúc_dữ_liệu",
            ("khoa", "học", "máy", "tính"): "khoa_học_máy_tính",
        }
        
        # ... compound detection logic
        return tokens
```

**Deliverables:**
- ✅ Enhanced Vietnamese preprocessor
- ✅ Compound word dictionary (100+ entries)
- ✅ Spell correction (optional)

**Acceptance Criteria:**
- [ ] Handles all diacritics correctly
- [ ] Preserves entity boundaries
- [ ] Processing time: <20ms per query

---

#### Task B2: Query Expansion & Synonyms (Tuesday-Wednesday - 6h)
**Owner:** NLP Engineer  
**Priority:** P2

**Query Expansion:**

```python
# Add synonyms for better recall
query_expander = QueryExpander()

expanded = query_expander.expand("Môn IT003 cần học gì trước?")
# Returns: [
#   "Môn IT003 cần học gì trước?",
#   "IT003 có tiên quyết gì?",
#   "Điều kiện để học IT003?"
# ]
```

**Deliverables:**
- ✅ `core/services/query_expander.py`
- ✅ Synonym dictionary for Vietnamese academic terms

**Acceptance Criteria:**
- [ ] Expands to 2-3 variations
- [ ] Improves recall by 5-10%

---

#### Task B3: Query Reformulation for Graph Traversal (Wednesday-Thursday - 6h)
**Owner:** Both Teams  
**Priority:** P1

**Graph Query Translation:**

```python
# Convert natural language to Cypher
translator = NLToCypherTranslator()

cypher = translator.translate(
    query="Tìm tất cả môn tiên quyết của IT005",
    intent=QueryIntent.TIEN_QUYET
)

# Output:
# MATCH (course:MON_HOC {ma_mon: 'IT005'})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq)
# RETURN prereq.ma_mon, prereq.ten_mon
```

**Deliverables:**
- ✅ `core/services/nl_to_cypher_translator.py`
- ✅ Query templates for common patterns

**Acceptance Criteria:**
- [ ] Correctly translates 80%+ prerequisite queries
- [ ] Handles multi-hop traversals

---

## 🎬 Friday Integration Demo

### **CatRAG Retrieval Pipeline:**

```bash
# Test query routing
curl -X POST http://localhost:8000/catrag/query \
  -d '{"query": "Môn IT003 cần học gì trước?"}' \
  -H "Content-Type: application/json"

# Response:
{
  "routing_decision": {
    "intent": "TIEN_QUYET",
    "confidence": 0.95,
    "route_to": "graph_traversal",
    "reasoning": "Detected keywords: tiên quyết, cần học"
  },
  "results": [
    {"course_code": "IT002", "course_name": "Cấu trúc dữ liệu", ...},
    {"course_code": "IT001", "course_name": "Nhập môn lập trình", ...}
  ],
  "latency_ms": 245
}
```

---

## 📊 Success Metrics

### **Router Accuracy:**
- Intent classification: >90%
- Routing decision: >90%
- End-to-end retrieval quality: >85% (vs baseline 75%)

### **Performance:**
- Intent classification: <50ms
- Full routing pipeline: <500ms
- Handles 100 concurrent queries

---

## 🔜 Week 4 Preview

**Team A:** Advanced graph algorithms (multi-hop reasoning, path ranking)  
**Team B:** Context-aware retrieval, conversation history integration  
**Integration:** Production deployment preparation

---

**Last Updated:** November 13, 2025  
**Status:** 📝 Ready for Week 3
