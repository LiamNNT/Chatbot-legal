# tests/test_ingest_api.py
"""
Tests for the document ingestion API.

Tests cover:
- API contract tests (request/response schemas)
- Job state transitions
- Job store operations (in-memory)
- File upload validation
- Configuration endpoint
"""

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO
import httpx

from fastapi import FastAPI, UploadFile
from httpx import ASGITransport

from app.api.schemas.ingest import (
    JobStatus,
    IngestJobResponse,
    IngestJobDetail,
    JobListResponse,
    ChunkListResponse,
    ChunkInfo,
    JobProgress,
    JobMetrics,
    JobError,
)
from core.services.job_store import (
    InMemoryJobStore,
    JobStore,
    get_job_store,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def job_store() -> InMemoryJobStore:
    """Create a fresh in-memory job store."""
    return InMemoryJobStore(max_jobs=50)


@pytest.fixture
def mock_ingest_service():
    """Create a mock ingest service."""
    with patch('core.services.ingest_service.get_ingest_service') as mock:
        service = MagicMock()
        service.start_ingestion = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def app(job_store: InMemoryJobStore):
    """Create a test FastAPI app with mocked dependencies."""
    from app.api.v1.routes.ingest import router
    
    test_app = FastAPI()
    test_app.include_router(router, prefix="/v1")
    
    # Override job store dependency
    with patch('core.services.job_store.get_job_store', return_value=job_store):
        yield test_app


@pytest.fixture
async def client(app, job_store: InMemoryJobStore):
    """Create an async test client using httpx."""
    with patch('app.api.v1.routes.ingest.get_job_store', return_value=job_store):
        with patch('app.api.v1.routes.ingest.get_ingest_service') as mock_service:
            service = MagicMock()
            service.start_ingestion = AsyncMock()
            mock_service.return_value = service
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac


# =============================================================================
# Job Store Tests
# =============================================================================

class TestInMemoryJobStore:
    """Test in-memory job store operations."""
    
    @pytest.mark.asyncio
    async def test_create_job(self, job_store: InMemoryJobStore):
        """Test creating a new job."""
        job_id = await job_store.create_job(
            filename="test.docx",
            law_id="20/2023/QH15",
            law_name="Luật Test",
        )
        
        assert job_id is not None
        assert len(job_id) == 36  # UUID format
    
    @pytest.mark.asyncio
    async def test_get_job(self, job_store: InMemoryJobStore):
        """Test getting job details."""
        job_id = await job_store.create_job(filename="test.docx")
        
        job = await job_store.get_job(job_id)
        
        assert job is not None
        assert job.job_id == job_id
        assert job.filename == "test.docx"
        assert job.status == JobStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, job_store: InMemoryJobStore):
        """Test getting a non-existent job."""
        job = await job_store.get_job("nonexistent-id")
        assert job is None
    
    @pytest.mark.asyncio
    async def test_update_status(self, job_store: InMemoryJobStore):
        """Test updating job status."""
        job_id = await job_store.create_job(filename="test.docx")
        
        progress = JobProgress(
            stage="parsing",
            current=50,
            total=100,
            percentage=50.0,
            message="Parsing..."
        )
        
        result = await job_store.update_status(
            job_id,
            JobStatus.PARSING,
            progress
        )
        
        assert result is True
        
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.PARSING
        assert job.progress.stage == "parsing"
        assert job.progress.percentage == 50.0
    
    @pytest.mark.asyncio
    async def test_set_started(self, job_store: InMemoryJobStore):
        """Test marking job as started."""
        job_id = await job_store.create_job(filename="test.docx")
        
        await job_store.set_started(job_id)
        
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.PARSING
        assert job.started_at is not None
    
    @pytest.mark.asyncio
    async def test_set_completed(self, job_store: InMemoryJobStore):
        """Test marking job as completed."""
        job_id = await job_store.create_job(filename="test.docx")
        
        metrics = JobMetrics(
            chunk_count=100,
            parse_time_ms=500,
            total_time_ms=2000,
        )
        
        await job_store.set_completed(job_id, metrics)
        
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.metrics.chunk_count == 100
    
    @pytest.mark.asyncio
    async def test_set_failed(self, job_store: InMemoryJobStore):
        """Test marking job as failed."""
        job_id = await job_store.create_job(filename="test.docx")
        
        error = JobError(
            code="PARSE_ERROR",
            message="Failed to parse document",
            stage="parsing",
        )
        
        await job_store.set_failed(job_id, error)
        
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error.code == "PARSE_ERROR"
    
    @pytest.mark.asyncio
    async def test_store_and_get_chunks(self, job_store: InMemoryJobStore):
        """Test storing and retrieving chunks."""
        job_id = await job_store.create_job(filename="test.docx")
        
        chunks = [
            ChunkInfo(
                chunk_id=f"chunk_{i}",
                content=f"Content {i}",
                embedding_prefix=f"PREFIX_{i}",
                metadata={"index": i},
            )
            for i in range(10)
        ]
        
        await job_store.store_chunks(job_id, chunks)
        
        retrieved, total = await job_store.get_chunks(job_id, page=1, page_size=5)
        
        assert total == 10
        assert len(retrieved) == 5
        assert retrieved[0].chunk_id == "chunk_0"
    
    @pytest.mark.asyncio
    async def test_list_jobs(self, job_store: InMemoryJobStore):
        """Test listing jobs."""
        # Create multiple jobs
        for i in range(5):
            await job_store.create_job(filename=f"test_{i}.docx")
        
        jobs, total = await job_store.list_jobs(page=1, page_size=3)
        
        assert total == 5
        assert len(jobs) == 3
    
    @pytest.mark.asyncio
    async def test_list_jobs_with_status_filter(self, job_store: InMemoryJobStore):
        """Test listing jobs with status filter."""
        job1 = await job_store.create_job(filename="test1.docx")
        job2 = await job_store.create_job(filename="test2.docx")
        
        await job_store.set_completed(job1)
        
        jobs, total = await job_store.list_jobs(status=JobStatus.COMPLETED)
        
        assert total == 1
        assert jobs[0].status == JobStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_update_law_info(self, job_store: InMemoryJobStore):
        """Test updating law info after parsing."""
        job_id = await job_store.create_job(filename="test.docx")
        
        await job_store.update_law_info(
            job_id,
            law_id="20/2023/QH15",
            law_name="Luật Giao dịch điện tử"
        )
        
        job = await job_store.get_job(job_id)
        assert job.law_id == "20/2023/QH15"
        assert job.law_name == "Luật Giao dịch điện tử"
    
    @pytest.mark.asyncio
    async def test_max_jobs_cleanup(self, job_store: InMemoryJobStore):
        """Test that old jobs are cleaned up when max is exceeded."""
        job_store = InMemoryJobStore(max_jobs=5)
        
        # Create 10 jobs
        job_ids = []
        for i in range(10):
            job_id = await job_store.create_job(filename=f"test_{i}.docx")
            job_ids.append(job_id)
        
        # First 5 should be cleaned up
        for old_id in job_ids[:5]:
            job = await job_store.get_job(old_id)
            assert job is None
        
        # Last 5 should still exist
        for new_id in job_ids[5:]:
            job = await job_store.get_job(new_id)
            assert job is not None


# =============================================================================
# Job State Transition Tests
# =============================================================================

class TestJobStateTransitions:
    """Test job state machine transitions."""
    
    @pytest.mark.asyncio
    async def test_normal_flow(self, job_store: InMemoryJobStore):
        """Test normal job flow: QUEUED -> PARSING -> ... -> COMPLETED."""
        job_id = await job_store.create_job(filename="test.docx")
        
        # Initial state
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.QUEUED
        
        # Start processing
        await job_store.set_started(job_id)
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.PARSING
        
        # Progress through stages
        stages = [
            JobStatus.CHUNKING,
            JobStatus.EMBEDDING,
            JobStatus.INDEXING_VECTOR,
            JobStatus.INDEXING_GRAPH,
        ]
        
        for stage in stages:
            await job_store.update_status(job_id, stage)
            job = await job_store.get_job(job_id)
            assert job.status == stage
        
        # Complete
        await job_store.set_completed(job_id)
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_failure_flow(self, job_store: InMemoryJobStore):
        """Test failure flow: QUEUED -> PARSING -> FAILED."""
        job_id = await job_store.create_job(filename="test.docx")
        
        await job_store.set_started(job_id)
        
        error = JobError(
            code="PARSE_ERROR",
            message="Invalid document format"
        )
        await job_store.set_failed(job_id, error)
        
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error is not None


# =============================================================================
# API Contract Tests
# =============================================================================

class TestIngestAPIContract:
    """Test API endpoint contracts."""
    
    @pytest.mark.asyncio
    async def test_start_ingestion_returns_202(self, client: httpx.AsyncClient):
        """Test that POST /ingest/docx returns 202 Accepted."""
        # Create a minimal DOCX-like file
        file_content = b"PK\x03\x04test content"
        
        response = await client.post(
            "/v1/ingest/docx",
            files={"file": ("test.docx", BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"law_name": "Test Law", "run_kg": "true", "run_vector": "true"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
    
    @pytest.mark.asyncio
    async def test_start_ingestion_rejects_invalid_file(self, client: httpx.AsyncClient):
        """Test that invalid file types are rejected."""
        response = await client.post(
            "/v1/ingest/docx",
            files={"file": ("test.pdf", BytesIO(b"PDF content"), "application/pdf")},
        )
        
        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_list_jobs_returns_paginated_list(self, client: httpx.AsyncClient, job_store: InMemoryJobStore):
        """Test that GET /ingest/jobs returns paginated list."""
        # Create some jobs directly in store
        for i in range(3):
            await job_store.create_job(filename=f"test_{i}.docx")
        
        response = await client.get("/v1/ingest/jobs")
        
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert data["total"] == 3
    
    @pytest.mark.asyncio
    async def test_get_job_status_returns_detail(self, client: httpx.AsyncClient, job_store: InMemoryJobStore):
        """Test that GET /ingest/jobs/{job_id} returns job detail."""
        # Create a job
        job_id = await job_store.create_job(filename="test.docx", law_id="20/2023/QH15")
        
        response = await client.get(f"/v1/ingest/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["filename"] == "test.docx"
        assert data["law_id"] == "20/2023/QH15"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_job_returns_404(self, client: httpx.AsyncClient):
        """Test that getting non-existent job returns 404."""
        response = await client.get("/v1/ingest/jobs/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_job_chunks_returns_paginated_chunks(self, client: httpx.AsyncClient, job_store: InMemoryJobStore):
        """Test that GET /ingest/jobs/{job_id}/chunks returns chunks."""
        # Create a job with chunks
        job_id = await job_store.create_job(filename="test.docx")
        chunks = [
            ChunkInfo(
                chunk_id=f"chunk_{i}",
                content=f"Content {i}",
                embedding_prefix=f"PREFIX_{i}",
                metadata={"index": i},
            )
            for i in range(5)
        ]
        await job_store.store_chunks(job_id, chunks)
        
        response = await client.get(f"/v1/ingest/jobs/{job_id}/chunks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["chunks"]) == 5
    
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, client: httpx.AsyncClient, job_store: InMemoryJobStore):
        """Test cancelling a queued job."""
        job_id = await job_store.create_job(filename="test.docx")
        
        response = await client.delete(f"/v1/ingest/jobs/{job_id}")
        
        assert response.status_code == 204
        
        # Verify job is cancelled
        job = await job_store.get_job(job_id)
        assert job.status == JobStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cannot_cancel_running_job(self, client: httpx.AsyncClient, job_store: InMemoryJobStore):
        """Test that running jobs cannot be cancelled."""
        job_id = await job_store.create_job(filename="test.docx")
        await job_store.set_started(job_id)
        
        response = await client.delete(f"/v1/ingest/jobs/{job_id}")
        
        assert response.status_code == 400


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfigEndpoint:
    """Test configuration endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_config(self, client: httpx.AsyncClient):
        """Test GET /ingest/config returns configuration."""
        with patch('app.config.settings.settings') as mock_settings:
            mock_settings.vector_backend = "weaviate"
            mock_settings.emb_model = "intfloat/multilingual-e5-base"
            mock_settings.redis_url = None
            
            response = await client.get("/v1/ingest/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "vector_backend" in data
        assert "embedding_model" in data
        assert "redis_available" in data


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemas:
    """Test Pydantic schema validation."""
    
    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
    
    def test_chunk_info_serialization(self):
        """Test ChunkInfo can be serialized."""
        chunk = ChunkInfo(
            chunk_id="test:chunk",
            content="Test content",
            embedding_prefix="TEST | CHUNK",
            metadata={"key": "value"},
            indexed_vector=True,
            indexed_graph=False,
        )
        
        data = chunk.model_dump()
        
        assert data["chunk_id"] == "test:chunk"
        assert data["indexed_vector"] is True
    
    def test_job_metrics_optional_fields(self):
        """Test that JobMetrics fields are optional."""
        metrics = JobMetrics(chunk_count=10)
        
        assert metrics.chunk_count == 10
        assert metrics.parse_time_ms is None
        assert metrics.total_time_ms is None
    
    def test_job_error_schema(self):
        """Test JobError schema."""
        error = JobError(
            code="TEST_ERROR",
            message="Test error message",
            stage="parsing",
            traceback="Traceback...",
        )
        
        assert error.code == "TEST_ERROR"
        assert error.stage == "parsing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
