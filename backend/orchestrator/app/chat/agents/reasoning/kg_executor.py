"""
KG Executor — Stage 3 of the Symbolic Verification Pipeline.

Executes a **verified** Cypher query against Neo4j via the existing
``Neo4jGraphAdapter.execute_cypher()`` method in the RAG service.

Only runs if the ``CypherVerificationResult.passed`` flag is True.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from .models import GeneratedCypher, KGRecord, KGResult

logger = logging.getLogger(__name__)


class KGExecutor:
    """
    Execute verified Cypher queries on Neo4j.

    *graph_adapter* must expose ``async execute_cypher(cypher, params) -> list[dict]``.
    This is satisfied by ``Neo4jGraphAdapter`` from the RAG service.
    """

    def __init__(self, graph_adapter: Any):
        """
        Args:
            graph_adapter: An object with an ``execute_cypher`` method
                           (e.g. ``Neo4jGraphAdapter``).
        """
        self._adapter = graph_adapter

    async def execute(self, cypher: GeneratedCypher) -> KGResult:
        """
        Run the Cypher query and return structured ``KGResult``.

        Raises:
            RuntimeError: if the adapter is unavailable or the query fails.
        """
        if self._adapter is None:
            raise RuntimeError("Neo4j graph adapter is not available")

        start = time.time()
        try:
            raw_records: List[Dict[str, Any]] = await self._adapter.execute_cypher(
                cypher.cypher, cypher.params
            )
        except Exception as e:
            logger.error(f"Cypher execution failed: {e}")
            raise RuntimeError(f"Lỗi khi truy vấn Knowledge Graph: {e}") from e

        elapsed_ms = (time.time() - start) * 1000

        if not raw_records:
            logger.info("Cypher returned 0 records")
            return KGResult(
                records=[],
                query_used=cypher.cypher,
                execution_time_ms=elapsed_ms,
                is_empty=True,
                raw_records=[],
            )

        records = [self._to_kg_record(r) for r in raw_records]

        logger.info(
            f"KG query returned {len(records)} records in {elapsed_ms:.0f}ms"
        )
        return KGResult(
            records=records,
            query_used=cypher.cypher,
            execution_time_ms=elapsed_ms,
            is_empty=False,
            raw_records=raw_records,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_kg_record(raw: Dict[str, Any]) -> KGRecord:
        """Convert a raw Neo4j record dict into a ``KGRecord``."""
        labels: List[str] = []
        rel_types: List[str] = []
        cleaned: Dict[str, Any] = {}

        for key, value in raw.items():
            # Neo4j nodes may come as dicts with special keys
            if hasattr(value, "labels"):          # neo4j.graph.Node
                labels.extend(value.labels)
                cleaned[key] = dict(value)
            elif hasattr(value, "type"):          # neo4j.graph.Relationship
                rel_types.append(value.type)
                cleaned[key] = dict(value)
            else:
                cleaned[key] = value

        return KGRecord(
            data=cleaned,
            node_labels=labels,
            relationship_types=rel_types,
        )
