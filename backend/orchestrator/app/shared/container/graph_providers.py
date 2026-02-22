"""
Graph / symbolic-reasoning provider methods for the orchestrator DI container.

Provides creation / caching of:
- Neo4j Graph Adapter (for knowledge-graph queries)
- SymbolicGraphExtension
- SymbolicReasoningEngine
"""

import os
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Ensure backend/ is on sys.path so we can import rag as a proper package
_BACKEND_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _get_symbolic_reasoning_engine():
    """Lazy import to avoid circular dependencies."""
    from ...reasoning.symbolic_engine import SymbolicReasoningEngine, ReasoningMode
    from ...reasoning.symbolic_graph_extension import SymbolicGraphExtension
    return SymbolicReasoningEngine, ReasoningMode, SymbolicGraphExtension


class GraphProviderMixin:
    """Mixin that adds graph / symbolic-reasoning methods to a ServiceContainer."""

    _graph_adapter: Optional[object]
    _symbolic_graph_extension: Optional[object]
    _symbolic_reasoning_engine: Optional[object]

    # provided by PortProviderMixin — declared here for type-checker
    def get_agent_port(self): ...  # pragma: no cover

    # ------------------------------------------------------------------
    # Neo4j Graph Adapter
    # ------------------------------------------------------------------
    def get_graph_adapter(self):
        if self._graph_adapter is None:
            enable_graph = os.getenv("ENABLE_GRAPH_REASONING", "true").lower() == "true"
            if not enable_graph:
                logger.info("Graph Reasoning is DISABLED by environment variable")
                return None

            try:
                from rag.app.knowledge_graph.stores.neo4j_store import Neo4jGraphAdapter

                neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                neo4j_user = os.getenv("NEO4J_USER", "neo4j")
                neo4j_password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
                neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

                logger.info(f"🔗 Connecting to Neo4j: {neo4j_uri}")
                self._graph_adapter = Neo4jGraphAdapter(
                    uri=neo4j_uri,
                    username=neo4j_user,
                    password=neo4j_password,
                    database=neo4j_database,
                )
                logger.info("✓ Neo4j Graph Adapter initialized successfully")

            except ImportError as e:
                logger.warning(f"⚠ Could not import Neo4jGraphAdapter: {e}")
                logger.warning("Graph Reasoning will be DISABLED")
                return None
            except Exception as e:
                logger.warning(f"⚠ Could not connect to Neo4j: {e}")
                logger.warning("Graph Reasoning will be DISABLED")
                return None

        return self._graph_adapter

    # ------------------------------------------------------------------
    # Symbolic Graph Extension
    # ------------------------------------------------------------------
    def get_symbolic_graph_extension(self):
        if self._symbolic_graph_extension is None:
            graph_adapter = self.get_graph_adapter()
            if not graph_adapter:
                logger.info("Graph adapter not available, symbolic extension disabled")
                return None

            try:
                _, _, SymbolicGraphExtension = _get_symbolic_reasoning_engine()
                self._symbolic_graph_extension = SymbolicGraphExtension(graph_adapter)
                logger.info("✓ Symbolic Graph Extension initialized")
            except ImportError as e:
                logger.warning(f"⚠ Could not import SymbolicGraphExtension: {e}")
                return None
            except Exception as e:
                logger.warning(f"⚠ Could not initialize Symbolic Graph Extension: {e}")
                return None

        return self._symbolic_graph_extension

    # ------------------------------------------------------------------
    # Symbolic Reasoning Engine
    # ------------------------------------------------------------------
    def get_symbolic_reasoning_engine(self):
        if self._symbolic_reasoning_engine is None:
            enable_symbolic = os.getenv("ENABLE_SYMBOLIC_REASONING", "true").lower() == "true"
            if not enable_symbolic:
                logger.info("Symbolic Reasoning is DISABLED by environment variable")
                return None

            symbolic_ext = self.get_symbolic_graph_extension()
            graph_adapter = symbolic_ext or self.get_graph_adapter()
            if not graph_adapter:
                logger.warning("No graph adapter available for symbolic reasoning")
                return None

            try:
                SymbolicReasoningEngine, ReasoningMode, _ = _get_symbolic_reasoning_engine()

                mode_str = os.getenv("SYMBOLIC_REASONING_MODE", "hybrid").lower()
                mode = {
                    "rule_based": ReasoningMode.RULE_BASED,
                    "react": ReasoningMode.REACT,
                }.get(mode_str, ReasoningMode.HYBRID)

                llm_port = self.get_agent_port() if mode != ReasoningMode.RULE_BASED else None

                self._symbolic_reasoning_engine = SymbolicReasoningEngine(
                    graph_adapter=graph_adapter,
                    mode=mode,
                    llm_port=llm_port,
                )
                logger.info(f"✓ Symbolic Reasoning Engine initialized: mode={mode.value}")

            except ImportError as e:
                logger.warning(f"⚠ Could not import SymbolicReasoningEngine: {e}")
                return None
            except Exception as e:
                logger.warning(f"⚠ Could not initialize Symbolic Reasoning Engine: {e}")
                return None

        return self._symbolic_reasoning_engine
