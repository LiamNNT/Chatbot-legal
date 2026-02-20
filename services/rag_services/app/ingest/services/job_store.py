# core/services/job_store.py
"""
Job state management for ingestion pipeline.

Provides storage for job state with:
- Redis backend (production, preferred)
- In-memory fallback (development only)

The job store is responsible for:
- Creating and tracking ingestion jobs
- Updating job progress and status
- Storing job results (chunks, metrics)
- Listing recent jobs
"""

from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.ingest.schemas import (
    JobStatus,
    JobProgress,
    JobMetrics,
    JobError,
    IngestJobDetail,
    IngestJobSummary,
    ChunkInfo,
)

logger = logging.getLogger(__name__)


class JobStore(ABC):
    """Abstract base class for job storage."""
    
    @abstractmethod
    async def create_job(
        self,
        filename: str,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> str:
        """Create a new job and return its ID."""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[IngestJobDetail]:
        """Get job details by ID."""
        pass
    
    @abstractmethod
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[JobProgress] = None,
    ) -> bool:
        """Update job status and progress."""
        pass
    
    @abstractmethod
    async def set_started(self, job_id: str) -> bool:
        """Mark job as started."""
        pass
    
    @abstractmethod
    async def set_completed(
        self,
        job_id: str,
        metrics: Optional[JobMetrics] = None,
    ) -> bool:
        """Mark job as completed with metrics."""
        pass
    
    @abstractmethod
    async def set_failed(
        self,
        job_id: str,
        error: JobError,
    ) -> bool:
        """Mark job as failed with error info."""
        pass
    
    @abstractmethod
    async def store_chunks(
        self,
        job_id: str,
        chunks: List[ChunkInfo],
    ) -> bool:
        """Store chunks for a job."""
        pass
    
    @abstractmethod
    async def get_chunks(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[ChunkInfo], int]:
        """Get paginated chunks for a job."""
        pass
    
    @abstractmethod
    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobStatus] = None,
    ) -> tuple[List[IngestJobSummary], int]:
        """List jobs with optional filtering."""
        pass
    
    @abstractmethod
    async def update_law_info(
        self,
        job_id: str,
        law_id: str,
        law_name: str,
    ) -> bool:
        """Update law ID and name after parsing."""
        pass
    
    @abstractmethod
    async def update_doc_metadata(
        self,
        job_id: str,
        doc_kind: str,
        document_number: str,
        issuer: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """Update document metadata after parsing (doc_kind, document_number, etc.)."""
        pass
    
    @abstractmethod
    async def update_metrics(
        self,
        job_id: str,
        metrics: JobMetrics,
    ) -> bool:
        """Update job metrics."""
        pass


class InMemoryJobStore(JobStore):
    """
    In-memory job store for development/testing.
    
    WARNING: This store does not persist data across restarts.
    Use Redis in production!
    """
    
    def __init__(self, max_jobs: int = 100):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._chunks: Dict[str, List[ChunkInfo]] = {}
        self._job_order: List[str] = []  # For ordering
        self._max_jobs = max_jobs
        logger.warning(
            "Using in-memory job store - data will be lost on restart! "
            "Configure Redis for production use."
        )
    
    def _cleanup_old_jobs(self):
        """Remove old jobs if we exceed max_jobs."""
        while len(self._job_order) > self._max_jobs:
            old_job_id = self._job_order.pop(0)
            self._jobs.pop(old_job_id, None)
            self._chunks.pop(old_job_id, None)
    
    async def create_job(
        self,
        filename: str,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "filename": filename,
            "law_id": law_id,
            "law_name": law_name,
            "index_namespace": index_namespace,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "metrics": None,
            "error": None,
            "run_kg": run_kg,
            "run_vector": run_vector,
            # PHASE 2 additions
            "doc_kind": None,
            "document_number": None,
            "issuer": None,
        }
        self._job_order.append(job_id)
        self._cleanup_old_jobs()
        
        logger.info(f"Created job {job_id} for file: {filename}")
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[IngestJobDetail]:
        job_data = self._jobs.get(job_id)
        if not job_data:
            return None
        
        return IngestJobDetail(
            job_id=job_data["job_id"],
            status=job_data["status"],
            filename=job_data["filename"],
            law_id=job_data["law_id"],
            law_name=job_data["law_name"],
            index_namespace=job_data["index_namespace"],
            created_at=job_data["created_at"],
            started_at=job_data["started_at"],
            completed_at=job_data["completed_at"],
            progress=job_data["progress"],
            metrics=job_data["metrics"],
            error=job_data["error"],
            run_kg=job_data["run_kg"],
            run_vector=job_data["run_vector"],
            # PHASE 2 additions
            doc_kind=job_data.get("doc_kind"),
            document_number=job_data.get("document_number"),
            issuer=job_data.get("issuer"),
        )
    
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[JobProgress] = None,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["status"] = status
        if progress:
            self._jobs[job_id]["progress"] = progress
        
        logger.debug(f"Job {job_id} status: {status.value}")
        return True
    
    async def set_started(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["started_at"] = datetime.utcnow()
        self._jobs[job_id]["status"] = JobStatus.PARSING
        return True
    
    async def set_completed(
        self,
        job_id: str,
        metrics: Optional[JobMetrics] = None,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["status"] = JobStatus.COMPLETED
        self._jobs[job_id]["completed_at"] = datetime.utcnow()
        if metrics:
            self._jobs[job_id]["metrics"] = metrics
        
        logger.info(f"Job {job_id} completed")
        return True
    
    async def set_failed(
        self,
        job_id: str,
        error: JobError,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["status"] = JobStatus.FAILED
        self._jobs[job_id]["completed_at"] = datetime.utcnow()
        self._jobs[job_id]["error"] = error
        
        logger.error(f"Job {job_id} failed: {error.message}")
        return True
    
    async def store_chunks(
        self,
        job_id: str,
        chunks: List[ChunkInfo],
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._chunks[job_id] = chunks
        
        # Update metrics
        if self._jobs[job_id]["metrics"]:
            self._jobs[job_id]["metrics"].chunk_count = len(chunks)
        else:
            self._jobs[job_id]["metrics"] = JobMetrics(chunk_count=len(chunks))
        
        return True
    
    async def get_chunks(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[ChunkInfo], int]:
        chunks = self._chunks.get(job_id, [])
        total = len(chunks)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        return chunks[start:end], total
    
    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobStatus] = None,
    ) -> tuple[List[IngestJobSummary], int]:
        # Filter and sort jobs
        jobs = list(self._jobs.values())
        
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        
        # Sort by created_at descending
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        
        total = len(jobs)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        page_jobs = jobs[start:end]
        
        summaries = [
            IngestJobSummary(
                job_id=j["job_id"],
                status=j["status"],
                filename=j["filename"],
                law_id=j["law_id"],
                created_at=j["created_at"],
                completed_at=j["completed_at"],
                chunk_count=j["metrics"].chunk_count if j["metrics"] else None,
            )
            for j in page_jobs
        ]
        
        return summaries, total
    
    async def update_law_info(
        self,
        job_id: str,
        law_id: str,
        law_name: str,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["law_id"] = law_id
        self._jobs[job_id]["law_name"] = law_name
        return True
    
    async def update_doc_metadata(
        self,
        job_id: str,
        doc_kind: str,
        document_number: str,
        issuer: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """Update document metadata after parsing."""
        if job_id not in self._jobs:
            return False
        
        self._jobs[job_id]["doc_kind"] = doc_kind
        self._jobs[job_id]["document_number"] = document_number
        if issuer is not None:
            self._jobs[job_id]["issuer"] = issuer
        if title is not None:
            self._jobs[job_id]["law_name"] = title
        return True
    
    async def update_metrics(
        self,
        job_id: str,
        metrics: JobMetrics,
    ) -> bool:
        if job_id not in self._jobs:
            return False
        
        existing = self._jobs[job_id].get("metrics")
        if existing:
            # Merge metrics
            updated = JobMetrics(
                parse_time_ms=metrics.parse_time_ms or existing.parse_time_ms,
                chunk_count=metrics.chunk_count or existing.chunk_count,
                embed_time_ms=metrics.embed_time_ms or existing.embed_time_ms,
                vector_index_time_ms=metrics.vector_index_time_ms or existing.vector_index_time_ms,
                graph_index_time_ms=metrics.graph_index_time_ms or existing.graph_index_time_ms,
                total_time_ms=metrics.total_time_ms or existing.total_time_ms,
                chapters_count=metrics.chapters_count or existing.chapters_count,
                articles_count=metrics.articles_count or existing.articles_count,
                nodes_created=metrics.nodes_created or existing.nodes_created,
                relationships_created=metrics.relationships_created or existing.relationships_created,
            )
            self._jobs[job_id]["metrics"] = updated
        else:
            self._jobs[job_id]["metrics"] = metrics
        
        return True


class RedisJobStore(JobStore):
    """
    Redis-backed job store for production use.
    
    Provides persistent storage with TTL for automatic cleanup.
    """
    
    JOB_PREFIX = "ingest:job:"
    CHUNKS_PREFIX = "ingest:chunks:"
    JOB_LIST_KEY = "ingest:jobs"
    JOB_TTL = 7 * 24 * 60 * 60  # 7 days
    
    def __init__(self, redis_client):
        self._redis = redis_client
        logger.info("Using Redis job store for ingestion jobs")
    
    def _job_key(self, job_id: str) -> str:
        return f"{self.JOB_PREFIX}{job_id}"
    
    def _chunks_key(self, job_id: str) -> str:
        return f"{self.CHUNKS_PREFIX}{job_id}"
    
    def _serialize_job(self, job_data: Dict[str, Any]) -> str:
        """Serialize job data for Redis storage."""
        data = job_data.copy()
        # Convert datetime to ISO string
        for key in ["created_at", "started_at", "completed_at"]:
            if data.get(key):
                data[key] = data[key].isoformat()
        # Convert enums
        if data.get("status"):
            data["status"] = data["status"].value
        # Convert Pydantic models to dicts
        if data.get("progress"):
            data["progress"] = data["progress"].model_dump() if hasattr(data["progress"], "model_dump") else data["progress"]
        if data.get("metrics"):
            data["metrics"] = data["metrics"].model_dump() if hasattr(data["metrics"], "model_dump") else data["metrics"]
        if data.get("error"):
            data["error"] = data["error"].model_dump() if hasattr(data["error"], "model_dump") else data["error"]
        return json.dumps(data)
    
    def _deserialize_job(self, data: str) -> Dict[str, Any]:
        """Deserialize job data from Redis."""
        job = json.loads(data)
        # Convert ISO strings back to datetime
        for key in ["created_at", "started_at", "completed_at"]:
            if job.get(key):
                job[key] = datetime.fromisoformat(job[key])
        # Convert status string to enum
        if job.get("status"):
            job["status"] = JobStatus(job["status"])
        # Convert dicts back to Pydantic models
        if job.get("progress"):
            job["progress"] = JobProgress(**job["progress"])
        if job.get("metrics"):
            job["metrics"] = JobMetrics(**job["metrics"])
        if job.get("error"):
            job["error"] = JobError(**job["error"])
        return job
    
    async def create_job(
        self,
        filename: str,
        law_id: Optional[str] = None,
        law_name: Optional[str] = None,
        index_namespace: str = "laws_vn",
        run_kg: bool = True,
        run_vector: bool = True,
    ) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        job_data = {
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "filename": filename,
            "law_id": law_id,
            "law_name": law_name,
            "index_namespace": index_namespace,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "metrics": None,
            "error": None,
            "run_kg": run_kg,
            "run_vector": run_vector,
            # PHASE 2 additions
            "doc_kind": None,
            "document_number": None,
            "issuer": None,
        }
        
        # Store job
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        
        # Add to job list (sorted set by timestamp)
        self._redis.zadd(self.JOB_LIST_KEY, {job_id: now.timestamp()})
        
        logger.info(f"Created job {job_id} for file: {filename}")
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[IngestJobDetail]:
        data = self._redis.get(self._job_key(job_id))
        if not data:
            return None
        
        job_data = self._deserialize_job(data)
        return IngestJobDetail(**job_data)
    
    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[JobProgress] = None,
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["status"] = status
        if progress:
            job_data["progress"] = progress
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def set_started(self, job_id: str) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["started_at"] = datetime.utcnow()
        job_data["status"] = JobStatus.PARSING
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def set_completed(
        self,
        job_id: str,
        metrics: Optional[JobMetrics] = None,
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["status"] = JobStatus.COMPLETED
        job_data["completed_at"] = datetime.utcnow()
        if metrics:
            job_data["metrics"] = metrics
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def set_failed(
        self,
        job_id: str,
        error: JobError,
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["status"] = JobStatus.FAILED
        job_data["completed_at"] = datetime.utcnow()
        job_data["error"] = error
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def store_chunks(
        self,
        job_id: str,
        chunks: List[ChunkInfo],
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        # Store chunks as JSON array
        chunks_data = [c.model_dump() for c in chunks]
        self._redis.setex(
            self._chunks_key(job_id),
            self.JOB_TTL,
            json.dumps(chunks_data)
        )
        
        # Update chunk count in metrics
        await self.update_metrics(job_id, JobMetrics(chunk_count=len(chunks)))
        
        return True
    
    async def get_chunks(
        self,
        job_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[ChunkInfo], int]:
        data = self._redis.get(self._chunks_key(job_id))
        if not data:
            return [], 0
        
        chunks_data = json.loads(data)
        chunks = [ChunkInfo(**c) for c in chunks_data]
        total = len(chunks)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        return chunks[start:end], total
    
    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[JobStatus] = None,
    ) -> tuple[List[IngestJobSummary], int]:
        # Get all job IDs from sorted set (newest first)
        job_ids = self._redis.zrevrange(self.JOB_LIST_KEY, 0, -1)
        
        summaries = []
        for job_id in job_ids:
            if isinstance(job_id, bytes):
                job_id = job_id.decode()
            
            job = await self.get_job(job_id)
            if not job:
                continue
            
            if status and job.status != status:
                continue
            
            summaries.append(IngestJobSummary(
                job_id=job.job_id,
                status=job.status,
                filename=job.filename,
                law_id=job.law_id,
                created_at=job.created_at,
                completed_at=job.completed_at,
                chunk_count=job.metrics.chunk_count if job.metrics else None,
            ))
        
        total = len(summaries)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        
        return summaries[start:end], total
    
    async def update_law_info(
        self,
        job_id: str,
        law_id: str,
        law_name: str,
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["law_id"] = law_id
        job_data["law_name"] = law_name
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def update_doc_metadata(
        self,
        job_id: str,
        doc_kind: str,
        document_number: str,
        issuer: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """Update document metadata after parsing."""
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        job_data["doc_kind"] = doc_kind
        job_data["document_number"] = document_number
        if issuer is not None:
            job_data["issuer"] = issuer
        if title is not None:
            job_data["law_name"] = title
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True
    
    async def update_metrics(
        self,
        job_id: str,
        metrics: JobMetrics,
    ) -> bool:
        job = await self.get_job(job_id)
        if not job:
            return False
        
        job_data = job.model_dump()
        existing = job_data.get("metrics")
        
        if existing:
            # Merge metrics
            for field in metrics.model_fields:
                new_val = getattr(metrics, field)
                if new_val is not None:
                    existing[field] = new_val
            job_data["metrics"] = existing
        else:
            job_data["metrics"] = metrics
        
        self._redis.setex(
            self._job_key(job_id),
            self.JOB_TTL,
            self._serialize_job(job_data)
        )
        return True


def create_job_store() -> JobStore:
    """
    Factory function to create the appropriate job store.
    
    Returns Redis store if available, otherwise falls back to in-memory.
    """
    try:
        import redis
        from app.shared.config.settings import settings
        
        # Try to get Redis URL from settings or environment
        redis_url = getattr(settings, 'redis_url', None)
        if not redis_url:
            import os
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        client = redis.from_url(redis_url)
        # Test connection
        client.ping()
        
        logger.info(f"Connected to Redis at {redis_url}")
        return RedisJobStore(client)
        
    except ImportError:
        logger.warning("redis package not installed, using in-memory store")
    except Exception as e:
        logger.warning(f"Could not connect to Redis ({e}), using in-memory store")
    
    return InMemoryJobStore()


# Singleton instance
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get the singleton job store instance."""
    global _job_store
    if _job_store is None:
        _job_store = create_job_store()
    return _job_store
