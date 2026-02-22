"""Data models for Smart Planner Agent."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ExtractedFilters:
    """Filters extracted from the query context."""
    doc_types: List[str] = field(default_factory=list)
    faculties: List[str] = field(default_factory=list)
    years: List[int] = field(default_factory=list)
    subjects: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.doc_types:
            result["doc_types"] = self.doc_types
        if self.faculties:
            result["faculties"] = self.faculties
        if self.years:
            result["years"] = self.years
        if self.subjects:
            result["subjects"] = self.subjects
        return result

    def is_empty(self) -> bool:
        return not any([self.doc_types, self.faculties, self.years, self.subjects])


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
