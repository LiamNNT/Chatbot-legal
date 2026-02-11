from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .entities import ConversationContext, RAGContext


@dataclass(frozen=True)
class AgentRequest:
    prompt: str
    context: Optional[ConversationContext] = None
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class AgentResponse:
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class OrchestrationRequest:
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
    response: str
    session_id: str
    rag_context: Optional[RAGContext] = None
    agent_metadata: Optional[Dict[str, Any]] = None
    processing_stats: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
