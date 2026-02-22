"""
Shared domain exceptions — canonical definitions.

Includes both the base ``DomainException`` hierarchy (used by internal /
rag_services) and the ``OrchestrationDomainException`` hierarchy (used by
the orchestrator service).
"""

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Base hierarchy (originally in services/internal)
# ---------------------------------------------------------------------------

class DomainException(Exception):
    """Base class for all domain-level exceptions."""

    def __init__(
        self,
        message: str,
        error_code: str = "DOMAIN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(message)


class AgentProcessingError(DomainException):
    def __init__(
        self,
        message: str = "Agent processing failed",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="AGENT_PROCESSING_FAILED",
            details=details,
            cause=cause,
        )


class RAGRetrievalError(DomainException):
    def __init__(
        self,
        message: str = "RAG retrieval failed",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="RAG_RETRIEVAL_FAILED",
            details=details,
            cause=cause,
        )


class ContextManagementError(DomainException):
    def __init__(
        self,
        message: str = "Context management failed",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONTEXT_MANAGEMENT_FAILED",
            details=details,
            cause=cause,
        )


class InvalidRoleError(DomainException):
    def __init__(self, role: str):
        super().__init__(
            message=f"Invalid conversation role: '{role}'",
            error_code="INVALID_ROLE",
            details={"role": role},
        )


# ---------------------------------------------------------------------------
# Orchestration hierarchy (originally in services/orchestrator)
# ---------------------------------------------------------------------------

class OrchestrationDomainException(Exception):
    """Base class for orchestration-specific domain exceptions."""

    def __init__(
        self,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        super().__init__(error_code)


class AgentProcessingFailedException(OrchestrationDomainException):
    def __init__(
        self,
        agent_error: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code="AGENT_PROCESSING_FAILED",
            details={"agent_error": agent_error, **(details or {})},
            cause=cause,
        )


class RAGRetrievalFailedException(OrchestrationDomainException):
    def __init__(
        self,
        rag_error: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code="RAG_RETRIEVAL_FAILED",
            details={"rag_error": rag_error, **(details or {})},
            cause=cause,
        )


class ContextManagementFailedException(OrchestrationDomainException):
    def __init__(
        self,
        context_error: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code="CONTEXT_MANAGEMENT_FAILED",
            details={"context_error": context_error, **(details or {})},
            cause=cause,
        )
