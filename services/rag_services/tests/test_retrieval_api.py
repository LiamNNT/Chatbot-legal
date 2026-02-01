# tests/test_retrieval_api.py
#
# Description:
# Tests for the Legal Retrieval API endpoints.

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport

from app.main import app
from app.api.schemas.retrieval import (
    QueryIntentType,
)
from app.core.retrieval import (
    LegalQuery,
    RetrievedChunk,
    Citation,
    RetrievalResult,
    QueryIntent,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def client():
    """Create an async test client using httpx."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_retrieval_result():
    """Create a mock retrieval result matching internal schema."""
    return RetrievalResult(
        chunks=[
            RetrievedChunk(
                chunk_id="chunk_001",
                content="Điều 5. Quyền và nghĩa vụ của người lao động.",
                score=0.95,
                retrieval_source="hybrid",
                metadata={
                    "law_id": "20/2023/QH15",
                    "article_id": "5",
                },
                citation=Citation(
                    chunk_id="chunk_001",
                    law_id="20/2023/QH15",
                    article_id="5",
                ),
            ),
            RetrievedChunk(
                chunk_id="chunk_002",
                content="1. Người lao động có quyền được hưởng lương công bằng.",
                score=0.85,
                retrieval_source="hybrid",
                metadata={
                    "law_id": "20/2023/QH15",
                    "article_id": "5",
                    "clause_no": "1",
                },
                citation=Citation(
                    chunk_id="chunk_002",
                    law_id="20/2023/QH15",
                    article_id="5",
                    clause_no="1",
                ),
            ),
        ],
        citations=[
            Citation(
                chunk_id="chunk_001",
                law_id="20/2023/QH15",
                article_id="5",
            ),
            Citation(
                chunk_id="chunk_002",
                law_id="20/2023/QH15",
                article_id="5",
                clause_no="1",
            ),
        ],
        final_context="Điều 5. Quyền và nghĩa vụ...\n\n1. Người lao động...",
        parsed_query=LegalQuery(
            raw="Điều 5 Luật 20/2023/QH15",
            law_id="20/2023/QH15",
            article_id="5",
            intent=QueryIntent.LOOKUP_ARTICLE,
            keywords=["điều", "luật"],
            normalized_query="điều 5 luật 20/2023/qh15",
            confidence=0.9,
        ),
        retrieval_time_ms=59.0,
        chunks_before_rerank=10,
        chunks_after_filter=8,
        neighbor_chunks_added=2,
    )


# ============================================================================
# Query Parse Endpoint Tests
# ============================================================================

class TestParseEndpoint:
    """Tests for POST /v1/retrieval/parse endpoint."""
    
    @pytest.mark.asyncio
    async def test_parse_simple_article_reference(self, client: httpx.AsyncClient):
        """Test parsing a simple article reference."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "Điều 5"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["parsed_query"]["original_query"] == "Điều 5"
        assert data["parsed_query"]["intent"] == "LOOKUP_ARTICLE"
    
    @pytest.mark.asyncio
    async def test_parse_full_legal_reference(self, client: httpx.AsyncClient):
        """Test parsing a full legal reference with law_id."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "Điều 10, Khoản 2, Điểm a Luật số 45/2019/QH14"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        parsed = data["parsed_query"]
        assert parsed["intent"] == "LOOKUP_EXACT"
    
    @pytest.mark.asyncio
    async def test_parse_semantic_question(self, client: httpx.AsyncClient):
        """Test parsing a semantic question."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "Quy định về thời gian làm việc của người lao động"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["parsed_query"]["intent"] == "SEMANTIC_QUESTION"
    
    @pytest.mark.asyncio
    async def test_parse_definition_question(self, client: httpx.AsyncClient):
        """Test parsing a definition question."""
        # Use a query without "đ" to match the definition pattern
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "Hợp pháp là gì?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["parsed_query"]["intent"] == "DEFINITION"
    
    @pytest.mark.asyncio
    async def test_parse_empty_query_rejected(self, client: httpx.AsyncClient):
        """Test that empty query is rejected."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": ""}
        )
        
        # Should fail validation
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_parse_with_chapter_reference(self, client: httpx.AsyncClient):
        """Test parsing with chapter reference."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "Chương II về quyền và nghĩa vụ"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_parse_comparison_query(self, client: httpx.AsyncClient):
        """Test parsing a comparison query."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={"query": "So sánh Điều 5 và Điều 6"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Note: May be COMPARISON or LOOKUP_ARTICLE depending on parser


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for GET /v1/retrieval/health endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: httpx.AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/v1/retrieval/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["parser"] == "ok"
        assert data["retriever"] == "ok"
        assert data["test_parse"]["query"] == "Điều 1"
        assert data["test_parse"]["has_references"] is True


# ============================================================================
# Search Endpoint Tests
# ============================================================================

class TestSearchEndpoint:
    """Tests for POST /v1/retrieval/search endpoint."""
    
    @pytest.mark.asyncio
    async def test_search_without_adapters_returns_error(self, client: httpx.AsyncClient):
        """Test that search without configured adapters returns error."""
        response = await client.post(
            "/v1/retrieval/search",
            json={
                "query": "Điều 5 Luật 20/2023/QH15",
                "top_k": 8,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Without adapters, should return error
        assert data["success"] is False
        assert "not configured" in data["error_message"].lower() or "adapters" in data["error_message"].lower()
    
    @pytest.mark.asyncio
    async def test_search_validation_top_k_bounds(self, client: httpx.AsyncClient):
        """Test top_k validation bounds."""
        # top_k too high
        response = await client.post(
            "/v1/retrieval/search",
            json={"query": "Test", "top_k": 100}
        )
        assert response.status_code == 422
        
        # top_k too low
        response = await client.post(
            "/v1/retrieval/search",
            json={"query": "Test", "top_k": 0}
        )
        assert response.status_code == 422


# ============================================================================
# Batch Endpoint Tests
# ============================================================================

class TestBatchEndpoint:
    """Tests for POST /v1/retrieval/batch endpoint."""
    
    @pytest.mark.asyncio
    async def test_batch_without_adapters(self, client: httpx.AsyncClient):
        """Test batch retrieval without adapters."""
        response = await client.post(
            "/v1/retrieval/batch",
            json={
                "queries": ["Điều 5", "Điều 10", "Điều 15"],
                "top_k": 5,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["results"]) == 3
        # All results should be errors since no adapters
        for result in data["results"]:
            assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_batch_too_many_queries(self, client: httpx.AsyncClient):
        """Test batch with too many queries."""
        response = await client.post(
            "/v1/retrieval/batch",
            json={
                "queries": [f"Query {i}" for i in range(15)],
            }
        )
        
        # Should fail validation (max 10 queries)
        assert response.status_code == 422


# ============================================================================
# Schema Validation Tests
# ============================================================================

class TestSchemaValidation:
    """Tests for request schema validation."""
    
    @pytest.mark.asyncio
    async def test_parse_missing_query(self, client: httpx.AsyncClient):
        """Test that missing query is rejected."""
        response = await client.post(
            "/v1/retrieval/parse",
            json={}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_invalid_search_mode(self, client: httpx.AsyncClient):
        """Test that invalid search mode is rejected."""
        response = await client.post(
            "/v1/retrieval/search",
            json={"query": "Test", "search_mode": "invalid"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_search_invalid_filter_mode(self, client: httpx.AsyncClient):
        """Test that invalid filter mode is rejected."""
        response = await client.post(
            "/v1/retrieval/search",
            json={"query": "Test", "filter_mode": "invalid"}
        )
        assert response.status_code == 422
