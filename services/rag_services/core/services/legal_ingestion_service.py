# core/services/legal_ingestion_service.py
"""
Unified Legal Document Ingestion Service.

This service provides a unified interface for ingesting Vietnamese legal documents
regardless of their format (DOCX, DOC, or PDF). It automatically routes to the
appropriate parser and provides methods for indexing to Vector DB and Neo4j.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                  LegalIngestionService                          │
    │                                                                 │
    │  ingest_file(path) ─┬─► DOCX/DOC ─► VietnamLegalDocxParser     │
    │                     │                     ↓                     │
    │                     │              ParseResult + LegalChunks    │
    │                     │                     ↓                     │
    │                     └─► PDF ─────► LlamaIndexExtractionService │
    │                                          ↓                      │
    │                                   ExtractionResult +            │
    │                                   Entities + Relations          │
    │                                                                 │
    │  index_to_vector_db(chunks) ─► Weaviate/OpenSearch             │
    │  index_to_neo4j(entities, relations) ─► Neo4j                  │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    service = LegalIngestionService.from_settings()
    
    # Ingest any supported file
    result = await service.ingest_file(Path("law.docx"))
    
    # Index to databases
    await service.index_to_vector_db(result.chunks)
    await service.index_to_neo4j(result.entities, result.relations)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Domain Models
# =============================================================================

@dataclass
class UnifiedChunk:
    """
    Unified chunk representation for both DOCX and PDF sources.
    
    This normalizes the output from VietnamLegalDocxParser and 
    LlamaIndexExtractionService into a common format.
    """
    chunk_id: str
    content: str
    embedding_prefix: str
    source_type: str  # "docx" or "pdf"
    
    # Legal document metadata
    law_id: Optional[str] = None
    law_name: Optional[str] = None
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None
    article_id: Optional[str] = None
    article_title: Optional[str] = None
    clause_no: Optional[str] = None
    point_no: Optional[str] = None
    
    # Relationships
    parent_id: Optional[str] = None
    prev_sibling_id: Optional[str] = None
    next_sibling_id: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "embedding_prefix": self.embedding_prefix,
            "source_type": self.source_type,
            "law_id": self.law_id,
            "law_name": self.law_name,
            "chapter_id": self.chapter_id,
            "chapter_title": self.chapter_title,
            "article_id": self.article_id,
            "article_title": self.article_title,
            "clause_no": self.clause_no,
            "point_no": self.point_no,
            "parent_id": self.parent_id,
            "prev_sibling_id": self.prev_sibling_id,
            "next_sibling_id": self.next_sibling_id,
            "metadata": self.metadata,
            "token_count": self.token_count,
        }


@dataclass
class UnifiedEntity:
    """Unified entity representation from PDF extraction."""
    entity_id: str
    entity_type: str
    text: str
    normalized: Optional[str] = None
    source_chunk_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "text": self.text,
            "normalized": self.normalized,
            "source_chunk_id": self.source_chunk_id,
            "properties": self.properties,
            "confidence": self.confidence,
        }


@dataclass
class UnifiedRelation:
    """Unified relation representation from PDF extraction."""
    source_id: str
    target_id: str
    relation_type: str
    evidence: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.9
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "evidence": self.evidence,
            "properties": self.properties,
            "confidence": self.confidence,
        }


@dataclass
class IngestionResult:
    """
    Unified result from document ingestion.
    
    Contains:
    - law_id: Identifier for the law document
    - law_name: Human-readable name of the law
    - chunks: List of text chunks for vector DB indexing
    - entities: List of extracted entities (PDF only)
    - relations: List of extracted relations (PDF only)
    - metadata: Additional document metadata
    - errors: List of any errors encountered
    """
    law_id: str
    law_name: str
    source_path: str
    source_type: str  # "docx", "doc", or "pdf"
    
    chunks: List[UnifiedChunk] = field(default_factory=list)
    entities: List[UnifiedEntity] = field(default_factory=list)
    relations: List[UnifiedRelation] = field(default_factory=list)
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Processing stats
    parse_time_ms: int = 0
    total_tokens: int = 0
    
    @property
    def is_success(self) -> bool:
        """Check if ingestion was successful."""
        return len(self.chunks) > 0 and len(self.errors) == 0
    
    @property
    def has_kg_data(self) -> bool:
        """Check if knowledge graph data was extracted (PDF only)."""
        return len(self.entities) > 0 or len(self.relations) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "law_id": self.law_id,
            "law_name": self.law_name,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "chunks": [c.to_dict() for c in self.chunks],
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "metadata": self.metadata,
            "errors": self.errors,
            "stats": {
                "chunk_count": len(self.chunks),
                "entity_count": len(self.entities),
                "relation_count": len(self.relations),
                "total_tokens": self.total_tokens,
                "parse_time_ms": self.parse_time_ms,
            }
        }


# =============================================================================
# Service Configuration
# =============================================================================

class IngestionConfig(BaseModel):
    """Configuration for the ingestion service."""
    
    # Parser settings
    token_threshold: int = Field(default=800, description="Token threshold for DOCX chunking")
    
    # Vector DB settings
    vector_backend: str = Field(default="weaviate", description="weaviate or opensearch")
    weaviate_url: str = Field(default="http://localhost:8090")
    weaviate_class_name: str = Field(default="LegalChunk")
    opensearch_host: str = Field(default="localhost")
    opensearch_port: int = Field(default=9200)
    opensearch_index: str = Field(default="legal_chunks")
    
    # Neo4j settings
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    
    # Embedding settings
    embedding_model: str = Field(default="intfloat/multilingual-e5-base")
    embedding_batch_size: int = Field(default=32)
    
    # LlamaParse settings (for PDF)
    llama_cloud_api_key: Optional[str] = Field(default=None)
    llm_api_key: Optional[str] = Field(default=None)
    llm_base_url: Optional[str] = Field(default=None)
    llm_model: str = Field(default="gpt-4o-mini")
    use_gpt4o_mode: bool = Field(default=True)
    
    # Processing settings
    run_kg_extraction: bool = Field(default=True, description="Extract KG for PDF files")
    run_vector_indexing: bool = Field(default=True, description="Index to vector DB")
    
    @classmethod
    def from_settings(cls) -> "IngestionConfig":
        """Load from app settings."""
        try:
            from app.config.settings import settings
            return cls(
                token_threshold=getattr(settings, 'ingest_token_threshold', 800),
                vector_backend=settings.vector_backend,
                weaviate_url=settings.weaviate_url,
                weaviate_class_name=settings.weaviate_class_name,
                opensearch_host=settings.opensearch_host,
                opensearch_port=settings.opensearch_port,
                opensearch_index=settings.opensearch_index,
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password,
                embedding_model=settings.emb_model,
                llama_cloud_api_key=getattr(settings, 'llama_cloud_api_key', None),
                llm_api_key=settings.openai_api_key or getattr(settings, 'openrouter_api_key', None),
                llm_base_url=settings.openai_base_url or None,
                llm_model=settings.llm_model,
                use_gpt4o_mode=getattr(settings, 'llama_parse_gpt4o_mode', True),
            )
        except ImportError:
            logger.warning("Could not import settings, using defaults")
            return cls()


# =============================================================================
# Legal Ingestion Service
# =============================================================================

class LegalIngestionService:
    """
    Unified service for ingesting Vietnamese legal documents.
    
    Supports:
    - DOCX files: Uses VietnamLegalDocxParser for hierarchical chunking
    - DOC files: Converts to DOCX first, then parses
    - PDF files: Uses LlamaIndexExtractionService for parsing + KG extraction
    
    Example:
        service = LegalIngestionService.from_settings()
        
        # Ingest a DOCX file
        result = await service.ingest_file(Path("law.docx"))
        print(f"Extracted {len(result.chunks)} chunks")
        
        # Ingest a PDF file with KG extraction
        result = await service.ingest_file(Path("regulation.pdf"))
        print(f"Extracted {len(result.entities)} entities")
        
        # Index to databases
        await service.index_to_vector_db(result.chunks)
        if result.has_kg_data:
            await service.index_to_neo4j(result.entities, result.relations)
    """
    
    SUPPORTED_EXTENSIONS = {".docx", ".doc", ".pdf"}
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        """
        Initialize the ingestion service.
        
        Args:
            config: Service configuration. If None, loads from app settings.
        """
        self.config = config or IngestionConfig.from_settings()
        
        # Lazy-loaded components
        self._docx_parser = None
        self._pdf_extractor = None
        self._embedder = None
        self._vector_adapter = None
        self._graph_adapter = None
        
        logger.info("LegalIngestionService initialized")
    
    @classmethod
    def from_settings(cls) -> "LegalIngestionService":
        """Create service with configuration from app settings."""
        return cls(IngestionConfig.from_settings())
    
    # =========================================================================
    # Parser Accessors
    # =========================================================================
    
    @property
    def docx_parser(self):
        """Get or create the DOCX parser."""
        if self._docx_parser is None:
            from indexing.loaders.vietnam_legal_docx_parser import VietnamLegalDocxParser
            self._docx_parser = VietnamLegalDocxParser(
                token_threshold=self.config.token_threshold
            )
            logger.info("VietnamLegalDocxParser initialized")
        return self._docx_parser
    
    @property
    def pdf_extractor(self):
        """Get or create the PDF extractor."""
        if self._pdf_extractor is None:
            from app.core.extraction.llamaindex_extractor import (
                LlamaIndexExtractionService,
                ExtractionConfig,
            )
            
            pdf_config = ExtractionConfig(
                llama_cloud_api_key=self.config.llama_cloud_api_key,
                llm_api_key=self.config.llm_api_key,
                llm_base_url=self.config.llm_base_url,
                llm_model=self.config.llm_model,
                neo4j_uri=self.config.neo4j_uri,
                neo4j_user=self.config.neo4j_user,
                neo4j_password=self.config.neo4j_password,
                use_gpt4o_mode=self.config.use_gpt4o_mode,
            )
            self._pdf_extractor = LlamaIndexExtractionService(pdf_config)
            logger.info("LlamaIndexExtractionService initialized")
        return self._pdf_extractor
    
    def _get_embedder(self):
        """Lazy-load the embedding model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.config.embedding_model)
                logger.info(f"Loaded embedding model: {self.config.embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to load embedder: {e}")
                self._embedder = None
        return self._embedder
    
    def _get_vector_adapter(self):
        """Get or create vector DB adapter."""
        if self._vector_adapter is None:
            if self.config.vector_backend == "weaviate":
                try:
                    from adapters.weaviate_vector_adapter import WeaviateVectorAdapter
                    self._vector_adapter = WeaviateVectorAdapter(
                        weaviate_url=self.config.weaviate_url,
                        collection_name=self.config.weaviate_class_name,
                    )
                    logger.info(f"Weaviate adapter initialized: {self.config.weaviate_url}")
                except Exception as e:
                    logger.error(f"Failed to create Weaviate adapter: {e}")
            else:
                # OpenSearch adapter
                try:
                    from infrastructure.store.opensearch.client import get_opensearch_client
                    from adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter
                    self._vector_adapter = OpenSearchKeywordAdapter(get_opensearch_client())
                    logger.info(f"OpenSearch adapter initialized")
                except Exception as e:
                    logger.error(f"Failed to create OpenSearch adapter: {e}")
        return self._vector_adapter
    
    def _get_graph_adapter(self):
        """Get or create Neo4j adapter."""
        if self._graph_adapter is None:
            try:
                from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
                self._graph_adapter = Neo4jGraphAdapter(
                    uri=self.config.neo4j_uri,
                    user=self.config.neo4j_user,
                    password=self.config.neo4j_password,
                )
                logger.info(f"Neo4j adapter initialized: {self.config.neo4j_uri}")
            except Exception as e:
                logger.error(f"Failed to create Neo4j adapter: {e}")
        return self._graph_adapter
    
    # =========================================================================
    # Main Ingestion Methods
    # =========================================================================
    
    async def ingest_file(
        self,
        file_path: Path,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest a legal document file.
        
        Automatically detects file type and routes to appropriate parser:
        - .docx/.doc: VietnamLegalDocxParser
        - .pdf: LlamaIndexExtractionService
        
        Args:
            file_path: Path to the document file
            law_id: Optional law identifier (auto-detected if not provided)
            law_name: Optional law name (auto-detected if not provided)
            
        Returns:
            IngestionResult with chunks, entities, and relations
        """
        import time
        start_time = time.time()
        
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix not in self.SUPPORTED_EXTENSIONS:
            return IngestionResult(
                law_id=law_id or "unknown",
                law_name=law_name or file_path.stem,
                source_path=str(file_path),
                source_type=suffix,
                errors=[f"Unsupported file type: {suffix}. Supported: {self.SUPPORTED_EXTENSIONS}"]
            )
        
        logger.info(f"📄 Ingesting file: {file_path.name} (type: {suffix})")
        
        try:
            if suffix in {".docx", ".doc"}:
                result = await self._ingest_docx(file_path, law_id, law_name)
            elif suffix == ".pdf":
                result = await self._ingest_pdf(file_path, law_id, law_name)
            else:
                result = IngestionResult(
                    law_id=law_id or "unknown",
                    law_name=law_name or file_path.stem,
                    source_path=str(file_path),
                    source_type=suffix,
                    errors=[f"Handler not implemented for: {suffix}"]
                )
            
            # Add timing
            result.parse_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"✅ Ingestion complete: {len(result.chunks)} chunks, "
                f"{len(result.entities)} entities, {result.parse_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            import traceback
            return IngestionResult(
                law_id=law_id or "unknown",
                law_name=law_name or file_path.stem,
                source_path=str(file_path),
                source_type=suffix,
                errors=[str(e), traceback.format_exc()]
            )
    
    async def _ingest_docx(
        self,
        file_path: Path,
        law_id: Optional[str],
        law_name: Optional[str],
    ) -> IngestionResult:
        """Ingest a DOCX or DOC file using VietnamLegalDocxParser."""
        
        # Convert DOC to DOCX if needed
        if file_path.suffix.lower() == ".doc":
            file_path = await self._convert_doc_to_docx(file_path)
        
        # Parse with VietnamLegalDocxParser
        parse_result = await asyncio.to_thread(
            self.docx_parser.parse, file_path
        )
        
        # Use parsed law info if not provided
        law_id = law_id or parse_result.law_id
        law_name = law_name or parse_result.law_name
        
        # Convert LegalChunks to UnifiedChunks
        unified_chunks = []
        total_tokens = 0
        
        for chunk in parse_result.chunks:
            unified_chunk = UnifiedChunk(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                embedding_prefix=chunk.embedding_prefix,
                source_type="docx",
                law_id=chunk.law_id,
                law_name=chunk.law_name,
                chapter_id=chunk.chapter_id,
                chapter_title=chunk.chapter_title,
                article_id=chunk.article_id,
                article_title=chunk.article_title,
                clause_no=chunk.clause_no,
                point_no=chunk.point_no,
                parent_id=chunk.parent_id,
                prev_sibling_id=chunk.prev_sibling_id,
                next_sibling_id=chunk.next_sibling_id,
                metadata=chunk.metadata,
                token_count=chunk.token_count,
            )
            unified_chunks.append(unified_chunk)
            total_tokens += chunk.token_count
        
        return IngestionResult(
            law_id=law_id,
            law_name=law_name,
            source_path=str(file_path),
            source_type="docx",
            chunks=unified_chunks,
            entities=[],  # DOCX parsing doesn't extract KG entities
            relations=[],
            metadata={
                "parser": "VietnamLegalDocxParser",
                "tree_stats": parse_result.metadata.get("tree_stats", {}),
            },
            errors=[],
            total_tokens=total_tokens,
        )
    
    async def _ingest_pdf(
        self,
        file_path: Path,
        law_id: Optional[str],
        law_name: Optional[str],
    ) -> IngestionResult:
        """Ingest a PDF file using LlamaIndexExtractionService."""
        
        # Generate document ID
        doc_id = law_id or self._generate_document_id(file_path)
        
        # Extract with LlamaIndex
        extraction_result = await self.pdf_extractor.extract_from_pdf(
            file_path, 
            document_id=doc_id
        )
        
        # Convert parsed chunks to UnifiedChunks
        unified_chunks = []
        total_tokens = 0
        
        for chunk in extraction_result.parsed_document.chunks:
            # Estimate tokens (rough approximation)
            tokens = len(chunk.get("content", "").split()) * 1.3
            total_tokens += int(tokens)
            
            # Build embedding prefix from chunk metadata
            prefix_parts = []
            if law_id:
                prefix_parts.append(f"LAW={law_id}")
            if chunk.get("chapter"):
                prefix_parts.append(f"CHUONG={chunk['chapter']}")
            if chunk.get("article_number"):
                prefix_parts.append(f"DIEU={chunk['article_number']}")
            
            embedding_prefix = " | ".join(prefix_parts) if prefix_parts else f"PDF={file_path.stem}"
            
            unified_chunk = UnifiedChunk(
                chunk_id=chunk.get("id", f"pdf_chunk_{len(unified_chunks)}"),
                content=chunk.get("content", ""),
                embedding_prefix=embedding_prefix,
                source_type="pdf",
                law_id=law_id,
                law_name=law_name or file_path.stem,
                article_id=chunk.get("article_number"),
                metadata={
                    "is_article": chunk.get("is_article", False),
                    "chapter": chunk.get("chapter"),
                    "type": chunk.get("type"),
                },
                token_count=int(tokens),
            )
            unified_chunks.append(unified_chunk)
        
        # Convert entities
        unified_entities = [
            UnifiedEntity(
                entity_id=e.id,
                entity_type=e.type.value if hasattr(e.type, 'value') else str(e.type),
                text=e.text,
                normalized=e.normalized,
                source_chunk_id=e.source_chunk_id,
                properties=e.properties,
                confidence=e.confidence,
            )
            for e in extraction_result.entities
        ]
        
        # Convert relations
        unified_relations = [
            UnifiedRelation(
                source_id=r.source_id,
                target_id=r.target_id,
                relation_type=r.type.value if hasattr(r.type, 'value') else str(r.type),
                evidence=r.evidence,
                properties=r.properties,
                confidence=r.confidence,
            )
            for r in extraction_result.relations
        ]
        
        return IngestionResult(
            law_id=doc_id,
            law_name=law_name or file_path.stem,
            source_path=str(file_path),
            source_type="pdf",
            chunks=unified_chunks,
            entities=unified_entities,
            relations=unified_relations,
            metadata={
                "parser": "LlamaIndexExtractionService",
                "pages": extraction_result.parsed_document.pages,
                "tables": len(extraction_result.parsed_document.tables),
                **extraction_result.metadata,
            },
            errors=extraction_result.errors,
            total_tokens=total_tokens,
        )
    
    async def _convert_doc_to_docx(self, doc_path: Path) -> Path:
        """Convert .doc file to .docx using LibreOffice."""
        logger.info(f"Converting DOC to DOCX: {doc_path.name}")
        
        # Create temp directory for conversion
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Run LibreOffice conversion
            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to", "docx",
                "--outdir", temp_dir,
                str(doc_path)
            ]
            
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, timeout=60
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"LibreOffice conversion failed: {result.stderr.decode()}"
                )
            
            # Find converted file
            docx_name = doc_path.stem + ".docx"
            docx_path = Path(temp_dir) / docx_name
            
            if not docx_path.exists():
                raise FileNotFoundError(f"Converted file not found: {docx_path}")
            
            logger.info(f"✅ Converted to: {docx_path}")
            return docx_path
            
        except Exception as e:
            # Cleanup on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"DOC to DOCX conversion failed: {e}")
    
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate a document ID from file path."""
        # Use filename stem + hash of path for uniqueness
        path_hash = hashlib.md5(str(file_path).encode()).hexdigest()[:8]
        return f"{file_path.stem}_{path_hash}"
    
    # =========================================================================
    # Indexing Methods
    # =========================================================================
    
    async def index_to_vector_db(
        self,
        chunks: List[UnifiedChunk],
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Index chunks to vector database (Weaviate or OpenSearch).
        
        Args:
            chunks: List of chunks to index
            batch_size: Batch size for embedding generation
            
        Returns:
            Dict with indexing stats
        """
        if not chunks:
            return {"status": "skipped", "reason": "No chunks to index"}
        
        batch_size = batch_size or self.config.embedding_batch_size
        embedder = self._get_embedder()
        adapter = self._get_vector_adapter()
        
        if not embedder or not adapter:
            return {"status": "error", "reason": "Embedder or adapter not available"}
        
        logger.info(f"📊 Indexing {len(chunks)} chunks to {self.config.vector_backend}")
        
        indexed_count = 0
        errors = []
        
        try:
            # Generate embeddings in batches
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Prepare texts for embedding (prefix + content)
                texts = [
                    f"{c.embedding_prefix}\n{c.content}" 
                    for c in batch
                ]
                
                # Generate embeddings
                embeddings = await asyncio.to_thread(
                    embedder.encode, texts
                )
                
                # Prepare documents for indexing
                documents = []
                for j, chunk in enumerate(batch):
                    doc = {
                        "id": chunk.chunk_id,
                        "text": chunk.content,
                        "embedding_prefix": chunk.embedding_prefix,
                        "vector": embeddings[j].tolist(),
                        "metadata": {
                            "law_id": chunk.law_id,
                            "law_name": chunk.law_name,
                            "chapter_id": chunk.chapter_id,
                            "article_id": chunk.article_id,
                            "clause_no": chunk.clause_no,
                            "point_no": chunk.point_no,
                            "source_type": chunk.source_type,
                            **chunk.metadata,
                        }
                    }
                    documents.append(doc)
                
                # Index to vector DB
                await asyncio.to_thread(
                    adapter.upsert_batch, documents
                )
                indexed_count += len(batch)
                
                logger.debug(f"Indexed batch {i//batch_size + 1}: {len(batch)} chunks")
            
            return {
                "status": "success",
                "indexed_count": indexed_count,
                "backend": self.config.vector_backend,
            }
            
        except Exception as e:
            logger.error(f"Vector indexing failed: {e}")
            return {
                "status": "error",
                "indexed_count": indexed_count,
                "error": str(e),
            }
    
    async def index_to_neo4j(
        self,
        entities: List[UnifiedEntity],
        relations: List[UnifiedRelation],
    ) -> Dict[str, Any]:
        """
        Index entities and relations to Neo4j knowledge graph.
        
        Args:
            entities: List of entities to create as nodes
            relations: List of relations to create as edges
            
        Returns:
            Dict with indexing stats
        """
        if not entities and not relations:
            return {"status": "skipped", "reason": "No KG data to index"}
        
        adapter = self._get_graph_adapter()
        if not adapter:
            return {"status": "error", "reason": "Neo4j adapter not available"}
        
        logger.info(f"🔗 Indexing {len(entities)} entities, {len(relations)} relations to Neo4j")
        
        try:
            from core.domain.graph_models import GraphNode, GraphRelationship, NodeCategory, RelationshipType
            
            # Convert entities to GraphNodes
            graph_nodes = []
            for entity in entities:
                try:
                    category = NodeCategory[entity.entity_type]
                except KeyError:
                    category = NodeCategory.DIEU_KIEN
                
                node = GraphNode(
                    id=entity.entity_id,
                    category=category,
                    properties={
                        "text": entity.text,
                        "normalized": entity.normalized,
                        "source_chunk": entity.source_chunk_id,
                        "confidence": entity.confidence,
                        **entity.properties,
                    }
                )
                graph_nodes.append(node)
            
            # Convert relations to GraphRelationships
            graph_rels = []
            for rel in relations:
                try:
                    rel_type = RelationshipType[rel.relation_type]
                except KeyError:
                    rel_type = RelationshipType.LIEN_QUAN_NOI_DUNG
                
                relationship = GraphRelationship(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    rel_type=rel_type,
                    properties={
                        "evidence": rel.evidence,
                        "confidence": rel.confidence,
                        **rel.properties,
                    }
                )
                graph_rels.append(relationship)
            
            # Store to Neo4j
            await asyncio.to_thread(
                adapter.upsert_nodes, graph_nodes
            )
            await asyncio.to_thread(
                adapter.upsert_relationships, graph_rels
            )
            
            return {
                "status": "success",
                "nodes_created": len(graph_nodes),
                "relationships_created": len(graph_rels),
            }
            
        except Exception as e:
            logger.error(f"Neo4j indexing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def ingest_and_index(
        self,
        file_path: Path,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_vector: bool = True,
        index_kg: bool = True,
    ) -> Tuple[IngestionResult, Dict[str, Any]]:
        """
        Ingest a file and index to all configured databases.
        
        Args:
            file_path: Path to document
            law_id: Optional law identifier
            law_name: Optional law name
            index_vector: Whether to index to vector DB
            index_kg: Whether to index to Neo4j (if KG data available)
            
        Returns:
            Tuple of (IngestionResult, indexing_stats)
        """
        # Ingest
        result = await self.ingest_file(file_path, law_id, law_name)
        
        indexing_stats = {}
        
        # Index to vector DB
        if index_vector and result.chunks:
            indexing_stats["vector"] = await self.index_to_vector_db(result.chunks)
        
        # Index to Neo4j
        if index_kg and result.has_kg_data:
            indexing_stats["neo4j"] = await self.index_to_neo4j(
                result.entities, result.relations
            )
        
        return result, indexing_stats


# =============================================================================
# Factory Functions
# =============================================================================

_ingestion_service_instance: Optional[LegalIngestionService] = None


def get_ingestion_service() -> LegalIngestionService:
    """Get singleton instance of LegalIngestionService."""
    global _ingestion_service_instance
    if _ingestion_service_instance is None:
        _ingestion_service_instance = LegalIngestionService.from_settings()
    return _ingestion_service_instance


def reset_ingestion_service():
    """Reset the singleton instance (for testing)."""
    global _ingestion_service_instance
    _ingestion_service_instance = None
