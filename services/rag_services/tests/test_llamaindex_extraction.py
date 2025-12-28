"""
Tests for LlamaIndex Extraction Pipeline.

Tests the LlamaParse and PropertyGraphIndex integration for
knowledge graph extraction from PDF documents.
"""

import asyncio
import pytest
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.extraction.llamaindex_extractor import (
    ExtractionConfig,
    EntityType,
    RelationType,
    ExtractedEntity,
    ExtractedRelation,
    ParsedDocument,
    ExtractionResult,
    LlamaParseDocumentParser,
    PropertyGraphKGExtractor,
    LlamaIndexExtractionService,
    VIETNAMESE_ACADEMIC_SCHEMA
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_config():
    """Create sample extraction config."""
    return ExtractionConfig(
        llama_cloud_api_key="test_key",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test_password",
        llm_model="gpt-4o-mini",
        llm_api_key="test_llm_key",
        llm_base_url="https://api.openai.com/v1"
    )


@pytest.fixture
def sample_markdown_content():
    """Sample parsed markdown content with Vietnamese legal structure."""
    return """
# Quyết định số 790/QĐ-ĐHCNTT

## Chương I: Quy định chung

### Điều 1: Phạm vi điều chỉnh

Quy chế này quy định về công tác đào tạo đại học hệ chính quy theo hệ thống tín chỉ tại Trường Đại học Công nghệ Thông tin.

### Điều 2: Đối tượng áp dụng

1. Sinh viên hệ chính quy
2. Sinh viên chương trình tiên tiến (CTTT)
3. Sinh viên chương trình chất lượng cao (CLC)

### Điều 5: Điều kiện đăng ký môn học

| STT | Môn học | Số tín chỉ | Điều kiện tiên quyết |
|-----|---------|------------|---------------------|
| 1   | Anh văn 2 | 3 | Anh văn 1 |
| 2   | Toán cao cấp 2 | 3 | Toán cao cấp 1 |

Sinh viên phải hoàn thành môn tiên quyết trước khi đăng ký.

### Điều 10: Điều kiện miễn học Anh văn

Sinh viên đạt chứng chỉ IELTS 6.0 hoặc TOEIC 600 được miễn học Anh văn cơ bản.
"""


@pytest.fixture
def sample_chunks(sample_markdown_content):
    """Create sample chunks from content."""
    return [
        {
            "id": "chunk_0",
            "content": "Quy chế này quy định về công tác đào tạo đại học hệ chính quy theo hệ thống tín chỉ tại Trường Đại học Công nghệ Thông tin.",
            "is_article": False
        },
        {
            "id": "chunk_1", 
            "content": "Điều 5: Điều kiện đăng ký môn học. Sinh viên phải hoàn thành môn tiên quyết trước khi đăng ký. Anh văn 2 yêu cầu Anh văn 1.",
            "is_article": True
        },
        {
            "id": "chunk_2",
            "content": "Điều 10: Điều kiện miễn học Anh văn. Sinh viên đạt chứng chỉ IELTS 6.0 hoặc TOEIC 600 được miễn học Anh văn cơ bản.",
            "is_article": True
        }
    ]


# =============================================================================
# Test ExtractionConfig
# =============================================================================

class TestExtractionConfig:
    """Tests for ExtractionConfig."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = ExtractionConfig()
        
        assert config.result_type == "markdown"
        assert config.chunk_size == 1024
        assert config.chunk_overlap == 200
        assert config.include_metadata is True
    
    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict('os.environ', {
            'LLAMA_CLOUD_API_KEY': 'test_llama_key',
            'NEO4J_URI': 'bolt://test:7687',
            'NEO4J_USER': 'test_user',
            'NEO4J_PASSWORD': 'test_pass',
            'LLM_MODEL': 'gpt-4',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = ExtractionConfig.from_env()
            
            assert config.llama_cloud_api_key == 'test_llama_key'
            assert config.neo4j_uri == 'bolt://test:7687'
            assert config.neo4j_user == 'test_user'
            assert config.llm_model == 'gpt-4'


# =============================================================================
# Test Entity and Relation Types
# =============================================================================

class TestEntityTypes:
    """Tests for EntityType enum."""
    
    def test_all_entity_types_defined(self):
        """Ensure all required entity types are defined."""
        required_types = [
            "MON_HOC", "QUY_DINH", "DIEU_KIEN", "CHUNG_CHI",
            "DIEM_SO", "DOI_TUONG", "THOI_GIAN", "KHOA"
        ]
        
        for type_name in required_types:
            assert hasattr(EntityType, type_name)
            assert EntityType[type_name].value == type_name
    
    def test_entity_type_values(self):
        """Test entity type string values."""
        assert EntityType.MON_HOC.value == "MON_HOC"
        assert EntityType.CHUNG_CHI.value == "CHUNG_CHI"


class TestRelationTypes:
    """Tests for RelationType enum."""
    
    def test_all_relation_types_defined(self):
        """Ensure all required relation types are defined."""
        required_types = [
            "YEU_CAU", "AP_DUNG_CHO", "DAT_DIEM", "TUONG_DUONG",
            "MIEN_GIAM", "SUA_DOI", "THAY_THE"
        ]
        
        for type_name in required_types:
            assert hasattr(RelationType, type_name)


# =============================================================================
# Test ExtractedEntity
# =============================================================================

class TestExtractedEntity:
    """Tests for ExtractedEntity dataclass."""
    
    def test_entity_creation(self):
        """Test creating an extracted entity."""
        entity = ExtractedEntity(
            id="ent_1",
            type=EntityType.MON_HOC,
            text="Anh văn 1",
            normalized="ENG101"
        )
        
        assert entity.id == "ent_1"
        assert entity.type == EntityType.MON_HOC
        assert entity.text == "Anh văn 1"
        assert entity.normalized == "ENG101"
        assert entity.confidence == 0.9
    
    def test_entity_with_properties(self):
        """Test entity with additional properties."""
        entity = ExtractedEntity(
            id="ent_2",
            type=EntityType.DIEM_SO,
            text="6.0",
            properties={"min_score": True, "certificate": "IELTS"}
        )
        
        assert entity.properties["min_score"] is True
        assert entity.properties["certificate"] == "IELTS"


# =============================================================================
# Test ExtractedRelation
# =============================================================================

class TestExtractedRelation:
    """Tests for ExtractedRelation dataclass."""
    
    def test_relation_creation(self):
        """Test creating an extracted relation."""
        relation = ExtractedRelation(
            source_id="ent_1",
            target_id="ent_2",
            type=RelationType.DAT_DIEM,
            evidence="IELTS đạt 6.0"
        )
        
        assert relation.source_id == "ent_1"
        assert relation.target_id == "ent_2"
        assert relation.type == RelationType.DAT_DIEM
        assert relation.evidence == "IELTS đạt 6.0"


# =============================================================================
# Test ParsedDocument
# =============================================================================

class TestParsedDocument:
    """Tests for ParsedDocument dataclass."""
    
    def test_parsed_document_creation(self):
        """Test creating a parsed document."""
        doc = ParsedDocument(
            content="Test content",
            tables=[{"id": "table_1", "content": "| A | B |"}],
            metadata={"source": "test.pdf"},
            pages=5
        )
        
        assert doc.content == "Test content"
        assert len(doc.tables) == 1
        assert doc.pages == 5
    
    def test_parsed_document_defaults(self):
        """Test default values."""
        doc = ParsedDocument(content="Content only")
        
        assert doc.tables == []
        assert doc.metadata == {}
        assert doc.pages == 0


# =============================================================================
# Test ExtractionResult
# =============================================================================

class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""
    
    def test_extraction_result_creation(self):
        """Test creating an extraction result."""
        parsed_doc = ParsedDocument(content="Test", pages=3)
        
        entity = ExtractedEntity(
            id="e1",
            type=EntityType.MON_HOC,
            text="Toán"
        )
        
        relation = ExtractedRelation(
            source_id="e1",
            target_id="e2",
            type=RelationType.YEU_CAU
        )
        
        result = ExtractionResult(
            document_id="doc_1",
            parsed_document=parsed_doc,
            entities=[entity],
            relations=[relation]
        )
        
        assert result.document_id == "doc_1"
        assert len(result.entities) == 1
        assert len(result.relations) == 1
    
    def test_to_graph_models(self):
        """Test converting to graph models."""
        parsed_doc = ParsedDocument(content="Test")
        
        entity = ExtractedEntity(
            id="e1",
            type=EntityType.MON_HOC,
            text="Anh văn 1"
        )
        
        relation = ExtractedRelation(
            source_id="e1",
            target_id="e2",
            type=RelationType.DIEU_KIEN_TIEN_QUYET
        )
        
        result = ExtractionResult(
            document_id="doc_1",
            parsed_document=parsed_doc,
            entities=[entity],
            relations=[relation]
        )
        
        nodes, rels = result.to_graph_models()
        
        assert len(nodes) == 1
        assert len(rels) == 1
        assert nodes[0].id == "e1"
        assert nodes[0].properties["text"] == "Anh văn 1"


# =============================================================================
# Test LlamaParseDocumentParser
# =============================================================================

class TestLlamaParseDocumentParser:
    """Tests for LlamaParseDocumentParser."""
    
    def test_parser_initialization(self, sample_config):
        """Test parser initialization."""
        parser = LlamaParseDocumentParser(sample_config)
        
        assert parser.config == sample_config
        assert parser._parser is None
    
    def test_extract_tables(self, sample_config, sample_markdown_content):
        """Test table extraction from markdown."""
        parser = LlamaParseDocumentParser(sample_config)
        
        tables = parser._extract_tables(sample_markdown_content)
        
        assert len(tables) == 1
        assert "table_1" == tables[0]["id"]
        assert "STT" in tables[0]["header"]
    
    def test_create_semantic_chunks(self, sample_config, sample_markdown_content):
        """Test semantic chunk creation from content."""
        parser = LlamaParseDocumentParser(sample_config)
        parser.config.chunk_size = 200
        
        chunks = parser._create_semantic_chunks(sample_markdown_content)
        
        assert len(chunks) > 0
        assert all("id" in chunk for chunk in chunks)
        assert all("content" in chunk for chunk in chunks)
    
    def test_create_semantic_chunks_preserves_articles(self, sample_config):
        """Test that semantic chunks preserve article boundaries."""
        parser = LlamaParseDocumentParser(sample_config)
        parser.config.chunk_size = 500
        
        content = """
Điều 1: Phạm vi điều chỉnh
Nội dung điều 1

Điều 2: Đối tượng áp dụng
Nội dung điều 2
"""
        
        chunks = parser._create_semantic_chunks(content)
        
        # Should have chunks starting with "Điều"
        article_chunks = [c for c in chunks if c.get("is_article")]
        assert len(article_chunks) >= 1


# =============================================================================
# Test PropertyGraphKGExtractor
# =============================================================================

class TestPropertyGraphKGExtractor:
    """Tests for PropertyGraphKGExtractor."""
    
    def test_extractor_initialization(self, sample_config):
        """Test extractor initialization."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        assert extractor.config == sample_config
        assert extractor._llm is None
    
    def test_map_entity_type(self, sample_config):
        """Test entity type mapping."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        assert extractor._map_entity_type("MON_HOC") == EntityType.MON_HOC
        assert extractor._map_entity_type("CHUNG_CHI") == EntityType.CHUNG_CHI
        # Unknown type should fallback
        assert extractor._map_entity_type("UNKNOWN") == EntityType.DIEU_KIEN
    
    def test_map_relation_type(self, sample_config):
        """Test relation type mapping."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        assert extractor._map_relation_type("YEU_CAU") == RelationType.YEU_CAU
        assert extractor._map_relation_type("DAT_DIEM") == RelationType.DAT_DIEM
        # Unknown type should fallback
        assert extractor._map_relation_type("UNKNOWN") == RelationType.LIEN_QUAN_NOI_DUNG
    
    def test_create_extraction_prompt(self, sample_config):
        """Test extraction prompt generation."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        text = "Sinh viên đạt IELTS 6.0 được miễn Anh văn"
        prompt = extractor._create_extraction_prompt(text)
        
        assert "entities" in prompt
        assert "relations" in prompt
        assert text in prompt
    
    def test_parse_extraction_response(self, sample_config):
        """Test parsing LLM extraction response."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        response = '''
{
    "entities": [
        {"id": "1", "type": "CHUNG_CHI", "text": "IELTS"},
        {"id": "2", "type": "DIEM_SO", "text": "6.0"}
    ],
    "relations": [
        {"source_id": "1", "target_id": "2", "type": "DAT_DIEM", "evidence": "đạt 6.0"}
    ]
}
'''
        
        entities, relations = extractor._parse_extraction_response(
            response, "chunk_0", "doc_1"
        )
        
        assert len(entities) == 2
        assert len(relations) == 1
        assert entities[0].type == EntityType.CHUNG_CHI
        assert relations[0].type == RelationType.DAT_DIEM
    
    def test_parse_extraction_response_with_code_block(self, sample_config):
        """Test parsing response wrapped in code block."""
        extractor = PropertyGraphKGExtractor(sample_config)
        
        response = '''```json
{
    "entities": [{"id": "1", "type": "MON_HOC", "text": "Toán"}],
    "relations": []
}
```'''
        
        entities, relations = extractor._parse_extraction_response(
            response, "chunk_0", "doc_1"
        )
        
        assert len(entities) == 1
        assert entities[0].text == "Toán"


# =============================================================================
# Test LlamaIndexExtractionService
# =============================================================================

class TestLlamaIndexExtractionService:
    """Tests for LlamaIndexExtractionService."""
    
    def test_service_initialization(self, sample_config):
        """Test service initialization."""
        service = LlamaIndexExtractionService(sample_config)
        
        assert service.config == sample_config
        assert service.parser is not None
        assert service.kg_extractor is not None
    
    @pytest.mark.asyncio
    async def test_extract_from_pdf_mock(self, sample_config, sample_chunks):
        """Test extraction with mocked components."""
        service = LlamaIndexExtractionService(sample_config)
        
        # Mock parser
        mock_parsed = ParsedDocument(
            content="Test content",
            chunks=sample_chunks,
            pages=3
        )
        service.parser.parse_pdf = AsyncMock(return_value=mock_parsed)
        
        # Mock KG extractor
        mock_entities = [
            ExtractedEntity(id="e1", type=EntityType.MON_HOC, text="Toán")
        ]
        mock_relations = [
            ExtractedRelation(
                source_id="e1", 
                target_id="e2", 
                type=RelationType.YEU_CAU
            )
        ]
        service.kg_extractor.extract_from_chunks = AsyncMock(
            return_value=(mock_entities, mock_relations)
        )
        
        result = await service.extract_from_pdf(Path("test.pdf"))
        
        assert result.document_id == "test"
        assert len(result.entities) == 1
        assert len(result.relations) == 1
    
    def test_service_from_env(self):
        """Test creating service from environment."""
        with patch.dict('os.environ', {
            'LLAMA_CLOUD_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai'
        }):
            service = LlamaIndexExtractionService.from_env()
            
            assert service.config.llama_cloud_api_key == 'test_key'


# =============================================================================
# Test Schema Definition
# =============================================================================

class TestVietnameseAcademicSchema:
    """Tests for the Vietnamese academic schema."""
    
    def test_schema_contains_entity_types(self):
        """Ensure schema documents entity types."""
        assert "MON_HOC" in VIETNAMESE_ACADEMIC_SCHEMA
        assert "CHUNG_CHI" in VIETNAMESE_ACADEMIC_SCHEMA
        assert "DIEM_SO" in VIETNAMESE_ACADEMIC_SCHEMA
    
    def test_schema_contains_relation_types(self):
        """Ensure schema documents relation types."""
        assert "YEU_CAU" in VIETNAMESE_ACADEMIC_SCHEMA
        assert "DAT_DIEM" in VIETNAMESE_ACADEMIC_SCHEMA
        assert "TUONG_DUONG" in VIETNAMESE_ACADEMIC_SCHEMA
    
    def test_schema_contains_guidelines(self):
        """Ensure schema contains extraction guidelines."""
        assert "Guidelines" in VIETNAMESE_ACADEMIC_SCHEMA or "guidelines" in VIETNAMESE_ACADEMIC_SCHEMA.lower()


# =============================================================================
# Integration Tests (Async)
# =============================================================================

class TestIntegration:
    """Integration tests for the extraction pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self, sample_config, sample_markdown_content):
        """Test full pipeline with mocks."""
        service = LlamaIndexExtractionService(sample_config)
        
        # Create realistic mock data
        chunks = [
            {
                "id": "chunk_0",
                "content": "Điều 10: Sinh viên đạt IELTS 6.0 được miễn Anh văn cơ bản.",
                "is_article": True
            }
        ]
        
        mock_parsed = ParsedDocument(
            content=sample_markdown_content,
            chunks=chunks,
            pages=1,
            tables=[{"id": "table_1", "content": "| A | B |"}]
        )
        
        mock_entities = [
            ExtractedEntity(id="e1", type=EntityType.CHUNG_CHI, text="IELTS"),
            ExtractedEntity(id="e2", type=EntityType.DIEM_SO, text="6.0"),
            ExtractedEntity(id="e3", type=EntityType.MON_HOC, text="Anh văn cơ bản")
        ]
        
        mock_relations = [
            ExtractedRelation(
                source_id="e1", 
                target_id="e2", 
                type=RelationType.DAT_DIEM,
                evidence="đạt IELTS 6.0"
            ),
            ExtractedRelation(
                source_id="e1",
                target_id="e3",
                type=RelationType.MIEN_GIAM,
                evidence="được miễn Anh văn cơ bản"
            )
        ]
        
        service.parser.parse_pdf = AsyncMock(return_value=mock_parsed)
        service.kg_extractor.extract_from_chunks = AsyncMock(
            return_value=(mock_entities, mock_relations)
        )
        
        result = await service.extract_from_pdf(Path("regulation.pdf"))
        
        # Verify result
        assert result.document_id == "regulation"
        assert len(result.entities) == 3
        assert len(result.relations) == 2
        
        # Verify conversion to graph models
        nodes, rels = result.to_graph_models()
        assert len(nodes) == 3
        assert len(rels) == 2
        
        # Check entity types are preserved
        entity_types = {n.category.name for n in nodes}
        assert "CHUNG_CHI" in entity_types
        assert "DIEM_SO" in entity_types
        assert "MON_HOC" in entity_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
