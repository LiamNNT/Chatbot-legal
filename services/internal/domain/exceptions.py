from typing import Any, Dict, Optional


class DomainException(Exception):
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
