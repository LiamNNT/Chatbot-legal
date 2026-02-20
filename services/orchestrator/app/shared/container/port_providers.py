"""
Port provider methods for the orchestrator DI container.

Provides creation / caching of the three primary ports:
- AgentPort (OpenRouter LLM adapter)
- RAGServicePort (HTTP adapter to rag_services)
- ConversationManagerPort (in-memory, swappable to Redis / DB)
"""

import os
import logging
from typing import Optional

from ...shared.ports import AgentPort, RAGServicePort, ConversationManagerPort
from ...chat.adapters.openrouter_adapter import OpenRouterAdapter
from ...chat.adapters.rag_adapter import RAGServiceAdapter
from ...conversation.conversation_manager import InMemoryConversationManagerAdapter

logger = logging.getLogger(__name__)


class PortProviderMixin:
    """Mixin that adds port-creation methods to a ServiceContainer."""

    _agent_port: Optional[AgentPort]
    _rag_port: Optional[RAGServicePort]
    _conversation_manager: Optional[ConversationManagerPort]

    # ------------------------------------------------------------------
    # Agent (LLM)
    # ------------------------------------------------------------------
    def get_agent_port(self) -> AgentPort:
        if self._agent_port is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required")

            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            default_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-3.5-turbo")
            timeout_env = os.getenv("OPENROUTER_TIMEOUT", "30")
            timeout = None if timeout_env.lower() == "none" else int(timeout_env)
            max_retries = int(os.getenv("OPENROUTER_MAX_RETRIES", "3"))

            self._agent_port = OpenRouterAdapter(
                api_key=api_key,
                base_url=base_url,
                default_model=default_model,
                timeout=timeout,
                max_retries=max_retries,
            )
        return self._agent_port

    # ------------------------------------------------------------------
    # RAG
    # ------------------------------------------------------------------
    def get_rag_port(self) -> RAGServicePort:
        if self._rag_port is None:
            rag_service_url = os.getenv("RAG_SERVICE_URL", "http://localhost:8000")
            timeout_env = os.getenv("RAG_SERVICE_TIMEOUT", "60")
            timeout = None if timeout_env.lower() == "none" else int(timeout_env)
            max_retries = int(os.getenv("RAG_SERVICE_MAX_RETRIES", "3"))

            self._rag_port = RAGServiceAdapter(
                rag_service_url=rag_service_url,
                timeout=timeout,
                max_retries=max_retries,
            )
        return self._rag_port

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------
    def get_conversation_manager(self) -> ConversationManagerPort:
        if self._conversation_manager is None:
            # Swap to Redis / DB implementation here when ready
            self._conversation_manager = InMemoryConversationManagerAdapter()
        return self._conversation_manager
