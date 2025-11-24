"""
End-to-End Integration Tests for Graph Pipeline

Tests the complete pipeline flow:
1. Document loading
2. Entity extraction
3. Relation extraction
4. Graph building
5. Neo4j storage

Requires:
- Docker Neo4j running on localhost:7687
- OpenAI API key (optional - can use mock)
- Weaviate running (for embedding deduplication)

Run with:
    pytest tests/integration/test_graph_pipeline_e2e.py -v

Author: GitHub Copilot
Date: November 2025
"""

import pytest
import asyncio
from typing import List, Dict, Any
import os
from pathlib import Path

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# Test Data
SAMPLE_DOCUMENT = """
# Quy định học vụ - Khoa KHMT

## Học phần Lập trình Python (CS101)

Học phần Lập trình Python là một môn học cơ bản thuộc Khoa Khoa học và Kỹ thuật Máy tính.

**Thông tin:**
- Mã học phần: CS101
- Số tín chỉ: 3
- Điều kiện tiên quyết: Không
- Học phần liên quan: Cấu trúc dữ liệu (CS201)

## Học phần Trí tuệ nhân tạo (CS301)

Học phần Trí tuệ nhân tạo thuộc Khoa KHMT.

**Thông tin:**
- Mã học phần: CS301
- Số tín chỉ: 4
- Điều kiện tiên quyết: Lập trình Python (CS101)
"""


@pytest.fixture(scope="module")
def neo4j_available() -> bool:
    """Check if Neo4j is available"""
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        # Try to connect
        async def test_connection():
            async with driver.session() as session:
                await session.run("RETURN 1")
        
        asyncio.run(test_connection())
        driver.close()
        return True
    except Exception as e:
        print(f"Neo4j not available: {e}")
        return False


@pytest.fixture(scope="module")
def openai_available() -> bool:
    """Check if OpenAI API is configured"""
    return bool(os.getenv("OPENAI_API_KEY"))


@pytest.fixture
async def clean_neo4j_database():
    """Clean Neo4j database before and after tests"""
    from neo4j import AsyncGraphDatabase
    
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password")
    )
    
    # Clean before test
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    
    yield
    
    # Clean after test
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    
    await driver.close()


class TestDocumentLoading:
    """Test document loading from various sources"""
    
    def test_load_text_document(self, tmp_path):
        """Test loading plain text document"""
        from indexing.graph_etl_pipeline import TextLoader
        
        # Create temp file
        doc_file = tmp_path / "test.txt"
        doc_file.write_text(SAMPLE_DOCUMENT)
        
        loader = TextLoader()
        documents = loader.load(str(doc_file))
        
        assert len(documents) == 1
        assert "Lập trình Python" in documents[0]["text"]
        assert documents[0]["metadata"]["source"] == str(doc_file)
    
    def test_load_markdown_document(self, tmp_path):
        """Test loading markdown document"""
        from indexing.graph_etl_pipeline import MarkdownLoader
        
        # Create temp markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text(SAMPLE_DOCUMENT)
        
        loader = MarkdownLoader()
        documents = loader.load(str(md_file))
        
        assert len(documents) >= 1
        assert any("Lập trình Python" in doc["text"] for doc in documents)


class TestEntityExtraction:
    """Test entity extraction pipeline"""
    
    @pytest.mark.asyncio
    async def test_extract_entities_from_document(self):
        """Test extracting entities from document"""
        from core.domain.models import Entity
        from indexing.category_guided_entity_extractor import CategoryGuidedEntityExtractor
        
        # Create extractor (mock mode for testing)
        extractor = CategoryGuidedEntityExtractor(use_mock=True)
        
        entities = await extractor.extract_entities(SAMPLE_DOCUMENT)
        
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)
        
        # Should find course entities
        course_entities = [e for e in entities if e.label == "HOC_PHAN"]
        assert len(course_entities) > 0


class TestRelationExtraction:
    """Test LLM relation extraction"""
    
    @pytest.mark.asyncio
    async def test_extract_relations_with_mock(self):
        """Test relation extraction using mock LLM"""
        from indexing.llm_relation_extractor import LLMRelationExtractor
        from adapters.llm.llm_client import MockLLMClient
        from core.domain.models import Entity
        
        # Create mock client
        mock_client = MockLLMClient()
        extractor = LLMRelationExtractor(llm_client=mock_client)
        
        # Sample entities
        entities = [
            Entity(text="Lập trình Python", label="HOC_PHAN", start_char=0, end_char=16),
            Entity(text="Khoa KHMT", label="KHOA", start_char=50, end_char=59),
        ]
        
        result = await extractor.extract_relations(SAMPLE_DOCUMENT, entities)
        
        assert result.cost_usd == 0.0  # Mock has no cost
        # Mock client should return some relations
        # (implementation depends on MockLLMClient)
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not configured")
    @pytest.mark.asyncio
    async def test_extract_relations_with_openai(self):
        """Test relation extraction using real OpenAI API"""
        from indexing.llm_relation_extractor import LLMRelationExtractor
        from adapters.llm.openai_client import OpenAIClient
        from core.domain.models import Entity
        
        # Create OpenAI client
        client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
        extractor = LLMRelationExtractor(llm_client=client)
        
        entities = [
            Entity(text="Lập trình Python", label="HOC_PHAN", start_char=40, end_char=56),
            Entity(text="Khoa Khoa học và Kỹ thuật Máy tính", label="KHOA", start_char=85, end_char=119),
        ]
        
        result = await extractor.extract_relations(SAMPLE_DOCUMENT[:500], entities)
        
        assert result.cost_usd > 0  # Real API has cost
        assert result.tokens_used > 0
        # Should extract THUOC_KHOA relation
        if result.relations:
            assert any(r.type == "THUOC_KHOA" for r in result.relations)


class TestGraphBuilding:
    """Test graph building from entities and relations"""
    
    @pytest.mark.asyncio
    async def test_build_graph_from_entities(self):
        """Test building graph nodes from entities"""
        from core.services.graph_builder_service import GraphBuilderService, EntityProcessor
        from core.services.graph_builder_config import GraphBuilderConfig
        from core.domain.models import Entity
        from unittest.mock import AsyncMock, Mock
        
        # Mock repository
        mock_repo = Mock()
        mock_repo.batch_create_nodes = AsyncMock(return_value=["n1", "n2"])
        mock_repo.batch_create_relationships = AsyncMock(return_value=["r1"])
        
        # Mock extractor
        mock_extractor = Mock()
        
        config = GraphBuilderConfig.default()
        service = GraphBuilderService(
            graph_repo=mock_repo,
            entity_extractor=mock_extractor,
            config=config
        )
        
        entities = [
            Entity(text="Python", label="HOC_PHAN", start_char=0, end_char=6),
            Entity(text="KHMT", label="KHOA", start_char=10, end_char=14),
        ]
        
        result = await service.build_from_entities(entities, [])
        
        assert result.created_nodes > 0
        assert mock_repo.batch_create_nodes.called


@pytest.mark.skipif(
    not os.path.exists("/var/run/docker.sock"),
    reason="Docker not available"
)
class TestNeo4jIntegration:
    """Test Neo4j database integration"""
    
    @pytest.mark.asyncio
    async def test_neo4j_connection(self, neo4j_available, clean_neo4j_database):
        """Test basic Neo4j connection"""
        if not neo4j_available:
            pytest.skip("Neo4j not available")
        
        from infrastructure.repositories.neo4j_graph_repository import Neo4jGraphRepository
        
        repo = Neo4jGraphRepository(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        
        # Test creating a node
        from core.domain.models import GraphNode
        from core.domain.graph_schema import NodeType
        
        node = GraphNode(
            id="test_001",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Test Course"}
        )
        
        node_id = await repo.create_node(node)
        assert node_id is not None
    
    @pytest.mark.asyncio
    async def test_create_nodes_and_relationships(self, neo4j_available, clean_neo4j_database):
        """Test creating nodes and relationships in Neo4j"""
        if not neo4j_available:
            pytest.skip("Neo4j not available")
        
        from infrastructure.repositories.neo4j_graph_repository import Neo4jGraphRepository
        from core.domain.models import GraphNode, GraphRelationship
        from core.domain.graph_schema import NodeType, RelationType
        
        repo = Neo4jGraphRepository(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        
        # Create two nodes
        node1 = GraphNode(
            id="hp_test_001",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Python", "ma_hoc_phan": "CS101"}
        )
        node2 = GraphNode(
            id="khoa_test_001",
            type=NodeType.KHOA,
            properties={"ten": "KHMT", "ma_khoa": "KHMT"}
        )
        
        id1 = await repo.create_node(node1)
        id2 = await repo.create_node(node2)
        
        # Create relationship
        rel = GraphRelationship(
            source_id=id1,
            target_id=id2,
            type=RelationType.THUOC_KHOA,
            properties={"confidence": 0.95}
        )
        
        rel_id = await repo.create_relationship(rel)
        assert rel_id is not None


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_pipeline_mock(self, tmp_path):
        """Test full pipeline with mock dependencies"""
        from indexing.graph_etl_pipeline import GraphETLPipeline, TextLoader
        from core.services.graph_builder_service import GraphBuilderService
        from core.services.graph_builder_config import GraphBuilderConfig
        from unittest.mock import AsyncMock, Mock
        
        # Create test document
        doc_file = tmp_path / "test.txt"
        doc_file.write_text(SAMPLE_DOCUMENT)
        
        # Mock graph builder
        mock_builder = AsyncMock()
        mock_builder.build_from_documents = AsyncMock(return_value=Mock(
            created_nodes=5,
            created_relationships=3,
            skipped_entities=0,
            errors=[]
        ))
        
        # Create pipeline
        pipeline = GraphETLPipeline(graph_builder=mock_builder)
        
        # Run pipeline
        result = await pipeline.load_and_process(str(doc_file))
        
        assert result.processed_documents == 1
        assert result.created_nodes == 5
        assert result.created_relationships == 3
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.skipif(
        not (os.getenv("OPENAI_API_KEY") and os.path.exists("/var/run/docker.sock")),
        reason="Requires OpenAI API and Docker Neo4j"
    )
    async def test_full_pipeline_real(self, tmp_path, neo4j_available, clean_neo4j_database):
        """Test full pipeline with real dependencies (OpenAI + Neo4j)"""
        if not neo4j_available:
            pytest.skip("Neo4j not available")
        
        from indexing.graph_etl_pipeline import GraphETLPipeline
        from core.services.graph_builder_service import GraphBuilderService
        from core.services.graph_builder_config import GraphBuilderConfig
        from infrastructure.repositories.neo4j_graph_repository import Neo4jGraphRepository
        from indexing.category_guided_entity_extractor import CategoryGuidedEntityExtractor
        
        # Create test document
        doc_file = tmp_path / "test.txt"
        doc_file.write_text(SAMPLE_DOCUMENT)
        
        # Real components
        repo = Neo4jGraphRepository(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        
        extractor = CategoryGuidedEntityExtractor(use_mock=False)
        
        config = GraphBuilderConfig.default()
        builder = GraphBuilderService(
            graph_repo=repo,
            entity_extractor=extractor,
            config=config
        )
        
        # Create pipeline
        pipeline = GraphETLPipeline(graph_builder=builder)
        
        # Run pipeline
        result = await pipeline.load_and_process(str(doc_file))
        
        assert result.processed_documents == 1
        assert result.created_nodes > 0
        print(f"Created {result.created_nodes} nodes and {result.created_relationships} relationships")


class TestQueryOptimizer:
    """Test query optimizer functionality"""
    
    @pytest.mark.asyncio
    async def test_query_caching(self):
        """Test query result caching"""
        from core.services.query_optimizer import QueryOptimizer
        from unittest.mock import AsyncMock, Mock
        
        optimizer = QueryOptimizer(enable_cache=True, cache_ttl=60)
        
        # Mock session
        mock_session = Mock()
        mock_result = Mock()
        mock_result.data = AsyncMock(return_value={"count": 10})
        
        async def mock_record_iterator():
            yield mock_result
        
        mock_session.run = AsyncMock(return_value=mock_record_iterator())
        
        query = "MATCH (n:HOC_PHAN) RETURN count(n)"
        
        # First call - cache miss
        result1 = await optimizer.execute_cached(mock_session, query)
        
        # Second call - cache hit (should not call session again)
        call_count_before = mock_session.run.call_count
        result2 = await optimizer.execute_cached(mock_session, query)
        call_count_after = mock_session.run.call_count
        
        # Should not make additional call
        assert call_count_after == call_count_before
        
        # Results should match
        assert result1 == result2
    
    def test_query_plan_analysis(self):
        """Test query plan analysis"""
        from core.services.query_optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer()
        
        query = """
        MATCH (hp:HOC_PHAN)-[:THUOC_KHOA]->(k:KHOA)
        WHERE hp.ma_hoc_phan = 'CS101'
        RETURN hp, k
        """
        
        plan = optimizer.analyze_query(query)
        
        assert plan.estimated_cost > 0
        assert plan.cache_key is not None
        
        # Should suggest index if not found
        if not optimizer._known_indexes:
            assert len(plan.optimization_suggestions) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
