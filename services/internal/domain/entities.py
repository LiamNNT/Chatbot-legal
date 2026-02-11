from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

class ConversationRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(Enum):
    TEXT = "text"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"


class AgentProvider(Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

@dataclass
class ConversationMessage:
    role: ConversationRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value,
            "metadata": self.metadata or {},
        }

@dataclass
class ConversationContext:
    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def add_message(self, message: ConversationMessage) -> None:
        self.messages.append(message)

    def get_recent_messages(self, count: int) -> List[ConversationMessage]:
        return self.messages[-count:] if count < len(self.messages) else list(self.messages)


@dataclass
class RAGContext:
    query: str
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    search_metadata: Optional[Dict[str, Any]] = None
    relevance_scores: Optional[List[float]] = None
    rewritten_queries: Optional[List[str]] = None
