# app/api/schemas/ingest.py
"""
Pydantic schemas for the document ingestion API.

These schemas define the request/response contracts for:
- File upload and job creation
- Job status and progress tracking
- Chunk listing and pagination
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of an ingestion job."""
    QUEUED = "queued"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING_VECTOR = "indexing_vector"
    INDEXING_GRAPH = "indexing_graph"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestJobCreate(BaseModel):
    """Request schema for creating an ingestion job."""
    law_name: Optional[str] = Field(None, description="Override law name")
    law_id: Optional[str] = Field(None, description="Override law ID")
    index_namespace: Optional[str] = Field(
        "laws_vn", 
        description="Namespace for indexing (e.g., 'laws_vn')"
    )
    run_kg: bool = Field(True, description="Whether to build Knowledge Graph in Neo4j")
    run_vector: bool = Field(True, description="Whether to index in Vector DB")


class IngestJobResponse(BaseModel):
    """Response schema for job creation."""
    job_id: str
    status: JobStatus
    message: str


class JobProgress(BaseModel):
    """Progress information for a job stage."""
    stage: str
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    message: Optional[str] = None


class JobMetrics(BaseModel):
    """Metrics collected during job execution."""
    parse_time_ms: Optional[int] = None
    chunk_count: Optional[int] = None
    embed_time_ms: Optional[int] = None
    vector_index_time_ms: Optional[int] = None
    graph_index_time_ms: Optional[int] = None
    total_time_ms: Optional[int] = None
    chapters_count: Optional[int] = None
    articles_count: Optional[int] = None
    nodes_created: Optional[int] = None
    relationships_created: Optional[int] = None


class JobError(BaseModel):
    """Error information for a failed job."""
    code: str
    message: str
    stage: Optional[str] = None
    traceback: Optional[str] = None


class IngestJobDetail(BaseModel):
    """Detailed job status response."""
    job_id: str
    status: JobStatus
    filename: str
    law_id: Optional[str] = None
    law_name: Optional[str] = None
    index_namespace: str = "laws_vn"
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    progress: Optional[JobProgress] = None
    
    # Metrics
    metrics: Optional[JobMetrics] = None
    
    # Error (if failed)
    error: Optional[JobError] = None
    
    # Configuration
    run_kg: bool = True
    run_vector: bool = True


class IngestJobSummary(BaseModel):
    """Summary job info for listing."""
    job_id: str
    status: JobStatus
    filename: str
    law_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    chunk_count: Optional[int] = None


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[IngestJobSummary]
    total: int
    page: int = 1
    page_size: int = 20


class ChunkInfo(BaseModel):
    """Information about a single chunk."""
    chunk_id: str
    content: str
    embedding_prefix: str
    metadata: Dict[str, Any]
    indexed_vector: bool = False
    indexed_graph: bool = False


class ChunkListResponse(BaseModel):
    """Response for listing chunks from a job."""
    job_id: str
    chunks: List[ChunkInfo]
    total: int
    page: int = 1
    page_size: int = 50


class IngestConfigResponse(BaseModel):
    """Response showing current ingestion configuration."""
    vector_backend: str
    graph_backend: str = "neo4j"
    embedding_model: str
    token_threshold: int = 800
    redis_available: bool = False
