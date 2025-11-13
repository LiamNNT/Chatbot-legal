# Week 4: Advanced Graph Algorithms & Production Optimization

**Duration:** Week 4 (Dec 4-10, 2025)  
**Phase:** Advanced Features & Optimization  
**Objective:** Multi-hop reasoning, performance optimization, production readiness

---

## 🎯 Week Goals

### Team A (Advanced Graph Algorithms)
- 🔬 Multi-hop reasoning and path ranking
- 🔬 Graph embeddings for semantic similarity
- 🔬 Subgraph extraction and pruning
- 🔬 Query performance optimization (caching, indexing)
- 🔬 Graph versioning and schema migration

### Team B (Context-Aware Retrieval)
- 💬 Conversation history integration
- 💬 Context windowing and memory management
- 💬 Follow-up query understanding
- 💬 Personalized retrieval (user preferences)
- 💬 Response generation with graph context

### Integration Goal
- **Friday:** Production-ready CatRAG system with context-aware retrieval

---

## 📋 Detailed Tasks

### **Team A: Advanced Graph Algorithms**

#### Task A1: Multi-Hop Reasoning (Monday-Tuesday - 10h)
**Owner:** Senior Backend Developer + ML Engineer  
**Priority:** P0

**Concept:**
Complex queries requiring traversal through multiple relationship types.

**Example:**
```
Query: "Tôi đã học IT001 và IT002, tôi có thể học môn nào tiếp theo?"

Multi-hop reasoning:
1. Find courses with prerequisites IT001 OR IT002
2. Filter courses where ALL prerequisites are met
3. Rank by relevance and difficulty
```

**Implementation:**

```python
# core/services/multi_hop_reasoner.py

class MultiHopReasoner:
    """Advanced graph reasoning for complex queries"""
    
    async def find_eligible_courses(
        self,
        completed_courses: List[str],
        max_recommendations: int = 10
    ) -> List[CourseRecommendation]:
        """Find courses student can take based on completed prerequisites"""
        
        # Cypher query for multi-hop reasoning
        cypher = """
        // Find all courses
        MATCH (course:MON_HOC)
        
        // Get prerequisites for each course
        OPTIONAL MATCH (course)-[:DIEU_KIEN_TIEN_QUYET]->(prereq:MON_HOC)
        
        // Aggregate prerequisites
        WITH course, COLLECT(prereq.ma_mon) AS prerequisites
        
        // Filter: all prerequisites must be in completed_courses
        WHERE ALL(p IN prerequisites WHERE p IN $completed_courses)
          AND NOT course.ma_mon IN $completed_courses
        
        // Rank by number of prerequisites met
        RETURN course.ma_mon AS course_code,
               course.ten_mon AS course_name,
               course.so_tin_chi AS credits,
               SIZE(prerequisites) AS num_prerequisites,
               prerequisites
        ORDER BY num_prerequisites DESC
        LIMIT $limit
        """
        
        results = await self.graph_repo.execute_cypher(
            cypher,
            {
                "completed_courses": completed_courses,
                "limit": max_recommendations
            }
        )
        
        # Convert to recommendations
        recommendations = []
        for record in results:
            rec = CourseRecommendation(
                course_code=record["course_code"],
                course_name=record["course_name"],
                credits=record["credits"],
                prerequisites_met=record["num_prerequisites"],
                reasoning=f"All {record['num_prerequisites']} prerequisites completed",
                confidence=self._compute_confidence(record)
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def find_learning_path(
        self,
        target_course: str,
        completed_courses: List[str]
    ) -> LearningPath:
        """Find optimal path from current progress to target course"""
        
        # Find all prerequisites not yet completed
        cypher = """
        MATCH path = (target:MON_HOC {ma_mon: $target})-[:DIEU_KIEN_TIEN_QUYET*]->(prereq:MON_HOC)
        WHERE NOT prereq.ma_mon IN $completed
        
        // Get all paths
        WITH COLLECT(path) AS all_paths
        
        // Find shortest path
        UNWIND all_paths AS path
        WITH path, LENGTH(path) AS path_length
        ORDER BY path_length ASC
        LIMIT 1
        
        RETURN [node IN NODES(path) | node.ma_mon] AS course_sequence
        """
        
        result = await self.graph_repo.execute_cypher(
            cypher,
            {"target": target_course, "completed": completed_courses}
        )
        
        if result:
            sequence = result[0]["course_sequence"]
            return LearningPath(
                target=target_course,
                required_courses=sequence,
                total_credits=await self._calculate_credits(sequence),
                estimated_semesters=len(sequence) // 4  # 4 courses per semester
            )
        else:
            return LearningPath(
                target=target_course,
                required_courses=[],
                message="All prerequisites completed! You can enroll now."
            )
    
    async def find_course_dependencies(
        self,
        course_code: str,
        depth: int = 3
    ) -> DependencyGraph:
        """Extract full dependency subgraph for a course"""
        
        cypher = """
        MATCH path = (course:MON_HOC {ma_mon: $code})-[rel:DIEU_KIEN_TIEN_QUYET*1..$depth]-(related:MON_HOC)
        
        WITH COLLECT(DISTINCT course) + COLLECT(DISTINCT related) AS all_nodes,
             COLLECT(DISTINCT rel) AS all_rels
        
        RETURN all_nodes, all_rels
        """
        
        # ... extract and return DependencyGraph
```

**Deliverables:**
- ✅ `core/services/multi_hop_reasoner.py` (600+ lines)
- ✅ Complex Cypher queries for multi-hop traversal
- ✅ Learning path recommendation engine
- ✅ Unit tests with mock graph data

**Acceptance Criteria:**
- [ ] Correctly finds eligible courses (100% accuracy on test cases)
- [ ] Learning path is optimal (shortest path)
- [ ] Handles circular dependencies gracefully
- [ ] Query performance: <300ms for depth 5

---

#### Task A2: Graph Embeddings (Tuesday-Wednesday - 8h)
**Owner:** ML Engineer  
**Priority:** P2

**Concept:**
Use Node2Vec or GraphSAGE to create embeddings for courses, then use for semantic similarity.

**Use Case:**
```
Query: "Tìm các môn học tương tự IT003"

Traditional: Only uses LIEN_QUAN relationships (limited)
With embeddings: Finds semantically similar courses based on graph structure
```

**Implementation:**

```python
# core/services/graph_embedder.py

from node2vec import Node2Vec
import networkx as nx

class GraphEmbedder:
    """Generate graph embeddings for semantic similarity"""
    
    async def train_node2vec(
        self,
        dimensions: int = 128,
        walk_length: int = 30,
        num_walks: int = 200
    ):
        """Train Node2Vec model on knowledge graph"""
        
        # Export Neo4j graph to NetworkX
        nx_graph = await self._export_to_networkx()
        
        # Train Node2Vec
        node2vec = Node2Vec(
            nx_graph,
            dimensions=dimensions,
            walk_length=walk_length,
            num_walks=num_walks,
            workers=4
        )
        
        model = node2vec.fit(window=10, min_count=1, batch_words=4)
        
        # Save embeddings
        self.embeddings = {
            node: model.wv[node]
            for node in nx_graph.nodes()
        }
        
        return model
    
    async def find_similar_courses(
        self,
        course_code: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Find similar courses using embedding similarity"""
        
        if course_code not in self.embeddings:
            return []
        
        target_emb = self.embeddings[course_code]
        
        # Compute cosine similarity with all other courses
        similarities = []
        for other_code, other_emb in self.embeddings.items():
            if other_code != course_code:
                sim = cosine_similarity(target_emb, other_emb)
                similarities.append((other_code, float(sim)))
        
        # Sort and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
```

**Deliverables:**
- ✅ `core/services/graph_embedder.py`
- ✅ Trained Node2Vec model: `models/graph_node2vec.bin`
- ✅ Similarity search API endpoint

**Acceptance Criteria:**
- [ ] Embeddings trained successfully
- [ ] Similarity search returns relevant courses (>80% accuracy)
- [ ] Inference time: <50ms

---

#### Task A3: Performance Optimization (Wednesday-Thursday - 8h)
**Owner:** Senior Backend Developer + DevOps  
**Priority:** P1

**Optimization Strategies:**

1. **Query Result Caching:**
```python
from functools import lru_cache
import redis

class GraphQueryCache:
    """Redis-backed cache for graph queries"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour
    
    async def get_or_execute(
        self,
        query_key: str,
        query_func: Callable,
        *args
    ):
        """Check cache, execute if miss"""
        
        # Check cache
        cached = self.redis.get(query_key)
        if cached:
            return json.loads(cached)
        
        # Cache miss - execute query
        result = await query_func(*args)
        
        # Store in cache
        self.redis.setex(
            query_key,
            self.ttl,
            json.dumps(result)
        )
        
        return result
```

2. **Connection Pooling:**
```python
# Increase Neo4j connection pool
neo4j_config = {
    "max_connection_pool_size": 100,
    "max_connection_lifetime": 3600,
    "connection_acquisition_timeout": 120
}
```

3. **Index Optimization:**
```cypher
// Create composite indexes
CREATE INDEX course_search IF NOT EXISTS
FOR (m:MON_HOC) ON (m.ma_mon, m.khoa);

// Vector index for full-text search
CALL db.index.fulltext.createNodeIndex(
  'course_fulltext',
  ['MON_HOC'],
  ['ten_mon', 'mo_ta']
);
```

4. **Query Batching:**
```python
async def batch_get_courses(
    self,
    course_codes: List[str]
) -> List[GraphNode]:
    """Get multiple courses in single query"""
    
    cypher = """
    UNWIND $codes AS code
    MATCH (course:MON_HOC {ma_mon: code})
    RETURN course
    """
    
    results = await self.execute_cypher(cypher, {"codes": course_codes})
    return [self._record_to_node(r) for r in results]
```

**Deliverables:**
- ✅ Redis caching layer
- ✅ Optimized Neo4j configuration
- ✅ Query batching utilities
- ✅ Performance benchmarks before/after

**Acceptance Criteria:**
- [ ] Cache hit rate > 60%
- [ ] Query latency reduced by 40%+
- [ ] Can handle 200 concurrent requests

---

#### Task A4: Schema Migration Tools (Thursday-Friday - 4h)
**Owner:** Backend Developer  
**Priority:** P2

**Versioned Schema Management:**

```python
# scripts/graph_migrations/001_add_difficulty_field.py

class Migration001:
    """Add difficulty rating to courses"""
    
    async def up(self, driver):
        """Apply migration"""
        cypher = """
        MATCH (m:MON_HOC)
        SET m.difficulty = COALESCE(m.difficulty, 'medium')
        """
        await driver.execute_query(cypher)
    
    async def down(self, driver):
        """Rollback migration"""
        cypher = """
        MATCH (m:MON_HOC)
        REMOVE m.difficulty
        """
        await driver.execute_query(cypher)
```

**Deliverables:**
- ✅ Migration framework: `scripts/graph_migrations/`
- ✅ Version tracking in Neo4j
- ✅ CLI tool: `python scripts/run_migration.py`

**Acceptance Criteria:**
- [ ] Migrations are reversible
- [ ] Version tracking works
- [ ] Zero downtime migrations

---

### **Team B: Context-Aware Retrieval**

#### Task B1: Conversation History Integration (Monday-Tuesday - 8h)
**Owner:** Backend Developer + ML Engineer  
**Priority:** P0

**Context Window Management:**

```python
# core/services/conversation_manager.py

class ConversationManager:
    """Manage conversation history and context"""
    
    def __init__(self, max_history: int = 10):
        self.conversations = {}  # session_id -> ConversationHistory
        self.max_history = max_history
    
    async def add_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        routing_decision: RoutingDecision,
        retrieved_docs: List[Document]
    ):
        """Add conversation turn to history"""
        
        if session_id not in self.conversations:
            self.conversations[session_id] = ConversationHistory()
        
        turn = ConversationTurn(
            timestamp=datetime.now(),
            user_query=user_query,
            assistant_response=assistant_response,
            routing_decision=routing_decision,
            retrieved_docs=retrieved_docs,
            extracted_entities=self._extract_entities(user_query)
        )
        
        self.conversations[session_id].add_turn(turn)
        
        # Trim if exceeds max
        if len(self.conversations[session_id].turns) > self.max_history:
            self.conversations[session_id].turns.pop(0)
    
    async def get_context(
        self,
        session_id: str,
        window_size: int = 3
    ) -> ConversationContext:
        """Get recent conversation context"""
        
        if session_id not in self.conversations:
            return ConversationContext(turns=[])
        
        recent_turns = self.conversations[session_id].turns[-window_size:]
        
        # Extract entities from history
        all_entities = []
        for turn in recent_turns:
            all_entities.extend(turn.extracted_entities)
        
        # Deduplicate
        unique_entities = self._deduplicate_entities(all_entities)
        
        return ConversationContext(
            turns=recent_turns,
            mentioned_entities=unique_entities,
            last_intent=recent_turns[-1].routing_decision.intent if recent_turns else None
        )
    
    async def resolve_follow_up(
        self,
        query: str,
        context: ConversationContext
    ) -> ResolvedQuery:
        """Resolve pronouns and implicit references in follow-up queries"""
        
        # Example: "Môn đó có khó không?" → "IT003 có khó không?"
        
        if self._is_follow_up(query):
            # Find referred entity from context
            referred_entity = self._find_referred_entity(query, context)
            
            if referred_entity:
                # Substitute pronoun with entity
                resolved_text = query.replace("môn đó", referred_entity.text)
                resolved_text = resolved_text.replace("nó", referred_entity.text)
                
                return ResolvedQuery(
                    original=query,
                    resolved=resolved_text,
                    referred_entity=referred_entity,
                    is_follow_up=True
                )
        
        return ResolvedQuery(
            original=query,
            resolved=query,
            is_follow_up=False
        )
```

**Deliverables:**
- ✅ `core/services/conversation_manager.py` (400+ lines)
- ✅ Follow-up query resolution
- ✅ Context window management
- ✅ Session storage (Redis)

**Acceptance Criteria:**
- [ ] Correctly resolves follow-up queries (>85% accuracy)
- [ ] Context window preserves last 10 turns
- [ ] Session management with expiration

---

#### Task B2: Personalized Retrieval (Tuesday-Wednesday - 6h)
**Owner:** ML Engineer  
**Priority:** P2

**User Preferences:**

```python
# core/services/personalization_service.py

class PersonalizationService:
    """Personalize retrieval based on user profile"""
    
    async def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get user's learning preferences"""
        
        # Example preferences:
        return UserPreferences(
            preferred_difficulty="easy",
            completed_courses=["IT001", "IT002"],
            favorite_departments=["CNTT", "KHMT"],
            learning_style="practical"  # vs "theoretical"
        )
    
    async def personalize_ranking(
        self,
        results: List[Document],
        user_prefs: UserPreferences
    ) -> List[Document]:
        """Re-rank results based on user preferences"""
        
        for doc in results:
            # Boost if matches preferences
            boost = 1.0
            
            if doc.metadata.get("khoa") in user_prefs.favorite_departments:
                boost *= 1.2
            
            if doc.metadata.get("difficulty") == user_prefs.preferred_difficulty:
                boost *= 1.15
            
            doc.score *= boost
        
        # Re-sort by boosted scores
        results.sort(key=lambda d: d.score, reverse=True)
        return results
```

**Deliverables:**
- ✅ `core/services/personalization_service.py`
- ✅ User preference storage
- ✅ Personalized ranking logic

**Acceptance Criteria:**
- [ ] Ranking improves with personalization (10%+ better relevance)
- [ ] Preferences update based on user interactions

---

#### Task B3: Response Generation with Graph Context (Wednesday-Thursday - 8h)
**Owner:** Both Teams  
**Priority:** P1

**Graph-Enhanced Response:**

```python
# core/services/response_generator.py

class GraphAwareResponseGenerator:
    """Generate responses using graph context"""
    
    async def generate_response(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        conversation_context: ConversationContext
    ) -> GeneratedResponse:
        """Generate answer with graph structure awareness"""
        
        # Extract graph structure from results
        if retrieval_result.routing_decision.route_to == "graph_traversal":
            # Graph-structured answer
            response = await self._generate_graph_response(
                query,
                retrieval_result
            )
        else:
            # Vector/BM25 answer
            response = await self._generate_text_response(
                query,
                retrieval_result
            )
        
        return response
    
    async def _generate_graph_response(
        self,
        query: str,
        result: RetrievalResult
    ) -> str:
        """Generate structured answer from graph traversal"""
        
        # Example for prerequisites query
        if result.routing_decision.intent == QueryIntent.TIEN_QUYET:
            courses = [doc.metadata["course_code"] for doc in result.results]
            
            response = f"Để học môn này, bạn cần hoàn thành:\n"
            for i, course in enumerate(courses, 1):
                course_name = result.results[i-1].metadata["course_name"]
                response += f"{i}. {course} - {course_name}\n"
            
            # Add learning path suggestion
            response += "\nGợi ý: Nên học theo thứ tự trên để đảm bảo nắm vững kiến thức."
            
            return response
```

**Deliverables:**
- ✅ `core/services/response_generator.py`
- ✅ Graph-aware templates
- ✅ LLM integration for natural responses (optional)

**Acceptance Criteria:**
- [ ] Responses use graph structure (prerequisites, paths)
- [ ] Natural language quality (coherent, informative)
- [ ] Generation time: <200ms

---

## 🎬 Friday Production Demo

### **Full System Demonstration:**

**Test Case 1: Multi-hop reasoning**
```
User: "Tôi đã học IT001 và IT002, tôi nên học môn nào tiếp theo?"

System:
- Intent: TU_VAN_HOC_TAP (Advisory)
- Route: Multi-strategy (Graph + Vector)
- Response: "Dựa vào các môn bạn đã học, bạn có thể đăng ký:
  1. IT003 - Cấu trúc dữ liệu và giải thuật
  2. IT004 - Cơ sở dữ liệu
  ..."
```

**Test Case 2: Context-aware follow-up**
```
User: "IT003 có khó không?"
System: [Routes to vector search for course description]

User: "Môn đó cần học gì trước?"
System: [Resolves "môn đó" → IT003, routes to graph traversal]
Response: "IT003 yêu cầu hoàn thành IT002 và IT001 trước."
```

---

## 📊 Success Metrics

### **Performance:**
- Multi-hop queries: <300ms
- Cache hit rate: >60%
- Concurrent users: 200+

### **Accuracy:**
- Multi-hop reasoning: >95%
- Follow-up resolution: >85%
- Personalized ranking: +10% relevance

---

## 🔜 Week 5 Preview

**Team A:** API documentation, integration testing, load testing  
**Team B:** UI enhancements, feedback collection, error handling  
**Integration:** User acceptance testing (UAT)

---

**Last Updated:** November 13, 2025  
**Status:** 📝 Ready for Week 4
