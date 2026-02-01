# core/services/ingest_service.py
"""
Document Ingestion Service for Vietnamese Legal Documents.

This service orchestrates the ingestion pipeline:
1. Parse DOCX/PDF -> hierarchical chunks (+ KG entities for PDF)
2. Generate embeddings
3. Index to Vector DB (OpenSearch/Weaviate)
4. Build Knowledge Graph in Neo4j

The service runs processing in the background and updates job progress.

Supported file types:
- DOCX/DOC: Uses VietnamLegalDocxParser for hierarchical chunking
- PDF: Uses LlamaIndexExtractionService for parsing + KG extraction
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.api.schemas.ingest import (
    JobStatus,
    JobProgress,
    JobMetrics,
    JobError,
    ChunkInfo,
)
from core.services.job_store import JobStore, get_job_store
from indexing.loaders.vietnam_legal_docx_parser import (
    VietnamLegalDocxParser,
    LegalChunk,
    LegalNode,
    LegalNodeType,
    ParseResult,
)

logger = logging.getLogger(__name__)


class IngestService:
    """
    Service for ingesting Vietnamese legal documents.
    
    Handles:
    - File parsing with VietnamLegalDocxParser (DOCX/DOC) or LlamaIndexExtractionService (PDF)
    - Embedding generation
    - Vector DB indexing (Weaviate or OpenSearch)
    - Neo4j Knowledge Graph building
    - Progress tracking
    
    File type routing:
    - .docx, .doc: VietnamLegalDocxParser (hierarchical structure extraction)
    - .pdf: LlamaIndexExtractionService (LlamaParse + KG extraction)
    """
    
    DOCX_EXTENSIONS = {".docx", ".doc"}
    PDF_EXTENSIONS = {".pdf"}
    
    def __init__(
        self,
        job_store: Optional[JobStore] = None,
        vector_backend: str = "weaviate",
        embedding_model: Optional[str] = None,
        token_threshold: int = 800,
    ):
        """
        Initialize the ingestion service.
        
        Args:
            job_store: Job state storage (defaults to singleton)
            vector_backend: "weaviate" or "opensearch"
            embedding_model: Embedding model name
            token_threshold: Token threshold for chunk splitting
        """
        self.job_store = job_store or get_job_store()
        self.vector_backend = vector_backend
        self.embedding_model = embedding_model
        self.token_threshold = token_threshold
        
        # Lazy-loaded components
        self._parser: Optional[VietnamLegalDocxParser] = None
        self._pdf_extractor = None
        self._embedder = None
        self._vector_adapter = None
        self._graph_adapter = None
    
    @property
    def parser(self) -> VietnamLegalDocxParser:
        """Get or create the legal document parser."""
        if self._parser is None:
            self._parser = VietnamLegalDocxParser(
                token_threshold=self.token_threshold
            )
        return self._parser
    
    @property
    def pdf_extractor(self):
        """Get or create the PDF extractor (LlamaIndexExtractionService)."""
        if self._pdf_extractor is None:
            try:
                from app.core.extraction.llamaindex_extractor import (
                    LlamaIndexExtractionService,
                    ExtractionConfig,
                )
                from app.config.settings import settings
                
                config = ExtractionConfig(
                    llama_cloud_api_key=getattr(settings, 'llama_cloud_api_key', None),
                    llm_api_key=settings.openai_api_key or getattr(settings, 'openrouter_api_key', None),
                    llm_base_url=settings.openai_base_url or None,
                    llm_model=settings.llm_model,
                    neo4j_uri=settings.neo4j_uri,
                    neo4j_user=settings.neo4j_user,
                    neo4j_password=settings.neo4j_password,
                    use_gpt4o_mode=getattr(settings, 'llama_parse_gpt4o_mode', True),
                )
                self._pdf_extractor = LlamaIndexExtractionService(config)
                logger.info("Initialized LlamaIndexExtractionService for PDF parsing")
            except Exception as e:
                logger.error(f"Failed to initialize PDF extractor: {e}")
                raise
        return self._pdf_extractor
    
    def _is_pdf(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        return file_path.suffix.lower() in self.PDF_EXTENSIONS
    
    def _is_docx(self, file_path: Path) -> bool:
        """Check if file is a DOCX/DOC."""
        return file_path.suffix.lower() in self.DOCX_EXTENSIONS
    
    def _get_embedder(self):
        """Lazy-load the embedding model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                from app.config.settings import settings
                
                model_name = self.embedding_model or settings.emb_model
                self._embedder = SentenceTransformer(model_name)
                logger.info(f"Loaded embedding model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._embedder
    
    def _get_vector_adapter(self):
        """Lazy-load the vector database adapter."""
        if self._vector_adapter is None:
            from app.config.settings import settings
            
            if self.vector_backend == "weaviate":
                from adapters.weaviate_vector_adapter import WeaviateVectorAdapter
                
                class SimpleEmbedding:
                    def __init__(self, embedder):
                        self.embedder = embedder
                    
                    def get_text_embedding(self, text: str):
                        return self.embedder.encode(text).tolist()
                
                self._vector_adapter = WeaviateVectorAdapter(
                    weaviate_url=settings.weaviate_url,
                    embedding_model=SimpleEmbedding(self._get_embedder()),
                    api_key=settings.weaviate_api_key if settings.weaviate_api_key else None
                )
                logger.info(f"Initialized Weaviate adapter: {settings.weaviate_url}")
            else:
                # OpenSearch adapter
                from infrastructure.store.opensearch.client import get_opensearch_client
                from adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter
                
                self._vector_adapter = OpenSearchKeywordAdapter(get_opensearch_client())
                logger.info("Initialized OpenSearch adapter")
        
        return self._vector_adapter
    
    def _get_graph_adapter(self):
        """Lazy-load the Neo4j graph adapter."""
        if self._graph_adapter is None:
            try:
                from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
                from app.config.settings import settings
                
                self._graph_adapter = Neo4jGraphAdapter(
                    uri=settings.neo4j_uri,
                    username=settings.neo4j_user,
                    password=settings.neo4j_password,
                )
                logger.info(f"Initialized Neo4j adapter: {settings.neo4j_uri}")
            except Exception as e:
                logger.warning(f"Failed to initialize Neo4j adapter: {e}")
                self._graph_adapter = None
        
        return self._graph_adapter
    
    async def start_ingestion(
        self,
        job_id: str,
        file_path: Path,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> None:
        """
        Start the ingestion process for a document.
        
        Routes to appropriate handler based on file type:
        - DOCX/DOC: Uses VietnamLegalDocxParser for hierarchical parsing
        - PDF: Uses LlamaIndexExtractionService for parsing + KG extraction
        
        Progress is tracked via the job store.
        
        Args:
            job_id: ID of the job to process
            file_path: Path to the uploaded file
            law_id: Optional law ID override
            law_name: Optional law name override
            index_namespace: Namespace for indexing
            run_kg: Whether to build knowledge graph
            run_vector: Whether to index to vector DB
        """
        file_path = Path(file_path)
        
        # Route based on file type
        if self._is_pdf(file_path):
            await self._ingest_pdf(
                job_id=job_id,
                file_path=file_path,
                law_id=law_id,
                law_name=law_name,
                index_namespace=index_namespace,
                run_kg=run_kg,
                run_vector=run_vector,
            )
        elif self._is_docx(file_path):
            await self._ingest_docx(
                job_id=job_id,
                file_path=file_path,
                law_id=law_id,
                law_name=law_name,
                index_namespace=index_namespace,
                run_kg=run_kg,
                run_vector=run_vector,
            )
        else:
            error = JobError(
                code="UNSUPPORTED_FILE",
                message=f"Unsupported file type: {file_path.suffix}",
                stage="validation",
            )
            await self.job_store.set_failed(job_id, error)
    
    async def _ingest_docx(
        self,
        job_id: str,
        file_path: Path,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> None:
        """
        Ingest a DOCX/DOC file using VietnamLegalDocxParser.
        
        This is the original ingestion flow for Word documents.
        
        Args:
            job_id: ID of the job to process
            file_path: Path to the uploaded file
            law_id: Optional law ID override
            law_name: Optional law name override
            index_namespace: Namespace for indexing
            run_kg: Whether to build knowledge graph
            run_vector: Whether to index to vector DB
        """
        start_time = time.time()
        metrics = JobMetrics()
        
        try:
            # Mark job as started
            await self.job_store.set_started(job_id)
            
            # =================================================================
            # Stage 1: Parse Document
            # =================================================================
            await self.job_store.update_status(
                job_id,
                JobStatus.PARSING,
                JobProgress(stage="parsing", message="Parsing document...")
            )
            
            parse_start = time.time()
            parse_result = self.parser.parse(
                file_path,
                law_id=law_id,
                law_name=law_name,
            )
            parse_time = int((time.time() - parse_start) * 1000)
            metrics.parse_time_ms = parse_time
            
            if not parse_result.success:
                raise ValueError(f"Parse failed: {parse_result.errors}")
            
            # Update law info from parsed result
            if parse_result.tree:
                extracted_law_id = parse_result.tree.identifier
                extracted_law_name = parse_result.tree.title or ""
                await self.job_store.update_law_info(
                    job_id,
                    law_id or extracted_law_id,
                    law_name or extracted_law_name,
                )
            
            # Update metrics from parse
            metrics.chapters_count = parse_result.statistics.get("chapters", 0)
            metrics.articles_count = parse_result.statistics.get("articles", 0)
            metrics.chunk_count = len(parse_result.chunks)
            
            logger.info(
                f"Job {job_id}: Parsed {len(parse_result.chunks)} chunks, "
                f"{metrics.chapters_count} chapters, {metrics.articles_count} articles"
            )
            
            # =================================================================
            # Stage 2: Chunking (already done by parser, convert to ChunkInfo)
            # =================================================================
            await self.job_store.update_status(
                job_id,
                JobStatus.CHUNKING,
                JobProgress(
                    stage="chunking",
                    current=len(parse_result.chunks),
                    total=len(parse_result.chunks),
                    percentage=100.0,
                    message=f"Created {len(parse_result.chunks)} chunks"
                )
            )
            
            # Convert LegalChunks to ChunkInfo for storage
            chunk_infos = [
                ChunkInfo(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    embedding_prefix=chunk.embedding_prefix,
                    metadata=chunk.metadata,
                    indexed_vector=False,
                    indexed_graph=False,
                )
                for chunk in parse_result.chunks
            ]
            
            # Store chunks in job store
            await self.job_store.store_chunks(job_id, chunk_infos)
            
            # =================================================================
            # Stage 3: Generate Embeddings (if vector indexing)
            # =================================================================
            embeddings: List[List[float]] = []
            
            if run_vector:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.EMBEDDING,
                    JobProgress(
                        stage="embedding",
                        current=0,
                        total=len(parse_result.chunks),
                        message="Generating embeddings..."
                    )
                )
                
                embed_start = time.time()
                embedder = self._get_embedder()
                
                # Generate embeddings in batches
                batch_size = 32
                texts = [
                    f"{chunk.embedding_prefix}\n{chunk.content}"
                    for chunk in parse_result.chunks
                ]
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = embedder.encode(batch).tolist()
                    embeddings.extend(batch_embeddings)
                    
                    # Update progress
                    progress = min(i + batch_size, len(texts))
                    await self.job_store.update_status(
                        job_id,
                        JobStatus.EMBEDDING,
                        JobProgress(
                            stage="embedding",
                            current=progress,
                            total=len(texts),
                            percentage=(progress / len(texts)) * 100,
                            message=f"Generated {progress}/{len(texts)} embeddings"
                        )
                    )
                
                embed_time = int((time.time() - embed_start) * 1000)
                metrics.embed_time_ms = embed_time
                
                logger.info(f"Job {job_id}: Generated {len(embeddings)} embeddings in {embed_time}ms")
            
            # =================================================================
            # Stage 4: Index to Vector DB
            # =================================================================
            if run_vector:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_VECTOR,
                    JobProgress(
                        stage="indexing_vector",
                        current=0,
                        total=len(parse_result.chunks),
                        message="Indexing to vector database..."
                    )
                )
                
                vector_start = time.time()
                
                try:
                    indexed_count = await self._index_to_vector_db(
                        job_id,
                        parse_result.chunks,
                        embeddings,
                        index_namespace,
                    )
                    
                    # Update chunk_infos to mark as indexed
                    for info in chunk_infos:
                        info.indexed_vector = True
                    await self.job_store.store_chunks(job_id, chunk_infos)
                    
                except Exception as e:
                    logger.error(f"Vector indexing failed: {e}")
                    # Continue with graph indexing even if vector fails
                
                vector_time = int((time.time() - vector_start) * 1000)
                metrics.vector_index_time_ms = vector_time
                
                logger.info(f"Job {job_id}: Vector indexing completed in {vector_time}ms")
            
            # =================================================================
            # Stage 5: Build Knowledge Graph
            # =================================================================
            if run_kg:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_GRAPH,
                    JobProgress(
                        stage="indexing_graph",
                        current=0,
                        total=1,
                        message="Building knowledge graph..."
                    )
                )
                
                graph_start = time.time()
                
                try:
                    nodes_created, rels_created = await self._build_knowledge_graph(
                        job_id,
                        parse_result.tree,
                        parse_result.chunks,
                    )
                    
                    metrics.nodes_created = nodes_created
                    metrics.relationships_created = rels_created
                    
                    # Update chunk_infos to mark as indexed
                    for info in chunk_infos:
                        info.indexed_graph = True
                    await self.job_store.store_chunks(job_id, chunk_infos)
                    
                except Exception as e:
                    logger.error(f"Knowledge graph building failed: {e}")
                    # Continue - graph is optional
                
                graph_time = int((time.time() - graph_start) * 1000)
                metrics.graph_index_time_ms = graph_time
                
                logger.info(f"Job {job_id}: Knowledge graph built in {graph_time}ms")
            
            # =================================================================
            # Complete
            # =================================================================
            total_time = int((time.time() - start_time) * 1000)
            metrics.total_time_ms = total_time
            
            await self.job_store.set_completed(job_id, metrics)
            
            logger.info(
                f"Job {job_id}: Completed in {total_time}ms - "
                f"{metrics.chunk_count} chunks, "
                f"{metrics.nodes_created or 0} nodes, "
                f"{metrics.relationships_created or 0} relationships"
            )
            
        except Exception as e:
            logger.exception(f"Job {job_id} failed: {e}")
            
            error = JobError(
                code="INGEST_ERROR",
                message=str(e),
                stage=None,
                traceback=traceback.format_exc(),
            )
            
            await self.job_store.set_failed(job_id, error)
    
    async def _ingest_pdf(
        self,
        job_id: str,
        file_path: Path,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> None:
        """
        Ingest a PDF file using LlamaIndexExtractionService.
        
        This uses LlamaParse + PropertyGraphIndex for:
        - Document parsing (handles complex tables)
        - Entity/relation extraction using GPT-4o
        - Direct Neo4j integration
        
        Args:
            job_id: ID of the job to process
            file_path: Path to the uploaded file
            law_id: Optional law ID override
            law_name: Optional law name override
            index_namespace: Namespace for indexing
            run_kg: Whether to extract and build knowledge graph
            run_vector: Whether to index chunks to vector DB
        """
        start_time = time.time()
        metrics = JobMetrics()
        
        try:
            # Mark job as started
            await self.job_store.set_started(job_id)
            
            # =================================================================
            # Stage 1: Parse PDF with LlamaParse
            # =================================================================
            await self.job_store.update_status(
                job_id,
                JobStatus.PARSING,
                JobProgress(stage="parsing", message="Parsing PDF with LlamaParse...")
            )
            
            parse_start = time.time()
            
            # Generate document ID
            doc_id = law_id or file_path.stem
            
            # Extract using LlamaIndexExtractionService
            extraction_result = await self.pdf_extractor.extract_from_pdf(
                file_path,
                document_id=doc_id
            )
            
            parse_time = int((time.time() - parse_start) * 1000)
            metrics.parse_time_ms = parse_time
            
            # Check for errors
            if extraction_result.errors and not extraction_result.parsed_document.chunks:
                raise ValueError(f"PDF extraction failed: {extraction_result.errors}")
            
            # Update law info
            final_law_id = law_id or doc_id
            final_law_name = law_name or file_path.stem
            await self.job_store.update_law_info(job_id, final_law_id, final_law_name)
            
            # Update metrics
            metrics.chunk_count = len(extraction_result.parsed_document.chunks)
            
            logger.info(
                f"Job {job_id}: PDF parsed - {metrics.chunk_count} chunks, "
                f"{len(extraction_result.entities)} entities, "
                f"{len(extraction_result.relations)} relations"
            )
            
            # =================================================================
            # Stage 2: Convert to ChunkInfo
            # =================================================================
            await self.job_store.update_status(
                job_id,
                JobStatus.CHUNKING,
                JobProgress(
                    stage="chunking",
                    current=len(extraction_result.parsed_document.chunks),
                    total=len(extraction_result.parsed_document.chunks),
                    percentage=100.0,
                    message=f"Created {len(extraction_result.parsed_document.chunks)} chunks from PDF"
                )
            )
            
            # Convert PDF chunks to ChunkInfo
            chunk_infos = []
            for chunk in extraction_result.parsed_document.chunks:
                # Build embedding prefix
                prefix_parts = []
                if final_law_id:
                    prefix_parts.append(f"LAW={final_law_id}")
                if chunk.get("chapter"):
                    prefix_parts.append(f"CHUONG={chunk['chapter']}")
                if chunk.get("article_number"):
                    prefix_parts.append(f"DIEU={chunk['article_number']}")
                
                embedding_prefix = " | ".join(prefix_parts) if prefix_parts else f"PDF={file_path.stem}"
                
                chunk_info = ChunkInfo(
                    chunk_id=chunk.get("id", f"pdf_chunk_{len(chunk_infos)}"),
                    content=chunk.get("content", ""),
                    embedding_prefix=embedding_prefix,
                    metadata={
                        "law_id": final_law_id,
                        "law_name": final_law_name,
                        "source_type": "pdf",
                        "is_article": chunk.get("is_article", False),
                        "chapter": chunk.get("chapter"),
                        "article_number": chunk.get("article_number"),
                        "type": chunk.get("type"),
                    },
                    indexed_vector=False,
                    indexed_graph=False,
                )
                chunk_infos.append(chunk_info)
            
            # Store chunks in job store
            await self.job_store.store_chunks(job_id, chunk_infos)
            
            # =================================================================
            # Stage 3: Generate Embeddings (if vector indexing)
            # =================================================================
            embeddings: List[List[float]] = []
            
            if run_vector and chunk_infos:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.EMBEDDING,
                    JobProgress(
                        stage="embedding",
                        current=0,
                        total=len(chunk_infos),
                        message="Generating embeddings..."
                    )
                )
                
                embed_start = time.time()
                embedder = self._get_embedder()
                
                # Generate embeddings in batches
                batch_size = 32
                texts = [
                    f"{chunk.embedding_prefix}\n{chunk.content}"
                    for chunk in chunk_infos
                ]
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = embedder.encode(batch).tolist()
                    embeddings.extend(batch_embeddings)
                    
                    # Update progress
                    progress = min(i + batch_size, len(texts))
                    await self.job_store.update_status(
                        job_id,
                        JobStatus.EMBEDDING,
                        JobProgress(
                            stage="embedding",
                            current=progress,
                            total=len(texts),
                            percentage=(progress / len(texts)) * 100,
                            message=f"Generated {progress}/{len(texts)} embeddings"
                        )
                    )
                
                embed_time = int((time.time() - embed_start) * 1000)
                metrics.embed_time_ms = embed_time
                
                logger.info(f"Job {job_id}: Generated {len(embeddings)} embeddings in {embed_time}ms")
            
            # =================================================================
            # Stage 4: Index to Vector DB
            # =================================================================
            if run_vector and chunk_infos and embeddings:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_VECTOR,
                    JobProgress(
                        stage="indexing_vector",
                        current=0,
                        total=len(chunk_infos),
                        message="Indexing to vector database..."
                    )
                )
                
                vector_start = time.time()
                
                try:
                    # Index PDF chunks to vector DB
                    indexed_count = await self._index_pdf_chunks_to_vector_db(
                        job_id,
                        chunk_infos,
                        embeddings,
                        index_namespace,
                    )
                    
                    # Update chunk_infos to mark as indexed
                    for info in chunk_infos:
                        info.indexed_vector = True
                    await self.job_store.store_chunks(job_id, chunk_infos)
                    
                except Exception as e:
                    logger.error(f"Vector indexing failed: {e}")
                    # Continue with graph indexing
                
                vector_time = int((time.time() - vector_start) * 1000)
                metrics.vector_index_time_ms = vector_time
                
                logger.info(f"Job {job_id}: Vector indexing completed in {vector_time}ms")
            
            # =================================================================
            # Stage 5: Index Entities/Relations to Neo4j (PDF-specific KG)
            # =================================================================
            if run_kg and (extraction_result.entities or extraction_result.relations):
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_GRAPH,
                    JobProgress(
                        stage="indexing_graph",
                        current=0,
                        total=len(extraction_result.entities) + len(extraction_result.relations),
                        message="Building knowledge graph from extracted entities..."
                    )
                )
                
                graph_start = time.time()
                
                try:
                    nodes_created, rels_created = await self._index_pdf_kg_to_neo4j(
                        job_id,
                        extraction_result.entities,
                        extraction_result.relations,
                    )
                    
                    metrics.nodes_created = nodes_created
                    metrics.relationships_created = rels_created
                    
                    # Update chunk_infos to mark as indexed
                    for info in chunk_infos:
                        info.indexed_graph = True
                    await self.job_store.store_chunks(job_id, chunk_infos)
                    
                except Exception as e:
                    logger.error(f"Knowledge graph building failed: {e}")
                
                graph_time = int((time.time() - graph_start) * 1000)
                metrics.graph_index_time_ms = graph_time
                
                logger.info(
                    f"Job {job_id}: Knowledge graph built in {graph_time}ms - "
                    f"{metrics.nodes_created} nodes, {metrics.relationships_created} relations"
                )
            
            # =================================================================
            # Complete
            # =================================================================
            total_time = int((time.time() - start_time) * 1000)
            metrics.total_time_ms = total_time
            
            await self.job_store.set_completed(job_id, metrics)
            
            logger.info(
                f"Job {job_id}: PDF ingestion completed in {total_time}ms - "
                f"{metrics.chunk_count} chunks, "
                f"{metrics.nodes_created or 0} nodes, "
                f"{metrics.relationships_created or 0} relationships"
            )
            
        except Exception as e:
            logger.exception(f"Job {job_id} (PDF) failed: {e}")
            
            error = JobError(
                code="PDF_INGEST_ERROR",
                message=str(e),
                stage=None,
                traceback=traceback.format_exc(),
            )
            
            await self.job_store.set_failed(job_id, error)
    
    async def _index_pdf_chunks_to_vector_db(
        self,
        job_id: str,
        chunk_infos: List[ChunkInfo],
        embeddings: List[List[float]],
        namespace: str,
    ) -> int:
        """Index PDF chunks to vector database."""
        from core.domain.models import DocumentChunk, DocumentMetadata, DocumentLanguage
        
        adapter = self._get_vector_adapter()
        
        doc_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunk_infos, embeddings)):
            metadata = DocumentMetadata(
                doc_id=chunk.metadata.get("law_id", "unknown"),
                chunk_id=chunk.chunk_id,
                title=chunk.metadata.get("article_number", ""),
                doc_type="legal_pdf",
                language=DocumentLanguage.VIETNAMESE,
                extra={
                    "law_name": chunk.metadata.get("law_name"),
                    "source_type": "pdf",
                    "is_article": chunk.metadata.get("is_article"),
                    "chapter": chunk.metadata.get("chapter"),
                    "embedding_prefix": chunk.embedding_prefix,
                }
            )
            
            doc_chunk = DocumentChunk(
                text=chunk.content,
                metadata=metadata,
                chunk_index=i,
                embedding=embedding,
            )
            doc_chunks.append(doc_chunk)
            
            # Update progress periodically
            if (i + 1) % 50 == 0:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_VECTOR,
                    JobProgress(
                        stage="indexing_vector",
                        current=i + 1,
                        total=len(chunk_infos),
                        percentage=((i + 1) / len(chunk_infos)) * 100,
                        message=f"Indexing {i + 1}/{len(chunk_infos)} chunks"
                    )
                )
        
        # Bulk index
        success = await adapter.index_documents(doc_chunks)
        
        if not success:
            raise RuntimeError("Vector indexing failed")
        
        return len(doc_chunks)
    
    async def _index_pdf_kg_to_neo4j(
        self,
        job_id: str,
        entities: List,
        relations: List,
    ) -> Tuple[int, int]:
        """Index PDF-extracted entities and relations to Neo4j."""
        from core.domain.graph_models import GraphNode, GraphRelationship, NodeCategory, RelationshipType
        
        adapter = self._get_graph_adapter()
        if not adapter:
            logger.warning("Neo4j adapter not available, skipping graph building")
            return (0, 0)
        
        nodes_created = 0
        relationships_created = 0
        
        # Convert entities to GraphNodes
        for entity in entities:
            try:
                # Map entity type to NodeCategory
                try:
                    category = NodeCategory[entity.type.value if hasattr(entity.type, 'value') else str(entity.type)]
                except KeyError:
                    category = NodeCategory.DIEU_KIEN
                
                node = GraphNode(
                    id=entity.id,
                    category=category,
                    properties={
                        "text": entity.text,
                        "normalized": entity.normalized,
                        "source_chunk": entity.source_chunk_id,
                        "confidence": entity.confidence,
                        **entity.properties,
                    }
                )
                
                await adapter.add_node(node)
                nodes_created += 1
                
            except Exception as e:
                logger.debug(f"Entity node creation skipped: {e}")
        
        # Convert relations to GraphRelationships
        for rel in relations:
            try:
                # Map relation type
                try:
                    rel_type = RelationshipType[rel.type.value if hasattr(rel.type, 'value') else str(rel.type)]
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
                
                await adapter.add_relationship(relationship)
                relationships_created += 1
                
            except Exception as e:
                logger.debug(f"Relationship creation skipped: {e}")
            
            # Update progress
            if (nodes_created + relationships_created) % 20 == 0:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_GRAPH,
                    JobProgress(
                        stage="indexing_graph",
                        current=nodes_created + relationships_created,
                        total=len(entities) + len(relations),
                        message=f"Created {nodes_created} nodes, {relationships_created} relationships"
                    )
                )
        
        return (nodes_created, relationships_created)

    async def _index_to_vector_db(
        self,
        job_id: str,
        chunks: List[LegalChunk],
        embeddings: List[List[float]],
        namespace: str,
    ) -> int:
        """
        Index chunks with embeddings to the vector database.
        
        Returns:
            Number of chunks indexed
        """
        from core.domain.models import DocumentChunk, DocumentMetadata, DocumentLanguage
        
        adapter = self._get_vector_adapter()
        
        # Convert to domain DocumentChunk format
        doc_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            metadata = DocumentMetadata(
                doc_id=chunk.metadata.get("law_id", "unknown"),
                chunk_id=chunk.chunk_id,
                title=chunk.metadata.get("article_title", ""),
                doc_type="legal_law",
                language=DocumentLanguage.VIETNAMESE,
                section=chunk.metadata.get("chapter"),
                subsection=chunk.metadata.get("section"),
                extra={
                    "law_name": chunk.metadata.get("law_name"),
                    "article_id": chunk.metadata.get("article_id"),
                    "clause_no": chunk.metadata.get("clause_no"),
                    "point_no": chunk.metadata.get("point_no"),
                    "lineage": chunk.metadata.get("lineage"),
                    "embedding_prefix": chunk.embedding_prefix,
                }
            )
            
            doc_chunk = DocumentChunk(
                text=chunk.content,
                metadata=metadata,
                chunk_index=i,
                embedding=embedding,
            )
            doc_chunks.append(doc_chunk)
            
            # Update progress periodically
            if (i + 1) % 50 == 0:
                await self.job_store.update_status(
                    job_id,
                    JobStatus.INDEXING_VECTOR,
                    JobProgress(
                        stage="indexing_vector",
                        current=i + 1,
                        total=len(chunks),
                        percentage=((i + 1) / len(chunks)) * 100,
                        message=f"Indexing {i + 1}/{len(chunks)} chunks"
                    )
                )
        
        # Bulk index
        success = await adapter.index_documents(doc_chunks)
        
        if not success:
            raise RuntimeError("Vector indexing failed")
        
        return len(doc_chunks)
    
    async def _build_knowledge_graph(
        self,
        job_id: str,
        tree: LegalNode,
        chunks: List[LegalChunk],
    ) -> Tuple[int, int]:
        """
        Build knowledge graph in Neo4j from the document tree.
        
        Creates:
        - Law node
        - Chapter nodes
        - Section nodes
        - Article nodes
        - Clause nodes
        - THUOC_VE (belongs to) relationships
        - THAM_CHIEU (references) relationships (if detected)
        
        Returns:
            Tuple of (nodes_created, relationships_created)
        """
        from core.domain.graph_models import GraphNode, NodeType, EdgeType
        
        adapter = self._get_graph_adapter()
        if not adapter:
            logger.warning("Neo4j adapter not available, skipping graph building")
            return (0, 0)
        
        nodes_created = 0
        relationships_created = 0
        
        # Helper to create node ID
        def make_node_id(node: LegalNode) -> str:
            return node.get_full_id().replace(":", "_").replace("/", "_")
        
        # Create law (root) node
        law_node = GraphNode(
            id=make_node_id(tree),
            node_type=NodeType.DOCUMENT,
            name=f"Luật {tree.title}" if tree.title else f"Luật {tree.identifier}",
            content=tree.content[:500] if tree.content else "",
            properties={
                "law_id": tree.identifier,
                "law_name": tree.title or "",
                "node_type": "LAW",
            }
        )
        
        try:
            await adapter.add_node(law_node)
            nodes_created += 1
        except Exception as e:
            logger.warning(f"Failed to create law node: {e}")
        
        # Recursive function to create nodes and relationships
        async def process_node(node: LegalNode, parent_id: Optional[str] = None):
            nonlocal nodes_created, relationships_created
            
            node_id = make_node_id(node)
            
            # Determine node type
            if node.node_type == LegalNodeType.CHAPTER:
                node_type = NodeType.SECTION
                name = f"Chương {node.identifier}"
            elif node.node_type == LegalNodeType.SECTION:
                node_type = NodeType.SUBSECTION
                name = f"Mục {node.identifier}"
            elif node.node_type == LegalNodeType.ARTICLE:
                node_type = NodeType.CLAUSE
                name = f"Điều {node.identifier}"
            elif node.node_type == LegalNodeType.CLAUSE:
                node_type = NodeType.POINT
                name = f"Khoản {node.identifier}"
            elif node.node_type == LegalNodeType.POINT:
                node_type = NodeType.POINT
                name = f"Điểm {node.identifier}"
            else:
                return  # Skip unknown types
            
            # Create node
            graph_node = GraphNode(
                id=node_id,
                node_type=node_type,
                name=name + (f". {node.title}" if node.title else ""),
                content=node.content[:1000] if node.content else "",
                properties={
                    "identifier": node.identifier,
                    "title": node.title or "",
                    "legal_type": node.node_type.value,
                }
            )
            
            try:
                await adapter.add_node(graph_node)
                nodes_created += 1
            except Exception as e:
                logger.debug(f"Node creation skipped (may exist): {e}")
            
            # Create relationship to parent
            if parent_id:
                try:
                    from core.domain.graph_models import GraphRelationship
                    
                    rel = GraphRelationship(
                        source_id=node_id,
                        target_id=parent_id,
                        edge_type=EdgeType.BELONGS_TO,
                        properties={"relationship": "THUOC_VE"}
                    )
                    await adapter.add_relationship(rel)
                    relationships_created += 1
                except Exception as e:
                    logger.debug(f"Relationship creation skipped: {e}")
            
            # Process children
            for child in node.children:
                await process_node(child, node_id)
            
            # Update progress
            await self.job_store.update_status(
                job_id,
                JobStatus.INDEXING_GRAPH,
                JobProgress(
                    stage="indexing_graph",
                    current=nodes_created,
                    total=nodes_created + 10,  # Estimate
                    message=f"Created {nodes_created} nodes, {relationships_created} relationships"
                )
            )
        
        # Process all children of the law node
        law_node_id = make_node_id(tree)
        for child in tree.children:
            await process_node(child, law_node_id)
        
        logger.info(
            f"Knowledge graph built: {nodes_created} nodes, "
            f"{relationships_created} relationships"
        )
        
        return (nodes_created, relationships_created)


# Singleton instance
_ingest_service: Optional[IngestService] = None


def get_ingest_service() -> IngestService:
    """Get the singleton ingest service instance."""
    global _ingest_service
    if _ingest_service is None:
        from app.config.settings import settings
        
        _ingest_service = IngestService(
            vector_backend=settings.vector_backend,
            embedding_model=settings.emb_model,
            token_threshold=800,
        )
    return _ingest_service
