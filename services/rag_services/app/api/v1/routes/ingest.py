# app/api/v1/routes/ingest.py
"""
API routes for document ingestion.

Endpoints:
- POST /api/v1/ingest/docx - Start ingestion job
- GET /api/v1/ingest/jobs - List recent jobs
- GET /api/v1/ingest/jobs/{job_id} - Get job status
- GET /api/v1/ingest/jobs/{job_id}/chunks - Get job chunks
- DELETE /api/v1/ingest/jobs/{job_id} - Cancel job (if queued)
- GET /api/v1/ingest/config - Get current configuration
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.api.schemas.ingest import (
    JobStatus,
    IngestJobCreate,
    IngestJobResponse,
    IngestJobDetail,
    JobListResponse,
    ChunkListResponse,
    IngestConfigResponse,
)
from core.services.job_store import get_job_store
from core.services.ingest_service import get_ingest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Directory for uploaded files
UPLOAD_DIR = Path(tempfile.gettempdir()) / "rag_ingest_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".docx", ".doc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix}. Only .docx and .doc are allowed."
        )


async def _save_upload(file: UploadFile) -> Path:
    """Save uploaded file to temporary directory."""
    # Generate safe filename
    safe_name = file.filename.replace(" ", "_").replace("/", "_")
    file_path = UPLOAD_DIR / f"{os.urandom(8).hex()}_{safe_name}"
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved upload: {file_path} ({len(content)} bytes)")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {e}"
        )


async def _process_ingestion(
    job_id: str,
    file_path: Path,
    law_id: Optional[str],
    law_name: Optional[str],
    index_namespace: str,
    run_kg: bool,
    run_vector: bool,
) -> None:
    """Background task to process document ingestion."""
    try:
        service = get_ingest_service()
        await service.start_ingestion(
            job_id=job_id,
            file_path=file_path,
            law_id=law_id,
            law_name=law_name,
            index_namespace=index_namespace,
            run_kg=run_kg,
            run_vector=run_vector,
        )
    finally:
        # Clean up uploaded file
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up upload: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up upload: {e}")


@router.post(
    "/docx",
    response_model=IngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start document ingestion",
    description="""
    Upload a Vietnamese legal document (.docx or .doc) for ingestion.
    
    The document will be processed in the background:
    1. Parse document structure (Chapters, Articles, Clauses, Points)
    2. Generate text embeddings
    3. Index to vector database (Weaviate/OpenSearch)
    4. Build knowledge graph in Neo4j
    
    Returns a job_id for tracking progress.
    """,
)
async def start_ingestion(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="DOCX or DOC file to ingest"),
    law_name: Optional[str] = Form(None, description="Override law name"),
    law_id: Optional[str] = Form(None, description="Override law ID"),
    index_namespace: str = Form("laws_vn", description="Namespace for indexing"),
    run_kg: bool = Form(True, description="Build knowledge graph in Neo4j"),
    run_vector: bool = Form(True, description="Index to vector database"),
):
    """Start ingestion of a legal document."""
    # Validate file
    _validate_file(file)
    
    # Save file
    file_path = await _save_upload(file)
    
    # Create job
    job_store = get_job_store()
    job_id = await job_store.create_job(
        filename=file.filename,
        law_id=law_id,
        law_name=law_name,
        index_namespace=index_namespace,
        run_kg=run_kg,
        run_vector=run_vector,
    )
    
    # Start background processing
    background_tasks.add_task(
        _process_ingestion,
        job_id=job_id,
        file_path=file_path,
        law_id=law_id,
        law_name=law_name,
        index_namespace=index_namespace,
        run_kg=run_kg,
        run_vector=run_vector,
    )
    
    logger.info(f"Started ingestion job {job_id} for {file.filename}")
    
    return IngestJobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Ingestion started. Poll GET /api/v1/ingest/jobs/{job_id} for progress.",
    )


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List ingestion jobs",
    description="Get a paginated list of recent ingestion jobs.",
)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by status"),
):
    """List recent ingestion jobs."""
    job_store = get_job_store()
    jobs, total = await job_store.list_jobs(
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=IngestJobDetail,
    summary="Get job status",
    description="Get detailed status and progress of an ingestion job.",
)
async def get_job_status(job_id: str):
    """Get status of a specific ingestion job."""
    job_store = get_job_store()
    job = await job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    return job


@router.get(
    "/jobs/{job_id}/chunks",
    response_model=ChunkListResponse,
    summary="Get job chunks",
    description="Get paginated list of chunks created by an ingestion job.",
)
async def get_job_chunks(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
):
    """Get chunks created by an ingestion job."""
    job_store = get_job_store()
    
    # Verify job exists
    job = await job_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    chunks, total = await job_store.get_chunks(
        job_id=job_id,
        page=page,
        page_size=page_size,
    )
    
    return ChunkListResponse(
        job_id=job_id,
        chunks=chunks,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel job",
    description="Cancel a queued job. Running jobs cannot be cancelled.",
)
async def cancel_job(job_id: str):
    """Cancel a queued ingestion job."""
    job_store = get_job_store()
    job = await job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}"
        )
    
    if job.status != JobStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )
    
    from app.api.schemas.ingest import JobError
    
    await job_store.set_failed(
        job_id,
        JobError(code="CANCELLED", message="Job cancelled by user")
    )
    
    # Update status to cancelled
    await job_store.update_status(job_id, JobStatus.CANCELLED)
    
    logger.info(f"Cancelled job {job_id}")


@router.get(
    "/config",
    response_model=IngestConfigResponse,
    summary="Get ingestion configuration",
    description="Get current ingestion pipeline configuration.",
)
async def get_config():
    """Get current ingestion configuration."""
    from app.config.settings import settings
    from core.services.job_store import get_job_store
    
    # Check Redis availability
    job_store = get_job_store()
    redis_available = not isinstance(job_store, type(job_store).__bases__[0])  # Not InMemoryJobStore
    
    # Check actual type
    from core.services.job_store import InMemoryJobStore
    redis_available = not isinstance(job_store, InMemoryJobStore)
    
    return IngestConfigResponse(
        vector_backend=settings.vector_backend,
        graph_backend="neo4j",
        embedding_model=settings.emb_model,
        token_threshold=800,
        redis_available=redis_available,
    )
