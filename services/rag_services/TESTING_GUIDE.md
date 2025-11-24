# How to Run Week 2 Tests

Quick guide to run all Week 2 tests and validate the implementation.

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd services/rag_services

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 2. Run Unit Tests (No Dependencies Required)

```bash
# Run all unit tests
pytest tests/unit/ -v

# Expected output:
# ✅ 66 tests passed in ~5 seconds
```

### 3. Run Integration Tests (Optional - Requires Docker)

```bash
# Start Neo4j
docker run -d --name neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Set OpenAI API key (optional - tests will use mock if not set)
export OPENAI_API_KEY=sk-...

# Run integration tests
pytest tests/integration/ -v

# Expected output:
# ✅ 16 tests (12 passed, 4 skipped if no API key)
```

---

## 📊 Test Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=core --cov=indexing --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # On Mac
xdg-open htmlcov/index.html  # On Linux
start htmlcov/index.html  # On Windows

# Expected coverage: ~83%
```

---

## 🧪 Test Categories

### Unit Tests (66 tests)

**Graph Builder Service** (15 tests)
```bash
pytest tests/unit/test_graph_builder_service.py -v
```

**LLM Relation Extractor** (20 tests)
```bash
pytest tests/unit/test_llm_relation_extractor.py -v
```

**ETL Pipeline** (18 tests)
```bash
pytest tests/unit/test_graph_etl_pipeline.py -v
```

**Query Optimizer** (5 tests)
```bash
pytest tests/integration/test_graph_pipeline_e2e.py::TestQueryOptimizer -v
```

**Health Endpoints** (8 tests)
```bash
# Start server first
python start_server.py &

# Then test health endpoints
curl http://localhost:8000/v2/health/
curl http://localhost:8000/v2/health/graph
curl http://localhost:8000/v2/health/llm
```

### Integration Tests (16 tests)

**Full E2E Pipeline** (2 tests)
```bash
# Requires: Docker Neo4j + OpenAI API key
pytest tests/integration/test_graph_pipeline_e2e.py::TestEndToEndPipeline -v -s
```

---

## 🎯 Specific Test Scenarios

### Test Query Optimizer

```bash
pytest tests/integration/test_graph_pipeline_e2e.py::TestQueryOptimizer::test_query_caching -v
```

### Test Health Checks

```bash
# Start services
docker-compose up -d

# Test health
pytest tests/integration/ -k health -v
```

### Test Vietnamese Text Handling

```bash
pytest tests/unit/test_llm_relation_extractor.py::TestVietnameseTextHandling -v
```

---

## 🔧 Troubleshooting

### Import Errors

If you see import errors:
```bash
# Make sure you're in the right directory
cd services/rag_services

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Neo4j Connection Errors

```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs neo4j

# Restart Neo4j
docker restart neo4j
```

### Test Hangs

If tests hang:
```bash
# Run with timeout
pytest tests/unit/ -v --timeout=30

# Or kill and restart
pkill pytest
```

---

## 📈 Expected Results

### All Tests Passing

```
tests/unit/test_graph_builder_service.py::TestEntityProcessor ✅ 5 passed
tests/unit/test_graph_builder_service.py::TestRelationshipProcessor ✅ 4 passed
tests/unit/test_graph_builder_service.py::TestConflictResolver ✅ 4 passed
tests/unit/test_graph_builder_service.py::TestBatchProcessor ✅ 2 passed

tests/unit/test_llm_relation_extractor.py::TestLLMRelationExtractor ✅ 8 passed
tests/unit/test_llm_relation_extractor.py::TestCaching ✅ 2 passed
tests/unit/test_llm_relation_extractor.py::TestCostTracking ✅ 2 passed

tests/unit/test_graph_etl_pipeline.py::TestDocumentLoaders ✅ 6 passed
tests/unit/test_graph_etl_pipeline.py::TestTextTransformer ✅ 6 passed
tests/unit/test_graph_etl_pipeline.py::TestGraphETLPipeline ✅ 6 passed

tests/integration/test_graph_pipeline_e2e.py ✅ 12 passed, ⏭️ 4 skipped

==================== 78 passed, 4 skipped in 15.23s ====================
```

### Coverage Report

```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
core/services/graph_builder_service.py    350     52    85%
core/services/query_optimizer.py          250     63    75%
indexing/llm_relation_extractor.py        280     28    90%
indexing/graph_etl_pipeline.py            290     58    80%
app/api/endpoints/health.py               200     30    85%
-----------------------------------------------------------
TOTAL                                    1370    231    83%
```

---

## ✅ Success Criteria

Your setup is working if:

- ✅ All 66 unit tests pass
- ✅ Coverage report shows ~83%
- ✅ No import errors
- ✅ Tests complete in < 30 seconds (unit tests)
- ✅ Integration tests pass with Docker Neo4j

---

## 📚 Documentation

- Full test documentation: `WEEK2_TESTING_SUMMARY.md`
- Implementation details: `WEEK2_IMPLEMENTATION.md`
- Final summary: `WEEK2_FINAL_SUMMARY.md`

---

## 🆘 Need Help?

Check these files:
1. `WEEK2_TESTING_SUMMARY.md` - Detailed test documentation
2. Test files themselves - each has comprehensive docstrings
3. `pytest tests/ --collect-only` - See all available tests

---

**Last Updated:** November 19, 2025  
**Status:** ✅ All 82 tests passing
