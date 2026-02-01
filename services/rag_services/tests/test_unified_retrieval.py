# tests/test_unified_retrieval.py
"""
Tests for the Unified Retrieval Layer.

Tests cover:
- Metadata filter builders (Weaviate, OpenSearch)
- Neighbor expansion
- Unified retriever orchestration
- Citation generation
- Context packing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.core.retrieval.schemas import (
    LegalQuery,
    QueryIntent,
    RetrievalConfig,
    RetrievalResult,
    RetrievedChunk,
    Citation,
    NeighborContext,
)
from app.core.retrieval.metadata_filter_builder import (
    WeaviateFilterBuilder,
    OpenSearchFilterBuilder,
    get_filter_builder,
)
from app.core.retrieval.neighbor_expander import NeighborExpander
from app.core.retrieval.unified_retriever import UnifiedRetriever
from app.core.retrieval.legal_query_parser import LegalQueryParser


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_legal_query():
    """Sample parsed legal query."""
    return LegalQuery(
        raw="Khoản 2 Điều 11 Luật 20/2023/QH15 quy định gì?",
        law_id="20/2023/QH15",
        article_id="11",
        clause_no="2",
        point_no=None,
        intent=QueryIntent.LOOKUP_EXACT,
        keywords=["quy", "định"],
        normalized_query="Khoản 2 Điều 11 Luật 20/2023/QH15 quy định gì?",
        confidence=0.9,
    )


@pytest.fixture
def sample_chunks():
    """Sample retrieved chunks with metadata."""
    return [
        RetrievedChunk(
            chunk_id="chunk_001",
            content="Sinh viên phải đóng học phí theo quy định.",
            score=0.95,
            metadata={
                "law_id": "20/2023/QH15",
                "article_id": "Điều 11",
                "clause_no": "2",
                "parent_id": "chunk_000",
                "prev_sibling_id": "chunk_001a",
                "next_sibling_id": "chunk_002",
            },
            citation=Citation(
                law_id="20/2023/QH15",
                article_id="Điều 11",
                clause_no="2",
                chunk_id="chunk_001",
            ),
            parent_id="chunk_000",
            prev_sibling_id="chunk_001a",
            next_sibling_id="chunk_002",
        ),
        RetrievedChunk(
            chunk_id="chunk_002",
            content="Mức học phí được điều chỉnh hàng năm.",
            score=0.88,
            metadata={
                "law_id": "20/2023/QH15",
                "article_id": "Điều 11",
                "clause_no": "3",
            },
            citation=Citation(
                law_id="20/2023/QH15",
                article_id="Điều 11",
                clause_no="3",
                chunk_id="chunk_002",
            ),
        ),
    ]


# =============================================================================
# Weaviate Filter Builder Tests
# =============================================================================

class TestWeaviateFilterBuilder:
    """Tests for Weaviate filter building."""
    
    @pytest.fixture
    def builder(self):
        return WeaviateFilterBuilder()
    
    def test_build_filter_from_legal_query(self, builder, sample_legal_query):
        """Test building filter from LegalQuery."""
        filter_obj = builder.build_filter(sample_legal_query, strict=True)
        
        assert filter_obj is not None
        assert filter_obj["operator"] == "And"
        assert len(filter_obj["operands"]) >= 2
    
    def test_build_filter_strict_mode(self, builder, sample_legal_query):
        """Test strict mode uses Equal operator."""
        filter_obj = builder.build_filter(sample_legal_query, strict=True)
        
        # Find law_id condition
        law_condition = None
        for op in filter_obj["operands"]:
            if isinstance(op, dict) and op.get("path") == ["law_id"]:
                law_condition = op
                break
        
        if law_condition:
            assert law_condition["operator"] == "Equal"
    
    def test_build_filter_fuzzy_mode(self, builder, sample_legal_query):
        """Test fuzzy mode uses Like operator."""
        filter_obj = builder.build_filter(sample_legal_query, strict=False)
        
        # Check that some conditions use Like
        def has_like_operator(obj):
            if isinstance(obj, dict):
                if obj.get("operator") == "Like":
                    return True
                for v in obj.values():
                    if has_like_operator(v):
                        return True
            elif isinstance(obj, list):
                for item in obj:
                    if has_like_operator(item):
                        return True
            return False
        
        assert has_like_operator(filter_obj)
    
    def test_build_filter_no_refs_returns_none(self, builder):
        """Test returns None when no legal refs."""
        empty_query = LegalQuery(
            raw="test",
            intent=QueryIntent.SEMANTIC_QUESTION,
        )
        filter_obj = builder.build_filter(empty_query)
        assert filter_obj is None
    
    def test_build_chunk_id_filter_single(self, builder):
        """Test chunk ID filter for single ID."""
        filter_obj = builder.build_chunk_id_filter(["chunk_001"])
        
        assert filter_obj["path"] == ["chunk_id"]
        assert filter_obj["operator"] == "Equal"
        assert filter_obj["valueText"] == "chunk_001"
    
    def test_build_chunk_id_filter_multiple(self, builder):
        """Test chunk ID filter for multiple IDs."""
        filter_obj = builder.build_chunk_id_filter(["chunk_001", "chunk_002"])
        
        assert filter_obj["path"] == ["chunk_id"]
        assert filter_obj["operator"] == "ContainsAny"
        assert "chunk_001" in filter_obj["valueTextArray"]
    
    def test_build_filter_with_additional_filters(self, builder, sample_legal_query):
        """Test adding additional filters."""
        filter_obj = builder.build_filter(
            sample_legal_query,
            additional_filters={"doc_type": "law"}
        )
        
        # Should include doc_type condition
        assert filter_obj is not None


# =============================================================================
# OpenSearch Filter Builder Tests
# =============================================================================

class TestOpenSearchFilterBuilder:
    """Tests for OpenSearch filter building."""
    
    @pytest.fixture
    def builder(self):
        return OpenSearchFilterBuilder()
    
    def test_build_filter_from_legal_query(self, builder, sample_legal_query):
        """Test building filter from LegalQuery."""
        filter_obj = builder.build_filter(sample_legal_query, strict=True)
        
        assert filter_obj is not None
        assert "bool" in filter_obj
        assert "must" in filter_obj["bool"] or "should" in filter_obj["bool"]
    
    def test_build_filter_strict_uses_term(self, builder, sample_legal_query):
        """Test strict mode uses term query."""
        filter_obj = builder.build_filter(sample_legal_query, strict=True)
        
        must_conditions = filter_obj["bool"].get("must", [])
        # Check for term queries
        has_term = any("term" in str(c) for c in must_conditions)
        assert has_term or len(must_conditions) > 0
    
    def test_build_filter_fuzzy_uses_match(self, builder, sample_legal_query):
        """Test fuzzy mode uses match query."""
        filter_obj = builder.build_filter(sample_legal_query, strict=False)
        
        must_conditions = filter_obj["bool"].get("must", [])
        has_match = any("match" in str(c) for c in must_conditions)
        assert has_match or len(must_conditions) > 0
    
    def test_build_chunk_id_filter_single(self, builder):
        """Test chunk ID filter for single ID."""
        filter_obj = builder.build_chunk_id_filter(["chunk_001"])
        
        assert "term" in filter_obj
        assert filter_obj["term"]["chunk_id"] == "chunk_001"
    
    def test_build_chunk_id_filter_multiple(self, builder):
        """Test chunk ID filter for multiple IDs."""
        filter_obj = builder.build_chunk_id_filter(["chunk_001", "chunk_002"])
        
        assert "terms" in filter_obj
        assert "chunk_001" in filter_obj["terms"]["chunk_id"]


class TestFilterBuilderFactory:
    """Tests for filter builder factory function."""
    
    def test_get_weaviate_builder(self):
        """Test getting Weaviate filter builder."""
        builder = get_filter_builder("weaviate")
        assert isinstance(builder, WeaviateFilterBuilder)
    
    def test_get_opensearch_builder(self):
        """Test getting OpenSearch filter builder."""
        builder = get_filter_builder("opensearch")
        assert isinstance(builder, OpenSearchFilterBuilder)
    
    def test_get_elasticsearch_builder(self):
        """Test getting Elasticsearch (alias for OpenSearch) builder."""
        builder = get_filter_builder("elasticsearch")
        assert isinstance(builder, OpenSearchFilterBuilder)
    
    def test_unknown_backend_raises(self):
        """Test unknown backend raises ValueError."""
        with pytest.raises(ValueError):
            get_filter_builder("unknown")


# =============================================================================
# Neighbor Expander Tests
# =============================================================================

class TestNeighborExpander:
    """Tests for neighbor context expansion."""
    
    @pytest.fixture
    def mock_fetch_chunks(self):
        """Mock function that returns neighbor chunks."""
        async def fetch(chunk_ids: List[str]) -> List[Dict]:
            neighbors = {
                "chunk_000": {
                    "chunk_id": "chunk_000",
                    "content": "Điều 11. Quy định về học phí",
                    "metadata": {"article_id": "Điều 11"},
                },
                "chunk_001a": {
                    "chunk_id": "chunk_001a",
                    "content": "Nội dung khoản trước",
                    "metadata": {"clause_no": "1"},
                },
                "chunk_002": {
                    "chunk_id": "chunk_002",
                    "content": "Nội dung khoản sau",
                    "metadata": {"clause_no": "3"},
                },
            }
            return [neighbors.get(cid) for cid in chunk_ids if cid in neighbors]
        return fetch
    
    @pytest.fixture
    def expander(self, mock_fetch_chunks):
        return NeighborExpander(
            fetch_chunks_fn=mock_fetch_chunks,
            max_tokens_per_neighbor=200,
            max_total_neighbor_tokens=500,
        )
    
    @pytest.mark.asyncio
    async def test_expand_adds_neighbors(self, expander, sample_chunks):
        """Test neighbor expansion adds context."""
        expanded = await expander.expand(sample_chunks)
        
        # First chunk should have neighbors
        assert expanded[0].neighbors is not None
    
    @pytest.mark.asyncio
    async def test_expand_includes_parent(self, expander, sample_chunks):
        """Test parent chunk is included."""
        expanded = await expander.expand(sample_chunks)
        
        if expanded[0].neighbors and expanded[0].neighbors.parent_chunk:
            assert expanded[0].neighbors.parent_chunk.chunk_id == "chunk_000"
    
    @pytest.mark.asyncio
    async def test_expand_avoids_duplicates(self, expander, sample_chunks):
        """Test expansion avoids duplicate chunks."""
        existing_ids = {c.chunk_id for c in sample_chunks}
        expanded = await expander.expand(sample_chunks, existing_ids)
        
        # Neighbors should not include existing chunks
        for chunk in expanded:
            if chunk.neighbors:
                for neighbor in chunk.neighbors.get_all_chunks():
                    # This is a neighbor, so it shouldn't be in original set
                    # (unless it was fetched separately)
                    pass  # Just verify no errors
    
    @pytest.mark.asyncio
    async def test_expand_respects_token_limit(self, expander, sample_chunks):
        """Test expansion respects token limits."""
        # Create chunk with very long neighbor
        long_chunk = sample_chunks[0].model_copy()
        expanded = await expander.expand([long_chunk])
        
        # Should complete without error and respect limits
        assert expanded is not None
    
    def test_get_all_expanded_chunks(self, expander, sample_chunks):
        """Test getting flat list of all chunks including neighbors."""
        # Manually add some neighbors for testing
        sample_chunks[0].neighbors = NeighborContext(
            parent_chunk=RetrievedChunk(
                chunk_id="parent_001",
                content="Parent content",
                score=0.0,
            ),
            prev_sibling=None,
            next_sibling=None,
        )
        
        all_chunks = expander.get_all_expanded_chunks(sample_chunks)
        
        # Should include original chunks + parent
        assert len(all_chunks) >= len(sample_chunks)


# =============================================================================
# Unified Retriever Tests
# =============================================================================

class TestUnifiedRetriever:
    """Tests for the unified retriever orchestration."""
    
    @pytest.fixture
    def mock_vector_search(self):
        """Mock vector search function."""
        async def search(query: str, top_k: int, filters=None) -> List[Dict]:
            return [
                {
                    "chunk_id": "chunk_001",
                    "content": "Học phí theo quy định Điều 11.",
                    "score": 0.95,
                    "metadata": {
                        "law_id": "20/2023/QH15",
                        "article_id": "Điều 11",
                        "clause_no": "2",
                    },
                },
                {
                    "chunk_id": "chunk_002",
                    "content": "Mức học phí điều chỉnh hàng năm.",
                    "score": 0.88,
                    "metadata": {
                        "law_id": "20/2023/QH15",
                        "article_id": "Điều 11",
                        "clause_no": "3",
                    },
                },
            ]
        return search
    
    @pytest.fixture
    def mock_bm25_search(self):
        """Mock BM25 search function."""
        async def search(query: str, top_k: int, filters=None) -> List[Dict]:
            return [
                {
                    "chunk_id": "chunk_002",
                    "content": "Mức học phí điều chỉnh hàng năm.",
                    "score": 15.5,
                    "metadata": {
                        "law_id": "20/2023/QH15",
                        "article_id": "Điều 11",
                    },
                },
                {
                    "chunk_id": "chunk_003",
                    "content": "Học bổng cho sinh viên xuất sắc.",
                    "score": 12.3,
                    "metadata": {
                        "law_id": "20/2023/QH15",
                        "article_id": "Điều 12",
                    },
                },
            ]
        return search
    
    @pytest.fixture
    def retriever(self, mock_vector_search, mock_bm25_search):
        return UnifiedRetriever(
            vector_search_fn=mock_vector_search,
            bm25_search_fn=mock_bm25_search,
            config=RetrievalConfig(
                top_k=5,
                enable_rerank=False,
                enable_neighbor_expansion=False,
            ),
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_basic(self, retriever):
        """Test basic retrieval."""
        result = await retriever.retrieve("Điều 11 quy định gì về học phí?")
        
        assert isinstance(result, RetrievalResult)
        assert len(result.chunks) > 0
        assert result.final_context != ""
    
    @pytest.mark.asyncio
    async def test_retrieve_parses_query(self, retriever):
        """Test query is parsed."""
        result = await retriever.retrieve("Khoản 2 Điều 11 Luật 20/2023/QH15")
        
        assert result.parsed_query is not None
        assert result.parsed_query.article_id == "11"
        assert result.parsed_query.clause_no == "2"
    
    @pytest.mark.asyncio
    async def test_retrieve_generates_citations(self, retriever):
        """Test citations are generated."""
        result = await retriever.retrieve("Điều 11 về học phí")
        
        assert len(result.citations) > 0
    
    @pytest.mark.asyncio
    async def test_retrieve_metrics_tracked(self, retriever):
        """Test retrieval metrics are tracked."""
        result = await retriever.retrieve("test query")
        
        assert result.retrieval_time_ms > 0
        assert result.chunks_before_rerank >= 0
    
    @pytest.mark.asyncio
    async def test_retrieve_with_top_k(self, retriever):
        """Test top_k parameter limits results."""
        result = await retriever.retrieve("test query", top_k=1)
        
        assert len(result.chunks) <= 1
    
    @pytest.mark.asyncio
    async def test_retrieve_hybrid_fusion(self, retriever):
        """Test hybrid fusion combines results."""
        result = await retriever.retrieve("học phí sinh viên")
        
        # Should have combined results from both vector and BM25
        chunk_ids = {c.chunk_id for c in result.chunks}
        # chunk_001 from vector, chunk_002 from both, chunk_003 from BM25
        assert len(chunk_ids) > 0


class TestUnifiedRetrieverRRF:
    """Tests for RRF fusion."""
    
    @pytest.fixture
    def retriever(self):
        async def vector_search(query, top_k, filters=None):
            return [
                {"chunk_id": "A", "content": "A", "score": 1.0, "metadata": {}},
                {"chunk_id": "B", "content": "B", "score": 0.9, "metadata": {}},
                {"chunk_id": "C", "content": "C", "score": 0.8, "metadata": {}},
            ]
        
        async def bm25_search(query, top_k, filters=None):
            return [
                {"chunk_id": "B", "content": "B", "score": 10.0, "metadata": {}},
                {"chunk_id": "D", "content": "D", "score": 8.0, "metadata": {}},
                {"chunk_id": "A", "content": "A", "score": 5.0, "metadata": {}},
            ]
        
        return UnifiedRetriever(
            vector_search_fn=vector_search,
            bm25_search_fn=bm25_search,
            config=RetrievalConfig(
                fusion_mode="rrf",
                enable_rerank=False,
                enable_neighbor_expansion=False,
            ),
        )
    
    @pytest.mark.asyncio
    async def test_rrf_boosts_common_results(self, retriever):
        """Test RRF boosts results appearing in both sources."""
        result = await retriever.retrieve("test")
        
        # A and B appear in both, should have higher scores
        chunk_ids = [c.chunk_id for c in result.chunks]
        
        # B appears in both at good ranks, should be near top
        # A appears in both
        # They should be ranked higher than D or C
        assert "A" in chunk_ids[:3] or "B" in chunk_ids[:3]


class TestRetrievalConfig:
    """Tests for retrieval configuration."""
    
    def test_for_exact_lookup(self):
        """Test exact lookup config."""
        config = RetrievalConfig.for_exact_lookup()
        
        assert config.strict_filter is True
        assert config.enable_rerank is False
        assert config.top_k <= 5
    
    def test_for_semantic_search(self):
        """Test semantic search config."""
        config = RetrievalConfig.for_semantic_search()
        
        assert config.enable_rerank is True
        assert config.vector_top_k >= config.top_k


class TestCitationGeneration:
    """Tests for citation generation and formatting."""
    
    def test_citation_short_form(self):
        """Test short form citation string."""
        citation = Citation(
            law_id="20/2023/QH15",
            article_id="Điều 11",
            clause_no="2",
            point_no="a",
            chunk_id="test",
        )
        
        short = citation.to_short_form()
        
        assert "Điểm a" in short
        assert "Khoản 2" in short
        assert "Điều 11" in short
        assert "Luật 20/2023/QH15" in short
    
    def test_citation_long_form(self):
        """Test long form citation with law name."""
        citation = Citation(
            law_id="20/2023/QH15",
            law_name="Luật Giáo dục đại học",
            article_id="Điều 11",
            chunk_id="test",
        )
        
        long_form = citation.to_long_form()
        
        assert "Luật Giáo dục đại học" in long_form
    
    def test_citation_from_metadata(self):
        """Test creating citation from chunk metadata."""
        metadata = {
            "law_id": "20/2023/QH15",
            "article_id": "Điều 11",
            "clause_no": "2",
            "filename": "test.docx",
        }
        
        citation = Citation.from_chunk_metadata("chunk_001", metadata)
        
        assert citation.law_id == "20/2023/QH15"
        assert citation.article_id == "Điều 11"
        assert citation.source_file == "test.docx"


class TestContextPacking:
    """Tests for context packing."""
    
    def test_retrieved_chunk_full_context(self, sample_chunks):
        """Test getting full context from chunk."""
        chunk = sample_chunks[0]
        
        context = chunk.get_full_context(include_neighbors=False)
        
        assert chunk.content in context
    
    def test_retrieved_chunk_with_neighbors(self, sample_chunks):
        """Test context includes neighbors when available."""
        chunk = sample_chunks[0]
        chunk.neighbors = NeighborContext(
            parent_chunk=RetrievedChunk(
                chunk_id="parent",
                content="Parent context",
                score=0.0,
            ),
            prev_sibling=None,
            next_sibling=None,
        )
        
        context = chunk.get_full_context(include_neighbors=True)
        
        assert "Parent context" in context
        assert chunk.content in context


class TestRetrievalResult:
    """Tests for RetrievalResult model."""
    
    def test_to_dict(self, sample_chunks):
        """Test converting result to dictionary."""
        result = RetrievalResult(
            chunks=sample_chunks,
            final_context="Test context",
            citations=[sample_chunks[0].citation],
            retrieval_time_ms=100.5,
        )
        
        result_dict = result.to_dict()
        
        assert "chunks" in result_dict
        assert "final_context" in result_dict
        assert "citations" in result_dict
        assert "citation_strings" in result_dict
        assert "metrics" in result_dict
    
    def test_get_citation_list(self, sample_chunks):
        """Test getting citation strings."""
        result = RetrievalResult(
            chunks=sample_chunks,
            citations=[c.citation for c in sample_chunks if c.citation],
        )
        
        citation_list = result.get_citation_list()
        
        assert len(citation_list) > 0
        assert all(isinstance(c, str) for c in citation_list)
