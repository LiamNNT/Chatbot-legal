"""
Unit tests for LlamaIndex RAG integration.

Tests cover:
    - LlamaIndexHybridRetriever
    - RecursiveRankFusion
    - Postprocessors (Deduplication, Reranking, etc.)
    - LlamaIndexSearchService
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Import test targets
from core.domain.llamaindex_retriever import (
    LlamaIndexHybridRetriever,
    PortBasedVectorRetriever,
    PortBasedBM25Retriever,
    RecursiveRankFusion,
    RetrievalConfig,
    FusionMode,
    create_hybrid_retriever
)
from core.domain.llamaindex_postprocessors import (
    DeduplicationPostprocessor,
    CrossEncoderRerankPostprocessor,
    MetadataFilterPostprocessor,
    ScoreThresholdPostprocessor,
    CitationPostprocessor,
    TopKPostprocessor,
    PostprocessorPipeline,
    create_default_pipeline
)
from core.domain.llamaindex_search_service import (
    LlamaIndexSearchService,
    create_llamaindex_search_service
)
from core.domain.models import (
    SearchQuery,
    SearchMode,
    SearchResult,
    DocumentMetadata
)

# LlamaIndex imports
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_nodes() -> List[NodeWithScore]:
    """Create sample NodeWithScore objects for testing."""
    nodes = []
    for i in range(5):
        node = TextNode(
            text=f"Sample text content for document {i}",
            id_=f"doc_{i}",
            metadata={
                "doc_id": f"doc_{i}",
                "title": f"Document {i}",
                "doc_type": "regulation" if i % 2 == 0 else "syllabus",
                "faculty": "CNTT",
                "year": 2024,
                "page": i + 1
            }
        )
        nodes.append(NodeWithScore(node=node, score=1.0 - (i * 0.1)))
    return nodes


@pytest.fixture
def duplicate_nodes() -> List[NodeWithScore]:
    """Create nodes with duplicate content."""
    nodes = []
    for i in range(4):
        # Create pairs of duplicates
        text = f"Duplicate content {i // 2}"
        node = TextNode(
            text=text,
            id_=f"node_{i}",
            metadata={"doc_id": f"doc_{i // 2}"}
        )
        nodes.append(NodeWithScore(node=node, score=0.9 - (i * 0.1)))
    return nodes


@pytest.fixture
def mock_vector_repository():
    """Create mock vector search repository."""
    repo = AsyncMock()
    
    async def mock_search(query):
        return [
            SearchResult(
                text="Vector result 1",
                metadata=DocumentMetadata(doc_id="v1", title="Vector Doc 1"),
                score=0.95,
                source_type="vector"
            ),
            SearchResult(
                text="Vector result 2",
                metadata=DocumentMetadata(doc_id="v2", title="Vector Doc 2"),
                score=0.85,
                source_type="vector"
            )
        ]
    
    repo.search = mock_search
    return repo


@pytest.fixture
def mock_keyword_repository():
    """Create mock keyword search repository."""
    repo = AsyncMock()
    
    async def mock_search(query):
        return [
            SearchResult(
                text="BM25 result 1",
                metadata=DocumentMetadata(doc_id="b1", title="BM25 Doc 1"),
                score=0.90,
                source_type="bm25"
            ),
            SearchResult(
                text="BM25 result 2",
                metadata=DocumentMetadata(doc_id="v1", title="Vector Doc 1"),  # Duplicate
                score=0.80,
                source_type="bm25"
            )
        ]
    
    repo.search = mock_search
    return repo


@pytest.fixture
def mock_reranking_service():
    """Create mock reranking service."""
    service = AsyncMock()
    service.is_available.return_value = True
    
    async def mock_rerank(query, results, top_k=None):
        # Simply return results with slightly modified scores
        for i, r in enumerate(results):
            r.rerank_score = 0.9 - (i * 0.1)
        return results[:top_k] if top_k else results
    
    service.rerank = mock_rerank
    return service


# =============================================================================
# RecursiveRankFusion Tests
# =============================================================================

class TestRecursiveRankFusion:
    """Tests for RRF algorithm."""
    
    def test_fuse_empty_lists(self):
        """Test fusion with empty input."""
        result = RecursiveRankFusion.fuse([])
        assert result == []
    
    def test_fuse_single_list(self, sample_nodes):
        """Test fusion with single result list."""
        result = RecursiveRankFusion.fuse([sample_nodes])
        
        assert len(result) == len(sample_nodes)
        # Order should be preserved (RRF with single list)
        for i, node in enumerate(result):
            assert node.node.id_ == f"doc_{i}"
    
    def test_fuse_two_lists_with_overlap(self):
        """Test fusion with overlapping results."""
        # List 1: doc_a, doc_b
        list1 = [
            NodeWithScore(node=TextNode(text="A", id_="doc_a"), score=0.9),
            NodeWithScore(node=TextNode(text="B", id_="doc_b"), score=0.8),
        ]
        
        # List 2: doc_b, doc_c (doc_b appears in both)
        list2 = [
            NodeWithScore(node=TextNode(text="B", id_="doc_b"), score=0.85),
            NodeWithScore(node=TextNode(text="C", id_="doc_c"), score=0.75),
        ]
        
        result = RecursiveRankFusion.fuse([list1, list2], k=60)
        
        # doc_b should rank highest due to appearing in both lists
        assert len(result) == 3  # a, b, c
        
        # Find doc_b's RRF score (should be highest)
        doc_b = next(n for n in result if n.node.id_ == "doc_b")
        doc_a = next(n for n in result if n.node.id_ == "doc_a")
        
        assert doc_b.score > doc_a.score  # doc_b has contributions from both lists
    
    def test_fuse_with_weights(self):
        """Test fusion with custom weights."""
        list1 = [
            NodeWithScore(node=TextNode(text="A", id_="doc_a"), score=0.9),
        ]
        list2 = [
            NodeWithScore(node=TextNode(text="B", id_="doc_b"), score=0.9),
        ]
        
        # Give much higher weight to list1
        result = RecursiveRankFusion.fuse(
            [list1, list2],
            weights=[0.9, 0.1],
            k=60
        )
        
        assert len(result) == 2
        # doc_a should have higher score due to higher weight
        assert result[0].node.id_ == "doc_a"
    
    def test_fuse_with_top_k(self, sample_nodes):
        """Test fusion with top_k limit."""
        result = RecursiveRankFusion.fuse([sample_nodes], top_k=2)
        
        assert len(result) == 2


# =============================================================================
# Postprocessor Tests
# =============================================================================

class TestDeduplicationPostprocessor:
    """Tests for deduplication postprocessor."""
    
    def test_dedup_removes_duplicates(self, duplicate_nodes):
        """Test that duplicates are removed."""
        pp = DeduplicationPostprocessor(method="content_prefix")
        
        result = pp._postprocess_nodes(duplicate_nodes)
        
        # Should have 2 unique texts instead of 4
        assert len(result) == 2
    
    def test_dedup_keeps_highest_score(self, duplicate_nodes):
        """Test that highest scoring duplicate is kept."""
        pp = DeduplicationPostprocessor(
            method="content_prefix",
            keep_highest_score=True
        )
        
        result = pp._postprocess_nodes(duplicate_nodes)
        
        # Check scores are from highest-scoring duplicates
        for node in result:
            assert node.score >= 0.7  # Highest scores for each pair
    
    def test_dedup_by_node_id(self):
        """Test deduplication by node ID."""
        nodes = [
            NodeWithScore(node=TextNode(text="A", id_="same_id"), score=0.9),
            NodeWithScore(node=TextNode(text="B", id_="same_id"), score=0.8),
            NodeWithScore(node=TextNode(text="C", id_="other_id"), score=0.7),
        ]
        
        pp = DeduplicationPostprocessor(method="node_id")
        result = pp._postprocess_nodes(nodes)
        
        assert len(result) == 2  # same_id and other_id
    
    def test_dedup_empty_list(self):
        """Test deduplication with empty input."""
        pp = DeduplicationPostprocessor()
        result = pp._postprocess_nodes([])
        
        assert result == []


class TestMetadataFilterPostprocessor:
    """Tests for metadata filtering postprocessor."""
    
    def test_filter_by_doc_type(self, sample_nodes):
        """Test filtering by document type."""
        pp = MetadataFilterPostprocessor(doc_types=["regulation"])
        
        result = pp._postprocess_nodes(sample_nodes)
        
        # Only even-indexed nodes have doc_type="regulation"
        assert len(result) == 3  # nodes 0, 2, 4
        for node in result:
            assert node.node.metadata["doc_type"] == "regulation"
    
    def test_filter_by_faculty(self, sample_nodes):
        """Test filtering by faculty."""
        pp = MetadataFilterPostprocessor(faculties=["CNTT"])
        
        result = pp._postprocess_nodes(sample_nodes)
        
        # All nodes have faculty="CNTT"
        assert len(result) == len(sample_nodes)
    
    def test_filter_by_year(self, sample_nodes):
        """Test filtering by year."""
        pp = MetadataFilterPostprocessor(years=[2024])
        
        result = pp._postprocess_nodes(sample_nodes)
        
        assert len(result) == len(sample_nodes)
    
    def test_filter_multiple_criteria(self, sample_nodes):
        """Test filtering with multiple criteria."""
        pp = MetadataFilterPostprocessor(
            doc_types=["regulation"],
            years=[2024]
        )
        
        result = pp._postprocess_nodes(sample_nodes)
        
        assert len(result) == 3  # regulation AND 2024


class TestScoreThresholdPostprocessor:
    """Tests for score threshold postprocessor."""
    
    def test_filter_below_threshold(self, sample_nodes):
        """Test filtering by minimum score."""
        pp = ScoreThresholdPostprocessor(min_score=0.8)
        
        result = pp._postprocess_nodes(sample_nodes)
        
        # Only nodes with score >= 0.8 should remain
        for node in result:
            assert node.score >= 0.8
    
    def test_zero_threshold(self, sample_nodes):
        """Test with zero threshold (no filtering)."""
        pp = ScoreThresholdPostprocessor(min_score=0.0)
        
        result = pp._postprocess_nodes(sample_nodes)
        
        assert len(result) == len(sample_nodes)


class TestCitationPostprocessor:
    """Tests for citation postprocessor."""
    
    def test_adds_citations(self, sample_nodes):
        """Test that citations are added."""
        pp = CitationPostprocessor()
        
        result = pp._postprocess_nodes(sample_nodes)
        
        for i, node in enumerate(result, start=1):
            assert "citation" in node.node.metadata
            assert node.node.metadata["citation_index"] == i
    
    def test_citation_format(self, sample_nodes):
        """Test citation format."""
        pp = CitationPostprocessor()
        
        result = pp._postprocess_nodes(sample_nodes)
        
        citation = result[0].node.metadata["citation"]
        assert "index" in citation
        assert "title" in citation
        assert "formatted" in citation


class TestTopKPostprocessor:
    """Tests for top-k postprocessor."""
    
    def test_limits_to_top_k(self, sample_nodes):
        """Test that results are limited to k."""
        pp = TopKPostprocessor(top_k=2)
        
        result = pp._postprocess_nodes(sample_nodes)
        
        assert len(result) == 2
    
    def test_top_k_larger_than_input(self, sample_nodes):
        """Test when top_k is larger than input."""
        pp = TopKPostprocessor(top_k=100)
        
        result = pp._postprocess_nodes(sample_nodes)
        
        assert len(result) == len(sample_nodes)


# =============================================================================
# Pipeline Tests
# =============================================================================

class TestPostprocessorPipeline:
    """Tests for postprocessor pipeline."""
    
    def test_pipeline_chain(self, sample_nodes):
        """Test that pipeline chains postprocessors."""
        pipeline = (
            PostprocessorPipeline()
            .add(MetadataFilterPostprocessor(doc_types=["regulation"]))
            .add(TopKPostprocessor(top_k=2))
            .build()
        )
        
        result = pipeline.process(sample_nodes)
        
        assert len(result) == 2
        for node in result:
            assert node.node.metadata["doc_type"] == "regulation"
    
    def test_empty_pipeline(self, sample_nodes):
        """Test empty pipeline returns input unchanged."""
        pipeline = PostprocessorPipeline().build()
        
        result = pipeline.process(sample_nodes)
        
        assert result == sample_nodes
    
    @pytest.mark.asyncio
    async def test_pipeline_async(self, sample_nodes):
        """Test async pipeline execution."""
        pipeline = (
            PostprocessorPipeline()
            .add(DeduplicationPostprocessor())
            .add(TopKPostprocessor(top_k=3))
            .build()
        )
        
        result = await pipeline.process_async(sample_nodes)
        
        assert len(result) == 3


# =============================================================================
# Retriever Tests
# =============================================================================

class TestPortBasedVectorRetriever:
    """Tests for port-based vector retriever."""
    
    @pytest.mark.asyncio
    async def test_vector_retrieval(self, mock_vector_repository):
        """Test vector retrieval through port."""
        retriever = PortBasedVectorRetriever(
            vector_repository=mock_vector_repository,
            top_k=5
        )
        
        query_bundle = QueryBundle(query_str="test query")
        result = await retriever._aretrieve(query_bundle)
        
        assert len(result) == 2
        assert result[0].node.metadata["source_type"] == "vector"


class TestPortBasedBM25Retriever:
    """Tests for port-based BM25 retriever."""
    
    @pytest.mark.asyncio
    async def test_bm25_retrieval(self, mock_keyword_repository):
        """Test BM25 retrieval through port."""
        retriever = PortBasedBM25Retriever(
            keyword_repository=mock_keyword_repository,
            top_k=5
        )
        
        query_bundle = QueryBundle(query_str="test query")
        result = await retriever._aretrieve(query_bundle)
        
        assert len(result) == 2
        assert result[0].node.metadata["source_type"] == "bm25"


class TestLlamaIndexHybridRetriever:
    """Tests for hybrid retriever."""
    
    @pytest.mark.asyncio
    async def test_hybrid_retrieval(
        self, 
        mock_vector_repository, 
        mock_keyword_repository
    ):
        """Test hybrid retrieval with RRF fusion."""
        config = RetrievalConfig(
            vector_top_k=5,
            bm25_top_k=5,
            final_top_k=3,
            fusion_mode=FusionMode.RECIPROCAL_RANK
        )
        
        retriever = LlamaIndexHybridRetriever(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository,
            config=config
        )
        
        query_bundle = QueryBundle(query_str="test query")
        result = await retriever._aretrieve(query_bundle)
        
        # Should have fused results
        assert len(result) <= 3
        
        # Check source type is fused
        for node in result:
            assert node.node.metadata.get("source_type") == "fused"


# =============================================================================
# Search Service Tests
# =============================================================================

class TestLlamaIndexSearchService:
    """Tests for LlamaIndex search service."""
    
    @pytest.mark.asyncio
    async def test_vector_search(
        self, 
        mock_vector_repository,
        mock_keyword_repository
    ):
        """Test vector-only search."""
        service = LlamaIndexSearchService(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository
        )
        
        query = SearchQuery(
            text="test query",
            top_k=5,
            search_mode=SearchMode.VECTOR
        )
        
        response = await service.search(query)
        
        assert response.total_hits > 0
        assert response.search_metadata["search_mode"] == "vector"
        assert response.search_metadata["engine"] == "llamaindex"
    
    @pytest.mark.asyncio
    async def test_hybrid_search(
        self, 
        mock_vector_repository,
        mock_keyword_repository
    ):
        """Test hybrid search."""
        service = LlamaIndexSearchService(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository
        )
        
        query = SearchQuery(
            text="test query",
            top_k=5,
            search_mode=SearchMode.HYBRID
        )
        
        response = await service.search(query)
        
        assert response.total_hits > 0
        assert response.search_metadata["search_mode"] == "hybrid"
    
    @pytest.mark.asyncio
    async def test_search_with_reranking(
        self,
        mock_vector_repository,
        mock_keyword_repository,
        mock_reranking_service
    ):
        """Test search with reranking enabled."""
        service = LlamaIndexSearchService(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository,
            reranking_service=mock_reranking_service
        )
        
        query = SearchQuery(
            text="test query",
            top_k=5,
            search_mode=SearchMode.HYBRID,
            use_rerank=True
        )
        
        response = await service.search(query)
        
        assert response.total_hits > 0
        assert response.search_metadata["use_rerank"] is True
    
    @pytest.mark.asyncio
    async def test_search_with_filters(
        self,
        mock_vector_repository,
        mock_keyword_repository
    ):
        """Test search with metadata filters."""
        service = LlamaIndexSearchService(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository
        )
        
        query = SearchQuery(
            text="test query",
            top_k=5,
            search_mode=SearchMode.HYBRID,
            filters={"doc_types": ["regulation"]}
        )
        
        response = await service.search(query)
        
        assert response.search_metadata["filters_applied"] is True


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_create_hybrid_retriever(
        self,
        mock_vector_repository,
        mock_keyword_repository
    ):
        """Test hybrid retriever factory."""
        retriever = create_hybrid_retriever(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository,
            vector_weight=0.6,
            bm25_weight=0.4,
            top_k=10
        )
        
        assert isinstance(retriever, LlamaIndexHybridRetriever)
        assert retriever.config.vector_weight == 0.6
        assert retriever.config.bm25_weight == 0.4
    
    def test_create_llamaindex_search_service(
        self,
        mock_vector_repository,
        mock_keyword_repository
    ):
        """Test search service factory."""
        service = create_llamaindex_search_service(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository,
            vector_weight=0.5,
            bm25_weight=0.5,
            top_k=10
        )
        
        assert isinstance(service, LlamaIndexSearchService)
    
    def test_create_default_pipeline(self):
        """Test default pipeline factory."""
        pipeline = create_default_pipeline(
            enable_rerank=True,
            top_k=10
        )
        
        assert isinstance(pipeline, PostprocessorPipeline)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(
        self,
        mock_vector_repository,
        mock_keyword_repository,
        mock_reranking_service
    ):
        """Test full retrieval and postprocessing pipeline."""
        # Create service
        service = LlamaIndexSearchService(
            vector_repository=mock_vector_repository,
            keyword_repository=mock_keyword_repository,
            reranking_service=mock_reranking_service
        )
        
        # Execute search (note: need_citation is not a standard SearchQuery field)
        query = SearchQuery(
            text="What are the graduation requirements?",
            top_k=5,
            search_mode=SearchMode.HYBRID,
            use_rerank=True
        )
        
        response = await service.search(query)
        
        # Verify response
        assert response.total_hits > 0
        assert response.latency_ms >= 0
        assert response.search_metadata["engine"] == "llamaindex"
        
        # Check results have expected structure
        for result in response.results:
            assert result.text
            assert result.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
