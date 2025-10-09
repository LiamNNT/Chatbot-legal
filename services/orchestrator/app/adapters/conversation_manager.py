"""
In-memory conversation manager adapter.

This adapter provides conversation context management using in-memory storage.
For production use, this should be replaced with a persistent storage solution.
"""

from typing import Dict, Optional
from datetime import datetime
from ..ports.agent_ports import ConversationManagerPort
from ..core.domain import ConversationContext, ConversationMessage, ConversationRole, MessageType


class InMemoryConversationManagerAdapter(ConversationManagerPort):
    """
    In-memory implementation of conversation manager.
    
    This adapter stores conversation contexts in memory. For production use,
    consider implementing a persistent storage adapter (Redis, Database, etc.).
    """
    
    def __init__(self):
        """Initialize the conversation manager."""
        self._contexts: Dict[str, ConversationContext] = {}
    
    async def create_context(
        self, 
        session_id: str, 
        system_prompt: Optional[str] = None
    ) -> ConversationContext:
        """
        Create a new conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            system_prompt: Optional system prompt to initialize the conversation
            
        Returns:
            New ConversationContext instance
        """
        context = ConversationContext(
            session_id=session_id,
            messages=[],
            system_prompt=system_prompt,
            max_tokens=None,
            temperature=0.7,
            metadata={"created_at": datetime.now().isoformat()}
        )
        
        # Add system message if system prompt is provided
        if system_prompt:
            system_message = ConversationMessage(
                role=ConversationRole.SYSTEM,
                content=system_prompt,
                timestamp=datetime.now(),
                message_type=MessageType.TEXT
            )
            context.add_message(system_message)
        
        self._contexts[session_id] = context
        return context
    
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """
        Retrieve an existing conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            ConversationContext if found, None otherwise
        """
        return self._contexts.get(session_id)
    
    async def update_context(self, context: ConversationContext) -> None:
        """
        Update/save a conversation context.
        
        Args:
            context: The conversation context to update
        """
        # Update metadata
        if context.metadata is None:
            context.metadata = {}
        context.metadata["updated_at"] = datetime.now().isoformat()
        
        # Store the updated context
        self._contexts[context.session_id] = context
    
    async def delete_context(self, session_id: str) -> bool:
        """
        Delete a conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
            return True
        return False
    
    async def add_message_to_context(
        self, 
        session_id: str, 
        message: ConversationMessage
    ) -> Optional[ConversationContext]:
        """
        Add a message to an existing conversation context.
        
        Args:
            session_id: Unique identifier for the conversation session
            message: The message to add
            
        Returns:
            Updated ConversationContext if session exists, None otherwise
        """
        context = await self.get_context(session_id)
        if context:
            context.add_message(message)
            await self.update_context(context)
            return context
        return None
    
    def get_active_sessions(self) -> list[str]:
        """
        Get list of active session IDs.
        
        Returns:
            List of active session IDs
        """
        return list(self._contexts.keys())
    
    def get_context_count(self) -> int:
        """
        Get the number of active contexts.
        
        Returns:
            Number of active conversation contexts
        """
        return len(self._contexts)
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
        """
        Clean up old conversation contexts.
        
        Args:
            max_age_hours: Maximum age in hours before a context is considered old
            
        Returns:
            Number of contexts that were cleaned up
        """
        current_time = datetime.now()
        contexts_to_remove = []
        
        for session_id, context in self._contexts.items():
            if context.metadata and "created_at" in context.metadata:
                try:
                    created_at = datetime.fromisoformat(context.metadata["created_at"])
                    age_hours = (current_time - created_at).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        contexts_to_remove.append(session_id)
                except (ValueError, KeyError):
                    # If we can't parse the timestamp, consider it old
                    contexts_to_remove.append(session_id)
        
        # Remove old contexts
        for session_id in contexts_to_remove:
            await self.delete_context(session_id)
        
        return len(contexts_to_remove)