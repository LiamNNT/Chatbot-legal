"""
Smart Planner Agent — combines Planner + Query Rewriter in a single LLM call.

Responsibilities:
1. Intent classification
2. Complexity scoring (0-10)
3. Strategy determination (direct / standard_rag / advanced_rag)
4. Query rewriting and search term extraction
5. Filter extraction (legal domains, years, legal references)

The system prompt is loaded from YAML config at runtime.
"""

import json
from typing import Dict, Any, Optional

from ..base import SpecializedAgent, AgentConfig
from .models import SmartPlanResult, ExtractedFilters
from . import rules


# Complexity thresholds (defaults, overridden by config)
SIMPLE_MAX_SCORE = 3.5
COMPLEX_MIN_SCORE = 6.5


class SmartPlannerAgent(SpecializedAgent):
    def __init__(self, config: AgentConfig, agent_port):
        super().__init__(config, agent_port)
        params = getattr(config, 'parameters', {}) or {}
        thresholds = params.get('complexity_thresholds', {})
        self.simple_max = thresholds.get('simple_max', SIMPLE_MAX_SCORE)
        self.complex_min = thresholds.get('complex_min', COMPLEX_MIN_SCORE)
        self.default_top_k = params.get('default_top_k', 5)
        self.max_rewritten_queries = params.get('max_rewritten_queries', 3)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process(self, input_data: Dict[str, Any]) -> SmartPlanResult:
        query = input_data.get("query", "")

        # Fast-path: rule-based for trivial queries (no LLM needed)
        simple_result = rules.check_simple_query(query)
        if simple_result:
            return simple_result

        # Single LLM call – system prompt already loaded from YAML config
        response = await self._make_agent_request(query)
        return self._parse_response(response.content, query)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, response_content: str, original_query: str) -> SmartPlanResult:
        try:
            data = json.loads(response_content)
            return self._create_result_from_json(data, original_query)
        except json.JSONDecodeError:
            return self._create_fallback_result(original_query, response_content)

    def _create_result_from_json(self, data: Dict[str, Any], original_query: str) -> SmartPlanResult:
        complexity_score = data.get("complexity_score", 5.0)
        complexity = data.get("complexity", rules.score_to_complexity(complexity_score, self.simple_max, self.complex_min))
        requires_rag = data.get("requires_rag", True)
        intent = data.get("intent", "informational")

        # Determine RAG params based on complexity
        if complexity == "simple" or not requires_rag:
            top_k, hybrid_search, reranking = 0, False, False
        elif complexity == "complex" and complexity_score > 7.0:
            top_k = data.get("top_k", 10)
            hybrid_search = data.get("hybrid_search", True)
            reranking = True
        elif complexity == "complex":
            top_k = data.get("top_k", 8)
            hybrid_search = data.get("hybrid_search", True)
            reranking = False
        else:
            top_k = data.get("top_k", 5)
            hybrid_search = False
            reranking = False

        # Knowledge Graph decision
        needs_kg = rules.needs_knowledge_graph(original_query)
        use_knowledge_graph = data.get("use_knowledge_graph", None)
        if use_knowledge_graph is None:
            use_knowledge_graph = requires_rag

        # Graph query type
        graph_query_type = data.get("graph_query_type", None)
        if graph_query_type is None and use_knowledge_graph:
            graph_query_type = rules.determine_graph_query_type(original_query)
        elif graph_query_type is None:
            graph_query_type = "local"

        # Filters
        extracted_filters = rules.extract_filters_from_query(original_query) if requires_rag else None

        return SmartPlanResult(
            query=original_query,
            intent=intent,
            complexity=complexity,
            complexity_score=complexity_score,
            requires_rag=requires_rag,
            strategy=data.get("strategy", "standard_rag"),
            rewritten_queries=data.get("rewritten_queries", [original_query]),
            search_terms=data.get("search_terms", rules.extract_keywords(original_query)),
            top_k=top_k,
            hybrid_search=hybrid_search,
            reranking=reranking,
            use_knowledge_graph=use_knowledge_graph,
            use_vector_search=requires_rag,
            graph_query_type=graph_query_type,
            extracted_filters=extracted_filters,
            reasoning=data.get("reasoning", ""),
            confidence=0.85,
            metadata={
                "source": "llm_response",
                "kg_reason": "relationship_query" if needs_kg else None,
                "graph_reasoning_type": graph_query_type,
            },
        )

    def _create_fallback_result(self, query: str, response_content: str) -> SmartPlanResult:
        """Create fallback result using rule-based analysis."""
        complexity_score = rules.estimate_complexity_score(query)
        complexity = rules.score_to_complexity(complexity_score, self.simple_max, self.complex_min)
        requires_rag = complexity != "simple"

        rewritten_queries = rules.apply_rule_based_rewriting(query, self.max_rewritten_queries) if requires_rag else []
        search_terms = rules.extract_keywords(query) if requires_rag else []

        if complexity == "simple":
            top_k, hybrid_search, reranking = 0, False, False
            strategy = "direct_response"
        elif complexity == "complex" and complexity_score > 7.0:
            top_k, hybrid_search, reranking = 10, True, True
            strategy = "advanced_rag"
        elif complexity == "complex":
            top_k, hybrid_search, reranking = 8, True, False
            strategy = "advanced_rag"
        else:
            top_k, hybrid_search, reranking = 5, False, False
            strategy = "standard_rag"

        intent = rules.detect_intent(query)
        needs_kg = rules.needs_knowledge_graph(query)
        use_knowledge_graph = requires_rag and (complexity == "complex" or needs_kg or intent == "comparative")
        graph_query_type = rules.determine_graph_query_type(query) if use_knowledge_graph else "local"
        extracted_filters = rules.extract_filters_from_query(query) if requires_rag else None

        return SmartPlanResult(
            query=query,
            intent=intent,
            complexity=complexity,
            complexity_score=complexity_score,
            requires_rag=requires_rag,
            strategy=strategy,
            rewritten_queries=rewritten_queries,
            search_terms=search_terms,
            top_k=top_k,
            hybrid_search=hybrid_search,
            reranking=reranking,
            use_knowledge_graph=use_knowledge_graph,
            use_vector_search=requires_rag,
            graph_query_type=graph_query_type,
            extracted_filters=extracted_filters,
            reasoning="Fallback to rule-based analysis",
            confidence=0.6,
            metadata={
                "fallback": True,
                "original_response": response_content[:200],
                "kg_reason": "relationship_query" if needs_kg else None,
                "graph_reasoning_type": graph_query_type,
            },
        )
