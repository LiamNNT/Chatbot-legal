"""
Reasoning feature: symbolic + graph reasoning.

Components:
- GraphReasoningAgent: ReAct-based graph reasoning
- SymbolicReasoningAgent: Rule-based symbolic reasoning
- SymbolicReasoningEngine: Core reasoning engine
- ReasoningRules: Legal reasoning rules (R001-R008)
- QueryAnalyzer: NL query analysis
- ContextEnricher: Context enrichment for LLM
- SymbolicGraphExtension: Neo4j adapter extension
"""

from .symbolic_engine import SymbolicReasoningEngine, ReasoningMode
from .reasoning_rules import (
    ReasoningRule,
    ReasoningRuleRegistry,
    LEGAL_REASONING_RULES
)
from .query_analyzer import QueryAnalyzer, QueryComponents
from .context_enricher import ContextEnricher
from .symbolic_graph_extension import SymbolicGraphExtension
from .graph_reasoning_agent import GraphReasoningAgent, GraphQueryType, GraphReasoningResult
from .symbolic_reasoning_agent import (
    SymbolicReasoningAgent,
    SymbolicReasoningResult,
    SymbolicQueryType
)

__all__ = [
    "SymbolicReasoningEngine",
    "ReasoningMode",
    "ReasoningRule",
    "ReasoningRuleRegistry",
    "LEGAL_REASONING_RULES",
    "QueryAnalyzer",
    "QueryComponents",
    "ContextEnricher",
    "SymbolicGraphExtension",
    "GraphReasoningAgent",
    "GraphQueryType",
    "GraphReasoningResult",
    "SymbolicReasoningAgent",
    "SymbolicReasoningResult",
    "SymbolicQueryType",
]
