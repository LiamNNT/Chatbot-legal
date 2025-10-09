"""
Port interfaces for agent services.

These interfaces define the contracts that agent adapters must implement,
following the Ports & Adapters architecture pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator
from ..core.domain import (
    AgentRequest, 
    AgentResponse, 
    ConversationContext,
    AgentProvider
)


class AgentPort(ABC):
    """
    Port interface for agent communication services.
    
    This interface defines the contract for communicating with LLM agents,
    abstracting away the specific implementation details of different providers.
    """
    
    @abstractmethod
    async def generate_response(self, request: AgentRequest) -> AgentResponse:
        """
        Generate a response from the agent.
        
        Args:
            request: The agent request containing prompt and context
            
        Returns:
            AgentResponse containing the generated response and metadata
        """
        pass
    
    @abstractmethod
    async def stream_response(self, request: AgentRequest) -> AsyncGenerator[str, None]:
        """
        Stream a response from the agent.
        
        Args:
            request: The agent request containing prompt and context
            
        Yields:
            String chunks of the response as they are generated
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate that the agent service is available and accessible.
        
        Returns:
            True if the service is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """
        Get the list of models supported by this agent provider.
        
        Returns:
            List of model names/identifiers
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> AgentProvider:
        """
        Get information about the agent provider.
        
        Returns:
            AgentProvider enum indicating the provider type
        """
        pass


class ConversationManagerPort(ABC):
    """
    Port interface for managing conversation contexts and sessions.
    """
    
    @abstractmethod
    async def create_context(self, session_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        """
        Create a new conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            system_prompt: Optional system prompt to initialize the conversation
            
        Returns:
            New ConversationContext instance
        """
        pass
    
    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """
        Retrieve an existing conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            ConversationContext if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_context(self, context: ConversationContext) -> None:
        """
        Update/save a conversation context.
        
        Args:
            context: The conversation context to update
        """
        pass
    
    @abstractmethod
    async def delete_context(self, session_id: str) -> bool:
        """
        Delete a conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass


class RAGServicePort(ABC):
    """
    Port interface for RAG (Retrieval-Augmented Generation) services.
    """
    
    @abstractmethod
    async def retrieve_context(self, query: str, top_k: int = 5) -> dict:
        """
        Retrieve relevant context for a query using the RAG system.
        
        Args:
            query: The user query to search for relevant documents
            top_k: Number of top relevant documents to retrieve
            
        Returns:
            Dictionary containing retrieved documents and metadata
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the RAG service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        pass