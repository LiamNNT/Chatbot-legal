"""
Unit tests for Graph ETL Pipeline

Tests cover:
- Document loaders (PDF, JSON, Markdown, Text)
- Vietnamese text preprocessing
- Transform pipeline
- Batch processing
- Error handling
- Integration with Graph Builder
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Any
from pathlib import Path
import tempfile

from indexing.graph_etl_pipeline import (
    GraphETLPipeline,
    DocumentLoader,
    PDFLoader,
    JSONLoader,
    MarkdownLoader,
    TextLoader,
    TextTransformer,
    ETLResult,
)
from core.domain.models import Entity


# Test Data Fixtures
@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test files"""
    # Create test PDF (mock content)
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("Mock PDF content: Học phần Python")
    
    # Create test JSON
    json_file = tmp_path / "test.json"
    json_file.write_text('{"text": "Học phần Database", "metadata": {"source": "quy_dinh"}}')
    
    # Create test Markdown
    md_file = tmp_path / "test.md"
    md_file.write_text("# Quy định\n\nHọc phần AI thuộc khoa KHMT")
    
    # Create test text
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Học phần Machine Learning có 3 tín chỉ")
    
    return {
        "pdf": pdf_file,
        "json": json_file,
        "markdown": md_file,
        "text": txt_file,
    }


@pytest.fixture
def sample_documents() -> List[Dict[str, Any]]:
    """Sample documents for testing"""
    return [
        {
            "text": "Học phần Lập trình Python thuộc Khoa KHMT",
            "metadata": {"source": "quy_dinh.pdf", "page": 1}
        },
        {
            "text": "Môn AI có 3 tín chỉ",
            "metadata": {"source": "quy_dinh.pdf", "page": 2}
        },
    ]


@pytest.fixture
def mock_graph_builder():
    """Mock GraphBuilderService"""
    builder = AsyncMock()
    builder.build_from_documents = AsyncMock(return_value=Mock(
        created_nodes=10,
        created_relationships=5,
        skipped_entities=1,
        errors=[]
    ))
    return builder


# DocumentLoader Tests
class TestDocumentLoaders:
    """Test different document loaders"""

    def test_pdf_loader_loads_file(self, temp_test_files):
        """Test PDF loader"""
        with patch('PyPDF2.PdfReader') as mock_pdf:
            # Mock PDF reading
            mock_page = Mock()
            mock_page.extract_text.return_value = "Học phần Python"
            mock_pdf.return_value.pages = [mock_page]
            
            loader = PDFLoader()
            documents = loader.load(str(temp_test_files["pdf"]))
            
            assert len(documents) >= 1
            assert "text" in documents[0]

    def test_json_loader_loads_file(self, temp_test_files):
        """Test JSON loader"""
        loader = JSONLoader()
        documents = loader.load(str(temp_test_files["json"]))
        
        assert len(documents) == 1
        assert documents[0]["text"] == "Học phần Database"
        assert "metadata" in documents[0]

    def test_markdown_loader_loads_file(self, temp_test_files):
        """Test Markdown loader"""
        loader = MarkdownLoader()
        documents = loader.load(str(temp_test_files["markdown"]))
        
        assert len(documents) >= 1
        assert "Học phần AI" in documents[0]["text"]

    def test_text_loader_loads_file(self, temp_test_files):
        """Test plain text loader"""
        loader = TextLoader()
        documents = loader.load(str(temp_test_files["text"]))
        
        assert len(documents) == 1
        assert "Machine Learning" in documents[0]["text"]

    def test_loader_handles_missing_file(self):
        """Test loader handles missing file gracefully"""
        loader = TextLoader()
        
        with pytest.raises(FileNotFoundError):
            loader.load("/nonexistent/file.txt")

    def test_json_loader_handles_invalid_json(self, tmp_path):
        """Test JSON loader handles invalid JSON"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{broken json")
        
        loader = JSONLoader()
        
        with pytest.raises(Exception):  # Should raise JSON decode error
            loader.load(str(invalid_json))


# TextTransformer Tests
class TestTextTransformer:
    """Test text transformation pipeline"""

    def test_clean_vietnamese_text(self):
        """Test Vietnamese text cleaning"""
        transformer = TextTransformer()
        
        dirty_text = "  Học   phần    Python  \n\n\n  có  3  tín  chỉ  "
        clean_text = transformer.clean_vietnamese_text(dirty_text)
        
        # Should normalize whitespace
        assert "   " not in clean_text
        assert clean_text.strip() == clean_text
        assert "\n\n\n" not in clean_text

    def test_normalize_whitespace(self):
        """Test whitespace normalization"""
        transformer = TextTransformer()
        
        text = "Text\twith\tmultiple    spaces   and\ttabs"
        normalized = transformer.normalize_whitespace(text)
        
        assert "\t" not in normalized
        assert "    " not in normalized

    def test_remove_special_characters(self):
        """Test special character removal"""
        transformer = TextTransformer()
        
        text = "Text with @#$% special &*() characters"
        cleaned = transformer.remove_special_characters(text)
        
        # Should keep Vietnamese and alphanumeric
        assert "@#$%" not in cleaned
        assert "Text with special characters" in cleaned

    def test_chunk_long_text(self):
        """Test text chunking for long documents"""
        transformer = TextTransformer()
        
        # Create long text
        long_text = " ".join(["Học phần Python"] * 1000)
        
        chunks = transformer.chunk_text(long_text, chunk_size=500, overlap=50)
        
        assert len(chunks) > 1
        # Verify overlap
        assert len(chunks[0]) <= 500 + 50  # chunk_size + overlap margin

    def test_transform_preserves_vietnamese(self):
        """Test that transform preserves Vietnamese characters"""
        transformer = TextTransformer()
        
        vietnamese_text = "Học phần có điều kiện tiên quyết là Toán cao cấp"
        transformed = transformer.transform(vietnamese_text)
        
        # All Vietnamese words should be preserved
        assert "Học" in transformed
        assert "điều" in transformed
        assert "tiên" in transformed


# GraphETLPipeline Tests
class TestGraphETLPipeline:
    """Test GraphETLPipeline integration"""

    @pytest.mark.asyncio
    async def test_run_pipeline_success(
        self,
        mock_graph_builder,
        sample_documents
    ):
        """Test successful pipeline execution"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        result = await pipeline.run(sample_documents)
        
        assert isinstance(result, ETLResult)
        assert result.total_documents == len(sample_documents)
        assert result.processed_documents > 0
        assert mock_graph_builder.build_from_documents.called

    @pytest.mark.asyncio
    async def test_load_from_directory(
        self,
        mock_graph_builder,
        temp_test_files
    ):
        """Test loading documents from directory"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        # Get parent directory of test files
        source_dir = temp_test_files["text"].parent
        
        result = await pipeline.load_and_process(str(source_dir))
        
        assert result.total_documents > 0

    @pytest.mark.asyncio
    async def test_load_single_file(
        self,
        mock_graph_builder,
        temp_test_files
    ):
        """Test loading single file"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        result = await pipeline.load_and_process(str(temp_test_files["text"]))
        
        assert result.total_documents == 1
        assert result.processed_documents == 1

    @pytest.mark.asyncio
    async def test_batch_processing(
        self,
        mock_graph_builder,
        sample_documents
    ):
        """Test batch processing of documents"""
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            batch_size=1  # Process one at a time
        )
        
        # Create many documents
        many_docs = sample_documents * 10  # 20 documents
        
        result = await pipeline.run(many_docs)
        
        # Should process all in batches
        assert result.processed_documents == len(many_docs)

    @pytest.mark.asyncio
    async def test_handles_document_errors(self, mock_graph_builder):
        """Test handling of document processing errors"""
        # Mock builder that fails on specific document
        async def mock_build_with_error(docs):
            if "error" in docs[0]["text"]:
                raise Exception("Processing error")
            return Mock(created_nodes=1, created_relationships=0, errors=[])
        
        mock_graph_builder.build_from_documents = AsyncMock(
            side_effect=mock_build_with_error
        )
        
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        documents = [
            {"text": "Normal document", "metadata": {}},
            {"text": "Document with error keyword", "metadata": {}},
        ]
        
        result = await pipeline.run(documents)
        
        # Should continue despite errors
        assert len(result.errors) > 0
        assert "Processing error" in str(result.errors)

    @pytest.mark.asyncio
    async def test_tracks_processing_time(
        self,
        mock_graph_builder,
        sample_documents
    ):
        """Test that processing time is tracked"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        result = await pipeline.run(sample_documents)
        
        assert result.processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_statistics_tracking(
        self,
        mock_graph_builder,
        sample_documents
    ):
        """Test ETL statistics tracking"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        result = await pipeline.run(sample_documents)
        
        assert result.total_documents == len(sample_documents)
        assert result.processed_documents <= result.total_documents
        assert result.created_nodes >= 0
        assert result.created_relationships >= 0


# Integration Tests
class TestETLIntegration:
    """Test ETL pipeline integration scenarios"""

    @pytest.mark.asyncio
    async def test_end_to_end_pdf_to_graph(
        self,
        mock_graph_builder,
        temp_test_files
    ):
        """Test complete pipeline from PDF to graph"""
        with patch('PyPDF2.PdfReader') as mock_pdf:
            # Mock PDF content
            mock_page = Mock()
            mock_page.extract_text.return_value = "Học phần Python thuộc KHMT"
            mock_pdf.return_value.pages = [mock_page]
            
            pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
            
            result = await pipeline.load_and_process(str(temp_test_files["pdf"]))
            
            assert result.processed_documents > 0
            assert mock_graph_builder.build_from_documents.called

    @pytest.mark.asyncio
    async def test_mixed_file_types(
        self,
        mock_graph_builder,
        temp_test_files
    ):
        """Test processing mixed file types from directory"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        source_dir = temp_test_files["text"].parent
        result = await pipeline.load_and_process(str(source_dir))
        
        # Should process multiple file types
        assert result.total_documents >= 3  # At least JSON, MD, TXT

    @pytest.mark.asyncio
    async def test_transform_and_extract_pipeline(
        self,
        mock_graph_builder
    ):
        """Test full transform and extraction pipeline"""
        pipeline = GraphETLPipeline(graph_builder=mock_graph_builder)
        
        # Document with messy formatting
        messy_doc = {
            "text": "  Học   phần   Python   \n\n  thuộc   Khoa  KHMT  ",
            "metadata": {"source": "test"}
        }
        
        result = await pipeline.run([messy_doc])
        
        # Text should be cleaned before extraction
        assert result.processed_documents == 1


# Performance Tests
class TestETLPerformance:
    """Test ETL pipeline performance"""

    @pytest.mark.asyncio
    async def test_large_batch_processing(self, mock_graph_builder):
        """Test processing large number of documents"""
        import time
        
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            batch_size=100
        )
        
        # Create 500 documents
        many_docs = [
            {"text": f"Document {i}", "metadata": {}}
            for i in range(500)
        ]
        
        start_time = time.time()
        result = await pipeline.run(many_docs)
        elapsed = time.time() - start_time
        
        assert result.processed_documents == 500
        print(f"Processed 500 documents in {elapsed:.2f}s")

    @pytest.mark.asyncio
    async def test_concurrent_batch_processing(self, mock_graph_builder):
        """Test concurrent processing of batches"""
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            batch_size=10,
            max_concurrent_batches=3
        )
        
        documents = [
            {"text": f"Doc {i}", "metadata": {}}
            for i in range(100)
        ]
        
        result = await pipeline.run(documents)
        
        assert result.processed_documents == 100


# Error Recovery Tests
class TestErrorRecovery:
    """Test error recovery and retry logic"""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, mock_graph_builder):
        """Test retry logic on transient errors"""
        call_count = 0
        
        async def mock_with_retry(docs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return Mock(created_nodes=1, created_relationships=0, errors=[])
        
        mock_graph_builder.build_from_documents = AsyncMock(
            side_effect=mock_with_retry
        )
        
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            max_retries=3
        )
        
        documents = [{"text": "Test doc", "metadata": {}}]
        result = await pipeline.run(documents)
        
        # Should succeed after retry
        assert call_count == 2
        assert result.processed_documents == 1

    @pytest.mark.asyncio
    async def test_continues_on_single_document_failure(self, mock_graph_builder):
        """Test pipeline continues when single document fails"""
        call_count = 0
        
        async def mock_with_selective_failure(docs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail second batch
                raise Exception("Document processing error")
            return Mock(created_nodes=1, created_relationships=0, errors=[])
        
        mock_graph_builder.build_from_documents = AsyncMock(
            side_effect=mock_with_selective_failure
        )
        
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            batch_size=1
        )
        
        documents = [
            {"text": "Doc 1", "metadata": {}},
            {"text": "Doc 2", "metadata": {}},
            {"text": "Doc 3", "metadata": {}},
        ]
        
        result = await pipeline.run(documents)
        
        # Should process docs 1 and 3, skip 2
        assert result.processed_documents >= 1
        assert len(result.errors) > 0


# Configuration Tests
class TestETLConfiguration:
    """Test different ETL configurations"""

    @pytest.mark.asyncio
    async def test_custom_batch_size(self, mock_graph_builder, sample_documents):
        """Test custom batch size configuration"""
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            batch_size=1  # Process one at a time
        )
        
        result = await pipeline.run(sample_documents * 5)
        
        # Should call builder multiple times (once per doc)
        assert mock_graph_builder.build_from_documents.call_count >= 5

    @pytest.mark.asyncio
    async def test_enable_transforms(self, mock_graph_builder):
        """Test with text transforms enabled"""
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            enable_transforms=True
        )
        
        messy_doc = {"text": "  Messy   text  ", "metadata": {}}
        result = await pipeline.run([messy_doc])
        
        assert result.processed_documents == 1

    @pytest.mark.asyncio
    async def test_disable_transforms(self, mock_graph_builder):
        """Test with text transforms disabled"""
        pipeline = GraphETLPipeline(
            graph_builder=mock_graph_builder,
            enable_transforms=False
        )
        
        messy_doc = {"text": "  Messy   text  ", "metadata": {}}
        result = await pipeline.run([messy_doc])
        
        # Should process without transformation
        assert result.processed_documents == 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
