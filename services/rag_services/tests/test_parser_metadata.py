# tests/test_parser_metadata.py
#
# Description:
# Tests for Vietnamese legal DOCX parser metadata correctness.
# Validates that chapter/article/clause metadata is properly attached to chunks.

import pytest
from pathlib import Path
from collections import defaultdict

from indexing.loaders.vietnam_legal_docx_parser import (
    VietnamLegalDocxParser,
    LegalNode,
    LegalNodeType,
)


class TestLegalNodeAncestors:
    """Test LegalNode.get_ancestors() method."""
    
    def test_get_ancestors_includes_self_by_default(self):
        """Test that get_ancestors includes self node when include_self=True (default)."""
        # Create hierarchy: LAW -> CHAPTER -> ARTICLE
        law = LegalNode(
            node_type=LegalNodeType.LAW,
            identifier="20/2023/QH15",
            title="Luật số 20/2023/QH15"
        )
        chapter = LegalNode(
            node_type=LegalNodeType.CHAPTER,
            identifier="II",
            title="NGHĨA VỤ QUÂN SỰ",
            parent=law
        )
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="7",
            title="Nội dung nghĩa vụ quân sự",
            parent=chapter
        )
        
        # Test default behavior (include_self=True)
        ancestors = article.get_ancestors()
        
        # Should include article itself
        assert "article_id" in ancestors, "article_id missing from ancestors"
        assert ancestors["article_id"] == "Điều 7"
        assert ancestors["article_number"] == "7"
        assert ancestors["article_title"] == "Nội dung nghĩa vụ quân sự"
        
        # Should include chapter
        assert "chapter" in ancestors
        assert "chapter_id" in ancestors
        assert ancestors["chapter_id"] == "II"
        
        # Should include law
        assert "law_id" in ancestors
        assert ancestors["law_id"] == "20/2023/QH15"
    
    def test_get_ancestors_exclude_self(self):
        """Test that get_ancestors excludes self node when include_self=False."""
        law = LegalNode(
            node_type=LegalNodeType.LAW,
            identifier="20/2023/QH15",
            title="Test Law"
        )
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="1",
            title="Test Article",
            parent=law
        )
        
        ancestors = article.get_ancestors(include_self=False)
        
        # Should NOT include article itself
        assert "article_id" not in ancestors
        assert "article_number" not in ancestors
        
        # Should include law
        assert "law_id" in ancestors
    
    def test_clause_has_article_in_ancestors(self):
        """Test that a clause node includes article in ancestors."""
        law = LegalNode(node_type=LegalNodeType.LAW, identifier="20/2023/QH15")
        chapter = LegalNode(node_type=LegalNodeType.CHAPTER, identifier="II", parent=law)
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="15",
            title="Test Title",
            parent=chapter
        )
        clause = LegalNode(
            node_type=LegalNodeType.CLAUSE,
            identifier="1",
            content="Test clause content",
            parent=article
        )
        
        ancestors = clause.get_ancestors()
        
        # Should include clause itself
        assert "clause_no" in ancestors
        assert ancestors["clause_no"] == "1"
        
        # Should include article
        assert "article_id" in ancestors
        assert ancestors["article_id"] == "Điều 15"
        assert ancestors["article_number"] == "15"
        
        # Should include chapter
        assert "chapter_id" in ancestors
        assert ancestors["chapter_id"] == "II"


class TestParserChunksMetadata:
    """Test parser output chunks have correct metadata."""
    
    @pytest.fixture
    def parser(self):
        return VietnamLegalDocxParser()
    
    def test_parsed_chunks_have_article_metadata(self, parser, tmp_path):
        """Test that parsed chunks contain article_id and article_title in metadata."""
        # This test requires a real DOCX file
        # For unit testing, we'll use the parser's internal methods
        
        # Create a simple tree structure
        law = LegalNode(
            node_type=LegalNodeType.LAW,
            identifier="20/2023/QH15",
            title="Test Law"
        )
        chapter = LegalNode(
            node_type=LegalNodeType.CHAPTER,
            identifier="II",
            title="CHƯƠNG II",
            parent=law
        )
        law.children.append(chapter)
        
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="7",
            title="Nghĩa vụ quân sự",
            content="Nội dung điều 7",
            parent=chapter
        )
        chapter.children.append(article)
        
        # Create chunk from article
        chunk = parser._create_chunk(
            node=article,
            content="Test content for article 7",
            source_file="test.docx",
            doc_kind="LAW"
        )
        
        # Validate metadata
        assert chunk.metadata.get("article_id") == "Điều 7"
        assert chunk.metadata.get("article_number") == "7"
        assert chunk.metadata.get("article_title") == "Nghĩa vụ quân sự"
        assert chunk.metadata.get("chapter_id") == "II"
        assert chunk.metadata.get("law_id") == "20/2023/QH15"
    
    def test_all_chapters_have_chunks(self, parser, tmp_path):
        """Test that chunks exist for all chapters (no missing Chapter II/III)."""
        # Create a law with 3 chapters
        law = LegalNode(
            node_type=LegalNodeType.LAW,
            identifier="20/2023/QH15"
        )
        
        for ch_num, ch_id in enumerate(["I", "II", "III"], 1):
            chapter = LegalNode(
                node_type=LegalNodeType.CHAPTER,
                identifier=ch_id,
                title=f"CHƯƠNG {ch_id}",
                parent=law
            )
            law.children.append(chapter)
            
            # Add 2 articles per chapter
            for art_num in range((ch_num - 1) * 2 + 1, (ch_num - 1) * 2 + 3):
                article = LegalNode(
                    node_type=LegalNodeType.ARTICLE,
                    identifier=str(art_num),
                    title=f"Điều {art_num} Title",
                    content=f"Content for article {art_num}",
                    parent=chapter
                )
                chapter.children.append(article)
        
        # Create chunks manually using _create_chunk for each article
        chunks = []
        articles = parser._find_all_nodes(law, LegalNodeType.ARTICLE)
        for article in articles:
            chunk = parser._create_chunk(article, article.content, "test.docx", "LAW")
            chunks.append(chunk)
        
        # Group chunks by chapter
        chapters_found = set()
        for chunk in chunks:
            chapter_id = chunk.metadata.get("chapter_id")
            if chapter_id:
                chapters_found.add(chapter_id)
        
        # Assert all 3 chapters are present
        assert "I" in chapters_found, "Chapter I missing from chunks"
        assert "II" in chapters_found, "Chapter II missing from chunks"
        assert "III" in chapters_found, "Chapter III missing from chunks"
    
    def test_chunks_grouped_by_chapter_have_article_ids(self, parser):
        """Test that when grouping chunks by chapter, all have valid article_ids."""
        # Create test tree
        law = LegalNode(node_type=LegalNodeType.LAW, identifier="TEST/2023")
        
        chapter2 = LegalNode(
            node_type=LegalNodeType.CHAPTER,
            identifier="II",
            title="Chapter Two",
            parent=law
        )
        law.children.append(chapter2)
        
        # Add articles 7-12 to Chapter II
        for art_num in range(7, 13):
            article = LegalNode(
                node_type=LegalNodeType.ARTICLE,
                identifier=str(art_num),
                title=f"Article {art_num} Title",
                parent=chapter2
            )
            chapter2.children.append(article)
            
            # Add a clause
            clause = LegalNode(
                node_type=LegalNodeType.CLAUSE,
                identifier="1",
                content=f"Clause 1 of article {art_num}",
                parent=article
            )
            article.children.append(clause)
        
        # Create chunks for articles and clauses
        chunks = []
        articles = parser._find_all_nodes(law, LegalNodeType.ARTICLE)
        for article in articles:
            chunk = parser._create_chunk(article, "article content", "test.docx", "LAW")
            chunks.append(chunk)
        
        clauses = parser._find_all_nodes(law, LegalNodeType.CLAUSE)
        for clause in clauses:
            chunk = parser._create_chunk(clause, clause.content, "test.docx", "LAW")
            chunks.append(chunk)
        
        # Filter chunks from Chapter II
        chapter2_chunks = [c for c in chunks if c.metadata.get("chapter_id") == "II"]
        
        # All should have article_id
        for chunk in chapter2_chunks:
            assert chunk.metadata.get("article_id") is not None, \
                f"Chunk {chunk.chunk_id} in Chapter II missing article_id"
            assert chunk.metadata.get("article_number") is not None, \
                f"Chunk {chunk.chunk_id} in Chapter II missing article_number"


class TestEmbeddingPrefixGeneration:
    """Test embedding prefix generation includes all hierarchy levels."""
    
    @pytest.fixture
    def parser(self):
        return VietnamLegalDocxParser()
    
    def test_embedding_prefix_contains_article(self, parser):
        """Test embedding prefix contains DIEU= for article chunks."""
        law = LegalNode(node_type=LegalNodeType.LAW, identifier="20/2023/QH15")
        chapter = LegalNode(node_type=LegalNodeType.CHAPTER, identifier="II", parent=law)
        article = LegalNode(
            node_type=LegalNodeType.ARTICLE,
            identifier="15",
            parent=chapter
        )
        
        chunk = parser._create_chunk(article, "test", "test.docx")
        
        assert "DIEU=15" in chunk.embedding_prefix, \
            f"embedding_prefix missing DIEU: {chunk.embedding_prefix}"
        assert "CHUONG=II" in chunk.embedding_prefix, \
            f"embedding_prefix missing CHUONG: {chunk.embedding_prefix}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
