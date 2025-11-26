"""
Dependency injection container for orchestrator service.

This module provides dependency injection and service management
following the Ports & Adapters architecture pattern.

Optimized 3-Agent Pipeline:
- SmartPlannerAgent: Planning + Query Rewriting
- AnswerAgent: Answer generation
- ResponseFormatterAgent: Verification + Formatting
"""

import os
import logging
from typing import Optional, Dict, Any
from ..core.orchestration_service import OrchestrationService
from ..agents.optimized_orchestrator import OptimizedMultiAgentOrchestrator
from ..ports.agent_ports import AgentPort, RAGServicePort, ConversationManagerPort
from ..adapters.openrouter_adapter import OpenRouterAdapter
from ..adapters.rag_adapter import RAGServiceAdapter
from ..adapters.conversation_manager import InMemoryConversationManagerAdapter
from ..core.config_manager import ConfigurationManager, get_config_manager
from ..core.agent_factory import AgentFactory, ConfigurableAgentFactory, get_agent_factory

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing service lifecycle.
    
    This container manages the creation and lifecycle of all services
    and their dependencies, ensuring proper separation of concerns.
    
    Uses optimized 3-agent pipeline for cost efficiency.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the container.
        
        Args:
            config_path: Optional path to configuration file
        """
        self._agent_port: Optional[AgentPort] = None
        self._rag_port: Optional[RAGServicePort] = None
        self._conversation_manager: Optional[ConversationManagerPort] = None
        self._orchestration_service: Optional[OrchestrationService] = None
        self._multi_agent_orchestrator: Optional[OptimizedMultiAgentOrchestrator] = None
        self._config_manager: Optional[ConfigurationManager] = None
        self._agent_factory: Optional[AgentFactory] = None
        
        # Initialize configuration
        self._config_path = config_path
    
    def get_agent_port(self) -> AgentPort:
        """
        Get or create the agent port instance.
        
        Returns:
            AgentPort implementation
        """
        if self._agent_port is None:
            # Get configuration from environment
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
                max_retries=max_retries
            )
        
        return self._agent_port
    
    def get_rag_port(self) -> RAGServicePort:
        """
        Get or create the RAG service port instance.
        
        Returns:
            RAGServicePort implementation
        """
        if self._rag_port is None:
            # Get configuration from environment
            rag_service_url = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
            timeout = int(os.getenv("RAG_SERVICE_TIMEOUT", "30"))
            max_retries = int(os.getenv("RAG_SERVICE_MAX_RETRIES", "3"))
            
            self._rag_port = RAGServiceAdapter(
                rag_service_url=rag_service_url,
                timeout=timeout,
                max_retries=max_retries
            )
        
        return self._rag_port
    
    def get_conversation_manager(self) -> ConversationManagerPort:
        """
        Get or create the conversation manager instance.
        
        Returns:
            ConversationManagerPort implementation
        """
        if self._conversation_manager is None:
            # For now, use in-memory implementation
            # In production, this could be replaced with Redis or database implementation
            self._conversation_manager = InMemoryConversationManagerAdapter()
        
        return self._conversation_manager
    
    def get_orchestration_service(self) -> OrchestrationService:
        """
        Get or create the orchestration service instance.
        
        Returns:
            OrchestrationService instance with all dependencies injected
        """
        if self._orchestration_service is None:
            # Get default system prompt from environment
            default_system_prompt = os.getenv("DEFAULT_SYSTEM_PROMPT")
            
            self._orchestration_service = OrchestrationService(
                agent_port=self.get_agent_port(),
                rag_port=self.get_rag_port(),
                conversation_manager=self.get_conversation_manager(),
                default_system_prompt=default_system_prompt
            )
        
        return self._orchestration_service
    
    def get_config_manager(self) -> ConfigurationManager:
        """
        Get or create the configuration manager instance.
        
        Returns:
            ConfigurationManager instance
        """
        if self._config_manager is None:
            self._config_manager = ConfigurationManager(self._config_path)
        return self._config_manager
    
    def get_agent_factory(self) -> AgentFactory:
        """
        Get or create the agent factory instance.
        
        Returns:
            AgentFactory instance
        """
        if self._agent_factory is None:
            self._agent_factory = ConfigurableAgentFactory(self.get_config_manager())
        return self._agent_factory
    
    def get_multi_agent_orchestrator(self) -> OptimizedMultiAgentOrchestrator:
        """
        Get or create the multi-agent orchestrator instance.
        
        Uses OptimizedMultiAgentOrchestrator (3 agents, 40% cost savings).
        
        Returns:
            OptimizedMultiAgentOrchestrator instance with all dependencies injected
        """
        if self._multi_agent_orchestrator is None:
            # Get configuration from config manager
            config_manager = self.get_config_manager()
            system_config = config_manager.get_system_config()
            
            # Override with environment variables if present
            enable_verification = os.getenv("ENABLE_VERIFICATION")
            if enable_verification is not None:
                enable_verification = enable_verification.lower() == "true"
            else:
                enable_verification = system_config.enable_verification
                
            enable_planning = os.getenv("ENABLE_PLANNING")
            if enable_planning is not None:
                enable_planning = enable_planning.lower() == "true"
            else:
                enable_planning = system_config.enable_planning
            
            logger.info("=" * 60)
            logger.info("🚀 Using OPTIMIZED orchestrator (3 agents, 40% cost savings)")
            logger.info("=" * 60)
            
            self._multi_agent_orchestrator = OptimizedMultiAgentOrchestrator(
                agent_port=self.get_agent_port(),
                rag_port=self.get_rag_port(),
                agent_factory=self.get_agent_factory(),
                enable_verification=enable_verification,
                enable_planning=enable_planning
            )
        
        return self._multi_agent_orchestrator
    
    async def cleanup(self) -> None:
        """
        Cleanup resources used by the container.
        
        This method should be called when shutting down the application
        to properly close connections and release resources.
        """
        # Close agent port if it supports cleanup
        if self._agent_port and hasattr(self._agent_port, 'close'):
            await self._agent_port.close()
        
        # Close RAG port if it supports cleanup
        if self._rag_port and hasattr(self._rag_port, 'close'):
            await self._rag_port.close()
        
        # Reset instances
        self._agent_port = None
        self._rag_port = None
        self._conversation_manager = None
        self._orchestration_service = None
        self._multi_agent_orchestrator = None
        self._config_manager = None
        self._agent_factory = None


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container(config_path: Optional[str] = None) -> ServiceContainer:
    """
    Get the global service container instance.
    
    Args:
        config_path: Optional path to configuration file (only used on first call)
    
    Returns:
        ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer(config_path)
    return _container


def get_orchestration_service() -> OrchestrationService:
    """
    Get the orchestration service from the global container.
    
    Returns:
        OrchestrationService instance
    """
    container = get_container()
    return container.get_orchestration_service()


def get_multi_agent_orchestrator() -> OptimizedMultiAgentOrchestrator:
    """
    Get the multi-agent orchestrator from the global container.
    
    Returns:
        OptimizedMultiAgentOrchestrator instance (3 agents, 40% cost savings)
    """
    container = get_container()
    return container.get_multi_agent_orchestrator()


async def cleanup_container() -> None:
    """
    Cleanup the global container.
    
    This function should be called during application shutdown.
    """
    global _container
    if _container:
        await _container.cleanup()
        _container = None