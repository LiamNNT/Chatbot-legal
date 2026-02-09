"""
Symbolic Reasoning Module for Legal Knowledge Graph

This module implements rule-based symbolic reasoning for Vietnamese legal documents.
Combines Knowledge Graph traversal with inference rules for accurate legal answers.

Components:
- SymbolicReasoningEngine: Main reasoning engine
- ReasoningRule: Rule definitions (R001-R008)
- QueryAnalyzer: Natural language query analysis
- ContextEnricher: Context enrichment for LLM
- SymbolicGraphExtension: Neo4j adapter extension

Based on: SYMBOLIC_REASONING_GUIDE.md
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

__all__ = [
    "SymbolicReasoningEngine",
    "ReasoningMode",
    "ReasoningRule",
    "ReasoningRuleRegistry",
    "LEGAL_REASONING_RULES",
    "QueryAnalyzer",
    "QueryComponents",
    "ContextEnricher",
    "SymbolicGraphExtension"
]
