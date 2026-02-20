"""
Re-export canonical entities from the shared package.

All definitions now live in ``shared.domain.entities``.  This module
exists only for backward-compatibility so that existing imports like
``from ..domain.entities import ConversationRole`` keep working.
"""

from shared.domain.entities import (          # noqa: F401
    ConversationRole,
    MessageType,
    AgentProvider,
    ConversationMessage,
    ConversationContext,
    RAGContext,
)
