"""
Dependency injection container for orchestrator service.

The ServiceContainer composes three focused provider mixins:
- **PortProviderMixin**           — LLM, RAG, conversation ports
- **GraphProviderMixin**          — Neo4j, symbolic reasoning
- **OrchestrationProviderMixin**  — orchestration services, multi-agent, LangGraph

This file owns only:
1. The ``ServiceContainer`` class (init + cleanup)
2. Global singleton management / convenience functions
"""

import logging
from typing import Optional

from .port_providers import PortProviderMixin
from .graph_providers import GraphProviderMixin
from .orchestration_providers import OrchestrationProviderMixin

logger = logging.getLogger(__name__)


class ServiceContainer(
    PortProviderMixin,
    GraphProviderMixin,
    OrchestrationProviderMixin,
):
    """Composition-root DI container built from focused provider mixins."""

    def __init__(self, config_path: Optional[str] = None):
        # Port fields
        self._agent_port = None
        self._rag_port = None
        self._conversation_manager = None

        # Graph fields
        self._graph_adapter = None
        self._symbolic_graph_extension = None
        self._symbolic_reasoning_engine = None

        # Orchestration fields
        self._orchestration_service = None
        self._multi_agent_orchestrator = None
        self._langgraph_orchestrator = None
        self._config_manager = None
        self._agent_factory = None

        # Configuration
        self._config_path = config_path

    async def cleanup(self) -> None:
        """Release external resources and reset all cached instances."""
        if self._agent_port and hasattr(self._agent_port, "close"):
            await self._agent_port.close()
        if self._rag_port and hasattr(self._rag_port, "close"):
            await self._rag_port.close()

        # Reset all fields
        for attr in list(vars(self)):
            if attr.startswith("_") and attr != "_config_path":
                setattr(self, attr, None)


# ── Global singleton ──────────────────────────────────────────────────

_container: Optional[ServiceContainer] = None


def get_container(config_path: Optional[str] = None) -> ServiceContainer:
    global _container
    if _container is None:
        _container = ServiceContainer(config_path)
    return _container


def get_orchestration_service():
    return get_container().get_orchestration_service()


def get_multi_agent_orchestrator():
    return get_container().get_multi_agent_orchestrator()


def get_langgraph_orchestrator():
    return get_container().get_langgraph_orchestrator()


def get_symbolic_reasoning_engine():
    return get_container().get_symbolic_reasoning_engine()


def get_symbolic_graph_extension():
    return get_container().get_symbolic_graph_extension()


async def cleanup_container() -> None:
    global _container
    if _container:
        await _container.cleanup()
        _container = None