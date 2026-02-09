

from typing import Optional, Dict, Any


class OrchestrationDomainException(Exception):
    def __init__(self, error_code: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(error_code)


class AgentProcessingFailedException(OrchestrationDomainException):
    def __init__(self, agent_error: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            error_code="AGENT_PROCESSING_FAILED",
            details={
                "agent_error": agent_error,
                **(details or {})
            },
            cause=cause
        )


class RAGRetrievalFailedException(OrchestrationDomainException):
    def __init__(self, rag_error: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            error_code="RAG_RETRIEVAL_FAILED", 
            details={
                "rag_error": rag_error,
                **(details or {})
            },
            cause=cause
        )


class ContextManagementFailedException(OrchestrationDomainException):
    def __init__(self, context_error: str, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(
            error_code="CONTEXT_MANAGEMENT_FAILED",
            details={
                "context_error": context_error,
                **(details or {})
            },
            cause=cause
        )