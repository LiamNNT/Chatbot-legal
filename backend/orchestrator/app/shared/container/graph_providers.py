"""
Graph provider methods for the orchestrator DI container.

Provides creation / caching of:
- Neo4j Graph Adapter (for knowledge-graph queries)
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


class GraphProviderMixin:
    """Mixin that adds graph provider methods to a ServiceContainer."""

    _graph_adapter: Optional[object]

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

                neo4j_uri = os.getenv("NEO4J_URI", "")
                neo4j_user = os.getenv("NEO4J_USERNAME", "")
                neo4j_password = os.getenv("NEO4J_PASSWORD", "")
                neo4j_database = os.getenv("NEO4J_DATABASE", "")

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
