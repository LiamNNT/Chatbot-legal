"""
Unit tests for Graph Builder Service

Tests cover:
- Entity validation and normalization
- Relationship processing
- Deduplication strategies (exact, fuzzy, embedding, hybrid)
- Batch processing with retry logic
- Error handling and validation
- Configuration presets
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import asyncio

from core.services.graph_builder_service import (
    GraphBuilderService,
    EntityProcessor,
    RelationshipProcessor,
    ConflictResolver,
    BatchProcessor,
    GraphBuildResult,
)
from core.services.graph_builder_config import (
    GraphBuilderConfig,
    DeduplicationStrategy,
    ConflictResolutionStrategy,
    ValidationConfig,
)
from core.domain.models import GraphNode, GraphRelationship, Entity, Relation
from core.domain.graph_schema import NodeType, RelationType


# Test Data Fixtures
@pytest.fixture
def sample_entities() -> List[Entity]:
    """Sample entities for testing"""
    return [
        Entity(
            text="Học phần Lập trình Python",
            label="HOC_PHAN",
            start_char=0,
            end_char=25,
            metadata={"confidence": 0.95}
        ),
        Entity(
            text="Khoa Khoa học và Kỹ thuật Máy tính",
            label="KHOA",
            start_char=30,
            end_char=64,
            metadata={"confidence": 0.90}
        ),
        Entity(
            text="Lập trình Python",  # Duplicate with fuzzy match
            label="HOC_PHAN",
            start_char=100,
            end_char=116,
            metadata={"confidence": 0.85}
        ),
    ]


@pytest.fixture
def sample_relations(sample_entities) -> List[Relation]:
    """Sample relations for testing"""
    return [
        Relation(
            source=sample_entities[0],
            target=sample_entities[1],
            relation_type="THUOC_KHOA",
            confidence=0.92,
            evidence="Học phần thuộc Khoa KHMT",
            metadata={"extracted_by": "llm"}
        )
    ]


@pytest.fixture
def sample_graph_nodes() -> List[GraphNode]:
    """Sample graph nodes for testing"""
    return [
        GraphNode(
            id="hp_001",
            type=NodeType.HOC_PHAN,
            properties={
                "ma_hoc_phan": "CS101",
                "ten": "Lập trình Python",
                "so_tin_chi": 3
            },
            embedding=[0.1] * 768
        ),
        GraphNode(
            id="khoa_001",
            type=NodeType.KHOA,
            properties={
                "ma_khoa": "KHMT",
                "ten": "Khoa Khoa học và Kỹ thuật Máy tính"
            },
            embedding=[0.2] * 768
        ),
    ]


@pytest.fixture
def mock_graph_repository():
    """Mock GraphRepository"""
    repo = Mock()
    repo.create_node = AsyncMock(return_value="node_001")
    repo.create_relationship = AsyncMock(return_value="rel_001")
    repo.find_nodes_by_property = AsyncMock(return_value=[])
    repo.batch_create_nodes = AsyncMock(return_value=["n1", "n2", "n3"])
    repo.batch_create_relationships = AsyncMock(return_value=["r1", "r2"])
    return repo


@pytest.fixture
def mock_entity_extractor():
    """Mock CategoryGuidedEntityExtractor"""
    extractor = Mock()
    extractor.extract_entities = AsyncMock(return_value=[])
    return extractor


@pytest.fixture
def default_config() -> GraphBuilderConfig:
    """Default configuration for testing"""
    return GraphBuilderConfig.default()


# EntityProcessor Tests
class TestEntityProcessor:
    """Test EntityProcessor component"""

    def test_validate_entity_valid(self, sample_entities):
        """Test validation of valid entity"""
        processor = EntityProcessor(ValidationConfig())
        entity = sample_entities[0]
        
        is_valid, error = processor.validate_entity(entity)
        
        assert is_valid is True
        assert error is None

    def test_validate_entity_invalid_label(self):
        """Test validation rejects invalid label"""
        processor = EntityProcessor(ValidationConfig())
        entity = Entity(
            text="Test",
            label="INVALID_LABEL",
            start_char=0,
            end_char=4
        )
        
        is_valid, error = processor.validate_entity(entity)
        
        assert is_valid is False
        assert "Invalid entity label" in error

    def test_validate_entity_low_confidence(self):
        """Test validation rejects low confidence"""
        config = ValidationConfig(min_entity_confidence=0.9)
        processor = EntityProcessor(config)
        entity = Entity(
            text="Test",
            label="HOC_PHAN",
            start_char=0,
            end_char=4,
            metadata={"confidence": 0.5}
        )
        
        is_valid, error = processor.validate_entity(entity)
        
        assert is_valid is False
        assert "confidence" in error.lower()

    def test_normalize_entity_text(self):
        """Test text normalization"""
        processor = EntityProcessor(ValidationConfig())
        entity = Entity(
            text="  Học  Phần   Python  ",
            label="HOC_PHAN",
            start_char=0,
            end_char=23
        )
        
        normalized = processor.normalize_entity(entity)
        
        assert normalized.text == "Học Phần Python"
        assert " " not in normalized.text.strip()

    def test_convert_to_graph_node(self, sample_entities):
        """Test converting entity to GraphNode"""
        processor = EntityProcessor(ValidationConfig())
        entity = sample_entities[0]
        
        node = processor.convert_to_graph_node(entity)
        
        assert node.type == NodeType.HOC_PHAN
        assert "ten" in node.properties
        assert node.properties["ten"] == entity.text


# RelationshipProcessor Tests
class TestRelationshipProcessor:
    """Test RelationshipProcessor component"""

    def test_validate_relation_valid(self, sample_relations):
        """Test validation of valid relation"""
        config = ValidationConfig(min_relation_confidence=0.8)
        processor = RelationshipProcessor(config)
        relation = sample_relations[0]
        
        is_valid, error = processor.validate_relation(relation)
        
        assert is_valid is True
        assert error is None

    def test_validate_relation_low_confidence(self, sample_relations):
        """Test validation rejects low confidence relation"""
        config = ValidationConfig(min_relation_confidence=0.95)
        processor = RelationshipProcessor(config)
        relation = sample_relations[0]
        relation.confidence = 0.5
        
        is_valid, error = processor.validate_relation(relation)
        
        assert is_valid is False
        assert "confidence" in error.lower()

    def test_validate_relation_invalid_type(self, sample_entities):
        """Test validation rejects invalid relation type"""
        processor = RelationshipProcessor(ValidationConfig())
        relation = Relation(
            source=sample_entities[0],
            target=sample_entities[1],
            relation_type="INVALID_TYPE",
            confidence=0.9
        )
        
        is_valid, error = processor.validate_relation(relation)
        
        assert is_valid is False
        assert "Invalid relation type" in error

    def test_convert_to_graph_relationship(self, sample_relations, sample_graph_nodes):
        """Test converting relation to GraphRelationship"""
        processor = RelationshipProcessor(ValidationConfig())
        relation = sample_relations[0]
        
        # Map entities to nodes
        entity_to_node = {
            relation.source: sample_graph_nodes[0],
            relation.target: sample_graph_nodes[1],
        }
        
        graph_rel = processor.convert_to_graph_relationship(relation, entity_to_node)
        
        assert graph_rel.type == RelationType.THUOC_KHOA
        assert graph_rel.source_id == sample_graph_nodes[0].id
        assert graph_rel.target_id == sample_graph_nodes[1].id
        assert graph_rel.properties["confidence"] == relation.confidence


# ConflictResolver Tests
class TestConflictResolver:
    """Test ConflictResolver with different strategies"""

    def test_exact_match_deduplication(self, sample_graph_nodes):
        """Test exact match deduplication"""
        resolver = ConflictResolver(DeduplicationStrategy.EXACT)
        
        # Create duplicate with exact same properties
        duplicate = GraphNode(
            id="hp_002",
            type=NodeType.HOC_PHAN,
            properties={
                "ma_hoc_phan": "CS101",
                "ten": "Lập trình Python",
                "so_tin_chi": 3
            }
        )
        
        nodes = sample_graph_nodes + [duplicate]
        deduplicated = resolver.deduplicate_nodes(nodes)
        
        # Should keep only one
        assert len(deduplicated) == 2  # Original 2 different nodes
        
        # Verify CS101 appears only once
        cs101_nodes = [n for n in deduplicated if n.properties.get("ma_hoc_phan") == "CS101"]
        assert len(cs101_nodes) == 1

    def test_fuzzy_match_deduplication(self):
        """Test fuzzy string matching deduplication"""
        resolver = ConflictResolver(DeduplicationStrategy.FUZZY)
        
        nodes = [
            GraphNode(
                id="hp_001",
                type=NodeType.HOC_PHAN,
                properties={"ten": "Lập trình Python"}
            ),
            GraphNode(
                id="hp_002",
                type=NodeType.HOC_PHAN,
                properties={"ten": "Lap trinh Python"}  # Similar with fuzzy match
            ),
            GraphNode(
                id="hp_003",
                type=NodeType.HOC_PHAN,
                properties={"ten": "Cơ sở dữ liệu"}  # Different
            ),
        ]
        
        deduplicated = resolver.deduplicate_nodes(nodes)
        
        # Should merge similar Python courses
        assert len(deduplicated) == 2

    def test_merge_strategy_union(self, sample_graph_nodes):
        """Test UNION merge strategy"""
        resolver = ConflictResolver(
            DeduplicationStrategy.EXACT,
            ConflictResolutionStrategy.UNION
        )
        
        node1 = GraphNode(
            id="hp_001",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Python", "so_tin_chi": 3}
        )
        node2 = GraphNode(
            id="hp_002",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Python", "mo_ta": "Lập trình cơ bản"}
        )
        
        merged = resolver.merge_nodes([node1, node2])
        
        # Should have all properties
        assert "so_tin_chi" in merged.properties
        assert "mo_ta" in merged.properties
        assert merged.properties["ten"] == "Python"

    def test_merge_strategy_keep_first(self):
        """Test KEEP_FIRST merge strategy"""
        resolver = ConflictResolver(
            DeduplicationStrategy.EXACT,
            ConflictResolutionStrategy.KEEP_FIRST
        )
        
        node1 = GraphNode(
            id="hp_001",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Python", "so_tin_chi": 3}
        )
        node2 = GraphNode(
            id="hp_002",
            type=NodeType.HOC_PHAN,
            properties={"ten": "Python", "so_tin_chi": 4}  # Different
        )
        
        merged = resolver.merge_nodes([node1, node2])
        
        # Should keep first value
        assert merged.properties["so_tin_chi"] == 3


# BatchProcessor Tests
class TestBatchProcessor:
    """Test BatchProcessor with retry logic"""

    @pytest.mark.asyncio
    async def test_process_batch_success(self, mock_graph_repository):
        """Test successful batch processing"""
        from core.services.graph_builder_config import BatchConfig
        
        config = BatchConfig(batch_size=10, max_retries=3)
        processor = BatchProcessor(config, mock_graph_repository)
        
        nodes = [
            GraphNode(id=f"n{i}", type=NodeType.HOC_PHAN, properties={"ten": f"Node {i}"})
            for i in range(25)
        ]
        
        result = await processor.create_nodes_batch(nodes)
        
        assert result["total"] == 25
        assert result["success"] == 25
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_retry(self, mock_graph_repository):
        """Test batch processing with retry on failure"""
        from core.services.graph_builder_config import BatchConfig
        
        config = BatchConfig(batch_size=10, max_retries=3)
        processor = BatchProcessor(config, mock_graph_repository)
        
        # Simulate failure then success
        call_count = 0
        async def mock_create_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary network error")
            return ["n1", "n2"]
        
        mock_graph_repository.batch_create_nodes = AsyncMock(side_effect=mock_create_with_failure)
        
        nodes = [
            GraphNode(id=f"n{i}", type=NodeType.HOC_PHAN, properties={"ten": f"Node {i}"})
            for i in range(2)
        ]
        
        result = await processor.create_nodes_batch(nodes)
        
        # Should retry and succeed
        assert call_count == 2  # 1 failure + 1 retry success
        assert result["success"] > 0


# GraphBuilderService Integration Tests
class TestGraphBuilderService:
    """Test GraphBuilderService integration"""

    @pytest.mark.asyncio
    async def test_build_from_entities_success(
        self, 
        mock_graph_repository, 
        mock_entity_extractor,
        sample_entities,
        sample_relations,
        default_config
    ):
        """Test building graph from entities and relations"""
        service = GraphBuilderService(
            graph_repo=mock_graph_repository,
            entity_extractor=mock_entity_extractor,
            config=default_config
        )
        
        result = await service.build_from_entities(sample_entities, sample_relations)
        
        assert isinstance(result, GraphBuildResult)
        assert result.created_nodes > 0
        assert result.created_relationships >= 0
        assert result.skipped_entities >= 0

    @pytest.mark.asyncio
    async def test_build_from_documents(
        self,
        mock_graph_repository,
        mock_entity_extractor,
        sample_entities,
        default_config
    ):
        """Test building graph from documents"""
        # Mock entity extraction
        mock_entity_extractor.extract_entities = AsyncMock(return_value=sample_entities)
        
        service = GraphBuilderService(
            graph_repo=mock_graph_repository,
            entity_extractor=mock_entity_extractor,
            config=default_config
        )
        
        documents = [
            {
                "text": "Học phần Lập trình Python thuộc Khoa KHMT",
                "metadata": {"source": "quy_dinh.pdf"}
            }
        ]
        
        result = await service.build_from_documents(documents)
        
        assert isinstance(result, GraphBuildResult)
        assert mock_entity_extractor.extract_entities.called

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        mock_graph_repository,
        mock_entity_extractor,
        default_config
    ):
        """Test error handling in graph building"""
        # Mock repository failure
        mock_graph_repository.batch_create_nodes = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        
        service = GraphBuilderService(
            graph_repo=mock_graph_repository,
            entity_extractor=mock_entity_extractor,
            config=default_config
        )
        
        entities = [
            Entity(text="Test", label="HOC_PHAN", start_char=0, end_char=4)
        ]
        
        result = await service.build_from_entities(entities, [])
        
        # Should handle error gracefully
        assert len(result.errors) > 0
        assert "Database connection error" in str(result.errors)


# Configuration Tests
class TestGraphBuilderConfig:
    """Test GraphBuilderConfig presets"""

    def test_default_config(self):
        """Test default configuration preset"""
        config = GraphBuilderConfig.default()
        
        assert config.deduplication_strategy == DeduplicationStrategy.FUZZY
        assert config.batch_config.batch_size == 100
        assert config.enable_caching is True

    def test_high_performance_config(self):
        """Test high performance preset"""
        config = GraphBuilderConfig.high_performance()
        
        assert config.deduplication_strategy == DeduplicationStrategy.EXACT
        assert config.batch_config.batch_size == 500
        assert config.validation_config.strict_validation is False

    def test_high_quality_config(self):
        """Test high quality preset"""
        config = GraphBuilderConfig.high_quality()
        
        assert config.deduplication_strategy == DeduplicationStrategy.HYBRID
        assert config.validation_config.strict_validation is True
        assert config.validation_config.min_entity_confidence == 0.9


# Performance Tests
class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, mock_graph_repository):
        """Test processing large batches"""
        from core.services.graph_builder_config import BatchConfig
        import time
        
        config = BatchConfig(batch_size=100, max_retries=1)
        processor = BatchProcessor(config, mock_graph_repository)
        
        # Create 1000 nodes
        nodes = [
            GraphNode(
                id=f"n{i}", 
                type=NodeType.HOC_PHAN, 
                properties={"ten": f"Node {i}"}
            )
            for i in range(1000)
        ]
        
        start_time = time.time()
        result = await processor.create_nodes_batch(nodes)
        elapsed = time.time() - start_time
        
        assert result["success"] == 1000
        assert elapsed < 5.0  # Should complete in reasonable time
        print(f"Processed 1000 nodes in {elapsed:.2f}s")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
