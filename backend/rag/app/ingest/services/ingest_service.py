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
- DOCX/DOC: Uses LlamaIndexLegalParser for hierarchical chunking
- PDF: Uses LlamaIndexExtractionService for parsing + KG extraction
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ingest.schemas import (
    JobStatus,
    JobProgress,
    JobMetrics,
    JobError,
    ChunkInfo,
)
from app.ingest.services.job_store import JobStore, get_job_store
from app.ingest.loaders.llamaindex_legal_parser import (
    LlamaIndexLegalParser,
    ParserConfig,
    LegalChunk,
    ParseResult,
    LegalNode,
    LegalNodeType,
)

logger = logging.getLogger(__name__)


class IngestService:
    """
    Service for ingesting Vietnamese legal documents.
    
    Handles:
    - File parsing with LlamaIndexLegalParser (DOCX/DOC/PDF)
    - Embedding generation
    - Vector DB indexing (Weaviate or OpenSearch)
    - Neo4j Knowledge Graph building
    - Progress tracking
    
    File type routing:
    - .docx, .doc: LlamaIndexLegalParser (hierarchical structure extraction)
    - .pdf: LlamaIndexExtractionService (LlamaParse + KG extraction)
    """
    
    DOCX_EXTENSIONS = {".docx", ".doc"}
    PDF_EXTENSIONS = {".pdf"}
    
    def __init__(
        self,
        job_store: Optional[JobStore] = None,
        vector_backend: str = "weaviate",
        embedding_model: Optional[str] = None,
        token_threshold: int = 1500,
        # ── Pre-built adapters (preferred — avoids infra imports) ──
        embedder=None,
        vector_adapter=None,
        graph_adapter=None,
        pdf_extractor=None,
    ):
        """
        Initialize the ingestion service.
        
        Args:
            job_store: Job state storage (defaults to singleton)
            vector_backend: "weaviate" or "opensearch"
            embedding_model: Embedding model name
            token_threshold: Token threshold for chunk splitting (default 1500 to match legacy)
            embedder: Pre-built embedding model (avoids infra import)
            vector_adapter: Pre-built vector store adapter
            graph_adapter: Pre-built graph adapter
            pdf_extractor: Pre-built PDF extraction service
        """
        self.job_store = job_store or get_job_store()
        self.vector_backend = vector_backend
        self.embedding_model = embedding_model
        self.token_threshold = token_threshold
        
        # Lazy-loaded components (pre-inject to avoid infra coupling)
        self._parser: Optional[LlamaIndexLegalParser] = None
        self._pdf_extractor = pdf_extractor
        self._embedder = embedder
        self._vector_adapter = vector_adapter
        self._graph_adapter = graph_adapter
    
    @property
    def parser(self) -> LlamaIndexLegalParser:
        """Get or create the legal document parser (LlamaIndex-based)."""
        if self._parser is None:
            config = ParserConfig(
                llama_cloud_api_key=None,  # Use fallback docx parser
                chunk_size=self.token_threshold,
            )
            self._parser = LlamaIndexLegalParser(config)
        return self._parser
    
    @property
    def pdf_extractor(self):
        """Get or create the PDF extractor (LlamaIndexExtractionService)."""
        if self._pdf_extractor is None:
            try:
                from app.extraction.llamaindex_extractor import (
                    LlamaIndexExtractionService,
                    ExtractionConfig,
                )
                from app.shared.config.settings import settings
                
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
                from app.shared.config.settings import settings
                
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
            from app.shared.config.settings import settings
            
            if self.vector_backend == "weaviate":
                from app.search.adapters.weaviate_vector_adapter import WeaviateVectorAdapter
                
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
                from app.ingest.store.opensearch.client import get_opensearch_client
                from app.search.adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter
                
                self._vector_adapter = OpenSearchKeywordAdapter(get_opensearch_client())
                logger.info("Initialized OpenSearch adapter")
        
        return self._vector_adapter
    
    def _get_graph_adapter(self):
        """Lazy-load the Neo4j graph adapter."""
        if self._graph_adapter is None:
            try:
                from app.knowledge_graph.stores.neo4j_store import Neo4jGraphAdapter
                from app.shared.config.settings import settings
                
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
        - DOCX/DOC: Uses LlamaIndexLegalParser for hierarchical parsing
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
        Ingest a DOCX/DOC file using LlamaIndexLegalParser.
        
        This is the ingestion flow for Word documents.
        
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
            parse_result = await self.parser.parse(
                file_path,
                law_id=law_id,
                law_name=law_name,
            )
            parse_time = int((time.time() - parse_start) * 1000)
            metrics.parse_time_ms = parse_time
            
            if not parse_result.success:
                raise ValueError(f"Parse failed: {parse_result.errors}")
            
            # Extract doc_kind from parse_result metadata
            doc_kind = parse_result.metadata.get("doc_kind", "LAW")
            document_number = parse_result.metadata.get("document_number", "")
            doc_title = parse_result.metadata.get("title", "")
            issuer = parse_result.metadata.get("issuer")
            
            # Extract law info from metadata (LlamaIndexLegalParser stores in metadata)
            extracted_law_id = document_number or ""
            extracted_law_name = doc_title or ""
            
            # Update law info
            if extracted_law_id or law_id:
                await self.job_store.update_law_info(
                    job_id,
                    law_id or extracted_law_id,
                    law_name or extracted_law_name,
                )
            
            # Update document metadata (PHASE 2)
            await self.job_store.update_doc_metadata(
                job_id,
                doc_kind=doc_kind,
                document_number=document_number or law_id or "",
                issuer=issuer,
                title=doc_title or law_name or None,
            )
            
            # Update metrics from parse
            metrics.chapters_count = parse_result.statistics.get("chapters", 0)
            metrics.articles_count = parse_result.statistics.get("articles", 0)
            metrics.chunk_count = len(parse_result.chunks)
            
            logger.info(
                f"Job {job_id}: Parsed {len(parse_result.chunks)} chunks, "
                f"{metrics.chapters_count} chapters, {metrics.articles_count} articles, "
                f"doc_kind={doc_kind}"
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
            vector_indexed_successfully = False
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
                    # Log target database info
                    from app.shared.config.settings import settings
                    logger.info(f"[VECTOR_INDEX] Job {job_id}: Target backend={self.vector_backend}")
                    if self.vector_backend == "weaviate":
                        from app.ingest.store.vector.weaviate_store import get_collection_name
                        logger.info(f"[VECTOR_INDEX] Job {job_id}: Weaviate URL={settings.weaviate_url}, Collection={get_collection_name()}")
                    else:
                        logger.info(f"[VECTOR_INDEX] Job {job_id}: OpenSearch host={settings.opensearch_host}:{settings.opensearch_port}, Index={settings.opensearch_index}")
                    
                    indexed_count = await self._index_to_vector_db(
                        job_id,
                        parse_result.chunks,
                        embeddings,
                        index_namespace,
                    )
                    
                    logger.info(f"[VECTOR_INDEX] Job {job_id}: Successfully indexed {indexed_count} chunks")
                    vector_indexed_successfully = True
                    
                    # Update chunk_infos to mark as indexed
                    for info in chunk_infos:
                        info.indexed_vector = True
                    await self.job_store.store_chunks(job_id, chunk_infos)
                    
                except Exception as e:
                    logger.error(f"[VECTOR_INDEX] Job {job_id}: FAILED - {e}", exc_info=True)
                    # Log warning and continue with graph indexing
                
                vector_time = int((time.time() - vector_start) * 1000)
                metrics.vector_index_time_ms = vector_time
                
                logger.info(f"Job {job_id}: Vector indexing completed in {vector_time}ms (success={vector_indexed_successfully})")
            
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
                    # Check if tree is available (LlamaIndexLegalParser doesn't create tree)
                    if parse_result.tree is None:
                        logger.warning(
                            f"Job {job_id}: Skipping KG building - no tree structure available. "
                            "LlamaIndexLegalParser creates chunks without tree hierarchy."
                        )
                        nodes_created, rels_created = 0, 0
                    else:
                        nodes_created, rels_created = await self._build_knowledge_graph(
                            job_id,
                            parse_result.tree,
                            parse_result.chunks,
                            doc_kind=doc_kind,
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
        from shared.domain.rag_models import DocumentChunk, DocumentMetadata, DocumentLanguage
        
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
        """
        Index PDF-extracted entities and relations to Neo4j.
        
        Maps extracted entities to NodeType.THUAT_NGU (generic term node) and
        relations to EdgeType enum values where possible, with fallback to LIEN_QUAN.
        """
        from app.knowledge_graph.models import GraphNode, GraphRelationship, NodeType, EdgeType
        
        adapter = self._get_graph_adapter()
        if not adapter:
            logger.warning("Neo4j adapter not available, skipping graph building")
            return (0, 0)
        
        nodes_created = 0
        relationships_created = 0
        
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
        
        # Convert entities to GraphNodes
        for entity in entities:
            try:
                # Get entity type string
                entity_type_str = entity.type.value if hasattr(entity.type, 'value') else str(entity.type)
                
                # Use NodeType.THUAT_NGU as generic node type for extracted entities
                # Store original type in properties
                node = GraphNode(
                    id=entity.id,
                    node_type=NodeType.THUAT_NGU,
                    name=entity.text[:200] if entity.text else "",
                    content=entity.text or "",
                    properties={
                        "raw_type": entity_type_str,
                        "text": entity.text,
                        "normalized": getattr(entity, 'normalized', None),
                        "source_chunk": getattr(entity, 'source_chunk_id', None),
                        "confidence": getattr(entity, 'confidence', 0.9),
                        **getattr(entity, 'properties', {}),
                    }
                )
                
                await adapter.add_node(node)
                nodes_created += 1
                
            except Exception as e:
                logger.debug(f"Entity node creation skipped: {e}")
        
        # Convert relations to GraphRelationships
        for rel in relations:
            try:
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
                        "evidence": getattr(rel, 'evidence', ''),
                        "confidence": getattr(rel, 'confidence', 0.9),
                        **getattr(rel, 'properties', {}),
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
        from shared.domain.rag_models import DocumentChunk, DocumentMetadata, DocumentLanguage
        
        # DEBUG: Log chunks received
        logger.info(f"[VECTOR_INDEX] Job {job_id}: Received {len(chunks)} chunks and {len(embeddings)} embeddings")
        
        # DEBUG: Check for specific articles
        article_ids_found = []
        for chunk in chunks:
            article_id = chunk.metadata.get("article_id", "")
            if article_id:
                article_ids_found.append(article_id)
        logger.info(f"[VECTOR_INDEX] Article IDs in chunks: {sorted(set(article_ids_found))[:20]}...")
        
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
        
        # DEBUG: Log before indexing
        logger.info(f"[VECTOR_INDEX] Job {job_id}: About to index {len(doc_chunks)} doc_chunks to adapter")
        
        # Bulk index
        try:
            success = await adapter.index_documents(doc_chunks)
            logger.info(f"[VECTOR_INDEX] Job {job_id}: index_documents returned success={success}")
        except Exception as e:
            logger.error(f"[VECTOR_INDEX] Job {job_id}: index_documents EXCEPTION: {e}", exc_info=True)
            raise
        
        if not success:
            raise RuntimeError("Vector indexing failed")
        
        return len(doc_chunks)
    
    async def _build_knowledge_graph(
        self,
        job_id: str,
        tree: LegalNode,
        chunks: List[LegalChunk],
        doc_kind: str = "LAW",
    ) -> Tuple[int, int]:
        """
        Build knowledge graph in Neo4j from the document tree.
        
        Creates:
        - Document node (Luật/Nghị định/Thông tư based on doc_kind)
        - Chapter nodes (Chương)
        - Section nodes (Mục)
        - Article nodes (Điều)
        - Clause nodes (Khoản)
        - Point nodes (Điểm)
        - THUOC_VE (belongs to) relationships
        - KE_TIEP (next) relationships for siblings
        
        Args:
            job_id: ID of the job
            tree: Parsed legal document tree
            chunks: List of chunks (for potential future use)
            doc_kind: Document kind ("LAW", "DECREE", "CIRCULAR")
        
        Returns:
            Tuple of (nodes_created, relationships_created)
        """
        from app.knowledge_graph.models import GraphNode, GraphRelationship, NodeType, EdgeType
        
        adapter = self._get_graph_adapter()
        if not adapter:
            logger.warning("Neo4j adapter not available, skipping graph building")
            return (0, 0)
        
        nodes_created = 0
        relationships_created = 0
        
        # Collect nodes and relationships for batch operations
        nodes_to_create: List[GraphNode] = []
        rels_to_create: List[GraphRelationship] = []
        
        # Helper to create stable node ID
        def make_node_id(node: LegalNode) -> str:
            """Create a stable, unique node ID from the node's full hierarchical ID."""
            full_id = node.get_full_id()
            # Sanitize: replace problematic characters
            sanitized = full_id.replace(":", "_").replace("/", "_").replace(" ", "_")
            return sanitized if sanitized else f"node_{id(node)}"
        
        def sanitize_id(raw_id: str) -> str:
            """Sanitize an ID string for Neo4j compatibility."""
            return raw_id.replace(":", "_").replace("/", "_").replace(" ", "_")
        
        # Map doc_kind to NodeType
        doc_node_type_map = {
            "LAW": NodeType.LUAT,
            "DECREE": NodeType.NGHI_DINH,
            "CIRCULAR": NodeType.THONG_TU,
        }
        doc_node_type = doc_node_type_map.get(doc_kind, NodeType.LUAT)
        
        # Create document (root) node
        document_number = tree.identifier
        doc_id = sanitize_id(f"DOC={document_number}")
        doc_title = tree.title or document_number
        
        doc_node = GraphNode(
            id=doc_id,
            node_type=doc_node_type,
            name=doc_title,
            content=tree.content[:500] if tree.content else "",
            properties={
                "document_number": document_number,
                "title": doc_title,
                "doc_kind": doc_kind,
                "identifier": tree.identifier,
            }
        )
        nodes_to_create.append(doc_node)
        
        # Recursive function to process nodes
        def collect_nodes_and_rels(
            node: LegalNode,
            parent_id: str,
            prev_sibling_id: Optional[str] = None
        ) -> Optional[str]:
            """
            Recursively collect nodes and relationships.
            Returns the node ID for sibling linking.
            """
            node_id = make_node_id(node)
            
            # Map LegalNodeType to NodeType and set properties
            node_type: Optional[NodeType] = None
            name = ""
            props = {
                "identifier": node.identifier,
                "title": node.title or "",
            }
            
            if node.node_type == LegalNodeType.CHAPTER:
                node_type = NodeType.CHUONG
                name = f"Chương {node.identifier}"
                props["chapter_number"] = node.identifier
                props["chapter_title"] = node.title or ""
            elif node.node_type == LegalNodeType.SECTION:
                node_type = NodeType.MUC
                name = f"Mục {node.identifier}"
                # Try to parse section number as int
                try:
                    props["section_number"] = int(node.identifier)
                except (ValueError, TypeError):
                    props["section_number"] = node.identifier
                props["section_title"] = node.title or ""
            elif node.node_type == LegalNodeType.ARTICLE:
                node_type = NodeType.DIEU
                name = f"Điều {node.identifier}"
                # Parse article number as int if possible
                try:
                    # Handle cases like "1a", "10b" - extract the numeric part
                    num_match = re.match(r'^(\d+)', str(node.identifier))
                    props["article_number"] = int(num_match.group(1)) if num_match else node.identifier
                except (ValueError, TypeError):
                    props["article_number"] = node.identifier
                props["article_title"] = node.title or ""
                props["content"] = node.content[:2000] if node.content else ""
                props["is_definition_article"] = node.is_definition_article
            elif node.node_type == LegalNodeType.CLAUSE:
                node_type = NodeType.KHOAN
                name = f"Khoản {node.identifier}"
                try:
                    props["clause_number"] = int(node.identifier)
                except (ValueError, TypeError):
                    props["clause_number"] = node.identifier
                props["content"] = node.content[:2000] if node.content else ""
            elif node.node_type == LegalNodeType.POINT:
                node_type = NodeType.DIEM
                name = f"Điểm {node.identifier}"
                props["point_label"] = node.identifier
                props["content"] = node.content[:2000] if node.content else ""
            elif node.node_type == LegalNodeType.DEFINITION_ITEM:
                node_type = NodeType.KHAI_NIEM
                name = node.title or f"Định nghĩa {node.identifier}"
                props["term"] = node.title or node.identifier
                props["definition"] = node.content[:2000] if node.content else ""
            else:
                # Skip unknown types
                return None
            
            if node.title:
                name = f"{name}. {node.title}"
            
            # Create the node
            graph_node = GraphNode(
                id=node_id,
                node_type=node_type,
                name=name,
                content=node.content[:1000] if node.content else "",
                properties=props
            )
            nodes_to_create.append(graph_node)
            
            # Create THUOC_VE relationship to parent
            thuoc_ve_rel = GraphRelationship(
                source_id=node_id,
                target_id=parent_id,
                edge_type=EdgeType.THUOC_VE,
                properties={"relationship_type": "structural"}
            )
            rels_to_create.append(thuoc_ve_rel)
            
            # Create KE_TIEP relationship to previous sibling
            if prev_sibling_id:
                ke_tiep_rel = GraphRelationship(
                    source_id=prev_sibling_id,
                    target_id=node_id,
                    edge_type=EdgeType.KE_TIEP,
                    properties={"relationship_type": "sequential"}
                )
                rels_to_create.append(ke_tiep_rel)
            
            # Process children
            child_prev_sibling_id = None
            for child in node.children:
                child_prev_sibling_id = collect_nodes_and_rels(
                    child, node_id, child_prev_sibling_id
                )
            
            return node_id
        
        # Process all children of the document node
        prev_sibling_id = None
        for child in tree.children:
            prev_sibling_id = collect_nodes_and_rels(child, doc_id, prev_sibling_id)
        
        # Batch insert nodes
        for node in nodes_to_create:
            try:
                await adapter.add_node(node)
                nodes_created += 1
            except Exception as e:
                logger.debug(f"Node creation skipped (may exist): {e}")
        
        # Batch insert relationships
        for rel in rels_to_create:
            try:
                await adapter.add_relationship(rel)
                relationships_created += 1
            except Exception as e:
                logger.debug(f"Relationship creation skipped: {e}")
        
        # Update progress
        await self.job_store.update_status(
            job_id,
            JobStatus.INDEXING_GRAPH,
            JobProgress(
                stage="indexing_graph",
                current=nodes_created + relationships_created,
                total=len(nodes_to_create) + len(rels_to_create),
                percentage=100.0,
                message=f"Created {nodes_created} nodes, {relationships_created} relationships"
            )
        )
        
        logger.info(
            f"Knowledge graph built: {nodes_created} nodes, "
            f"{relationships_created} relationships"
        )
        
        return (nodes_created, relationships_created)


# ── Singleton accessor ───────────────────────────────────────────────
# Delegates to the infrastructure factory which handles all wiring.
# Kept here for backward-compatibility with existing import sites.

def get_ingest_service() -> IngestService:
    """Get the singleton IngestService (delegates to infrastructure factory)."""
    from app.shared.container.ingest_factory import get_ingest_service as _factory
    return _factory()
