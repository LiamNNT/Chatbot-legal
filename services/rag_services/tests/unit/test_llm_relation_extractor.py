"""
Unit tests for LLM Relation Extractor

Tests cover:
- Prompt building with Vietnamese templates
- LLM response parsing (JSON, markdown code blocks)
- Relation validation (confidence, schema, evidence)
- Cost tracking and token usage
- Response caching
- Error handling and retry logic
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
import json

from indexing.llm_relation_extractor import (
    LLMRelationExtractor,
    ExtractionResult,
    ExtractedRelation,
)
from core.domain.models import Entity
from adapters.llm.llm_client import LLMClient, LLMUsage
from adapters.llm.mock_client import MockLLMClient


# Test Data Fixtures
@pytest.fixture
def sample_text() -> str:
    """Sample Vietnamese text for extraction"""
    return """
    Học phần Lập trình Python là một môn học thuộc Khoa Khoa học và Kỹ thuật Máy tính.
    Môn học này có 3 tín chỉ và là điều kiện tiên quyết cho môn Trí tuệ nhân tạo.
    """


@pytest.fixture
def sample_entities() -> List[Entity]:
    """Sample entities for relation extraction"""
    return [
        Entity(
            text="Lập trình Python",
            label="HOC_PHAN",
            start_char=10,
            end_char=26,
            metadata={"ma_hoc_phan": "CS101"}
        ),
        Entity(
            text="Khoa Khoa học và Kỹ thuật Máy tính",
            label="KHOA",
            start_char=50,
            end_char=84,
            metadata={"ma_khoa": "KHMT"}
        ),
        Entity(
            text="Trí tuệ nhân tạo",
            label="HOC_PHAN",
            start_char=140,
            end_char=156,
            metadata={"ma_hoc_phan": "CS301"}
        ),
    ]


@pytest.fixture
def mock_llm_response() -> str:
    """Mock LLM response with relations"""
    return json.dumps({
        "relations": [
            {
                "source": "Lập trình Python",
                "target": "Khoa Khoa học và Kỹ thuật Máy tính",
                "type": "THUOC_KHOA",
                "confidence": 0.95,
                "evidence": "Học phần thuộc Khoa KHMT"
            },
            {
                "source": "Lập trình Python",
                "target": "Trí tuệ nhân tạo",
                "type": "DIEU_KIEN_TIEN_QUYET",
                "confidence": 0.92,
                "evidence": "là điều kiện tiên quyết cho"
            }
        ]
    }, ensure_ascii=False)


@pytest.fixture
def mock_llm_client(mock_llm_response):
    """Mock LLM client that returns predefined response"""
    client = AsyncMock(spec=LLMClient)
    client.complete = AsyncMock(return_value=mock_llm_response)
    client.calculate_cost = Mock(return_value=0.001)
    return client


# LLMRelationExtractor Tests
class TestLLMRelationExtractor:
    """Test LLMRelationExtractor core functionality"""

    @pytest.mark.asyncio
    async def test_extract_relations_success(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test successful relation extraction"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        assert isinstance(result, ExtractionResult)
        assert len(result.relations) == 2
        assert result.tokens_used > 0
        assert result.cost_usd > 0
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_extract_relations_filters_low_confidence(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test filtering of low confidence relations"""
        # Mock response with low confidence relation
        low_conf_response = json.dumps({
            "relations": [
                {
                    "source": "Lập trình Python",
                    "target": "Khoa KHMT",
                    "type": "THUOC_KHOA",
                    "confidence": 0.3,  # Low confidence
                    "evidence": "weak evidence"
                }
            ]
        })
        mock_llm_client.complete = AsyncMock(return_value=low_conf_response)
        
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            min_confidence=0.7  # High threshold
        )
        
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        # Should filter out low confidence relation
        assert len(result.relations) == 0

    @pytest.mark.asyncio
    async def test_parse_llm_response_json(
        self,
        mock_llm_client,
        mock_llm_response
    ):
        """Test parsing valid JSON response"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        relations = extractor._parse_llm_response(mock_llm_response)
        
        assert len(relations) == 2
        assert all(isinstance(r, ExtractedRelation) for r in relations)
        assert relations[0].source == "Lập trình Python"
        assert relations[0].type == "THUOC_KHOA"

    def test_parse_llm_response_markdown_codeblock(self, mock_llm_client):
        """Test parsing JSON inside markdown code block"""
        markdown_response = """
        Here are the extracted relations:
        
        ```json
        {
            "relations": [
                {
                    "source": "Python",
                    "target": "KHMT",
                    "type": "THUOC_KHOA",
                    "confidence": 0.9,
                    "evidence": "test"
                }
            ]
        }
        ```
        """
        
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        relations = extractor._parse_llm_response(markdown_response)
        
        assert len(relations) == 1
        assert relations[0].source == "Python"

    def test_parse_llm_response_invalid_json(self, mock_llm_client):
        """Test handling of invalid JSON"""
        invalid_response = "This is not valid JSON {broken"
        
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        relations = extractor._parse_llm_response(invalid_response)
        
        assert relations == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_build_prompt_includes_entities(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test that prompt includes all entities"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        prompt = extractor._build_prompt(sample_text, sample_entities)
        
        # Verify all entity texts are in prompt
        for entity in sample_entities:
            assert entity.text in prompt
        
        # Verify text is in prompt
        assert sample_text.strip() in prompt

    @pytest.mark.asyncio
    async def test_validate_relation_valid(self, mock_llm_client):
        """Test validation accepts valid relation"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        relation = ExtractedRelation(
            source="Lập trình Python",
            target="KHMT",
            type="THUOC_KHOA",
            confidence=0.9,
            evidence="Học phần thuộc khoa KHMT"
        )
        
        is_valid, error = extractor._validate_relation(relation)
        
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_relation_invalid_type(self, mock_llm_client):
        """Test validation rejects invalid relation type"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        relation = ExtractedRelation(
            source="Python",
            target="KHMT",
            type="INVALID_TYPE",
            confidence=0.9,
            evidence="test"
        )
        
        is_valid, error = extractor._validate_relation(relation)
        
        assert is_valid is False
        assert "invalid" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_relation_missing_evidence(self, mock_llm_client):
        """Test validation handles missing evidence"""
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            require_evidence=True
        )
        
        relation = ExtractedRelation(
            source="Python",
            target="KHMT",
            type="THUOC_KHOA",
            confidence=0.9,
            evidence=""  # Missing evidence
        )
        
        is_valid, error = extractor._validate_relation(relation)
        
        assert is_valid is False
        assert "evidence" in error.lower()


# Caching Tests
class TestCaching:
    """Test response caching functionality"""

    @pytest.mark.asyncio
    async def test_cache_hit_reduces_llm_calls(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test that cached responses reduce LLM API calls"""
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            enable_cache=True
        )
        
        # First call - cache miss
        result1 = await extractor.extract_relations(sample_text, sample_entities)
        call_count_1 = mock_llm_client.complete.call_count
        
        # Second call with same input - cache hit
        result2 = await extractor.extract_relations(sample_text, sample_entities)
        call_count_2 = mock_llm_client.complete.call_count
        
        # LLM should only be called once
        assert call_count_1 == 1
        assert call_count_2 == 1  # No additional call
        assert result1.relations == result2.relations

    @pytest.mark.asyncio
    async def test_cache_miss_on_different_input(
        self,
        mock_llm_client,
        sample_entities
    ):
        """Test cache miss with different input"""
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            enable_cache=True
        )
        
        # First call
        await extractor.extract_relations("Text 1", sample_entities)
        call_count_1 = mock_llm_client.complete.call_count
        
        # Second call with different text
        await extractor.extract_relations("Text 2", sample_entities)
        call_count_2 = mock_llm_client.complete.call_count
        
        # Should make two LLM calls
        assert call_count_2 == call_count_1 + 1


# Cost Tracking Tests
class TestCostTracking:
    """Test token usage and cost tracking"""

    @pytest.mark.asyncio
    async def test_tracks_token_usage(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test that token usage is tracked"""
        # Mock token usage
        mock_llm_client.calculate_cost = Mock(return_value=0.001)
        
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        assert result.tokens_used > 0
        assert result.cost_usd > 0

    @pytest.mark.asyncio
    async def test_accumulates_cost_over_multiple_calls(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test cost accumulation across multiple extractions"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        # Make multiple calls
        await extractor.extract_relations(sample_text, sample_entities)
        await extractor.extract_relations(sample_text + " more text", sample_entities)
        
        stats = extractor.get_usage_stats()
        
        assert stats["total_calls"] >= 2
        assert stats["total_cost"] > 0


# Error Handling Tests
class TestErrorHandling:
    """Test error handling and retry logic"""

    @pytest.mark.asyncio
    async def test_handles_llm_api_error(
        self,
        sample_text,
        sample_entities
    ):
        """Test handling of LLM API errors"""
        # Mock client that raises error
        error_client = AsyncMock(spec=LLMClient)
        error_client.complete = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )
        
        extractor = LLMRelationExtractor(llm_client=error_client)
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        # Should return empty result with error
        assert len(result.relations) == 0
        assert len(result.errors) > 0
        assert "API rate limit" in result.errors[0]

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self, sample_text, sample_entities):
        """Test retry logic on transient errors"""
        call_count = 0
        success_response = json.dumps({"relations": []})
        
        async def mock_complete_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary network error")
            return success_response
        
        retry_client = AsyncMock(spec=LLMClient)
        retry_client.complete = AsyncMock(side_effect=mock_complete_with_retry)
        retry_client.calculate_cost = Mock(return_value=0.001)
        
        extractor = LLMRelationExtractor(
            llm_client=retry_client,
            max_retries=3
        )
        
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        # Should succeed after retry
        assert call_count == 2
        assert len(result.errors) == 0


# Integration with Mock Client Tests
class TestMockClientIntegration:
    """Test integration with MockLLMClient"""

    @pytest.mark.asyncio
    async def test_works_with_mock_client(self, sample_text, sample_entities):
        """Test extraction works with MockLLMClient"""
        mock_client = MockLLMClient()
        extractor = LLMRelationExtractor(llm_client=mock_client)
        
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        # Mock client should return deterministic results
        assert isinstance(result, ExtractionResult)
        assert result.cost_usd == 0.0  # Mock has no cost


# Batch Processing Tests
class TestBatchProcessing:
    """Test batch relation extraction"""

    @pytest.mark.asyncio
    async def test_batch_extract_multiple_texts(
        self,
        mock_llm_client,
        sample_entities
    ):
        """Test extracting relations from multiple texts"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        texts = [
            "Text 1: Python thuộc KHMT",
            "Text 2: AI là điều kiện tiên quyết",
            "Text 3: Database liên quan đến SQL"
        ]
        
        results = []
        for text in texts:
            result = await extractor.extract_relations(text, sample_entities)
            results.append(result)
        
        assert len(results) == 3
        total_cost = sum(r.cost_usd for r in results)
        assert total_cost > 0


# Vietnamese Text Handling Tests
class TestVietnameseTextHandling:
    """Test Vietnamese language specific handling"""

    @pytest.mark.asyncio
    async def test_handles_vietnamese_diacritics(self, mock_llm_client):
        """Test handling of Vietnamese diacritics"""
        vietnamese_text = "Học phần Lập trình có điều kiện tiên quyết"
        entities = [
            Entity(text="Lập trình", label="HOC_PHAN", start_char=10, end_char=19),
            Entity(text="điều kiện tiên quyết", label="DIEU_KIEN", start_char=23, end_char=43),
        ]
        
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        result = await extractor.extract_relations(vietnamese_text, entities)
        
        # Should handle Vietnamese text without errors
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_prompt_in_vietnamese(self, mock_llm_client, sample_text, sample_entities):
        """Test that prompts are constructed in Vietnamese"""
        extractor = LLMRelationExtractor(llm_client=mock_llm_client)
        
        prompt = extractor._build_prompt(sample_text, sample_entities)
        
        # Verify Vietnamese keywords in prompt
        vietnamese_keywords = ["trích xuất", "mối quan hệ", "thực thể", "độ tin cậy"]
        assert any(keyword in prompt.lower() for keyword in vietnamese_keywords)


# Configuration Tests
class TestConfiguration:
    """Test different configuration options"""

    @pytest.mark.asyncio
    async def test_custom_confidence_threshold(
        self,
        mock_llm_client,
        sample_text,
        sample_entities
    ):
        """Test custom confidence threshold"""
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            min_confidence=0.95  # Very high threshold
        )
        
        result = await extractor.extract_relations(sample_text, sample_entities)
        
        # All returned relations should meet threshold
        assert all(r.confidence >= 0.95 for r in result.relations)

    @pytest.mark.asyncio
    async def test_disable_caching(self, mock_llm_client, sample_text, sample_entities):
        """Test with caching disabled"""
        extractor = LLMRelationExtractor(
            llm_client=mock_llm_client,
            enable_cache=False
        )
        
        # Make same call twice
        await extractor.extract_relations(sample_text, sample_entities)
        await extractor.extract_relations(sample_text, sample_entities)
        
        # Should call LLM twice without cache
        assert mock_llm_client.complete.call_count == 2


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
