"""
Pydantic schemas for orchestrator API request / response models.

These are the "presentation layer" schemas used by FastAPI route handlers.
They are intentionally separate from the internal domain dataclasses
(``shared.domain``) so that API shape can evolve independently.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    query: str = Field(..., description="User query text")
    session_id: Optional[str] = Field(None, description="Conversation session ID")
    use_rag: bool = Field(True, description="Whether to use RAG retrieval")
    use_knowledge_graph: Optional[bool] = Field(None, description="Whether to use Knowledge Graph reasoning")
    rag_top_k: int = Field(5, description="Number of top documents to retrieve")
    model: Optional[str] = Field(None, description="Override LLM model")
    temperature: Optional[float] = Field(None, description="LLM sampling temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens in response")
    stream: bool = Field(False, description="Enable streaming response")


class DocumentInfo(BaseModel):
    """Single retrieved document in the response."""

    title: str = "Untitled"
    content: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGContextInfo(BaseModel):
    """RAG context details returned alongside the answer."""

    query: str
    documents: List[DocumentInfo] = Field(default_factory=list)
    total_documents: int = 0
    search_mode: str = "unknown"
    processing_time: Optional[float] = None
    use_knowledge_graph: bool = False
    use_vector_search: bool = True
    complexity: Optional[str] = None
    strategy: Optional[str] = None


class ProcessingStats(BaseModel):
    """Timing / cost statistics for a single request."""

    total_time: float = 0.0
    rag_time: Optional[float] = None
    agent_time: Optional[float] = None
    documents_retrieved: Optional[int] = None
    tokens_used: Optional[int] = None
    rag_error: Optional[str] = None
    llm_calls: Optional[int] = None
    pipeline: Optional[str] = None
    planning_time: Optional[float] = None
    answer_generation_time: Optional[float] = None
    plan_complexity: Optional[str] = None
    plan_complexity_score: Optional[float] = None


class ChatResponse(BaseModel):
    """Response payload for chat endpoints."""

    response: str
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    rag_context: Optional[RAGContextInfo] = None
    processing_stats: Optional[ProcessingStats] = None
    model_used: Optional[str] = None


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class ConversationInfo(BaseModel):
    """Summary of a single conversation session."""

    session_id: str
    message_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationsResponse(BaseModel):
    """List of active conversations."""

    conversations: List[ConversationInfo] = Field(default_factory=list)
    total_count: int = 0


# ---------------------------------------------------------------------------
# Health / Admin
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, Any] = Field(default_factory=dict)
