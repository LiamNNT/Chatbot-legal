"""Data models for Smart Planner Agent."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ExtractedFilters:
    """Filters extracted from the query context."""
    doc_types: List[str] = field(default_factory=list)
    legal_domains: List[str] = field(default_factory=list)
    years: List[int] = field(default_factory=list)
    legal_references: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.doc_types:
            result["doc_types"] = self.doc_types
        if self.legal_domains:
            result["legal_domains"] = self.legal_domains
        if self.years:
            result["years"] = self.years
        if self.legal_references:
            result["legal_references"] = self.legal_references
        return result

    def is_empty(self) -> bool:
        return not any([self.doc_types, self.legal_domains, self.years, self.legal_references])


@dataclass
class SmartPlanResult:
    """Result from the Smart Planner agent (combined planning + query rewriting)."""
    # Planning fields
    query: str
    intent: str
    complexity: str  # "simple", "medium", "complex"
    complexity_score: float
    requires_rag: bool
    strategy: str  # "direct_response", "standard_rag", "advanced_rag"

    # Query rewriting fields
    rewritten_queries: List[str]
    search_terms: List[str]

    # RAG parameters
    top_k: int
    hybrid_search: bool
    reranking: bool

    # Metadata (required fields)
    reasoning: str
    confidence: float
    metadata: Dict[str, Any]

    # Search source selection (optional fields with defaults)
    use_knowledge_graph: bool = False
    use_vector_search: bool = True

    # Graph Reasoning Type: "local", "global", "multi_hop"
    graph_query_type: str = "local"

    # Extracted filters for RAG search
    extracted_filters: Optional[ExtractedFilters] = None
