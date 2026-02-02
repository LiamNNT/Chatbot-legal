# tests/test_doc_kind_detection.py
"""
Tests for document kind detection in Vietnamese legal documents.

Tests cover:
- Document kind detection from law_id (QH, NĐ-CP, TT-)
- Document kind detection from headers (LUẬT, NGHỊ ĐỊNH, THÔNG TƯ)
- Document kind detection from filename
- Title extraction for all document types
- Issuer detection
"""

import pytest
from indexing.loaders.vietnam_legal_docx_parser import (
    VietnamLegalDocxParser,
    ParseResult,
)


@pytest.fixture
def parser() -> VietnamLegalDocxParser:
    """Create a parser instance for testing."""
    return VietnamLegalDocxParser(token_threshold=800)


class TestDocKindDetection:
    """Test document kind detection logic."""
    
    def test_detect_law_from_law_id_qh(self, parser: VietnamLegalDocxParser):
        """Test detection of LAW from QH suffix in law_id."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="20/2023/QH15",
            raw_lines=[],
            filename=""
        )
        assert kind == "LAW"
        assert confidence >= 0.9
        assert "QH" in evidence
    
    def test_detect_decree_from_law_id_nd_cp(self, parser: VietnamLegalDocxParser):
        """Test detection of DECREE from NĐ-CP suffix in law_id."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="13/2023/NĐ-CP",
            raw_lines=[],
            filename=""
        )
        assert kind == "DECREE"
        assert confidence >= 0.9
        assert "NĐ-CP" in evidence
    
    def test_detect_decree_from_law_id_nd_cp_no_dash(self, parser: VietnamLegalDocxParser):
        """Test detection of DECREE from ND-CP suffix (no diacritics)."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="53/2022/ND-CP",
            raw_lines=[],
            filename=""
        )
        assert kind == "DECREE"
        assert confidence >= 0.9
    
    def test_detect_circular_from_law_id_tt(self, parser: VietnamLegalDocxParser):
        """Test detection of CIRCULAR from TT- prefix in law_id."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="38/2016/TT-BTTTT",
            raw_lines=[],
            filename=""
        )
        assert kind == "CIRCULAR"
        assert confidence >= 0.9
        assert "TT-" in evidence
    
    def test_detect_law_from_header(self, parser: VietnamLegalDocxParser):
        """Test detection of LAW from header line."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=["QUỐC HỘI", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "LUẬT", "BẢO VỆ MÔI TRƯỜNG"],
            filename=""
        )
        assert kind == "LAW"
        assert confidence >= 0.85
    
    def test_detect_decree_from_header(self, parser: VietnamLegalDocxParser):
        """Test detection of DECREE from header line."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=["CHÍNH PHỦ", "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "NGHỊ ĐỊNH", "Quy định chi tiết..."],
            filename=""
        )
        assert kind == "DECREE"
        assert confidence >= 0.85
    
    def test_detect_circular_from_header(self, parser: VietnamLegalDocxParser):
        """Test detection of CIRCULAR from header line."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=["BỘ THÔNG TIN VÀ TRUYỀN THÔNG", "THÔNG TƯ", "Quy định..."],
            filename=""
        )
        assert kind == "CIRCULAR"
        assert confidence >= 0.85
    
    def test_detect_law_from_filename(self, parser: VietnamLegalDocxParser):
        """Test detection of LAW from filename heuristic."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=[],
            filename="Luật-20-2023-QH15.docx"
        )
        assert kind == "LAW"
        assert confidence >= 0.75
    
    def test_detect_decree_from_filename(self, parser: VietnamLegalDocxParser):
        """Test detection of DECREE from filename heuristic."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=[],
            filename="Nghị-định-13-2023-NĐ-CP.docx"
        )
        assert kind == "DECREE"
        assert confidence >= 0.75
    
    def test_detect_circular_from_filename(self, parser: VietnamLegalDocxParser):
        """Test detection of CIRCULAR from filename heuristic."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=[],
            filename="Thông-tư-38-2016-TT-BTTTT.doc"
        )
        assert kind == "CIRCULAR"
        assert confidence >= 0.75
    
    def test_fallback_to_law(self, parser: VietnamLegalDocxParser):
        """Test fallback to LAW when no clear evidence."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=["Some random content"],
            filename="document.docx"
        )
        assert kind == "LAW"
        assert confidence < 0.7


class TestDocumentTitleExtraction:
    """Test document title extraction for different document types."""
    
    def test_extract_law_title(self, parser: VietnamLegalDocxParser):
        """Test extracting title for LUẬT document."""
        lines = [
            "QUỐC HỘI",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "LUẬT",
            "BẢO VỆ MÔI TRƯỜNG",
            "Căn cứ Hiến pháp...",
        ]
        title = parser._extract_document_title(lines)
        assert title == "BẢO VỆ MÔI TRƯỜNG"
    
    def test_extract_decree_title(self, parser: VietnamLegalDocxParser):
        """Test extracting title for NGHỊ ĐỊNH document."""
        lines = [
            "CHÍNH PHỦ",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "NGHỊ ĐỊNH",
            "Quy định chi tiết một số điều của Luật Bảo vệ dữ liệu cá nhân",
            "Căn cứ Luật...",
        ]
        title = parser._extract_document_title(lines)
        assert "Quy định chi tiết" in title
    
    def test_extract_circular_title(self, parser: VietnamLegalDocxParser):
        """Test extracting title for THÔNG TƯ document."""
        lines = [
            "BỘ THÔNG TIN VÀ TRUYỀN THÔNG",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "THÔNG TƯ",
            "Quy định về bảo đảm an toàn thông tin số",
        ]
        title = parser._extract_document_title(lines)
        assert "Quy định về bảo đảm" in title
    
    def test_extract_inline_law_title(self, parser: VietnamLegalDocxParser):
        """Test extracting inline LUẬT title."""
        lines = [
            "LUẬT AN NINH MẠNG",
            "Căn cứ Hiến pháp...",
        ]
        title = parser._extract_document_title(lines)
        assert "Luật AN NINH MẠNG" == title


class TestIssuerDetection:
    """Test issuing authority detection."""
    
    def test_detect_quoc_hoi(self, parser: VietnamLegalDocxParser):
        """Test detection of QUỐC HỘI issuer."""
        issuer = parser._detect_issuer([
            "QUỐC HỘI",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        ])
        assert issuer == "QUỐC HỘI"
    
    def test_detect_chinh_phu(self, parser: VietnamLegalDocxParser):
        """Test detection of CHÍNH PHỦ issuer."""
        issuer = parser._detect_issuer([
            "CHÍNH PHỦ",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        ])
        assert issuer == "CHÍNH PHỦ"
    
    def test_detect_bo(self, parser: VietnamLegalDocxParser):
        """Test detection of BỘ issuer."""
        issuer = parser._detect_issuer([
            "BỘ THÔNG TIN VÀ TRUYỀN THÔNG",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        ])
        # Should start with BỘ
        assert issuer is not None
        assert issuer.startswith("BỘ")


class TestParseResultMetadata:
    """Test that ParseResult includes proper metadata."""
    
    def test_parse_result_has_metadata_field(self):
        """Test that ParseResult dataclass has metadata field."""
        result = ParseResult(success=True)
        assert hasattr(result, 'metadata')
        assert isinstance(result.metadata, dict)
    
    def test_metadata_includes_doc_kind(self):
        """Test that metadata should include doc_kind after parsing."""
        # This would need a real document to parse, so we just verify the structure
        result = ParseResult(
            success=True,
            metadata={
                "doc_kind": "LAW",
                "document_number": "20/2023/QH15",
                "title": "Luật Bảo vệ môi trường",
                "issuer": "QUỐC HỘI",
            }
        )
        assert result.metadata["doc_kind"] == "LAW"
        assert result.metadata["document_number"] == "20/2023/QH15"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_lines(self, parser: VietnamLegalDocxParser):
        """Test with empty lines list."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="",
            raw_lines=[],
            filename=""
        )
        # Should fallback to LAW
        assert kind == "LAW"
    
    def test_mixed_case_detection(self, parser: VietnamLegalDocxParser):
        """Test detection with mixed case headers."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="UNKNOWN",
            raw_lines=["luật", "BẢO VỆ MÔI TRƯỜNG"],
            filename=""
        )
        assert kind == "LAW"
    
    def test_special_characters_in_law_id(self, parser: VietnamLegalDocxParser):
        """Test with special characters in law_id."""
        kind, confidence, evidence = parser.detect_doc_kind(
            law_id="13/2023/NĐ CP",  # Space instead of dash
            raw_lines=[],
            filename=""
        )
        assert kind == "DECREE"
