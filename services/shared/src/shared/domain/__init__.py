"""
Shared domain layer — canonical definitions of entities, value objects,
RAG models, and exceptions.
"""

from .entities import (
    ConversationRole,
    MessageType,
    AgentProvider,
    ConversationMessage,
    ConversationContext,
    RAGContext,
)
from .value_objects import (
    AgentRequest,
    AgentResponse,
    OrchestrationRequest,
    OrchestrationResponse,
)
from .exceptions import (
    DomainException,
    AgentProcessingError,
    RAGRetrievalError,
    ContextManagementError,
    InvalidRoleError,
    OrchestrationDomainException,
    AgentProcessingFailedException,
    RAGRetrievalFailedException,
    ContextManagementFailedException,
)
from .rag_models import (
    SearchMode,
    DocumentLanguage,
    CharacterSpan,
    DocumentMetadata,
    SearchFilters,
    RerankingMetadata,
    SearchQuery,
    SearchResult,
    SearchResponse,
    Document,
    DocumentChunk,
)

__all__ = [
    # Entities
    "ConversationRole",
    "MessageType",
    "AgentProvider",
    "ConversationMessage",
    "ConversationContext",
    "RAGContext",
    # Value objects
    "AgentRequest",
    "AgentResponse",
    "OrchestrationRequest",
    "OrchestrationResponse",
    # Exceptions
    "DomainException",
    "AgentProcessingError",
    "RAGRetrievalError",
    "ContextManagementError",
    "InvalidRoleError",
    "OrchestrationDomainException",
    "AgentProcessingFailedException",
    "RAGRetrievalFailedException",
    "ContextManagementFailedException",
    # RAG models
    "SearchMode",
    "DocumentLanguage",
    "CharacterSpan",
    "DocumentMetadata",
    "SearchFilters",
    "RerankingMetadata",
    "SearchQuery",
    "SearchResult",
    "SearchResponse",
    "Document",
    "DocumentChunk",
]
