"""
Orchestration provider methods for the orchestrator DI container.

Provides creation / caching of:
- OrchestrationService  (simple single-agent pipeline)
- OptimizedMultiAgentOrchestrator  (multi-agent pipeline)
- LangGraph orchestrator  (optional stateful orchestration)
- IRCoT configuration
"""

import os
import logging
from typing import Optional

from ...chat.services.orchestration_service import OrchestrationService
from ...chat.agents.orchestrator import OptimizedMultiAgentOrchestrator
from ..config.config_manager import ConfigurationManager, get_config_manager
from .agent_factory import AgentFactory, ConfigurableAgentFactory, get_agent_factory
from ..config.ircot_config import IRCoTConfig, IRCoTMode

logger = logging.getLogger(__name__)


class OrchestrationProviderMixin:
    """Mixin that adds orchestration-service methods to a ServiceContainer."""

    _orchestration_service: Optional[OrchestrationService]
    _multi_agent_orchestrator: Optional[OptimizedMultiAgentOrchestrator]
    _langgraph_orchestrator: Optional[object]
    _config_manager: Optional[ConfigurationManager]
    _agent_factory: Optional[AgentFactory]
    _config_path: Optional[str]

    # provided by other mixins — declared for type-checker
    def get_agent_port(self): ...   # pragma: no cover
    def get_rag_port(self): ...     # pragma: no cover
    def get_conversation_manager(self): ...  # pragma: no cover
    def get_graph_adapter(self): ...  # pragma: no cover
    def get_symbolic_reasoning_engine(self): ...  # pragma: no cover

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def get_config_manager(self) -> ConfigurationManager:
        if self._config_manager is None:
            self._config_manager = ConfigurationManager(self._config_path)
        return self._config_manager

    def get_agent_factory(self) -> AgentFactory:
        if self._agent_factory is None:
            self._agent_factory = ConfigurableAgentFactory(self.get_config_manager())
        return self._agent_factory

    # ------------------------------------------------------------------
    # Simple orchestration
    # ------------------------------------------------------------------
    def get_orchestration_service(self) -> OrchestrationService:
        if self._orchestration_service is None:
            default_system_prompt = os.getenv("DEFAULT_SYSTEM_PROMPT")
            ircot_config = self._create_ircot_config()
            langgraph_orchestrator = self.get_langgraph_orchestrator()

            self._orchestration_service = OrchestrationService(
                agent_port=self.get_agent_port(),
                rag_port=self.get_rag_port(),
                conversation_manager=self.get_conversation_manager(),
                default_system_prompt=default_system_prompt,
                ircot_config=ircot_config,
                langgraph_orchestrator=langgraph_orchestrator,
            )

            if langgraph_orchestrator:
                logger.info("✓ OrchestrationService created with LangGraph IRCoT support")
            else:
                logger.info("⚠ OrchestrationService created without LangGraph (standard mode)")

        return self._orchestration_service

    # ------------------------------------------------------------------
    # Multi-agent orchestration
    # ------------------------------------------------------------------
    def get_multi_agent_orchestrator(self) -> OptimizedMultiAgentOrchestrator:
        if self._multi_agent_orchestrator is None:
            config_manager = self.get_config_manager()
            system_config = config_manager.get_system_config()

            enable_verification = os.getenv("ENABLE_VERIFICATION")
            enable_verification = (
                enable_verification.lower() == "true"
                if enable_verification is not None
                else system_config.enable_verification
            )

            enable_planning = os.getenv("ENABLE_PLANNING")
            enable_planning = (
                enable_planning.lower() == "true"
                if enable_planning is not None
                else system_config.enable_planning
            )

            ircot_config = self._create_ircot_config()
            graph_adapter = self.get_graph_adapter()

            react_model = os.getenv("GRAPH_REACT_MODEL", None)
            if not react_model:
                try:
                    react_model_config = config_manager.get_model_config("graph_react_model")
                    if react_model_config:
                        react_model = react_model_config.name
                        logger.info(f"Graph ReAct model from config: {react_model}")
                except Exception as e:
                    logger.debug(f"Could not load Graph ReAct model from config: {e}")

            # --- startup banner ---
            logger.info("=" * 60)
            logger.info("🚀 Using OPTIMIZED orchestrator (3 agents, 40%% cost savings)")
            if ircot_config.enabled:
                logger.info(
                    f"🔄 IRCoT ENABLED: max_iterations={ircot_config.max_iterations}, "
                    f"threshold={ircot_config.complexity_threshold}"
                )
            if graph_adapter:
                react_model_info = f" (model: {react_model})" if react_model else ""
                logger.info(f"🔗 Graph Reasoning ENABLED (Neo4j connected){react_model_info}")
            else:
                logger.info("⚠ Graph Reasoning DISABLED (no graph adapter)")

            symbolic_engine = self.get_symbolic_reasoning_engine()
            if symbolic_engine:
                logger.info(f"🧠 Symbolic Reasoning ENABLED: mode={symbolic_engine.mode.value}")
            else:
                logger.info("⚠ Symbolic Reasoning DISABLED")
            logger.info("=" * 60)

            self._multi_agent_orchestrator = OptimizedMultiAgentOrchestrator(
                agent_port=self.get_agent_port(),
                rag_port=self.get_rag_port(),
                agent_factory=self.get_agent_factory(),
                enable_verification=enable_verification,
                enable_planning=enable_planning,
                graph_adapter=graph_adapter,
                ircot_config=ircot_config,
                react_model=react_model,
            )

        return self._multi_agent_orchestrator

    # ------------------------------------------------------------------
    # IRCoT configuration
    # ------------------------------------------------------------------
    def _create_ircot_config(self) -> IRCoTConfig:
        ircot_enabled = os.getenv("IRCOT_ENABLED", "true").lower() == "true"

        mode_str = os.getenv("IRCOT_MODE", "automatic").lower()
        mode = {"forced": IRCoTMode.FORCED, "disabled": IRCoTMode.DISABLED}.get(
            mode_str, IRCoTMode.AUTOMATIC
        )

        max_iterations = int(os.getenv("IRCOT_MAX_ITERATIONS", "3"))
        complexity_threshold = float(os.getenv("IRCOT_COMPLEXITY_THRESHOLD", "6.5"))
        early_stopping = os.getenv("IRCOT_EARLY_STOPPING", "true").lower() == "true"

        ircot_model = os.getenv("IRCOT_COT_MODEL", None)
        if not ircot_model:
            try:
                config_manager = self.get_config_manager()
                models_config = config_manager.get_model_config("ircot_cot_model")
                if models_config:
                    ircot_model = models_config.name
                    logger.info(f"IRCoT model from config: {ircot_model}")
            except Exception as e:
                logger.debug(f"Could not load IRCoT model from config: {e}")

        config = IRCoTConfig(
            enabled=ircot_enabled,
            mode=mode,
            max_iterations=max_iterations,
            complexity_threshold=complexity_threshold,
            early_stopping_enabled=early_stopping,
            cot_model=ircot_model,
        )
        logger.info(
            f"IRCoT Configuration: enabled={config.enabled}, mode={config.mode.value}, "
            f"max_iter={config.max_iterations}, threshold={config.complexity_threshold}, "
            f"model={config.cot_model or 'default'}"
        )
        return config

    # ------------------------------------------------------------------
    # LangGraph orchestrator (optional)
    # ------------------------------------------------------------------
    def get_langgraph_orchestrator(self):
        if self._langgraph_orchestrator is None:
            use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
            if not use_langgraph:
                logger.info("LangGraph mode is DISABLED. Set USE_LANGGRAPH=true to enable.")
                return None

            try:
                from ...chat.langgraph.workflow import create_langgraph_orchestrator
                from ...chat.services.context_service import ContextDomainService

                ircot_config = self._create_ircot_config()
                graph_adapter = self.get_graph_adapter()
                context_service = ContextDomainService(llm_client=self.get_agent_port())

                enable_checkpointing = (
                    os.getenv("LANGGRAPH_CHECKPOINTING", "false").lower() == "true"
                )

                logger.info("=" * 60)
                logger.info("🚀 Initializing LangGraph Orchestrator")
                logger.info(f"   Checkpointing: {'enabled' if enable_checkpointing else 'disabled'}")
                if graph_adapter:
                    logger.info("   Graph Reasoning: enabled")
                logger.info("=" * 60)

                self._langgraph_orchestrator = create_langgraph_orchestrator(
                    agent_port=self.get_agent_port(),
                    rag_port=self.get_rag_port(),
                    agent_factory=self.get_agent_factory(),
                    graph_adapter=graph_adapter,
                    conversation_manager=self.get_conversation_manager(),
                    context_service=context_service,
                    ircot_config=ircot_config,
                    enable_checkpointing=enable_checkpointing,
                )
                logger.info("✓ LangGraph Orchestrator initialized successfully")

            except ImportError as e:
                logger.warning(f"⚠ Could not import LangGraph: {e}")
                logger.warning("Install with: pip install langgraph langchain-core")
                return None
            except Exception as e:
                logger.warning(f"⚠ Could not initialize LangGraph orchestrator: {e}")
                return None

        return self._langgraph_orchestrator
