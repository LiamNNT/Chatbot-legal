import os
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from ..ports.agent_ports import ConversationManagerPort
from ..core.domain.domain import ConversationContext, ConversationMessage, ConversationRole, MessageType

logger = logging.getLogger(__name__)

# Configuration constants
MAX_MESSAGES_PER_SESSION = int(os.getenv("MAX_MESSAGES_PER_SESSION", "20"))
DEFAULT_HISTORY_LIMIT = int(os.getenv("DEFAULT_HISTORY_LIMIT", "6"))


class InMemoryConversationManagerAdapter(ConversationManagerPort):
    """
    In-memory implementation of conversation manager with Sliding Window memory.
    
    This adapter stores conversation contexts in memory with automatic pruning
    to prevent indefinite growth. Each session keeps at most MAX_MESSAGES_PER_SESSION
    messages.
    
    Features:
    - Sliding window memory (max 20 messages per session by default)
    - add_message() for easy message addition
    - get_history() for retrieving formatted message history
    - Automatic pruning of old messages
    - Optional Redis support for persistence
    """
    def __init__(self, max_messages: int = None, use_redis: bool = False, redis_url: str = None):
        self._contexts: Dict[str, ConversationContext] = {}
        self._max_messages = max_messages or MAX_MESSAGES_PER_SESSION
        self._use_redis = use_redis
        self._redis_client = None

        if self._use_redis:
            self._init_redis(redis_url)
        
        logger.info(f"ConversationManager initialized: max_messages={self._max_messages}, use_redis={self._use_redis}")
    
    def _init_redis(self, redis_url: str = None):
        try:
            import redis
            url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis_client = redis.from_url(url, decode_responses=True)
            self._redis_client.ping()
            logger.info("Redis connection established for conversation storage")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory storage.")
            self._use_redis = False
    
    def _get_redis_key(self, session_id: str) -> str:
        return f"conversation:{session_id}"
    
    def _prune_messages(self, context: ConversationContext) -> None:
        if len(context.messages) <= self._max_messages:
            return
        
        # Separate system messages from others
        system_messages = [m for m in context.messages if m.role == ConversationRole.SYSTEM]
        other_messages = [m for m in context.messages if m.role != ConversationRole.SYSTEM]
        
        # Keep only the most recent messages (sliding window)
        max_other = self._max_messages - len(system_messages)
        if len(other_messages) > max_other:
            other_messages = other_messages[-max_other:]
        
        # Rebuild messages list
        context.messages = system_messages + other_messages
        logger.debug(f"Pruned messages for session {context.session_id}: kept {len(context.messages)} messages")  
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        # Map string role to enum
        role_map = {
            "user": ConversationRole.USER,
            "assistant": ConversationRole.ASSISTANT,
            "system": ConversationRole.SYSTEM
        }
        
        conv_role = role_map.get(role.lower())
        if not conv_role:
            logger.warning(f"Invalid role: {role}")
            return False
        
        # Get or create context
        context = self._contexts.get(session_id)
        if not context:
            context = ConversationContext(
                session_id=session_id,
                messages=[],
                metadata={"created_at": datetime.now().isoformat()}
            )
            self._contexts[session_id] = context
        
        # Create and add message
        message = ConversationMessage(
            role=conv_role,
            content=content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        context.add_message(message)
        
        # Apply sliding window pruning
        self._prune_messages(context)
        
        # Update metadata
        if context.metadata is None:
            context.metadata = {}
        context.metadata["updated_at"] = datetime.now().isoformat()
        context.metadata["message_count"] = len(context.messages)
        
        # Save to Redis if configured
        if self._use_redis and self._redis_client:
            self._save_to_redis(session_id, context)
        
        return True
    
    def get_history(self, session_id: str, limit: int = None) -> List[Dict[str, str]]:
        limit = limit or DEFAULT_HISTORY_LIMIT
        
        # Try Redis first if configured
        if self._use_redis and self._redis_client:
            context = self._load_from_redis(session_id)
            if context:
                self._contexts[session_id] = context
        
        context = self._contexts.get(session_id)
        if not context or not context.messages:
            return []
        
        # Convert messages to dict format
        history = []
        for msg in context.messages:
            role_str = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            history.append({
                "role": role_str,
                "content": msg.content
            })
        
        # Return last 'limit' messages (excluding system messages from count)
        # But include system messages in result
        system_msgs = [h for h in history if h["role"] == "system"]
        other_msgs = [h for h in history if h["role"] != "system"]
        
        # Get the most recent messages
        recent_msgs = other_msgs[-limit:] if len(other_msgs) > limit else other_msgs
        
        return system_msgs + recent_msgs
    
    def _save_to_redis(self, session_id: str, context: ConversationContext) -> None:
        try:
            key = self._get_redis_key(session_id)
            data = {
                "session_id": session_id,
                "messages": [
                    {
                        "role": m.role.value if hasattr(m.role, 'value') else str(m.role),
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None
                    }
                    for m in context.messages
                ],
                "metadata": context.metadata
            }
            self._redis_client.setex(key, 86400, json.dumps(data))  # 24h TTL
        except Exception as e:
            logger.error(f"Failed to save to Redis: {e}")
    
    def _load_from_redis(self, session_id: str) -> Optional[ConversationContext]:
        try:
            key = self._get_redis_key(session_id)
            data = self._redis_client.get(key)
            if not data:
                return None
            
            data = json.loads(data)
            context = ConversationContext(
                session_id=session_id,
                messages=[],
                metadata=data.get("metadata", {})
            )
            
            role_map = {
                "user": ConversationRole.USER,
                "assistant": ConversationRole.ASSISTANT,
                "system": ConversationRole.SYSTEM
            }
            
            for msg_data in data.get("messages", []):
                role = role_map.get(msg_data["role"], ConversationRole.USER)
                timestamp = datetime.fromisoformat(msg_data["timestamp"]) if msg_data.get("timestamp") else datetime.now()
                msg = ConversationMessage(
                    role=role,
                    content=msg_data["content"],
                    timestamp=timestamp,
                    message_type=MessageType.TEXT
                )
                context.messages.append(msg)
            
            return context
        except Exception as e:
            logger.error(f"Failed to load from Redis: {e}")
            return None
    
    async def create_context(self, session_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        context = ConversationContext(
            session_id=session_id,
            messages=[],
            system_prompt=system_prompt,
            max_tokens=None,
            temperature=0.7,
            metadata={
                "created_at": datetime.now().isoformat(),
                "max_messages": self._max_messages
            }
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
        
        # Save to Redis if configured
        if self._use_redis and self._redis_client:
            self._save_to_redis(session_id, context)
        
        logger.debug(f"Created new context for session {session_id}")
        return context
    
    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        return self._contexts.get(session_id)
    
    async def update_context(self, context: ConversationContext) -> None:
        # Apply sliding window pruning
        self._prune_messages(context)
        
        # Update metadata
        if context.metadata is None:
            context.metadata = {}
        context.metadata["updated_at"] = datetime.now().isoformat()
        context.metadata["message_count"] = len(context.messages)
        
        # Store the updated context
        self._contexts[context.session_id] = context
        
        # Save to Redis if configured
        if self._use_redis and self._redis_client:
            self._save_to_redis(context.session_id, context)
    
    async def delete_context(self, session_id: str) -> bool:
        if session_id in self._contexts:
            del self._contexts[session_id]
            return True
        return False
    
    def get_active_sessions(self) -> list[str]:
        return list(self._contexts.keys())
    
    
    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
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