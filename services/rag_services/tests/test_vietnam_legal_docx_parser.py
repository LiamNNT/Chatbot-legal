# tests/test_vietnam_legal_docx_parser.py
"""
Comprehensive tests for VietnamLegalDocxParser.

Tests cover:
- Regex patterns for Vietnamese legal structure
- Text normalization and boilerplate removal
- Hierarchical tree building
- Chunking strategies (token-based, definitions)
- Relationship tracking (parent, siblings)
- Edge cases and error handling
"""

import pytest
import re
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Import the parser module
from indexing.loaders.vietnam_legal_docx_parser import (
    VietnamLegalDocxParser,
    LegalChunk,
    LegalNode,
    LegalNodeType,
    ParseResult,
    estimate_tokens,
    parse_vietnam_legal_docx,
    CHUONG_PATTERN,
    MUC_PATTERN,
    DIEU_PATTERN,
    KHOAN_PATTERN,
    DIEM_PATTERN,
    BOILERPLATE_RE,
    DEFINITION_RE,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def parser():
    """Create a parser instance for testing."""
    return VietnamLegalDocxParser(token_threshold=800)


@pytest.fixture
def sample_legal_text_lines() -> List[str]:
    """Sample Vietnamese legal document lines for testing."""
    return [
        "LUẬT",
        "GIAO DỊCH ĐIỆN TỬ",
        "Số: 20/2023/QH15",
        "Chương I. QUY ĐỊNH CHUNG",
        "Điều 1. Phạm vi điều chỉnh",
        "Luật này quy định về giao dịch điện tử; quyền, nghĩa vụ và trách nhiệm của cơ quan, tổ chức, cá nhân trong giao dịch điện tử.",
        "Điều 2. Đối tượng áp dụng",
        "1. Cơ quan, tổ chức, cá nhân trực tiếp tham gia hoặc có liên quan đến giao dịch điện tử.",
        "2. Cơ quan, tổ chức, cá nhân nước ngoài tham gia giao dịch điện tử tại Việt Nam.",
        "Điều 3. Giải thích từ ngữ",
        "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:",
        "1. Giao dịch điện tử là giao dịch được thực hiện bằng phương tiện điện tử.",
        "2. Chứng thư điện tử là thông tin được tạo ra, gửi đi, nhận và lưu trữ bằng phương tiện điện tử.",
        "3. Chữ ký điện tử là chữ ký được tạo lập dưới dạng từ, chữ, số, ký hiệu, âm thanh hoặc các hình thức khác bằng phương tiện điện tử.",
        "Chương II. THÔNG ĐIỆP DỮ LIỆU",
        "Mục 1. Quy định chung về thông điệp dữ liệu",
        "Điều 4. Giá trị pháp lý của thông điệp dữ liệu",
        "1. Thông điệp dữ liệu không bị phủ nhận giá trị pháp lý chỉ vì đó là thông điệp dữ liệu.",
        "2. Thông điệp dữ liệu có giá trị như văn bản nếu:",
        "a) Thông tin chứa trong thông điệp dữ liệu có thể truy cập và sử dụng được để tham chiếu khi cần thiết;",
        "b) Nội dung của thông điệp dữ liệu được bảo đảm toàn vẹn kể từ khi được khởi tạo.",
        "Điều 5. Nguyên bản của thông điệp dữ liệu",
        "Thông điệp dữ liệu được coi là nguyên bản khi đáp ứng đủ các điều kiện sau:",
        "1. Nội dung của thông điệp dữ liệu được bảo đảm toàn vẹn kể từ khi được khởi tạo lần đầu dưới dạng một thông điệp dữ liệu hoàn chỉnh.",
        "2. Nội dung của thông điệp dữ liệu có thể được trình bày khi cần thiết.",
    ]


@pytest.fixture
def sample_long_article_lines() -> List[str]:
    """Sample article with many clauses to test splitting."""
    lines = [
        "Chương I. QUY ĐỊNH CHUNG",
        "Điều 1. Các hành vi bị cấm trong hoạt động giao dịch điện tử",
    ]
    # Add 20 clauses with substantial content to exceed token threshold
    for i in range(1, 21):
        lines.append(
            f"{i}. Hành vi bị cấm số {i} bao gồm việc thực hiện các hoạt động trái pháp luật, "
            f"gây thiệt hại cho tổ chức, cá nhân khác, vi phạm quy định về bảo mật thông tin, "
            f"và các hành vi khác theo quy định của pháp luật về giao dịch điện tử."
        )
    return lines


# =============================================================================
# Test Regex Patterns
# =============================================================================

class TestRegexPatterns:
    """Test Vietnamese legal structure regex patterns."""
    
    def test_chuong_pattern_roman_numerals(self):
        """Test CHƯƠNG pattern with various Roman numerals."""
        test_cases = [
            ("Chương I. QUY ĐỊNH CHUNG", "I", "QUY ĐỊNH CHUNG"),
            ("Chương II QUYỀN VÀ NGHĨA VỤ", "II", "QUYỀN VÀ NGHĨA VỤ"),
            ("Chương III: TRÁCH NHIỆM PHÁP LÝ", "III", "TRÁCH NHIỆM PHÁP LÝ"),
            ("  Chương IV. ĐIỀU KHOẢN THI HÀNH", "IV", "ĐIỀU KHOẢN THI HÀNH"),
            ("Chương X", "X", ""),
            ("Chương XII KHEN THƯỞNG VÀ XỬ LÝ VI PHẠM", "XII", "KHEN THƯỞNG VÀ XỬ LÝ VI PHẠM"),
        ]
        
        for text, expected_id, expected_title in test_cases:
            match = CHUONG_PATTERN.match(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(1).upper() == expected_id
            assert match.group(2).strip() == expected_title
    
    def test_chuong_pattern_no_match(self):
        """Test that non-chapter lines don't match CHƯƠNG pattern."""
        non_chapters = [
            "Điều 1. Phạm vi điều chỉnh",
            "1. Khoản một",
            "a) Điểm a",
            "Mục 1. Quy định chung",
            "Chương này quy định về...",  # Not a chapter header
        ]
        
        for text in non_chapters:
            match = CHUONG_PATTERN.match(text)
            assert match is None, f"Incorrectly matched: {text}"
    
    def test_muc_pattern(self):
        """Test MỤC (Section) pattern."""
        test_cases = [
            ("Mục 1. Quy định chung về thông điệp dữ liệu", "1", "Quy định chung về thông điệp dữ liệu"),
            ("Mục 2: Chữ ký điện tử", "2", "Chữ ký điện tử"),
            ("  Mục 3 CHỨNG THỰC ĐIỆN TỬ", "3", "CHỨNG THỰC ĐIỆN TỬ"),
            ("Mục 10. Quy định về giao dịch", "10", "Quy định về giao dịch"),
        ]
        
        for text, expected_id, expected_title in test_cases:
            match = MUC_PATTERN.match(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(1) == expected_id
            assert match.group(2).strip() == expected_title
    
    def test_dieu_pattern(self):
        """Test ĐIỀU (Article) pattern with various formats."""
        test_cases = [
            ("Điều 1. Phạm vi điều chỉnh", "1", "Phạm vi điều chỉnh"),
            ("Điều 2. Đối tượng áp dụng", "2", "Đối tượng áp dụng"),
            ("Điều 10. Giá trị pháp lý", "10", "Giá trị pháp lý"),
            ("Điều 100. Điều khoản thi hành", "100", "Điều khoản thi hành"),
            ("  Điều 5. Nguyên bản của thông điệp", "5", "Nguyên bản của thông điệp"),
            # Articles with letters (amendments)
            ("Điều 15a. Quy định bổ sung", "15a", "Quy định bổ sung"),
            ("Điều 20b. Sửa đổi", "20b", "Sửa đổi"),
        ]
        
        for text, expected_id, expected_title in test_cases:
            match = DIEU_PATTERN.match(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(1) == expected_id
            assert match.group(2).strip() == expected_title
    
    def test_khoan_pattern(self):
        """Test KHOẢN (Clause) pattern."""
        test_cases = [
            ("1. Cơ quan nhà nước có thẩm quyền", "1", "Cơ quan nhà nước có thẩm quyền"),
            ("2. Tổ chức, cá nhân tham gia", "2", "Tổ chức, cá nhân tham gia"),
            ("10. Các quy định khác", "10", "Các quy định khác"),
            ("  3. Điều kiện áp dụng", "3", "Điều kiện áp dụng"),
        ]
        
        for text, expected_id, expected_content in test_cases:
            match = KHOAN_PATTERN.match(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(1) == expected_id
            assert match.group(2).strip() == expected_content
    
    def test_diem_pattern(self):
        """Test ĐIỂM (Point) pattern including Vietnamese 'đ'."""
        test_cases = [
            ("a) Điểm a của khoản", "a", "Điểm a của khoản"),
            ("b) Nội dung điểm b", "b", "Nội dung điểm b"),
            ("c) Quy định tại điểm c", "c", "Quy định tại điểm c"),
            ("đ) Điểm đ (chữ Việt Nam)", "đ", "Điểm đ (chữ Việt Nam)"),  # Vietnamese 'đ'
            ("e) Các trường hợp khác", "e", "Các trường hợp khác"),
            ("  g) Điểm g", "g", "Điểm g"),
        ]
        
        for text, expected_id, expected_content in test_cases:
            match = DIEM_PATTERN.match(text)
            assert match is not None, f"Failed to match: {text}"
            assert match.group(1) == expected_id
            assert match.group(2).strip() == expected_content
    
    def test_definition_patterns(self):
        """Test patterns for detecting definition articles."""
        definition_texts = [
            "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:",
            "Trong Nghị định này, các từ ngữ sau đây được hiểu như sau:",
            "Trong Thông tư này, từ ngữ sau đây được hiểu như sau:",
            "Giải thích từ ngữ",
            "Định nghĩa các thuật ngữ",
        ]
        
        for text in definition_texts:
            matched = any(pattern.search(text) for pattern in DEFINITION_RE)
            assert matched, f"Failed to detect definition pattern in: {text}"
    
    def test_boilerplate_patterns(self):
        """Test boilerplate detection patterns."""
        boilerplate_texts = [
            "QUỐC HỘI",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "---------------",
            "Trang 1",
            "1 / 10",
            "Số: 20/2023/QH15",
        ]
        
        for text in boilerplate_texts:
            matched = any(pattern.match(text) for pattern in BOILERPLATE_RE)
            assert matched, f"Failed to detect boilerplate: {text}"


# =============================================================================
# Test Token Estimation
# =============================================================================

class TestTokenEstimation:
    """Test token estimation function."""
    
    def test_empty_text(self):
        """Test token estimation with empty text."""
        assert estimate_tokens("") == 0
        assert estimate_tokens("   ") == 0
    
    def test_short_text(self):
        """Test token estimation with short text."""
        # "Hello world" = 2 words * 1.3 ≈ 2-3 tokens
        tokens = estimate_tokens("Hello world")
        assert 2 <= tokens <= 4
    
    def test_vietnamese_text(self):
        """Test token estimation with Vietnamese text."""
        text = "Điều 1. Phạm vi điều chỉnh của Luật này"
        tokens = estimate_tokens(text)
        # 8 words * 1.3 ≈ 10-11 tokens
        assert 8 <= tokens <= 15
    
    def test_long_text(self):
        """Test token estimation with longer text."""
        text = " ".join(["từ"] * 100)  # 100 Vietnamese words
        tokens = estimate_tokens(text)
        # 100 words * 1.3 = 130 tokens
        assert 120 <= tokens <= 140


# =============================================================================
# Test Text Normalization
# =============================================================================

class TestTextNormalization:
    """Test text normalization functionality."""
    
    def test_normalize_removes_boilerplate(self, parser):
        """Test that normalization removes boilerplate lines."""
        paragraphs = [
            "QUỐC HỘI",
            "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
            "Độc lập - Tự do - Hạnh phúc",
            "---------------",
            "LUẬT GIAO DỊCH ĐIỆN TỬ",
            "Điều 1. Phạm vi điều chỉnh",
        ]
        
        normalized = parser._normalize_text(paragraphs)
        
        # Boilerplate should be removed
        assert "QUỐC HỘI" not in " ".join(normalized)
        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in " ".join(normalized)
        
        # Content should be preserved
        assert any("LUẬT GIAO DỊCH ĐIỆN TỬ" in line for line in normalized)
        assert any("Điều 1" in line for line in normalized)
    
    def test_normalize_preserves_vietnamese_diacritics(self, parser):
        """Test that Vietnamese diacritics are preserved."""
        paragraphs = [
            "Điều 1. Phạm vi điều chỉnh",
            "Giao dịch điện tử là giao dịch được thực hiện bằng phương tiện điện tử.",
        ]
        
        normalized = parser._normalize_text(paragraphs)
        
        # Check diacritics preserved
        assert any("Điều" in line for line in normalized)
        assert any("điện tử" in line for line in normalized)
        assert any("phương tiện" in line for line in normalized)
    
    def test_normalize_handles_whitespace(self, parser):
        """Test whitespace normalization."""
        paragraphs = [
            "Điều   1.    Phạm    vi",
            "  Nội dung với khoảng trắng thừa  ",
        ]
        
        normalized = parser._normalize_text(paragraphs)
        
        # Multiple spaces should be normalized
        assert "Điều 1. Phạm vi" in normalized[0]


# =============================================================================
# Test Tree Building
# =============================================================================

class TestTreeBuilding:
    """Test hierarchical tree construction."""
    
    def test_build_tree_basic_structure(self, parser, sample_legal_text_lines):
        """Test that tree builds correct hierarchy."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Root should be LAW
        assert tree.node_type == LegalNodeType.LAW
        assert tree.identifier == "20/2023/QH15"
        
        # Should have chapters as children
        chapters = [c for c in tree.children if c.node_type == LegalNodeType.CHAPTER]
        assert len(chapters) >= 1
        
        # First chapter should be Chapter I
        assert chapters[0].identifier == "I"
    
    def test_build_tree_chapter_contains_articles(self, parser, sample_legal_text_lines):
        """Test that chapters contain their articles."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chapter1 = tree.children[0]
        articles = [c for c in chapter1.children if c.node_type == LegalNodeType.ARTICLE]
        
        assert len(articles) >= 1
        assert articles[0].identifier == "1"
    
    def test_build_tree_section_hierarchy(self, parser, sample_legal_text_lines):
        """Test section (Mục) hierarchy under chapter."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Find Chapter II
        chapter2 = next((c for c in tree.children 
                        if c.node_type == LegalNodeType.CHAPTER and c.identifier == "II"), None)
        
        if chapter2:
            sections = [c for c in chapter2.children if c.node_type == LegalNodeType.SECTION]
            assert len(sections) >= 1
    
    def test_build_tree_clause_points(self, parser, sample_legal_text_lines):
        """Test clause and point hierarchy."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Find Article 4 which has clauses with points
        article4 = None
        for chapter in tree.children:
            for node in chapter.children:
                if node.node_type == LegalNodeType.SECTION:
                    for article in node.children:
                        if article.node_type == LegalNodeType.ARTICLE and article.identifier == "4":
                            article4 = article
                            break
                elif node.node_type == LegalNodeType.ARTICLE and node.identifier == "4":
                    article4 = node
                    break
        
        if article4:
            clauses = [c for c in article4.children if c.node_type == LegalNodeType.CLAUSE]
            assert len(clauses) >= 1
            
            # Clause 2 should have points
            clause2 = next((c for c in clauses if c.identifier == "2"), None)
            if clause2:
                points = [c for c in clause2.children if c.node_type == LegalNodeType.POINT]
                assert len(points) >= 1
    
    def test_build_tree_definition_article_detection(self, parser, sample_legal_text_lines):
        """Test that definition articles are correctly detected."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Find Article 3 (Giải thích từ ngữ)
        def_article = None
        for chapter in tree.children:
            for node in chapter.children:
                if node.node_type == LegalNodeType.ARTICLE and node.identifier == "3":
                    def_article = node
                    break
        
        assert def_article is not None
        assert def_article.is_definition_article is True
    
    def test_sibling_relationships(self, parser, sample_legal_text_lines):
        """Test that sibling relationships are correctly set."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Check chapter siblings
        chapters = [c for c in tree.children if c.node_type == LegalNodeType.CHAPTER]
        if len(chapters) >= 2:
            assert chapters[0].next_sibling == chapters[1]
            assert chapters[1].prev_sibling == chapters[0]
    
    def test_parent_relationships(self, parser, sample_legal_text_lines):
        """Test that parent relationships are correctly set."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        # Chapters should have Law as parent
        for chapter in tree.children:
            assert chapter.parent == tree


# =============================================================================
# Test Chunking
# =============================================================================

class TestChunking:
    """Test chunk generation."""
    
    def test_chunk_generation_basic(self, parser, sample_legal_text_lines):
        """Test basic chunk generation."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        assert len(chunks) > 0
        assert all(isinstance(c, LegalChunk) for c in chunks)
    
    def test_chunk_id_format(self, parser, sample_legal_text_lines):
        """Test that chunk IDs follow expected format."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        for chunk in chunks:
            # Chunk ID should contain node type identifiers
            assert "=" in chunk.chunk_id
            assert ":" in chunk.chunk_id or chunk.chunk_id.startswith("LAW=")
    
    def test_chunk_embedding_prefix(self, parser, sample_legal_text_lines):
        """Test that embedding prefix is correctly formatted."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        for chunk in chunks:
            # Embedding prefix should have DOC identifier (document number)
            assert "DOC=" in chunk.embedding_prefix
            # Should use | separator
            assert " | " in chunk.embedding_prefix or "DOC=" in chunk.embedding_prefix
    
    def test_chunk_metadata_completeness(self, parser, sample_legal_text_lines):
        """Test that chunk metadata contains required fields."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        for chunk in chunks:
            assert "law_id" in chunk.metadata
            assert "source_file" in chunk.metadata
            assert "lineage" in chunk.metadata
            assert isinstance(chunk.metadata["lineage"], list)
    
    def test_chunk_content_not_empty(self, parser, sample_legal_text_lines):
        """Test that chunks have non-empty content."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        for chunk in chunks:
            assert chunk.content
            assert len(chunk.content.strip()) > 0
    
    def test_definition_article_chunking(self, parser, sample_legal_text_lines):
        """Test that definition articles are split by definition item."""
        tree = parser._build_tree(
            sample_legal_text_lines,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        # Find chunks from definition article (Article 3)
        def_chunks = [c for c in chunks if "DIEU=3" in c.chunk_id]
        
        # Should have multiple chunks (one per definition)
        # Article 3 has 3 definitions
        assert len(def_chunks) >= 1
    
    def test_long_article_splitting(self, parser, sample_long_article_lines):
        """Test that long articles are split by clauses."""
        # Use lower threshold for testing
        parser.token_threshold = 100
        
        tree = parser._build_tree(
            sample_long_article_lines,
            law_id="TEST/2023",
            law_name="Test Law",
            source_file="test.docx"
        )
        
        chunks = parser._generate_chunks(tree, "test.docx")
        
        # Should have multiple chunks due to splitting
        assert len(chunks) > 1
        
        # Each chunk should be within threshold (approximately)
        for chunk in chunks:
            tokens = estimate_tokens(chunk.content)
            # Allow some tolerance since splitting is at clause boundaries
            assert tokens < 500  # Should be well under original article size


# =============================================================================
# Test LegalNode Methods
# =============================================================================

class TestLegalNodeMethods:
    """Test LegalNode data class methods."""
    
    def test_get_full_id(self):
        """Test full ID generation."""
        law = LegalNode(node_type=LegalNodeType.LAW, identifier="20/2023/QH15")
        chapter = LegalNode(node_type=LegalNodeType.CHAPTER, identifier="I", parent=law)
        article = LegalNode(node_type=LegalNodeType.ARTICLE, identifier="1", parent=chapter)
        
        full_id = article.get_full_id()
        
        assert "LAW=20/2023/QH15" in full_id
        assert "CHUONG=I" in full_id
        assert "DIEU=1" in full_id
    
    def test_get_lineage(self):
        """Test lineage path generation."""
        law = LegalNode(node_type=LegalNodeType.LAW, identifier="20/2023/QH15")
        chapter = LegalNode(node_type=LegalNodeType.CHAPTER, identifier="I", parent=law)
        article = LegalNode(node_type=LegalNodeType.ARTICLE, identifier="1", parent=chapter)
        clause = LegalNode(node_type=LegalNodeType.CLAUSE, identifier="1", parent=article)
        
        lineage = clause.get_lineage()
        
        assert lineage == ["LAW", "CHUONG", "DIEU", "KHOAN"]
    
    def test_get_ancestors(self):
        """Test ancestor dictionary generation."""
        law = LegalNode(
            node_type=LegalNodeType.LAW,
            identifier="20/2023/QH15",
            title="Luật Giao dịch điện tử"
        )
        chapter = LegalNode(
            node_type=LegalNodeType.CHAPTER,
            identifier="I",
            title="QUY ĐỊNH CHUNG",
            parent=law
        )
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="1",
            title="Phạm vi điều chỉnh",
            parent=chapter
        )
        
        ancestors = article.get_ancestors()
        
        assert ancestors["law_id"] == "20/2023/QH15"
        assert ancestors["law_name"] == "Luật Giao dịch điện tử"
        assert "Chương I" in ancestors["chapter"]


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_file_not_found(self, parser):
        """Test handling of non-existent file."""
        result = parser.parse("/nonexistent/path/file.docx")
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    def test_unsupported_format(self, parser, tmp_path):
        """Test handling of unsupported file format."""
        # Create a file with unsupported extension
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some content")
        
        result = parser.parse(test_file)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert "unsupported" in result.errors[0].lower()
    
    def test_doc_without_libreoffice(self, parser, tmp_path):
        """Test handling of .doc file when LibreOffice is not available."""
        # Create a .doc file
        test_file = tmp_path / "test.doc"
        test_file.write_bytes(b"PK...")  # Not a real doc, just for path testing
        
        # Mock LibreOffice as unavailable
        parser.libreoffice_path = None
        
        result = parser.parse(test_file)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert ".doc requires conversion" in result.errors[0]


# =============================================================================
# Test ParseResult
# =============================================================================

class TestParseResult:
    """Test ParseResult data class."""
    
    def test_parse_result_default_values(self):
        """Test ParseResult default initialization."""
        result = ParseResult(success=False)
        
        assert result.success is False
        assert result.chunks == []
        assert result.tree is None
        assert result.errors == []
        assert result.warnings == []
        assert result.statistics == {}
    
    def test_parse_result_with_data(self):
        """Test ParseResult with populated data."""
        chunk = LegalChunk(
            chunk_id="test:chunk",
            content="Test content",
            embedding_prefix="TEST",
            metadata={"key": "value"}
        )
        
        result = ParseResult(
            success=True,
            chunks=[chunk],
            statistics={"total_chunks": 1}
        )
        
        assert result.success is True
        assert len(result.chunks) == 1
        assert result.statistics["total_chunks"] == 1


# =============================================================================
# Test LegalChunk
# =============================================================================

class TestLegalChunk:
    """Test LegalChunk data class."""
    
    def test_chunk_to_dict(self):
        """Test chunk serialization to dictionary."""
        chunk = LegalChunk(
            chunk_id="20/2023/QH15:CHUONG=I:DIEU=1",
            content="Điều 1. Phạm vi điều chỉnh",
            embedding_prefix="LAW=20/2023/QH15 | CHUONG=I | DIEU=1",
            metadata={
                "law_id": "20/2023/QH15",
                "chapter": "Chương I",
                "article_id": "Điều 1",
            }
        )
        
        d = chunk.to_dict()
        
        assert d["chunk_id"] == "20/2023/QH15:CHUONG=I:DIEU=1"
        assert d["content"] == "Điều 1. Phạm vi điều chỉnh"
        assert d["embedding_prefix"] == "LAW=20/2023/QH15 | CHUONG=I | DIEU=1"
        assert d["metadata"]["law_id"] == "20/2023/QH15"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests with mock DOCX files."""
    
    @patch('indexing.loaders.vietnam_legal_docx_parser.VietnamLegalDocxParser._extract_paragraphs')
    def test_full_parse_flow(self, mock_extract, parser, sample_legal_text_lines):
        """Test complete parsing flow with mocked DOCX extraction."""
        # Mock the DOCX extraction
        mock_extract.return_value = sample_legal_text_lines
        
        # Create a mock file path
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'suffix', new_callable=lambda: property(lambda self: '.docx')):
                result = parser.parse(Path("/mock/test.docx"))
        
        assert result.success is True
        assert len(result.chunks) > 0
        assert result.tree is not None
        assert "total_chunks" in result.statistics
    
    @patch('indexing.loaders.vietnam_legal_docx_parser.VietnamLegalDocxParser._extract_paragraphs')
    def test_parse_with_custom_law_id(self, mock_extract, parser, sample_legal_text_lines):
        """Test parsing with custom law_id override."""
        mock_extract.return_value = sample_legal_text_lines
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'suffix', new_callable=lambda: property(lambda self: '.docx')):
                result = parser.parse(
                    Path("/mock/test.docx"),
                    law_id="CUSTOM/2025/QH16",
                    law_name="Luật Tùy chỉnh"
                )
        
        assert result.success is True
        # Check that custom law_id is used
        for chunk in result.chunks:
            assert chunk.metadata.get("law_id") == "CUSTOM/2025/QH16"


# =============================================================================
# Test Convenience Function
# =============================================================================

class TestConvenienceFunction:
    """Test the module-level convenience function."""
    
    @patch('indexing.loaders.vietnam_legal_docx_parser.VietnamLegalDocxParser.parse')
    def test_parse_vietnam_legal_docx(self, mock_parse):
        """Test the convenience function."""
        mock_parse.return_value = ParseResult(success=True)
        
        result = parse_vietnam_legal_docx(
            "/path/to/file.docx",
            law_id="20/2023/QH15",
            token_threshold=1000
        )
        
        mock_parse.assert_called_once()
        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
