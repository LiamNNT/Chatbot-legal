"""
Shared domain entities — canonical definitions.

These are the ONLY authoritative definitions. Every service must
import from here (directly or via re-export wrappers).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ConversationRole(Enum):
    """Roles in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(Enum):
    """Types of messages in the conversation."""
    TEXT = "text"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"


class AgentProvider(Enum):
    """Supported agent providers."""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    role: ConversationRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "metadata": self.metadata or {},
        }


@dataclass
class ConversationContext:
    """Context for a conversation session."""
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    metadata: Optional[Dict[str, Any]] = None

    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)

    def get_recent_messages(self, count: int) -> List[ConversationMessage]:
        """Get the most recent N messages."""
        return self.messages[-count:] if count < len(self.messages) else list(self.messages)


@dataclass
class RAGContext:
    """Context from RAG system to be used in agent requests."""
    query: str
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    search_metadata: Optional[Dict[str, Any]] = None
    relevance_scores: Optional[List[float]] = None
    rewritten_queries: Optional[List[str]] = None
