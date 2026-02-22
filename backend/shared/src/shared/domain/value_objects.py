"""
Shared domain value objects — canonical definitions.

NOTE: AgentRequest / AgentResponse are intentionally *not* frozen
because the orchestrator service mutates them at runtime (e.g. attaching
metadata, overriding model). If immutability is desired in a specific
service, wrap them in a frozen subclass there.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .entities import ConversationContext, RAGContext


@dataclass
class AgentRequest:
    """Request to an agent service."""
    prompt: str
    context: Optional[ConversationContext] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AgentResponse:
    """Response from an agent service."""
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrchestrationRequest:
    """Complete request for the orchestration pipeline."""
    user_query: str
    session_id: Optional[str] = None
    use_rag: bool = True
    use_knowledge_graph: Optional[bool] = None
    rag_top_k: int = 5
    agent_model: Optional[str] = None
    conversation_context: Optional[ConversationContext] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrchestrationResponse:
    """Complete response from the orchestration pipeline."""
    response: str
    session_id: str
    rag_context: Optional[RAGContext] = None
    agent_metadata: Optional[Dict[str, Any]] = None
    processing_stats: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
