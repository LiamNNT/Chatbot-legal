# Week 5: Testing, Documentation & UAT Preparation

**Duration:** Week 5 (Dec 11-17, 2025)  
**Phase:** Quality Assurance & Documentation  
**Objective:** Comprehensive testing, API documentation, UAT preparation

---

## 🎯 Week Goals

### Team A (Testing & Infrastructure)
- 🧪 Integration testing suite (E2E scenarios)
- 🧪 Load testing and performance benchmarks
- 🧪 API documentation (OpenAPI/Swagger)
- 🧪 Monitoring and alerting setup
- 🧪 Error handling and logging improvements

### Team B (UI & User Testing)
- 🎨 Frontend enhancements for CatRAG features
- 🎨 Feedback collection mechanism
- 🎨 Error message improvements
- 🎨 User testing scenarios
- 🎨 Help documentation and tooltips

### Integration Goal
- **Friday:** User Acceptance Testing (UAT) with 10+ real users

---

## 📋 Detailed Tasks

### **Team A: Testing & Infrastructure**

#### Task A1: Integration Testing Suite (Monday-Tuesday - 10h)
**Owner:** QA Engineer + Backend Developer  
**Priority:** P0

**Test Scenarios:**

```python
# tests/integration/test_catrag_e2e.py

import pytest
from httpx import AsyncClient

class TestCatRAGE2E:
    """End-to-end CatRAG system tests"""
    
    @pytest.mark.asyncio
    async def test_prerequisite_query_flow(self, async_client: AsyncClient):
        """Test: Query → Intent Classification → Graph Routing → Results"""
        
        # Send query
        response = await async_client.post(
            "/api/v1/catrag/query",
            json={"query": "Môn IT003 cần học gì trước?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify routing decision
        assert data["routing_decision"]["intent"] == "TIEN_QUYET"
        assert data["routing_decision"]["route_to"] == "graph_traversal"
        assert data["routing_decision"]["confidence"] > 0.85
        
        # Verify results
        assert len(data["results"]) >= 2
        assert "IT002" in [r["course_code"] for r in data["results"]]
        assert "IT001" in [r["course_code"] for r in data["results"]]
        
        # Verify performance
        assert data["latency_ms"] < 500
    
    @pytest.mark.asyncio
    async def test_multi_hop_reasoning(self, async_client: AsyncClient):
        """Test: Complex multi-hop query"""
        
        response = await async_client.post(
            "/api/v1/catrag/query",
            json={
                "query": "Tôi đã học IT001 và IT002, tôi có thể học gì tiếp?",
                "user_context": {
                    "completed_courses": ["IT001", "IT002"]
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should recommend IT003, IT004
        recommended = [r["course_code"] for r in data["results"]]
        assert "IT003" in recommended
        assert "IT004" in recommended
    
    @pytest.mark.asyncio
    async def test_conversation_context(self, async_client: AsyncClient):
        """Test: Follow-up query with context"""
        
        # First query
        response1 = await async_client.post(
            "/api/v1/catrag/query",
            json={
                "query": "IT003 là môn gì?",
                "session_id": "test-session-123"
            }
        )
        
        assert response1.status_code == 200
        
        # Follow-up query
        response2 = await async_client.post(
            "/api/v1/catrag/query",
            json={
                "query": "Môn đó cần học gì trước?",  # "Môn đó" refers to IT003
                "session_id": "test-session-123"
            }
        )
        
        assert response2.status_code == 200
        data = response2.json()
        
        # Should resolve "môn đó" to IT003
        assert "IT002" in [r["course_code"] for r in data["results"]]
    
    @pytest.mark.asyncio
    async def test_llm_relation_extraction(self, async_client: AsyncClient):
        """Test: LLM extracts relations from text"""
        
        text = "Môn IT003 - Cấu trúc dữ liệu yêu cầu hoàn thành IT002 trước"
        
        response = await async_client.post(
            "/api/v1/graph/extract-relations",
            json={"text": text}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify relation extraction
        relations = data["relations"]
        assert len(relations) >= 1
        
        prereq_relation = relations[0]
        assert prereq_relation["source_entity"] == "IT003"
        assert prereq_relation["target_entity"] == "IT002"
        assert prereq_relation["relation_type"] == "DIEU_KIEN_TIEN_QUYET"
        assert prereq_relation["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_error_handling(self, async_client: AsyncClient):
        """Test: Graceful error handling"""
        
        # Test malformed query
        response = await async_client.post(
            "/api/v1/catrag/query",
            json={"query": ""}  # Empty query
        )
        
        assert response.status_code == 400
        assert "error" in response.json()
        
        # Test unknown course
        response = await async_client.post(
            "/api/v1/catrag/query",
            json={"query": "UNKNOWN999 có tiên quyết gì?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0
        assert "message" in data  # Helpful error message
```

**Test Coverage Goals:**
- Unit tests: >85% coverage
- Integration tests: 50+ scenarios
- E2E tests: 20+ user journeys

**Deliverables:**
- ✅ `tests/integration/test_catrag_e2e.py` (500+ lines)
- ✅ `tests/integration/test_graph_population.py`
- ✅ `tests/integration/test_router_integration.py`
- ✅ CI/CD pipeline integration (GitHub Actions)

**Acceptance Criteria:**
- [ ] All integration tests pass
- [ ] Test coverage > 85%
- [ ] CI pipeline runs on every commit
- [ ] Tests run in <5 minutes

---

#### Task A2: Load Testing & Performance Benchmarks (Tuesday-Wednesday - 8h)
**Owner:** DevOps + Backend Developer  
**Priority:** P1

**Load Testing Scenarios:**

```python
# tests/load/locustfile.py

from locust import HttpUser, task, between

class CatRAGUser(HttpUser):
    """Simulate realistic user behavior"""
    
    wait_time = between(1, 3)  # 1-3 seconds between requests
    
    @task(3)  # 30% of requests
    def prerequisite_query(self):
        """Most common query type"""
        courses = ["IT003", "IT004", "IT005", "SE104", "SE105"]
        course = random.choice(courses)
        
        self.client.post(
            "/api/v1/catrag/query",
            json={"query": f"Môn {course} cần học gì trước?"}
        )
    
    @task(2)  # 20% of requests
    def course_description_query(self):
        """Second most common"""
        courses = ["IT001", "IT002", "IT003"]
        course = random.choice(courses)
        
        self.client.post(
            "/api/v1/catrag/query",
            json={"query": f"Môn {course} học về gì?"}
        )
    
    @task(1)  # 10% of requests
    def multi_hop_query(self):
        """Complex queries"""
        self.client.post(
            "/api/v1/catrag/query",
            json={
                "query": "Tôi đã học IT001, IT002, tôi nên học gì tiếp?",
                "user_context": {"completed_courses": ["IT001", "IT002"]}
            }
        )
    
    @task(1)
    def graph_health_check(self):
        """Health monitoring"""
        self.client.get("/api/v1/graph/health")
```

**Load Test Targets:**

| Metric | Target | Critical |
|--------|--------|----------|
| Concurrent users | 200 | 500 |
| Requests/sec | 50 | 100 |
| P50 latency | <300ms | <500ms |
| P95 latency | <800ms | <1500ms |
| P99 latency | <1500ms | <3000ms |
| Error rate | <1% | <5% |

**Performance Benchmarks:**

```bash
# Run load test
locust -f tests/load/locustfile.py \
  --host http://localhost:8000 \
  --users 200 \
  --spawn-rate 10 \
  --run-time 10m \
  --html reports/load_test_week5.html
```

**Deliverables:**
- ✅ Locust load testing suite
- ✅ Performance benchmark report
- ✅ Bottleneck analysis and recommendations
- ✅ Grafana dashboard for real-time monitoring

**Acceptance Criteria:**
- [ ] System handles 200 concurrent users
- [ ] P95 latency < 800ms
- [ ] Error rate < 1%
- [ ] No memory leaks during 1-hour test

---

#### Task A3: API Documentation (Wednesday-Thursday - 6h)
**Owner:** Backend Developer  
**Priority:** P1

**OpenAPI/Swagger Documentation:**

```yaml
# docs/openapi.yaml

openapi: 3.0.0
info:
  title: CatRAG API
  version: 1.0.0
  description: Category-guided Graph RAG for UIT Chatbot

servers:
  - url: http://localhost:8000/api/v1
    description: Development server

paths:
  /catrag/query:
    post:
      summary: Execute CatRAG query
      description: |
        Perform intelligent retrieval using CatRAG approach:
        1. Intent classification
        2. Router Agent decides retrieval strategy
        3. Execute graph/vector/hybrid search
        4. Return ranked results
      
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - query
              properties:
                query:
                  type: string
                  description: User's natural language query
                  example: "Môn IT003 cần học gì trước?"
                session_id:
                  type: string
                  description: Session ID for conversation context
                  example: "session-123-abc"
                user_context:
                  type: object
                  description: Additional user context
                  properties:
                    completed_courses:
                      type: array
                      items:
                        type: string
                      example: ["IT001", "IT002"]
      
      responses:
        200:
          description: Successful retrieval
          content:
            application/json:
              schema:
                type: object
                properties:
                  routing_decision:
                    $ref: '#/components/schemas/RoutingDecision'
                  results:
                    type: array
                    items:
                      $ref: '#/components/schemas/RetrievalResult'
                  latency_ms:
                    type: integer
                    example: 245
        
        400:
          description: Invalid request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

components:
  schemas:
    RoutingDecision:
      type: object
      properties:
        intent:
          type: string
          enum: [TIEN_QUYET, MO_TA_MON_HOC, QUY_DINH, TU_VAN_HOC_TAP]
          example: "TIEN_QUYET"
        confidence:
          type: number
          format: float
          minimum: 0
          maximum: 1
          example: 0.95
        route_to:
          type: string
          enum: [graph_traversal, vector_search, bm25, hybrid, multi_strategy]
          example: "graph_traversal"
        reasoning:
          type: string
          example: "Detected keywords: tiên quyết, cần học"
    
    RetrievalResult:
      type: object
      properties:
        course_code:
          type: string
          example: "IT002"
        course_name:
          type: string
          example: "Cấu trúc dữ liệu và giải thuật"
        score:
          type: number
          format: float
          example: 0.92
        metadata:
          type: object
    
    Error:
      type: object
      properties:
        error:
          type: string
        message:
          type: string
        details:
          type: object
```

**Interactive API Docs:**

```python
# app/main.py

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    title="CatRAG API",
    description="Category-guided Graph RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Swagger UI available at: http://localhost:8000/docs
# ReDoc available at: http://localhost:8000/redoc
```

**Deliverables:**
- ✅ Complete OpenAPI specification
- ✅ Interactive Swagger UI
- ✅ API usage examples (Postman collection)
- ✅ Developer guide: `docs/API_GUIDE.md`

**Acceptance Criteria:**
- [ ] All endpoints documented
- [ ] Examples for each endpoint
- [ ] Swagger UI functional
- [ ] Postman collection tested

---

#### Task A4: Monitoring & Alerting (Thursday-Friday - 6h)
**Owner:** DevOps  
**Priority:** P2

**Metrics to Monitor:**

```python
# core/monitoring/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    'catrag_requests_total',
    'Total CatRAG requests',
    ['intent', 'route', 'status']
)

request_latency = Histogram(
    'catrag_request_latency_seconds',
    'Request latency in seconds',
    ['intent', 'route']
)

# Graph metrics
graph_node_count = Gauge(
    'graph_node_count',
    'Total nodes in knowledge graph',
    ['category']
)

graph_query_latency = Histogram(
    'graph_query_latency_seconds',
    'Graph query latency',
    ['query_type']
)

# Cache metrics
cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage'
)
```

**Alerting Rules:**

```yaml
# monitoring/alerts.yaml

groups:
  - name: catrag_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(catrag_requests_total{status="error"}[5m]) > 0.05
        for: 2m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% over last 5 minutes"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, catrag_request_latency_seconds) > 1.5
        for: 5m
        annotations:
          summary: "High P95 latency"
          description: "P95 latency is {{ $value }}s"
      
      - alert: Neo4jDown
        expr: up{job="neo4j"} == 0
        for: 1m
        annotations:
          summary: "Neo4j is down"
```

**Deliverables:**
- ✅ Prometheus metrics integration
- ✅ Grafana dashboards
- ✅ Alert rules configuration
- ✅ On-call runbook

**Acceptance Criteria:**
- [ ] All critical metrics tracked
- [ ] Alerts trigger correctly
- [ ] Grafana dashboards visualize metrics
- [ ] Runbook covers common issues

---

### **Team B: UI & User Testing**

#### Task B1: Frontend CatRAG Features (Monday-Tuesday - 8h)
**Owner:** Frontend Developer  
**Priority:** P1

**UI Enhancements:**

1. **Routing Decision Display:**
```jsx
// frontend/src/components/RoutingBadge.jsx

export const RoutingBadge = ({ routingDecision }) => {
  const getRouteColor = (route) => {
    const colors = {
      graph_traversal: "bg-blue-500",
      vector_search: "bg-green-500",
      hybrid: "bg-purple-500",
      multi_strategy: "bg-orange-500"
    };
    return colors[route] || "bg-gray-500";
  };
  
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`px-2 py-1 rounded ${getRouteColor(routingDecision.route_to)}`}>
        {routingDecision.intent}
      </span>
      <span className="text-gray-600">
        Confidence: {(routingDecision.confidence * 100).toFixed(0)}%
      </span>
      <Tooltip content={routingDecision.reasoning}>
        <InfoIcon className="w-4 h-4" />
      </Tooltip>
    </div>
  );
};
```

2. **Graph Visualization:**
```jsx
// frontend/src/components/GraphVisualization.jsx

import { ForceGraph2D } from 'react-force-graph';

export const GraphVisualization = ({ subgraph }) => {
  const graphData = {
    nodes: subgraph.nodes.map(n => ({
      id: n.id,
      label: n.properties.ma_mon,
      category: n.category
    })),
    links: subgraph.relationships.map(r => ({
      source: r.source_id,
      target: r.target_id,
      type: r.type
    }))
  };
  
  return (
    <ForceGraph2D
      graphData={graphData}
      nodeLabel="label"
      nodeColor={node => getCategoryColor(node.category)}
      linkDirectionalArrowLength={6}
      width={800}
      height={600}
    />
  );
};
```

**Deliverables:**
- ✅ Routing decision UI component
- ✅ Graph visualization (optional)
- ✅ Prerequisite chain display
- ✅ Loading states and error handling

**Acceptance Criteria:**
- [ ] Routing decision visible to users
- [ ] Graph visualization works (if implemented)
- [ ] UI responsive on mobile
- [ ] Accessibility (WCAG AA)

---

#### Task B2: Feedback Collection (Tuesday-Wednesday - 4h)
**Owner:** Frontend + Backend Developer  
**Priority:** P2

**Feedback Mechanism:**

```jsx
// frontend/src/components/FeedbackButtons.jsx

export const FeedbackButtons = ({ queryId }) => {
  const [feedback, setFeedback] = useState(null);
  
  const submitFeedback = async (isHelpful) => {
    await api.post('/api/v1/feedback', {
      query_id: queryId,
      helpful: isHelpful,
      timestamp: new Date().toISOString()
    });
    
    setFeedback(isHelpful);
  };
  
  return (
    <div className="flex gap-2 mt-4">
      <button
        onClick={() => submitFeedback(true)}
        className={`btn ${feedback === true ? 'btn-success' : 'btn-outline'}`}
      >
        👍 Helpful
      </button>
      <button
        onClick={() => submitFeedback(false)}
        className={`btn ${feedback === false ? 'btn-error' : 'btn-outline'}`}
      >
        👎 Not Helpful
      </button>
    </div>
  );
};
```

**Deliverables:**
- ✅ Feedback UI components
- ✅ Feedback storage (database)
- ✅ Feedback analytics dashboard

**Acceptance Criteria:**
- [ ] Users can submit feedback
- [ ] Feedback stored with query metadata
- [ ] Analytics show feedback trends

---

#### Task B3: User Testing Sessions (Thursday-Friday - 10h)
**Owner:** Both Teams + Product Owner  
**Priority:** P0

**UAT Plan:**

**Participants:** 10+ students from UIT

**Test Scenarios:**
1. **Basic prerequisite queries** (5 scenarios)
   - "Môn IT003 cần học gì trước?"
   - "Điều kiện để học SE104?"

2. **Multi-hop reasoning** (3 scenarios)
   - "Tôi đã học IT001, IT002, nên học gì tiếp?"

3. **Conversation context** (3 scenarios)
   - Initial query + 2 follow-ups

4. **Error cases** (2 scenarios)
   - Unknown course codes
   - Ambiguous queries

**Data Collection:**
- Task completion rate
- Time to complete
- Error rate
- User satisfaction (1-5 scale)
- Qualitative feedback

**Deliverables:**
- ✅ UAT test plan
- ✅ UAT results report
- ✅ Bug list with priorities
- ✅ Improvement recommendations

**Acceptance Criteria:**
- [ ] 10+ users complete testing
- [ ] Task completion rate > 80%
- [ ] User satisfaction > 4.0/5.0
- [ ] Critical bugs identified and documented

---

## 🎬 Friday UAT Session

**Schedule:**
- 9:00 AM: Briefing and system walkthrough
- 9:30 AM - 11:30 AM: Testing session 1 (5 users)
- 12:00 PM - 2:00 PM: Testing session 2 (5 users)
- 2:30 PM - 4:00 PM: Feedback discussion
- 4:00 PM - 5:00 PM: Team retrospective

---

## 📊 Success Metrics

### **Testing:**
- [ ] Test coverage > 85%
- [ ] All integration tests pass
- [ ] Load test targets met
- [ ] API fully documented

### **UAT:**
- [ ] 10+ users complete testing
- [ ] Task completion > 80%
- [ ] User satisfaction > 4.0/5.0
- [ ] <10 critical bugs found

---

## 🔜 Week 6 Preview

**Team A:** Production deployment, database migration, scaling  
**Team B:** Final UI polish, user training, documentation  
**Integration:** Production launch! 🚀

---

**Last Updated:** November 13, 2025  
**Status:** 📝 Ready for Week 5
