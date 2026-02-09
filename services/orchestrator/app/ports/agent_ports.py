from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator, Any
from ..core.domain.domain import (
    AgentRequest, 
    AgentResponse, 
    ConversationContext,
)


class AgentPort(ABC):
    @abstractmethod
    async def generate_response(self, request: AgentRequest) -> AgentResponse:
        pass
    
    @abstractmethod
    async def stream_response(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        pass

class ConversationManagerPort(ABC):
    @abstractmethod
    async def create_context(self, session_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        pass
    
    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        pass
    
    @abstractmethod
    async def update_context(self, context: ConversationContext) -> None:
        pass
    
    @abstractmethod
    async def delete_context(self, session_id: str) -> bool:
        pass


class RAGServicePort(ABC):
    @abstractmethod
    async def retrieve_context(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Any] = None,
        search_mode: str = "hybrid",
        use_rerank: bool = True,
        need_citation: bool = True,
        include_char_spans: bool = True
    ) -> dict:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass