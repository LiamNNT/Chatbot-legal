# tests/test_legal_query_parser.py
"""
Tests for LegalQueryParser.

Tests cover:
- Law ID extraction (various formats)
- Article, Clause, Point extraction
- Intent classification
- Keyword extraction
- Edge cases and Vietnamese text handling
"""

import pytest
from app.core.retrieval.legal_query_parser import (
    LegalQueryParser,
    parse_legal_query,
    extract_legal_refs,
)
from app.core.retrieval.schemas import QueryIntent


class TestLawIdExtraction:
    """Tests for law ID extraction from queries."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_standard_law_id_with_qh(self, parser):
        """Test extraction of standard QH law ID."""
        result = parser.parse("Theo Luật 20/2023/QH15 về giáo dục")
        assert result.law_id == "20/2023/QH15"
    
    def test_standard_law_id_without_issuer(self, parser):
        """Test extraction of law ID without issuer."""
        result = parser.parse("Luật số 20/2023 quy định")
        assert result.law_id == "20/2023"
    
    def test_law_id_with_dash_separator(self, parser):
        """Test extraction with dash separator."""
        result = parser.parse("Nghị định 24-2024-NĐ-CP về thuế")
        assert result.law_id is not None
        assert "24" in result.law_id
        assert "2024" in result.law_id
    
    def test_law_id_with_so_prefix(self, parser):
        """Test extraction with 'số' prefix."""
        result = parser.parse("Luật số 08/2023/QH15 về đấu thầu")
        assert result.law_id == "08/2023/QH15"
    
    def test_no_law_id(self, parser):
        """Test query without law ID."""
        result = parser.parse("Học phí đại học quy định như thế nào?")
        assert result.law_id is None


class TestArticleExtraction:
    """Tests for article (Điều) extraction."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_simple_article(self, parser):
        """Test simple article extraction."""
        result = parser.parse("Điều 11 quy định gì?")
        assert result.article_id == "11"
    
    def test_article_with_letter_suffix(self, parser):
        """Test article with letter suffix (11a, 11b)."""
        result = parser.parse("Theo Điều 11a về học phí")
        assert result.article_id == "11a"
    
    def test_article_lowercase(self, parser):
        """Test lowercase điều."""
        result = parser.parse("điều 5 nói về")
        assert result.article_id == "5"
    
    def test_article_with_so(self, parser):
        """Test article with số prefix."""
        result = parser.parse("Điều số 25 quy định")
        assert result.article_id == "25"
    
    def test_no_article(self, parser):
        """Test query without article."""
        result = parser.parse("Quy định về học phí như thế nào?")
        assert result.article_id is None


class TestClauseExtraction:
    """Tests for clause (Khoản) extraction."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_simple_clause(self, parser):
        """Test simple clause extraction."""
        result = parser.parse("Khoản 2 Điều 11 quy định")
        assert result.clause_no == "2"
        assert result.article_id == "11"
    
    def test_clause_lowercase(self, parser):
        """Test lowercase khoản."""
        result = parser.parse("khoản 3 điều 5")
        assert result.clause_no == "3"
    
    def test_abbreviated_clause(self, parser):
        """Test abbreviated K.2 format."""
        result = parser.parse("K.2 Điều 11")
        assert result.clause_no == "2"
    
    def test_no_clause(self, parser):
        """Test query without clause."""
        result = parser.parse("Điều 11 quy định gì?")
        assert result.clause_no is None


class TestPointExtraction:
    """Tests for point (Điểm) extraction."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_simple_point(self, parser):
        """Test simple point extraction."""
        result = parser.parse("Điểm a Khoản 2 Điều 11")
        assert result.point_no == "a"
        assert result.clause_no == "2"
        assert result.article_id == "11"
    
    def test_point_d_with_stroke(self, parser):
        """Test Vietnamese đ point."""
        result = parser.parse("Điểm đ Khoản 1 Điều 5")
        assert result.point_no == "đ"
    
    def test_point_uppercase_normalized(self, parser):
        """Test uppercase point normalized to lowercase."""
        result = parser.parse("ĐIỂM B khoản 3")
        assert result.point_no == "b"
    
    def test_no_point(self, parser):
        """Test query without point."""
        result = parser.parse("Khoản 2 Điều 11")
        assert result.point_no is None


class TestIntentClassification:
    """Tests for query intent classification."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_lookup_exact_with_point(self, parser):
        """Test exact lookup when point is specified."""
        result = parser.parse("Điểm a Khoản 2 Điều 11")
        assert result.intent == QueryIntent.LOOKUP_EXACT
    
    def test_lookup_exact_with_clause_and_article(self, parser):
        """Test exact lookup with clause and article."""
        result = parser.parse("Khoản 2 Điều 11 nói gì?")
        assert result.intent == QueryIntent.LOOKUP_EXACT
    
    def test_lookup_article(self, parser):
        """Test article lookup when only article specified."""
        result = parser.parse("Điều 11 quy định như thế nào?")
        assert result.intent == QueryIntent.LOOKUP_ARTICLE
    
    def test_semantic_question(self, parser):
        """Test semantic question without specific refs."""
        result = parser.parse("Học phí đại học được quy định như thế nào?")
        assert result.intent == QueryIntent.SEMANTIC_QUESTION
    
    def test_definition_query(self, parser):
        """Test definition query detection."""
        result = parser.parse("Sinh viên chính quy là gì?")
        assert result.intent == QueryIntent.DEFINITION
    
    def test_definition_query_giai_thich(self, parser):
        """Test giải thích từ ngữ query."""
        result = parser.parse("Giải thích từ ngữ về học phần")
        assert result.intent == QueryIntent.DEFINITION


class TestKeywordExtraction:
    """Tests for keyword extraction after removing legal refs."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_keywords_extracted(self, parser):
        """Test keywords are extracted after removing refs."""
        result = parser.parse("Điều 11 Luật 20/2023/QH15 quy định về học phí sinh viên")
        # Should have keywords like "học phí", "sinh viên"
        assert len(result.keywords) > 0
        assert any("học" in kw or "phí" in kw or "sinh" in kw for kw in result.keywords)
    
    def test_keywords_filter_filler_words(self, parser):
        """Test filler words are filtered out."""
        result = parser.parse("theo quy định của Điều 11 về học phí")
        # "theo", "của", "về" should be filtered
        assert "theo" not in result.keywords
        assert "của" not in result.keywords
    
    def test_no_keywords_for_pure_ref(self, parser):
        """Test pure reference has minimal keywords."""
        result = parser.parse("Điều 11 Khoản 2")
        # Most words are legal refs, few keywords left
        assert len(result.keywords) < 3


class TestComplexQueries:
    """Tests for complex real-world queries."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_full_citation(self, parser):
        """Test full citation parsing."""
        result = parser.parse("Điểm a Khoản 2 Điều 11 Luật 20/2023/QH15 quy định gì về mức học phí?")
        assert result.law_id == "20/2023/QH15"
        assert result.article_id == "11"
        assert result.clause_no == "2"
        assert result.point_no == "a"
        assert result.intent == QueryIntent.LOOKUP_EXACT
    
    def test_reverse_order_citation(self, parser):
        """Test citation in reverse order (Luật first)."""
        result = parser.parse("Luật 20/2023/QH15 Điều 11 Khoản 2")
        assert result.law_id == "20/2023/QH15"
        assert result.article_id == "11"
        assert result.clause_no == "2"
    
    def test_question_with_partial_ref(self, parser):
        """Test question with partial reference."""
        result = parser.parse("Điều 11 nói gì về quyền lợi sinh viên?")
        assert result.article_id == "11"
        assert result.intent == QueryIntent.LOOKUP_ARTICLE
        assert len(result.keywords) > 0
    
    def test_comparison_query(self, parser):
        """Test comparison query detection."""
        result = parser.parse("So sánh Điều 11 và Điều 12")
        # Should detect article and possibly comparison intent
        assert result.article_id is not None


class TestNormalization:
    """Tests for query normalization."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_normalized_query_standardizes_dieu(self, parser):
        """Test normalized query standardizes Điều format."""
        result = parser.parse("điều 11 khoản 2")
        assert "Điều 11" in result.normalized_query
        assert "Khoản 2" in result.normalized_query
    
    def test_normalized_query_preserves_content(self, parser):
        """Test normalized query preserves semantic content."""
        result = parser.parse("Điều 11 về học phí sinh viên")
        assert "học phí" in result.normalized_query
        assert "sinh viên" in result.normalized_query


class TestConfidenceScore:
    """Tests for confidence score calculation."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_high_confidence_full_ref(self, parser):
        """Test high confidence for full reference."""
        result = parser.parse("Điểm a Khoản 2 Điều 11 Luật 20/2023/QH15")
        assert result.confidence >= 0.8
    
    def test_medium_confidence_partial_ref(self, parser):
        """Test medium confidence for partial reference."""
        result = parser.parse("Điều 11 quy định")
        assert 0.5 <= result.confidence < 0.9
    
    def test_lower_confidence_no_ref(self, parser):
        """Test lower confidence for no legal reference."""
        result = parser.parse("Quy định về học phí")
        assert result.confidence <= 0.6


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_empty_query(self, parser):
        """Test empty query handling."""
        result = parser.parse("")
        assert result.raw == ""
        assert result.intent == QueryIntent.SEMANTIC_QUESTION
    
    def test_none_query(self, parser):
        """Test None-like query handling."""
        result = parser.parse("   ")
        assert result.intent == QueryIntent.SEMANTIC_QUESTION
    
    def test_only_numbers(self, parser):
        """Test query with only numbers."""
        result = parser.parse("11 2 3")
        # Should not extract article without Điều prefix
        assert result.article_id is None
    
    def test_unicode_handling(self, parser):
        """Test proper Unicode handling."""
        result = parser.parse("Điều 11 về học phí đại học")
        assert result.article_id == "11"
        assert "đại học" in result.normalized_query.lower()


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_parse_legal_query(self):
        """Test parse_legal_query convenience function."""
        result = parse_legal_query("Điều 11 Khoản 2")
        assert result.article_id == "11"
        assert result.clause_no == "2"
    
    def test_extract_legal_refs(self):
        """Test extract_legal_refs convenience function."""
        refs = extract_legal_refs("Điểm a Khoản 2 Điều 11 Luật 20/2023/QH15")
        assert refs["law_id"] == "20/2023/QH15"
        assert refs["article_id"] == "11"
        assert refs["clause_no"] == "2"
        assert refs["point_no"] == "a"


class TestValidation:
    """Tests for reference validation."""
    
    @pytest.fixture
    def parser(self):
        return LegalQueryParser()
    
    def test_valid_full_reference(self, parser):
        """Test validation of full valid reference."""
        is_valid, warnings = parser.validate_legal_reference(
            law_id="20/2023/QH15",
            article_id="11",
            clause_no="2",
            point_no="a"
        )
        assert is_valid
        assert len(warnings) == 0
    
    def test_invalid_point_without_clause(self, parser):
        """Test validation warns for point without clause."""
        is_valid, warnings = parser.validate_legal_reference(
            article_id="11",
            point_no="a"
        )
        assert not is_valid
        assert any("Khoản" in w for w in warnings)
    
    def test_invalid_clause_without_article(self, parser):
        """Test validation warns for clause without article."""
        is_valid, warnings = parser.validate_legal_reference(
            clause_no="2"
        )
        assert not is_valid
        assert any("Điều" in w for w in warnings)
