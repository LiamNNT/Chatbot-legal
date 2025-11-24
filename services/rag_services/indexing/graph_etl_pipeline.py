"""
Graph ETL Pipeline - Documents → Graph.

This module implements the ETL (Extract, Transform, Load) pipeline
for building the knowledge graph from various document sources.

Week 2 - Task A2: ETL Pipeline Implementation
Priority: P1

Pipeline Stages:
1. Extract: Load documents from various sources (PDF, DOCX, JSON, MD)
2. Transform: Clean text, extract entities, enrich metadata
3. Load: Build graph nodes and relationships

Example:
    ```python
    pipeline = GraphETLPipeline(
        graph_builder=graph_builder_service,
        config=ETLConfig()
    )
    
    result = await pipeline.run("data/quy_dinh")
    print(f"Processed {result.documents_processed} documents")
    ```
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from core.domain.graph_models import NodeCategory
from core.services.graph_builder_service import (
    GraphBuilderService,
    Document,
    GraphBuildResult
)
from indexing.category_guided_entity_extractor import CategoryGuidedEntityExtractor
from indexing.preprocess.vietnamese_text_cleaner import VietnameseTextCleaner

logger = logging.getLogger(__name__)


@dataclass
class ETLConfig:
    """Configuration for ETL pipeline"""
    batch_size: int = 50
    max_file_size_mb: int = 10
    skip_errors: bool = True
    save_intermediate: bool = False  # Save enriched documents
    intermediate_dir: Optional[Path] = None
    
    # File type filters
    allowed_extensions: List[str] = field(default_factory=lambda: [
        '.pdf', '.docx', '.json', '.md', '.txt'
    ])
    
    # Processing options
    clean_text: bool = True
    extract_metadata: bool = True
    detect_categories: bool = True
    
    # Progress tracking
    verbose: bool = True
    log_interval: int = 10


@dataclass
class ETLResult:
    """Result of ETL pipeline execution"""
    documents_processed: int = 0
    documents_failed: int = 0
    graph_result: Optional[GraphBuildResult] = None
    processing_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "processing_time_seconds": self.processing_time_seconds,
            "error_count": len(self.errors),
            "graph_result": self.graph_result.to_dict() if self.graph_result else None,
        }


@dataclass
class EnrichedDocument:
    """Document with enriched metadata"""
    content: str
    doc_id: str
    source_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_categories: List[NodeCategory] = field(default_factory=list)
    
    def to_document(self) -> Document:
        """Convert to simple Document"""
        return Document(
            content=self.content,
            doc_id=self.doc_id,
            metadata=self.metadata
        )


class DocumentLoader:
    """Base class for document loaders"""
    
    def can_load(self, file_path: Path) -> bool:
        """Check if this loader can load the file"""
        raise NotImplementedError
    
    async def load(self, file_path: Path) -> Optional[str]:
        """Load document content"""
        raise NotImplementedError


class PDFLoader(DocumentLoader):
    """
    Load PDF files with enhanced table extraction
    
    Uses pdfplumber instead of PyPDF2 for better handling of:
    - Tables and structured data
    - Multi-column layouts
    - Complex formatting
    
    Week 2 Enhancement: Integrated enhanced_pdf_parser.py
    """
    
    def __init__(self):
        """Initialize with EnhancedPDFLoader"""
        try:
            from indexing.enhanced_pdf_parser import EnhancedPDFLoader
            self._loader = EnhancedPDFLoader(extract_tables=True)
            self._use_enhanced = True
            logger.info("✅ Using EnhancedPDFLoader (pdfplumber) for PDF extraction")
        except ImportError as e:
            logger.warning(
                f"⚠️  EnhancedPDFLoader not available ({e}). "
                "Falling back to PyPDF2. Install pdfplumber for better table support: "
                "pip install pdfplumber"
            )
            self._use_enhanced = False
    
    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf'
    
    async def load(self, file_path: Path) -> Optional[str]:
        """
        Load PDF content with table extraction
        
        If pdfplumber is available:
            - Extracts text with preserved structure
            - Includes tables in readable format
            - Better multi-column handling
        
        Otherwise falls back to PyPDF2
        """
        try:
            if self._use_enhanced:
                # Use enhanced loader (pdfplumber)
                text = await self._loader.load(file_path)
                return text
            else:
                # Fallback to PyPDF2
                import PyPDF2
                
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                
        except Exception as e:
            logger.error(f"Failed to load PDF {file_path}: {e}")
            return None


class JSONLoader(DocumentLoader):
    """Load JSON files"""
    
    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.json'
    
    async def load(self, file_path: Path) -> Optional[str]:
        """Load JSON and extract text"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract text from JSON structure
            if isinstance(data, dict):
                # Try common text fields
                for key in ['content', 'text', 'description', 'body']:
                    if key in data:
                        return str(data[key])
                
                # Fallback: concatenate all string values
                texts = []
                for value in data.values():
                    if isinstance(value, str):
                        texts.append(value)
                    elif isinstance(value, list):
                        texts.extend([str(v) for v in value if isinstance(v, str)])
                
                return "\n".join(texts)
            
            elif isinstance(data, list):
                # Array of items
                texts = []
                for item in data:
                    if isinstance(item, dict):
                        # Extract text from each item
                        for key in ['content', 'text', 'description']:
                            if key in item:
                                texts.append(str(item[key]))
                                break
                    elif isinstance(item, str):
                        texts.append(item)
                
                return "\n\n".join(texts)
            
            else:
                return str(data)
                
        except Exception as e:
            logger.error(f"Failed to load JSON {file_path}: {e}")
            return None


class MarkdownLoader(DocumentLoader):
    """Load Markdown files"""
    
    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.md', '.markdown']
    
    async def load(self, file_path: Path) -> Optional[str]:
        """Load Markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load Markdown {file_path}: {e}")
            return None


class TextLoader(DocumentLoader):
    """Load plain text files"""
    
    def can_load(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.txt', '.text']
    
    async def load(self, file_path: Path) -> Optional[str]:
        """Load text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load text {file_path}: {e}")
            return None


class GraphETLPipeline:
    """
    ETL Pipeline: Documents → Graph.
    
    Orchestrates the entire pipeline from raw documents to knowledge graph.
    
    Stages:
    1. Extract: Load documents from disk
    2. Transform: Clean, enrich, extract metadata
    3. Load: Build graph via GraphBuilderService
    """
    
    def __init__(
        self,
        graph_builder: GraphBuilderService,
        config: Optional[ETLConfig] = None
    ):
        """
        Initialize ETL pipeline.
        
        Args:
            graph_builder: GraphBuilderService for graph construction
            config: ETL configuration
        """
        self.graph_builder = graph_builder
        self.config = config or ETLConfig()
        
        # Initialize components
        self.text_cleaner = VietnameseTextCleaner()
        self.entity_extractor = CategoryGuidedEntityExtractor()
        
        # Document loaders
        self.loaders: List[DocumentLoader] = [
            PDFLoader(),
            JSONLoader(),
            MarkdownLoader(),
            TextLoader(),
        ]
        
        logger.info("GraphETLPipeline initialized")
    
    async def run(
        self,
        source_path: str,
        category_hints: Optional[List[NodeCategory]] = None
    ) -> ETLResult:
        """
        Run ETL pipeline on source path.
        
        Args:
            source_path: Path to file or directory
            category_hints: Optional category hints for extraction
            
        Returns:
            ETLResult with processing statistics
        """
        start_time = datetime.now()
        result = ETLResult()
        
        logger.info(f"Starting ETL pipeline on: {source_path}")
        
        try:
            # Stage 1: Extract (Load documents)
            logger.info("Stage 1: Extracting documents...")
            documents = await self._load_documents(Path(source_path))
            logger.info(f"  Loaded {len(documents)} documents")
            
            if not documents:
                logger.warning("No documents loaded")
                return result
            
            # Stage 2: Transform (Enrich documents)
            logger.info("Stage 2: Transforming documents...")
            enriched = await self._transform_documents(documents)
            logger.info(f"  Enriched {len(enriched)} documents")
            result.documents_processed = len(enriched)
            
            # Save intermediate if configured
            if self.config.save_intermediate:
                await self._save_intermediate(enriched)
            
            # Stage 3: Load (Build graph)
            logger.info("Stage 3: Loading to graph...")
            simple_docs = [doc.to_document() for doc in enriched]
            
            graph_result = await self.graph_builder.build_from_documents(
                simple_docs,
                category_hints
            )
            
            result.graph_result = graph_result
            logger.info(f"  Graph built: {graph_result.to_dict()}")
            
            # Calculate timing
            result.processing_time_seconds = (
                datetime.now() - start_time
            ).total_seconds()
            
            logger.info(f"ETL pipeline completed in {result.processing_time_seconds:.2f}s")
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}")
            result.errors.append(str(e))
            import traceback
            traceback.print_exc()
        
        return result
    
    async def _load_documents(self, path: Path) -> List[EnrichedDocument]:
        """
        Load documents from path (file or directory).
        
        Args:
            path: Path to file or directory
            
        Returns:
            List of raw documents
        """
        documents = []
        
        if path.is_file():
            # Single file
            doc = await self._load_single_file(path)
            if doc:
                documents.append(doc)
        
        elif path.is_dir():
            # Directory: scan all files
            files = []
            for ext in self.config.allowed_extensions:
                files.extend(path.rglob(f"*{ext}"))
            
            logger.info(f"Found {len(files)} files to process")
            
            # Load files
            for i, file_path in enumerate(files):
                if self.config.verbose and i % self.config.log_interval == 0:
                    logger.info(f"  Loading file {i+1}/{len(files)}")
                
                doc = await self._load_single_file(file_path)
                if doc:
                    documents.append(doc)
        
        else:
            logger.error(f"Path not found: {path}")
        
        return documents
    
    async def _load_single_file(self, file_path: Path) -> Optional[EnrichedDocument]:
        """Load a single file"""
        # Check file size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            logger.warning(f"File too large ({size_mb:.1f}MB): {file_path.name}")
            return None
        
        # Find appropriate loader
        loader = None
        for l in self.loaders:
            if l.can_load(file_path):
                loader = l
                break
        
        if not loader:
            logger.warning(f"No loader for file: {file_path.name}")
            return None
        
        # Load content
        try:
            content = await loader.load(file_path)
            
            if not content or not content.strip():
                logger.warning(f"Empty content: {file_path.name}")
                return None
            
            return EnrichedDocument(
                content=content,
                doc_id=file_path.stem,
                source_path=file_path,
                metadata={
                    "source_file": str(file_path),
                    "file_type": file_path.suffix,
                    "file_size_bytes": file_path.stat().st_size,
                }
            )
            
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            if not self.config.skip_errors:
                raise
            return None
    
    async def _transform_documents(
        self,
        documents: List[EnrichedDocument]
    ) -> List[EnrichedDocument]:
        """
        Transform documents: clean, enrich, extract metadata.
        
        Args:
            documents: Raw documents
            
        Returns:
            Enriched documents
        """
        enriched = []
        
        for i, doc in enumerate(documents):
            if self.config.verbose and i % self.config.log_interval == 0:
                logger.info(f"  Transforming document {i+1}/{len(documents)}")
            
            try:
                # Clean text
                if self.config.clean_text:
                    doc.content = self.text_cleaner.clean(doc.content)
                
                # Extract metadata from content
                if self.config.extract_metadata:
                    metadata = self._extract_metadata(doc)
                    doc.metadata.update(metadata)
                
                # Detect categories
                if self.config.detect_categories:
                    categories = self._detect_categories(doc.content)
                    doc.detected_categories = categories
                
                enriched.append(doc)
                
            except Exception as e:
                logger.error(f"Error transforming doc {doc.doc_id}: {e}")
                if not self.config.skip_errors:
                    raise
        
        return enriched
    
    def _extract_metadata(self, doc: EnrichedDocument) -> Dict[str, Any]:
        """Extract metadata from document content"""
        metadata = {}
        
        # Simple metadata extraction
        lines = doc.content.split('\n')[:20]  # First 20 lines
        
        # Look for patterns
        for line in lines:
            # Title detection
            if line.startswith('#') or line.isupper():
                metadata['title'] = line.strip('#').strip()
                break
        
        # Word count
        metadata['word_count'] = len(doc.content.split())
        
        # Character count
        metadata['char_count'] = len(doc.content)
        
        return metadata
    
    def _detect_categories(self, text: str) -> List[NodeCategory]:
        """Detect likely categories from text"""
        categories = []
        
        # Simple keyword-based detection
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in ['môn học', 'course', 'it0', 'cs']):
            categories.append(NodeCategory.MON_HOC)
        
        if any(keyword in text_lower for keyword in ['quy chế', 'quy định', 'điều']):
            categories.append(NodeCategory.QUY_DINH)
        
        if any(keyword in text_lower for keyword in ['khoa', 'faculty', 'department']):
            categories.append(NodeCategory.KHOA)
        
        if any(keyword in text_lower for keyword in ['ngành', 'major', 'program']):
            categories.append(NodeCategory.NGANH)
        
        if any(keyword in text_lower for keyword in ['chương trình', 'curriculum']):
            categories.append(NodeCategory.CHUONG_TRINH_DAO_TAO)
        
        return categories or [NodeCategory.QUY_DINH]  # Default
    
    async def _save_intermediate(self, documents: List[EnrichedDocument]):
        """Save intermediate enriched documents"""
        if not self.config.intermediate_dir:
            self.config.intermediate_dir = Path("data/intermediate")
        
        self.config.intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        for doc in documents:
            output_path = self.config.intermediate_dir / f"{doc.doc_id}.json"
            
            data = {
                "doc_id": doc.doc_id,
                "content": doc.content,
                "metadata": doc.metadata,
                "detected_categories": [c.value for c in doc.detected_categories],
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(documents)} intermediate documents to {self.config.intermediate_dir}")
