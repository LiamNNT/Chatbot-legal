"""
Re-export canonical domain models from the shared package.

All definitions now live in ``shared.domain``.  This module exists only
for backward-compatibility so that existing relative imports like
``from ..domain.domain import AgentRequest`` keep working.
"""

from shared.domain.entities import (          # noqa: F401
    ConversationRole,
    MessageType,
    AgentProvider,
    ConversationMessage,
    ConversationContext,
    RAGContext,
)
from shared.domain.value_objects import (     # noqa: F401
    AgentRequest,
    AgentResponse,
    OrchestrationRequest,
    OrchestrationResponse,
)