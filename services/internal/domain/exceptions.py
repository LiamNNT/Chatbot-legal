"""
Re-export canonical exceptions from the shared package.
"""

from shared.domain.exceptions import (        # noqa: F401
    DomainException,
    AgentProcessingError,
    RAGRetrievalError,
    ContextManagementError,
    InvalidRoleError,
)
