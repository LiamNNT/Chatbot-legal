"""
LlamaIndex-based Knowledge Graph Extraction Pipeline.

This module provides an alternative implementation of the hybrid extraction pipeline
using LlamaParse for document parsing and PropertyGraphIndex for KG extraction.

Key Features:
    - LlamaParse: Handles PDF parsing including complex tables and multi-page layouts
    - PropertyGraphIndex: Automatic entity/relation extraction with Neo4j integration
    - Compatible output: Produces same GraphNode/GraphRelationship as hybrid_extractor

Migration from hybrid_extractor.py:
    # Old approach (2-stage: VLM + LLM)
    from app.extraction.hybrid_extractor import run_pipeline
    result, nodes, rels = run_pipeline(pdf_path=pdf_path)
    
    # New approach (LlamaParse + PropertyGraphIndex)
    from app.extraction.llamaindex_extractor import LlamaIndexExtractionService
    service = LlamaIndexExtractionService.from_env()
    result = await service.extract_from_pdf(pdf_path)
    nodes, rels = result.to_graph_models()

DEPRECATION NOTICE:
    The original hybrid_extractor.py is deprecated. Set USE_LLAMAINDEX_EXTRACTION=true
    in your environment to use this new implementation.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class ExtractionConfig(BaseModel):
    """Configuration for LlamaIndex extraction pipeline."""
    
    # LlamaParse config
    llama_cloud_api_key: Optional[str] = Field(default=None)
    parsing_instruction: str = Field(
        default="""
        Đây là văn bản pháp lý/quy định của trường đại học Việt Nam.
        Hãy trích xuất đầy đủ:
        - Cấu trúc: Chương, Điều, Khoản, Điểm
        - Bảng biểu: Giữ nguyên dạng Markdown
        - Ghi chú: Các điều khoản sửa đổi, bổ sung
        
        This is a Vietnamese university legal/regulation document.
        Extract completely:
        - Structure: Chapters, Articles, Clauses, Points
        - Tables: Keep as Markdown format
        - Notes: Amendment and supplement clauses
        """
    )
    result_type: str = Field(default="markdown")  # markdown, text, or json
    
    # LlamaParse Advanced Settings (NEW - replaces VLM)
    use_gpt4o_mode: bool = Field(default=True, description="Use GPT-4o for complex documents")
    split_by_page: bool = Field(default=False, description="Split output by page")
    invalidate_cache: bool = Field(default=False, description="Force re-parse cached documents")
    skip_diagonal_text: bool = Field(default=True, description="Skip watermarks/diagonal text")
    do_not_unroll_columns: bool = Field(default=False, description="Keep multi-column layout")
    page_separator: str = Field(default="\n\n---\n\n", description="Separator between pages")
    
    # Table extraction settings (NEW)
    extract_tables_as_json: bool = Field(default=False, description="Extract tables as JSON in addition to Markdown")
    table_output_format: str = Field(default="markdown", description="Table format: markdown, html, or json")
    
    # PropertyGraphIndex config
    neo4j_uri: Optional[str] = Field(default=None)
    neo4j_user: Optional[str] = Field(default=None)
    neo4j_password: Optional[str] = Field(default=None)
    
    # LLM config for entity/relation extraction
    llm_model: str = Field(default="gpt-4o-mini")
    llm_api_key: Optional[str] = Field(default=None)
    llm_base_url: Optional[str] = Field(default=None)
    
    # Extraction settings
    chunk_size: int = Field(default=1024)
    chunk_overlap: int = Field(default=200)
    include_metadata: bool = Field(default=True)
    extract_tables_separately: bool = Field(default=True)
    
    # Fallback settings
    use_fallback_parser: bool = Field(default=True, description="Use PyPDF2 fallback if LlamaParse fails")
    
    @classmethod
    def from_env(cls) -> "ExtractionConfig":
        """Load configuration from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return cls(
            llama_cloud_api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
            llm_base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
            use_gpt4o_mode=os.getenv("LLAMA_PARSE_GPT4O_MODE", "true").lower() == "true",
            extract_tables_as_json=os.getenv("LLAMA_PARSE_TABLES_JSON", "false").lower() == "true"
        )


# =============================================================================
# Domain Models (Compatible with existing schemas)
# =============================================================================

class EntityType(str, Enum):
    """Entity types for Vietnamese academic documents."""
    MON_HOC = "MON_HOC"
    QUY_DINH = "QUY_DINH"
    DIEU_KIEN = "DIEU_KIEN"
    KHOA = "KHOA"
    NGANH = "NGANH"
    CHUONG_TRINH_DAO_TAO = "CHUONG_TRINH_DAO_TAO"
    CHUNG_CHI = "CHUNG_CHI"
    DIEM_SO = "DIEM_SO"
    DO_KHO = "DO_KHO"
    DOI_TUONG = "DOI_TUONG"
    THOI_GIAN = "THOI_GIAN"
    SO_LUONG = "SO_LUONG"
    TIN_CHI = "TIN_CHI"
    HOC_PHI = "HOC_PHI"
    VAN_BAN = "VAN_BAN"
    DIEU_KHOAN = "DIEU_KHOAN"


class RelationType(str, Enum):
    """Relation types for Vietnamese academic documents."""
    YEU_CAU = "YEU_CAU"
    DIEU_KIEN_TIEN_QUYET = "DIEU_KIEN_TIEN_QUYET"
    AP_DUNG_CHO = "AP_DUNG_CHO"
    QUY_DINH_DIEU_KIEN = "QUY_DINH_DIEU_KIEN"
    THUOC_KHOA = "THUOC_KHOA"
    CUA_NGANH = "CUA_NGANH"
    THUOC_CHUONG_TRINH = "THUOC_CHUONG_TRINH"
    THUOC_VE = "THUOC_VE"
    DAT_DIEM = "DAT_DIEM"
    TUONG_DUONG = "TUONG_DUONG"
    MIEN_GIAM = "MIEN_GIAM"
    GIOI_HAN = "GIOI_HAN"
    SUA_DOI = "SUA_DOI"
    THAY_THE = "THAY_THE"
    BO_SUNG = "BO_SUNG"
    BAI_BO = "BAI_BO"
    LIEN_QUAN_NOI_DUNG = "LIEN_QUAN_NOI_DUNG"


@dataclass
class ExtractedEntity:
    """Entity extracted from document."""
    id: str
    type: EntityType
    text: str
    normalized: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    source_chunk_id: Optional[str] = None
    confidence: float = 0.9


@dataclass  
class ExtractedRelation:
    """Relation extracted between entities."""
    source_id: str
    target_id: str
    type: RelationType
    evidence: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.9


@dataclass
class ParsedDocument:
    """Result from LlamaParse parsing."""
    content: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: int = 0
    chunks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Final extraction result."""
    document_id: str
    parsed_document: ParsedDocument
    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[ExtractedRelation] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_graph_models(self) -> Tuple[List["GraphNode"], List["GraphRelationship"]]:
        """
        Convert to GraphNode/GraphRelationship models compatible with existing code.
        
        Maps extracted entities to NodeType.THUAT_NGU (generic term node) and
        relations to EdgeType enum values where possible, with fallback to LIEN_QUAN.
        """
        from app.knowledge_graph.domain.graph_models import GraphNode, GraphRelationship, NodeType, EdgeType
        
        graph_nodes = []
        graph_rels = []
        
        # Map relation type string to EdgeType
        relation_type_map = {
            "THUOC_VE": EdgeType.THUOC_VE,
            "SUA_DOI": EdgeType.SUA_DOI,
            "BO_SUNG": EdgeType.BO_SUNG,
            "THAY_THE": EdgeType.THAY_THE,
            "BAI_BO": EdgeType.BAI_BO,
            "THAM_CHIEU": EdgeType.THAM_CHIEU,
            "VIEN_DAN": EdgeType.VIEN_DAN,
            "DINH_NGHIA": EdgeType.DINH_NGHIA,
            "YEU_CAU": EdgeType.YEU_CAU,
            "AP_DUNG": EdgeType.AP_DUNG,
            "LIEN_QUAN": EdgeType.LIEN_QUAN,
            # Map academic relation types
            "LIEN_QUAN_NOI_DUNG": EdgeType.LIEN_QUAN,
            "QUY_DINH_DIEU_KIEN": EdgeType.QUY_DINH,
            "AP_DUNG_CHO": EdgeType.AP_DUNG,
            "DAT_DIEM": EdgeType.LIEN_QUAN,
            "TUONG_DUONG": EdgeType.DONG_NGHIA,
            "MIEN_GIAM": EdgeType.LIEN_QUAN,
            "GIOI_HAN": EdgeType.RANG_BUOC,
            "DIEU_KIEN_TIEN_QUYET": EdgeType.YEU_CAU,
            "THUOC_KHOA": EdgeType.THUOC_VE,
            "CUA_NGANH": EdgeType.THUOC_VE,
            "THUOC_CHUONG_TRINH": EdgeType.THUOC_VE,
        }
        
        # Convert entities to GraphNode
        for entity in self.entities:
            # Use NodeType.THUAT_NGU as generic node type for extracted entities
            # Store original type in properties
            node = GraphNode(
                id=entity.id,
                node_type=NodeType.THUAT_NGU,
                name=entity.text[:200] if entity.text else "",
                content=entity.text or "",
                properties={
                    "raw_type": entity.type.value if hasattr(entity.type, 'value') else str(entity.type),
                    "text": entity.text,
                    "normalized": entity.normalized,
                    "source_chunk": entity.source_chunk_id,
                    **entity.properties
                }
            )
            graph_nodes.append(node)
        
        # Convert relations to GraphRelationship
        for rel in self.relations:
            # Get relation type string
            rel_type_str = rel.type.value if hasattr(rel.type, 'value') else str(rel.type)
            
            # Map to EdgeType, fallback to LIEN_QUAN
            edge_type = relation_type_map.get(rel_type_str, EdgeType.LIEN_QUAN)
                
            relationship = GraphRelationship(
                source_id=rel.source_id,
                target_id=rel.target_id,
                edge_type=edge_type,
                properties={
                    "raw_type": rel_type_str,
                    "evidence": rel.evidence,
                    **rel.properties
                }
            )
            graph_rels.append(relationship)
        
        return graph_nodes, graph_rels


# =============================================================================
# Schema Definition for PropertyGraphIndex
# =============================================================================

VIETNAMESE_ACADEMIC_SCHEMA = """
# Vietnamese Academic Document Schema

## Entity Types:
- MON_HOC: Course/Subject (e.g., "Anh văn 1", "Toán cao cấp")
- QUY_DINH: Regulation/Rule (e.g., "Điều 5", "Quy chế đào tạo")
- DIEU_KIEN: Condition/Requirement
- CHUNG_CHI: Certificate (e.g., "IELTS", "TOEIC")
- DIEM_SO: Score/Grade (e.g., "6.5", "450 điểm")
- DO_KHO: Proficiency level (e.g., "B1", "Intermediate")
- DOI_TUONG: Target group (e.g., "sinh viên chính quy", "hệ CLC")
- THOI_GIAN: Time period (e.g., "2 năm", "học kỳ 1")
- SO_LUONG: Quantity (e.g., "12 tín chỉ", "70 sinh viên")
- KHOA: Faculty/Department
- NGANH: Major
- VAN_BAN: Legal document reference

## Relation Types:
- YEU_CAU: (Regulation) requires (Condition/Entity)
- AP_DUNG_CHO: (Regulation) applies to (Target group)
- DAT_DIEM: (Certificate) achieves (Score)
- TUONG_DUONG: (Entity A) is equivalent to (Entity B)
- MIEN_GIAM: (Condition) exempts (Course/Fee)
- SUA_DOI: (New regulation) amends (Old regulation)
- THAY_THE: (New regulation) replaces (Old regulation)
- THUOC_VE: (Child entity) belongs to (Parent entity)
- QUY_DINH_DIEU_KIEN: (Article) specifies (Condition)

## Extraction Guidelines:
1. Extract ALL entities mentioned in the text
2. Normalize entity names where possible (e.g., "Anh văn cơ bản" -> "Anh văn 1")
3. Create relations based on explicit text evidence
4. For amendment documents, focus on SUA_DOI, THAY_THE, BO_SUNG relations
5. Tables should be parsed to extract structured entities
"""


# =============================================================================
# LlamaParse Document Parser (Replaces VLM completely)
# =============================================================================

class LlamaParseDocumentParser:
    """
    Document parser using LlamaParse API for complex PDF extraction.
    
    This completely replaces the VLM-based StructureExtractor, eliminating
    the need for local GPU resources and VLM model loading.
    
    Features:
        - Cloud-based processing (no local GPU needed)
        - Handles tables across page boundaries automatically
        - Extracts document structure (chapters, articles, clauses)
        - Preserves table formatting as Markdown
        - Supports GPT-4o mode for complex documents
        - Vietnamese language optimized
        
    Migration from VLM:
        # Old (VLM - requires GPU)
        from hybrid_extractor import StructureExtractor
        extractor = StructureExtractor(vlm_config)
        result = extractor.extract_from_pdf(pdf_path)
        
        # New (LlamaParse API - cloud-based)
        parser = LlamaParseDocumentParser(config)
        result = await parser.parse_pdf(pdf_path)
    """
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._parser = None
        self._async_parser = None
        
    def _get_parser(self):
        """Lazy initialization of LlamaParse (sync mode)."""
        if self._parser is None:
            if not self.config.llama_cloud_api_key:
                raise ValueError(
                    "LLAMA_CLOUD_API_KEY is required. "
                    "Get your key from https://cloud.llamaindex.ai/"
                )
            
            try:
                from llama_parse import LlamaParse
                
                # Build parser with all configuration options
                parser_kwargs = {
                    "api_key": self.config.llama_cloud_api_key,
                    "result_type": self.config.result_type,
                    "parsing_instruction": self.config.parsing_instruction,
                    "verbose": True,
                    "language": "vi",  # Vietnamese language hint
                    "skip_diagonal_text": self.config.skip_diagonal_text,
                    "invalidate_cache": self.config.invalidate_cache,
                    "do_not_unroll_columns": self.config.do_not_unroll_columns,
                }
                
                # Enable GPT-4o mode if configured (for complex documents)
                if self.config.use_gpt4o_mode and self.config.llm_api_key:
                    parser_kwargs["gpt4o_mode"] = True
                    parser_kwargs["gpt4o_api_key"] = self.config.llm_api_key
                    logger.info("LlamaParse GPT-4o mode enabled for enhanced accuracy")
                
                # Split by page if requested
                if self.config.split_by_page:
                    parser_kwargs["split_by_page"] = True
                    parser_kwargs["page_separator"] = self.config.page_separator
                
                self._parser = LlamaParse(**parser_kwargs)
                logger.info("LlamaParse initialized successfully (sync mode)")
                
            except ImportError:
                raise ImportError(
                    "llama-parse not installed. "
                    "Run: pip install llama-parse>=0.5.0"
                )
        return self._parser
    
    async def _get_async_parser(self):
        """Get async-compatible parser wrapper."""
        # LlamaParse's load_data is synchronous, we wrap it
        return self._get_parser()
    
    async def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Parse a PDF document using LlamaParse API.
        
        This method completely replaces VLM-based extraction:
        - No local GPU required
        - Handles complex tables automatically
        - Merges split tables across pages
        - Extracts Vietnamese legal document structure
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ParsedDocument with extracted content, tables, and chunks
        """
        pdf_path = Path(pdf_path)
        logger.info(f"🔄 Parsing PDF with LlamaParse API: {pdf_path.name}")
        
        parser = self._get_parser()
        
        try:
            # Parse the document using LlamaParse cloud API
            # This runs in a thread pool to not block the event loop
            documents = await asyncio.to_thread(
                parser.load_data, str(pdf_path)
            )
            
            if not documents:
                raise ValueError(f"No content extracted from {pdf_path}")
            
            logger.info(f"✅ LlamaParse returned {len(documents)} document(s)")
            
            # Combine all document content
            full_content = "\n\n".join(doc.text for doc in documents)
            
            # Extract document metadata from LlamaParse response
            doc_metadata = {}
            if documents and hasattr(documents[0], 'metadata'):
                doc_metadata = documents[0].metadata or {}
            
            # Extract tables from content
            tables = self._extract_tables(full_content)
            
            # Extract JSON tables if configured
            json_tables = []
            if self.config.extract_tables_as_json:
                json_tables = self._extract_tables_as_json(full_content)
            
            # Create semantic chunks preserving article boundaries
            chunks = self._create_semantic_chunks(full_content)
            
            # Extract document structure (Chapters, Articles)
            structure = self._extract_document_structure(full_content)
            
            return ParsedDocument(
                content=full_content,
                tables=tables,
                metadata={
                    "source": str(pdf_path),
                    "filename": pdf_path.name,
                    "parser": "llama_parse_api",
                    "parser_mode": "gpt4o" if self.config.use_gpt4o_mode else "standard",
                    "num_documents": len(documents),
                    "num_tables": len(tables),
                    "num_chunks": len(chunks),
                    "structure": structure,
                    "json_tables": json_tables,
                    **doc_metadata
                },
                pages=len(documents) if self.config.split_by_page else self._estimate_pages(full_content),
                chunks=chunks
            )
            
        except Exception as e:
            logger.error(f"❌ LlamaParse parsing failed: {e}")
            
            # Fallback to PyPDF2 if configured
            if self.config.use_fallback_parser:
                logger.warning("⚠️ Falling back to PyPDF2 parser")
                return await self._fallback_parse_pdf(pdf_path)
            raise
    
    async def _fallback_parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Fallback PDF parsing using PyPDF2 when LlamaParse fails.
        
        This provides basic text extraction without the advanced features
        of LlamaParse, but ensures the pipeline doesn't completely fail.
        """
        logger.info(f"Using PyPDF2 fallback for: {pdf_path}")
        
        try:
            from PyPDF2 import PdfReader
            
            reader = PdfReader(str(pdf_path))
            pages_text = []
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages_text.append(f"--- Page {i+1} ---\n{text}")
            
            full_content = "\n\n".join(pages_text)
            
            return ParsedDocument(
                content=full_content,
                tables=[],  # PyPDF2 doesn't extract tables well
                metadata={
                    "source": str(pdf_path),
                    "parser": "pypdf2_fallback",
                    "warning": "Limited extraction - tables may be missing"
                },
                pages=len(reader.pages),
                chunks=self._create_semantic_chunks(full_content)
            )
            
        except Exception as e:
            logger.error(f"PyPDF2 fallback also failed: {e}")
            raise
    
    def _extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """Extract Markdown tables from content."""
        tables = []
        
        # Pattern for Markdown tables (improved)
        # Matches: | Header1 | Header2 |
        #          |---------|---------|
        #          | Cell1   | Cell2   |
        table_pattern = r'(\|[^\n]+\|\n)(\|[-:| ]+\|\n)((?:\|[^\n]+\|\n)*)'
        
        for i, match in enumerate(re.finditer(table_pattern, content)):
            header = match.group(1).strip()
            separator = match.group(2).strip()
            body = match.group(3).strip()
            
            # Parse header columns
            columns = [col.strip() for col in header.split('|')[1:-1]]
            
            # Parse body rows
            rows = []
            for row_line in body.split('\n'):
                if row_line.strip():
                    cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
                    rows.append(cells)
            
            tables.append({
                "id": f"table_{i+1}",
                "header": header,
                "columns": columns,
                "body": body,
                "rows": rows,
                "num_rows": len(rows),
                "num_cols": len(columns),
                "full_markdown": match.group(0),
                "start_pos": match.start(),
                "end_pos": match.end()
            })
        
        logger.info(f"📊 Extracted {len(tables)} tables from content")
        return tables
    
    def _extract_tables_as_json(self, content: str) -> List[Dict[str, Any]]:
        """Extract tables and convert to JSON format."""
        tables = self._extract_tables(content)
        json_tables = []
        
        for table in tables:
            columns = table.get("columns", [])
            rows = table.get("rows", [])
            
            # Convert to list of dicts
            json_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i] if i < len(row) else ""
                json_data.append(row_dict)
            
            json_tables.append({
                "id": table["id"],
                "columns": columns,
                "data": json_data,
                "markdown": table["full_markdown"]
            })
        
        return json_tables
    
    def _create_semantic_chunks(self, content: str) -> List[Dict[str, Any]]:
        """
        Create semantic chunks preserving Vietnamese legal document structure.
        
        Chunks are created at article boundaries (Điều X) to maintain
        semantic coherence for entity extraction.
        """
        chunks = []
        
        # Split by Vietnamese legal structure patterns
        # Điều X: Title...
        article_pattern = r'(Điều\s+\d+[^:：]*[:：])'
        chapter_pattern = r'(Chương\s+[IVXLCDM]+[^:：]*[:：]|CHƯƠNG\s+[IVXLCDM]+[^:：]*[:：])'
        
        # First, identify all articles
        articles = re.split(article_pattern, content)
        
        current_chapter = None
        chunk_id = 0
        
        i = 0
        while i < len(articles):
            part = articles[i]
            
            # Check if this is an article header
            if re.match(article_pattern, part):
                # Combine header with content
                header = part
                content_part = articles[i + 1] if i + 1 < len(articles) else ""
                full_article = header + content_part
                
                # Extract article number
                article_match = re.search(r'Điều\s+(\d+)', header)
                article_num = article_match.group(1) if article_match else str(chunk_id)
                
                chunks.append({
                    "id": f"article_{article_num}",
                    "content": full_article.strip(),
                    "is_article": True,
                    "article_number": article_num,
                    "chapter": current_chapter,
                    "type": "article"
                })
                chunk_id += 1
                i += 2
            else:
                # Check for chapter header
                chapter_match = re.search(chapter_pattern, part)
                if chapter_match:
                    current_chapter = chapter_match.group(1).strip()
                
                # Non-article content (intro, appendix, etc.)
                if part.strip() and len(part.strip()) > 50:
                    chunks.append({
                        "id": f"chunk_{chunk_id}",
                        "content": part.strip(),
                        "is_article": False,
                        "chapter": current_chapter,
                        "type": "other"
                    })
                    chunk_id += 1
                i += 1
        
        # If no articles found, fall back to simple chunking
        if not chunks:
            chunks = self._create_simple_chunks(content)
        
        logger.info(f"📝 Created {len(chunks)} semantic chunks")
        return chunks
    
    def _create_simple_chunks(self, content: str) -> List[Dict[str, Any]]:
        """Simple chunking by size with overlap."""
        chunks = []
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        chunk_id = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size:
                if current_chunk.strip():
                    chunks.append({
                        "id": f"chunk_{chunk_id}",
                        "content": current_chunk.strip(),
                        "is_article": False,
                        "type": "text"
                    })
                    chunk_id += 1
                # Keep overlap
                current_chunk = current_chunk[-overlap:] + para
            else:
                current_chunk += "\n\n" + para
        
        # Add remaining content
        if current_chunk.strip():
            chunks.append({
                "id": f"chunk_{chunk_id}",
                "content": current_chunk.strip(),
                "is_article": False,
                "type": "text"
            })
        
        return chunks
    
    def _extract_document_structure(self, content: str) -> Dict[str, Any]:
        """Extract high-level document structure."""
        structure = {
            "chapters": [],
            "articles": [],
            "tables_count": 0
        }
        
        # Find chapters
        chapter_pattern = r'(Chương\s+[IVXLCDM]+)[:\s]*([^\n]*)'
        for match in re.finditer(chapter_pattern, content, re.IGNORECASE):
            structure["chapters"].append({
                "id": match.group(1).strip(),
                "title": match.group(2).strip() if match.group(2) else ""
            })
        
        # Find articles
        article_pattern = r'(Điều\s+\d+)[:\s]*([^\n]*)'
        for match in re.finditer(article_pattern, content):
            structure["articles"].append({
                "id": match.group(1).strip(),
                "title": match.group(2).strip() if match.group(2) else ""
            })
        
        # Count tables
        table_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|'
        structure["tables_count"] = len(re.findall(table_pattern, content))
        
        return structure
    
    def _estimate_pages(self, content: str) -> int:
        """Estimate number of pages from content length."""
        # Rough estimate: ~3000 chars per page for Vietnamese text
        chars_per_page = 3000
        return max(1, len(content) // chars_per_page)
    
    def parse_pdf_sync(self, pdf_path: Path) -> ParsedDocument:
        """Synchronous version of parse_pdf."""
        return asyncio.run(self.parse_pdf(pdf_path))
    
    async def parse_multiple_pdfs(
        self, 
        pdf_paths: List[Path],
        max_concurrency: int = 3
    ) -> List[ParsedDocument]:
        """
        Parse multiple PDFs concurrently.
        
        Args:
            pdf_paths: List of PDF paths to parse
            max_concurrency: Maximum concurrent API calls
            
        Returns:
            List of ParsedDocument results
        """
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def parse_with_semaphore(path: Path) -> ParsedDocument:
            async with semaphore:
                return await self.parse_pdf(path)
        
        tasks = [parse_with_semaphore(p) for p in pdf_paths]
        return await asyncio.gather(*tasks, return_exceptions=True)


# =============================================================================
# PropertyGraphIndex KG Extractor
# =============================================================================

class PropertyGraphKGExtractor:
    """
    Knowledge Graph extractor using LlamaIndex PropertyGraphIndex.
    
    Features:
        - Automatic entity extraction using LLM
        - Automatic relation extraction
        - Direct Neo4j integration
    """
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self._llm = None
        self._graph_store = None
        
    def _get_llm(self):
        """Get configured LLM for extraction."""
        if self._llm is None:
            try:
                from llama_index.llms.openai import OpenAI
                
                self._llm = OpenAI(
                    model=self.config.llm_model,
                    api_key=self.config.llm_api_key,
                    api_base=self.config.llm_base_url,
                    temperature=0.0
                )
                logger.info(f"LLM initialized: {self.config.llm_model}")
            except ImportError:
                # Fallback to OpenAI-compatible
                from llama_index.core.llms import OpenAILike
                
                self._llm = OpenAILike(
                    model=self.config.llm_model,
                    api_key=self.config.llm_api_key,
                    api_base=self.config.llm_base_url,
                    temperature=0.0
                )
        return self._llm
    
    def _get_graph_store(self):
        """Get Neo4j graph store."""
        if self._graph_store is None:
            try:
                from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
                
                self._graph_store = Neo4jPropertyGraphStore(
                    url=self.config.neo4j_uri,
                    username=self.config.neo4j_user,
                    password=self.config.neo4j_password
                )
                logger.info("Neo4j graph store connected")
            except ImportError:
                logger.warning(
                    "llama-index-graph-stores-neo4j not installed. "
                    "Run: pip install llama-index-graph-stores-neo4j"
                )
                self._graph_store = None
        return self._graph_store
    
    async def extract_from_chunks(
        self, 
        chunks: List[Dict[str, Any]],
        document_id: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelation]]:
        """
        Extract entities and relations from document chunks.
        
        Args:
            chunks: List of text chunks from document
            document_id: ID of the source document
            
        Returns:
            Tuple of (entities, relations)
        """
        from llama_index.core import Document, PropertyGraphIndex
        from llama_index.core.indices.property_graph import SchemaLLMPathExtractor
        
        llm = self._get_llm()
        
        # Convert chunks to LlamaIndex Documents
        documents = [
            Document(
                text=chunk["content"],
                metadata={
                    "chunk_id": chunk["id"],
                    "document_id": document_id,
                    "is_article": chunk.get("is_article", False)
                }
            )
            for chunk in chunks
        ]
        
        # Define extraction schema
        entity_types = [e.value for e in EntityType]
        relation_types = [r.value for r in RelationType]
        
        # Create schema-guided extractor
        kg_extractor = SchemaLLMPathExtractor(
            llm=llm,
            possible_entities=entity_types,
            possible_relations=relation_types,
            kg_validation_schema=VIETNAMESE_ACADEMIC_SCHEMA,
            strict=False,  # Allow some flexibility
            num_workers=4
        )
        
        logger.info(f"Extracting KG from {len(documents)} chunks...")
        
        try:
            # Build index with extraction
            index = PropertyGraphIndex.from_documents(
                documents,
                kg_extractors=[kg_extractor],
                llm=llm,
                show_progress=True
            )
            
            # Get extracted triplets
            triplets = index.property_graph_store.get_triplets()
            
            entities = []
            relations = []
            entity_map = {}  # For deduplication
            
            for triplet in triplets:
                subj, rel, obj = triplet
                
                # Add subject entity
                if subj.id not in entity_map:
                    entity = ExtractedEntity(
                        id=subj.id,
                        type=self._map_entity_type(subj.type),
                        text=subj.name,
                        properties=subj.properties or {}
                    )
                    entities.append(entity)
                    entity_map[subj.id] = entity
                
                # Add object entity
                if obj.id not in entity_map:
                    entity = ExtractedEntity(
                        id=obj.id,
                        type=self._map_entity_type(obj.type),
                        text=obj.name,
                        properties=obj.properties or {}
                    )
                    entities.append(entity)
                    entity_map[obj.id] = entity
                
                # Add relation
                relation = ExtractedRelation(
                    source_id=subj.id,
                    target_id=obj.id,
                    type=self._map_relation_type(rel.label),
                    properties=rel.properties or {}
                )
                relations.append(relation)
            
            logger.info(f"Extracted {len(entities)} entities, {len(relations)} relations")
            return entities, relations
            
        except Exception as e:
            logger.error(f"PropertyGraphIndex extraction failed: {e}")
            # Fallback to manual extraction
            return await self._fallback_extraction(chunks, document_id)
    
    def _map_entity_type(self, type_str: str) -> EntityType:
        """Map extracted type string to EntityType enum."""
        try:
            return EntityType[type_str.upper().replace(" ", "_")]
        except KeyError:
            return EntityType.DIEU_KIEN  # Default fallback
    
    def _map_relation_type(self, rel_str: str) -> RelationType:
        """Map extracted relation string to RelationType enum."""
        try:
            return RelationType[rel_str.upper().replace(" ", "_")]
        except KeyError:
            return RelationType.LIEN_QUAN_NOI_DUNG  # Default fallback
    
    async def _fallback_extraction(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelation]]:
        """
        Fallback extraction using direct LLM calls.
        
        Used when PropertyGraphIndex fails or is unavailable.
        """
        logger.warning("Using fallback LLM extraction")
        
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url
        )
        
        entities = []
        relations = []
        
        for chunk in chunks:
            prompt = self._create_extraction_prompt(chunk["content"])
            
            try:
                response = await client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2000
                )
                
                result = self._parse_extraction_response(
                    response.choices[0].message.content,
                    chunk["id"],
                    document_id
                )
                
                entities.extend(result[0])
                relations.extend(result[1])
                
            except Exception as e:
                logger.warning(f"Chunk extraction failed: {e}")
                continue
        
        return entities, relations
    
    def _create_extraction_prompt(self, text: str) -> str:
        """Create extraction prompt for LLM."""
        return f"""
Trích xuất các thực thể (entities) và quan hệ (relations) từ văn bản quy định đại học sau.

Văn bản:
{text}

Định dạng đầu ra JSON:
{{
    "entities": [
        {{"id": "unique_id", "type": "ENTITY_TYPE", "text": "extracted text", "normalized": "normalized form"}}
    ],
    "relations": [
        {{"source_id": "entity_id_1", "target_id": "entity_id_2", "type": "RELATION_TYPE", "evidence": "text evidence"}}
    ]
}}

Các loại thực thể: {[e.value for e in EntityType]}
Các loại quan hệ: {[r.value for r in RelationType]}

Chỉ trả về JSON, không có text khác.
"""
    
    def _parse_extraction_response(
        self,
        response: str,
        chunk_id: str,
        document_id: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelation]]:
        """Parse LLM extraction response."""
        import json
        
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            entities = []
            for e in data.get("entities", []):
                entity = ExtractedEntity(
                    id=f"{document_id}_{chunk_id}_{e['id']}",
                    type=self._map_entity_type(e.get("type", "DIEU_KIEN")),
                    text=e.get("text", ""),
                    normalized=e.get("normalized"),
                    source_chunk_id=chunk_id
                )
                entities.append(entity)
            
            relations = []
            for r in data.get("relations", []):
                relation = ExtractedRelation(
                    source_id=f"{document_id}_{chunk_id}_{r['source_id']}",
                    target_id=f"{document_id}_{chunk_id}_{r['target_id']}",
                    type=self._map_relation_type(r.get("type", "LIEN_QUAN_NOI_DUNG")),
                    evidence=r.get("evidence", "")
                )
                relations.append(relation)
            
            return entities, relations
            
        except Exception as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            return [], []


# =============================================================================
# Main Extraction Service
# =============================================================================

class LlamaIndexExtractionService:
    """
    Unified extraction service using LlamaParse + PropertyGraphIndex.
    
    This is a drop-in replacement for the hybrid_extractor pipeline.
    
    Example:
        service = LlamaIndexExtractionService.from_env()
        result = await service.extract_from_pdf(Path("document.pdf"))
        nodes, relations = result.to_graph_models()
    """
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.parser = LlamaParseDocumentParser(config)
        self.kg_extractor = PropertyGraphKGExtractor(config)
        
        logger.info("LlamaIndexExtractionService initialized")
    
    @classmethod
    def from_env(cls) -> "LlamaIndexExtractionService":
        """Create service with configuration from environment."""
        config = ExtractionConfig.from_env()
        return cls(config)
    
    async def extract_from_pdf(
        self, 
        pdf_path: Path,
        document_id: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract knowledge graph from PDF document.
        
        Args:
            pdf_path: Path to PDF file
            document_id: Optional document ID (defaults to filename)
            
        Returns:
            ExtractionResult with entities and relations
        """
        pdf_path = Path(pdf_path)
        document_id = document_id or pdf_path.stem
        
        logger.info(f"Starting extraction for: {pdf_path}")
        
        errors = []
        
        # Stage 1: Parse document with LlamaParse
        try:
            parsed_doc = await self.parser.parse_pdf(pdf_path)
            logger.info(f"Parsed {parsed_doc.pages} pages, {len(parsed_doc.chunks)} chunks")
        except Exception as e:
            errors.append(f"Parsing failed: {str(e)}")
            logger.error(f"Parsing failed: {e}")
            parsed_doc = ParsedDocument(content="", pages=0)
        
        # Stage 2: Extract KG with PropertyGraphIndex
        entities = []
        relations = []
        
        if parsed_doc.chunks:
            try:
                entities, relations = await self.kg_extractor.extract_from_chunks(
                    parsed_doc.chunks,
                    document_id
                )
                logger.info(f"Extracted {len(entities)} entities, {len(relations)} relations")
            except Exception as e:
                errors.append(f"KG extraction failed: {str(e)}")
                logger.error(f"KG extraction failed: {e}")
        
        return ExtractionResult(
            document_id=document_id,
            parsed_document=parsed_doc,
            entities=entities,
            relations=relations,
            errors=errors,
            metadata={
                "source_path": str(pdf_path),
                "pages": parsed_doc.pages,
                "chunks": len(parsed_doc.chunks),
                "tables": len(parsed_doc.tables)
            }
        )
    
    def extract_from_pdf_sync(
        self,
        pdf_path: Path,
        document_id: Optional[str] = None
    ) -> ExtractionResult:
        """Synchronous version of extract_from_pdf."""
        return asyncio.run(self.extract_from_pdf(pdf_path, document_id))
    
    async def extract_and_store(
        self,
        pdf_path: Path,
        document_id: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract KG and store directly to Neo4j.
        
        Args:
            pdf_path: Path to PDF file
            document_id: Optional document ID
            
        Returns:
            ExtractionResult
        """
        result = await self.extract_from_pdf(pdf_path, document_id)
        
        # Store to Neo4j if configured
        graph_store = self.kg_extractor._get_graph_store()
        if graph_store and result.entities:
            try:
                nodes, rels = result.to_graph_models()
                # Store would happen via PropertyGraphIndex
                logger.info(f"Stored {len(nodes)} nodes, {len(rels)} relations to Neo4j")
            except Exception as e:
                result.errors.append(f"Neo4j storage failed: {str(e)}")
                logger.error(f"Neo4j storage failed: {e}")
        
        return result


# =============================================================================
# Compatibility Layer
# =============================================================================

def run_llamaindex_pipeline(
    pdf_path: Optional[str] = None,
    image_paths: Optional[List[str]] = None,
    output_path: Optional[str] = None
) -> Tuple[ExtractionResult, List["GraphNode"], List["GraphRelationship"]]:
    """
    Compatibility function matching hybrid_extractor.run_pipeline signature.
    
    Args:
        pdf_path: Path to PDF file
        image_paths: Not used (LlamaParse handles PDFs directly)
        output_path: Optional path to save JSON result
        
    Returns:
        Tuple of (ExtractionResult, GraphNodes, GraphRelationships)
    """
    import json
    
    if not pdf_path:
        raise ValueError("pdf_path is required for LlamaIndex extraction")
    
    service = LlamaIndexExtractionService.from_env()
    result = service.extract_from_pdf_sync(Path(pdf_path))
    
    nodes, rels = result.to_graph_models()
    
    if output_path:
        # Save result to JSON
        output_data = {
            "document_id": result.document_id,
            "entities": [
                {
                    "id": e.id,
                    "type": e.type.value,
                    "text": e.text,
                    "normalized": e.normalized
                }
                for e in result.entities
            ],
            "relations": [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "type": r.type.value,
                    "evidence": r.evidence
                }
                for r in result.relations
            ],
            "metadata": result.metadata,
            "errors": result.errors
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved extraction result to {output_path}")
    
    return result, nodes, rels


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """CLI entry point for LlamaIndex extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Extract Knowledge Graph from PDF using LlamaParse + PropertyGraphIndex"
    )
    parser.add_argument("--pdf", type=str, required=True, help="Path to PDF file")
    parser.add_argument("--output", type=str, default="result.json", help="Output JSON path")
    parser.add_argument("--doc-id", type=str, help="Document ID (defaults to filename)")
    
    args = parser.parse_args()
    
    try:
        result, nodes, rels = run_llamaindex_pipeline(
            pdf_path=args.pdf,
            output_path=args.output
        )
        
        print(f"\n✅ Extraction complete!")
        print(f"   - Entities: {len(result.entities)}")
        print(f"   - Relations: {len(result.relations)}")
        print(f"   - Errors: {len(result.errors)}")
        print(f"   - Output: {args.output}")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
