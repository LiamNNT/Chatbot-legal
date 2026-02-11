import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..domain.entities import (
    ConversationContext,
    ConversationMessage,
    ConversationRole,
    MessageType,
)
from ..domain.exceptions import InvalidRoleError
from ..ports.conversation_port import ConversationManagerPort

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "user": ConversationRole.USER,
    "assistant": ConversationRole.ASSISTANT,
    "system": ConversationRole.SYSTEM,
}

_DEFAULT_HISTORY_LIMIT = int(os.getenv("DEFAULT_HISTORY_LIMIT", "6"))


class InMemoryConversationManager(ConversationManagerPort):
    def __init__(self, use_redis: bool = False, redis_url: Optional[str] = None):
        self._store: Dict[str, ConversationContext] = {}
        self._use_redis = use_redis
        self._redis_client = None

        if use_redis:
            self._init_redis(redis_url)

    async def create_context(self, session_id: str, system_prompt: Optional[str] = None) -> ConversationContext:
        context = ConversationContext(
            session_id=session_id,
            messages=[],
            system_prompt=system_prompt,
            metadata={"created_at": datetime.now().isoformat()},
        )

        if system_prompt:
            context.add_message(
                ConversationMessage(
                    role=ConversationRole.SYSTEM,
                    content=system_prompt,
                    timestamp=datetime.now(),
                    message_type=MessageType.TEXT,
                )
            )

        self._store[session_id] = context
        self._persist(session_id, context)
        logger.debug("Created context for session %s", session_id)
        return context

    async def get_context(self, session_id: str) -> Optional[ConversationContext]:
        ctx = self._store.get(session_id)
        if ctx is None and self._use_redis:
            ctx = self._load_from_redis(session_id)
            if ctx:
                self._store[session_id] = ctx
        return ctx

    async def save_context(self, context: ConversationContext) -> None:
        self._store[context.session_id] = context
        self._persist(context.session_id, context)

    async def delete_context(self, session_id: str) -> bool:
        existed = session_id in self._store
        self._store.pop(session_id, None)

        if self._use_redis and self._redis_client:
            self._redis_client.delete(self._redis_key(session_id))

        return existed

    async def add_message(self, session_id: str, role: str, content: str) -> bool:
        conv_role = _ROLE_MAP.get(role.lower())
        if conv_role is None:
            raise InvalidRoleError(role)

        context = self._store.get(session_id)
        if not context:
            return False

        context.add_message(
            ConversationMessage(
                role=conv_role,
                content=content,
                timestamp=datetime.now(),
                message_type=MessageType.TEXT,
            )
        )
        self._persist(session_id, context)
        return True

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        limit = limit or _DEFAULT_HISTORY_LIMIT
        context = await self.get_context(session_id)
        if not context or not context.messages:
            return []

        all_msgs = [
            {"role": m.role.value, "content": m.content}
            for m in context.messages
        ]
        system = [m for m in all_msgs if m["role"] == "system"]
        others = [m for m in all_msgs if m["role"] != "system"]
        recent = others[-limit:] if len(others) > limit else others
        return system + recent

    def _init_redis(self, redis_url: Optional[str] = None) -> None:
        try:
            import redis

            url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
            self._redis_client = redis.from_url(url, decode_responses=True)
            self._redis_client.ping()
            logger.info("Redis connected for conversation storage")
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — falling back to in-memory", exc)
            self._use_redis = False

    @staticmethod
    def _redis_key(session_id: str) -> str:
        return f"conversation:{session_id}"

    def _persist(self, session_id: str, context: ConversationContext) -> None:
        """Save to Redis if available."""
        if not (self._use_redis and self._redis_client):
            return
        try:
            data = {
                "session_id": session_id,
                "system_prompt": context.system_prompt,
                "messages": [
                    {
                        "role": m.role.value,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    }
                    for m in context.messages
                ],
                "metadata": context.metadata,
            }
            self._redis_client.setex(
                self._redis_key(session_id),
                86400,  # 24 h TTL
                json.dumps(data),
            )
        except Exception as exc:
            logger.error("Failed to persist to Redis: %s", exc)

    def _load_from_redis(self, session_id: str) -> Optional[ConversationContext]:
        if not self._redis_client:
            return None
        try:
            raw = self._redis_client.get(self._redis_key(session_id))
            if not raw:
                return None

            data = json.loads(raw)
            messages = [
                ConversationMessage(
                    role=_ROLE_MAP.get(m["role"], ConversationRole.USER),
                    content=m["content"],
                    timestamp=(
                        datetime.fromisoformat(m["timestamp"])
                        if m.get("timestamp")
                        else datetime.now()
                    ),
                    message_type=MessageType.TEXT,
                )
                for m in data.get("messages", [])
            ]
            return ConversationContext(
                session_id=session_id,
                messages=messages,
                system_prompt=data.get("system_prompt"),
                metadata=data.get("metadata", {}),
            )
        except Exception as exc:
            logger.error("Failed to load from Redis: %s", exc)
            return None

    # ── Utility ──────────────────────────────────

    def get_active_sessions(self) -> List[str]:
        return list(self._store.keys())

    async def cleanup_old_contexts(self, max_age_hours: int = 24) -> int:
        now = datetime.now()
        to_remove = []
        for sid, ctx in self._store.items():
            created = ctx.metadata.get("created_at") if ctx.metadata else None
            if created:
                try:
                    age_h = (now - datetime.fromisoformat(created)).total_seconds() / 3600
                    if age_h > max_age_hours:
                        to_remove.append(sid)
                except (ValueError, TypeError):
                    to_remove.append(sid)

        for sid in to_remove:
            await self.delete_context(sid)
        return len(to_remove)
