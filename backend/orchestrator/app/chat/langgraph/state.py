"""
LangGraph State Definition for IRCoT Orchestration.

This module defines the state structure for LangGraph-based orchestration,
replacing the manual IRCoT loop implementation with a stateful graph workflow.

Benefits of using LangGraph:
1. Automatic state management across iterations
2. Visual debugging and tracing
3. Human-in-the-loop support
4. Easy extension to more agents
5. Built-in checkpointing for long-running tasks

Reference: https://python.langchain.com/docs/langgraph
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator


class WorkflowPhase(str, Enum):
    """Current phase of the orchestration workflow."""
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    REASONING = "reasoning"
    ANSWERING = "answering"
    COMPLETED = "completed"
    ERROR = "error"


class QueryComplexity(str, Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class ExtractedFiltersState:
    """Extracted filters from query analysis."""
    doc_types: List[str] = field(default_factory=list)
    legal_domains: List[str] = field(default_factory=list)
    years: List[int] = field(default_factory=list)
    legal_references: List[str] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return not (self.doc_types or self.legal_domains or self.years or self.legal_references)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_types": self.doc_types,
            "legal_domains": self.legal_domains,
            "years": self.years,
            "legal_references": self.legal_references
        }


@dataclass 
class RetrievedDocument:
    """A document retrieved from RAG/Graph sources."""
    content: str
    score: float
    title: str = ""
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None


@dataclass
class ReasoningStep:
    """A single reasoning step in the IRCoT chain."""
    iteration: int
    reasoning: str
    next_query: Optional[str] = None
    confidence: float = 0.0
    can_answer: bool = False
    information_gaps: List[str] = field(default_factory=list)


@dataclass
class PlanResult:
    """Result from the planning phase."""
    intent: str = "unknown"
    complexity: QueryComplexity = QueryComplexity.MEDIUM
    complexity_score: float = 5.0
    requires_rag: bool = True
    use_knowledge_graph: bool = False
    graph_query_type: str = "local"
    rewritten_queries: List[str] = field(default_factory=list)
    search_terms: List[str] = field(default_factory=list)
    extracted_filters: Optional[ExtractedFiltersState] = None
    strategy: str = "standard_rag"
    top_k: int = 5


class IRCoTState(TypedDict):
    """
    State for the IRCoT LangGraph workflow.
    
    This state is passed between nodes in the graph and contains
    all information needed for the reasoning-retrieval cycle.
    
    The state follows LangGraph conventions:
    - Annotated fields with operators for accumulation (append, merge)
    - All fields are serializable for checkpointing
    """
    
    # === Input State ===
    original_query: str  # The original user query
    session_id: str  # Session identifier for conversation tracking
    use_rag: bool  # Whether to use RAG retrieval
    rag_top_k: int  # Number of documents to retrieve
    use_knowledge_graph: bool  # Whether to use Knowledge Graph
    
    # === Planning State ===
    plan_result: Optional[Dict[str, Any]]  # Result from SmartPlanner
    standalone_query: str  # Query after contextual rewriting
    complexity: str  # Query complexity level
    complexity_score: float  # Numeric complexity score (0-10)
    
    # === Retrieval State ===
    # Use Annotated with operator.add to accumulate documents across iterations
    accumulated_documents: Annotated[List[Dict[str, Any]], operator.add]
    current_search_query: str  # Current query for retrieval
    search_queries_used: Annotated[List[str], operator.add]  # All queries used
    
    # === Graph Reasoning State ===
    graph_context: Optional[str]  # Context from Knowledge Graph
    graph_nodes_found: int
    graph_paths_found: int
    graph_confidence: float
    
    # === IRCoT Reasoning State ===
    # Use Annotated with operator.add to accumulate reasoning steps
    reasoning_steps: Annotated[List[Dict[str, Any]], operator.add]
    current_iteration: int
    max_iterations: int
    current_confidence: float
    can_answer_now: bool
    information_gaps: List[str]
    
    # === Workflow Control ===
    current_phase: str  # Current phase of workflow
    should_continue_ircot: bool  # Whether to continue IRCoT loop
    early_stopped: bool  # Whether stopped early due to confidence
    
    # === Output State ===
    final_answer: str  # Generated answer
    final_reasoning: str  # Compiled reasoning chain
    detailed_sources: List[Dict[str, Any]]  # Source citations
    
    # === Error Handling ===
    error: Optional[str]  # Error message if any
    error_details: Optional[Dict[str, Any]]  # Additional error info
    
    # === Timing & Stats ===
    start_time: float
    processing_stats: Dict[str, Any]


def create_initial_state(
    query: str,
    session_id: str = "default",
    use_rag: bool = True,
    rag_top_k: int = 5,
    use_knowledge_graph: bool = False,
    max_iterations: int = 2
) -> IRCoTState:
    """
    Create initial state for the IRCoT workflow.
    
    Args:
        query: The user's question
        session_id: Session identifier
        use_rag: Whether to use RAG
        rag_top_k: Number of documents to retrieve
        use_knowledge_graph: Whether to use Knowledge Graph
        max_iterations: Maximum IRCoT iterations
        
    Returns:
        Initial IRCoTState ready for workflow execution
    """
    import time
    
    return IRCoTState(
        # Input
        original_query=query,
        session_id=session_id,
        use_rag=use_rag,
        rag_top_k=rag_top_k,
        use_knowledge_graph=use_knowledge_graph,
        
        # Planning
        plan_result=None,
        standalone_query=query,
        complexity="medium",
        complexity_score=5.0,
        
        # Retrieval
        accumulated_documents=[],
        current_search_query=query,
        search_queries_used=[],
        
        # Graph
        graph_context=None,
        graph_nodes_found=0,
        graph_paths_found=0,
        graph_confidence=0.0,
        
        # IRCoT
        reasoning_steps=[],
        current_iteration=0,
        max_iterations=max_iterations,
        current_confidence=0.0,
        can_answer_now=False,
        information_gaps=[],
        
        # Workflow
        current_phase=WorkflowPhase.PLANNING.value,
        should_continue_ircot=True,
        early_stopped=False,
        
        # Output
        final_answer="",
        final_reasoning="",
        detailed_sources=[],
        
        # Error
        error=None,
        error_details=None,
        
        # Stats
        start_time=time.time(),
        processing_stats={}
    )


def merge_documents(
    existing: List[Dict[str, Any]], 
    new_docs: List[Dict[str, Any]],
    similarity_threshold: float = 0.9
) -> List[Dict[str, Any]]:
    """
    Merge new documents with existing ones, avoiding duplicates.
    
    Args:
        existing: Existing accumulated documents
        new_docs: New documents to add
        similarity_threshold: Threshold for considering documents as duplicates
        
    Returns:
        Merged list of documents without duplicates
    """
    if not new_docs:
        return existing
    
    result = list(existing)
    existing_ids = {doc.get("doc_id") or doc.get("chunk_id") for doc in existing}
    
    for doc in new_docs:
        doc_id = doc.get("doc_id") or doc.get("chunk_id")
        
        # Skip if we already have this document by ID
        if doc_id and doc_id in existing_ids:
            continue
            
        # Simple content-based deduplication
        content = doc.get("content", "")[:500]  # First 500 chars
        is_duplicate = any(
            existing_doc.get("content", "")[:500] == content 
            for existing_doc in result
        )
        
        if not is_duplicate:
            result.append(doc)
            if doc_id:
                existing_ids.add(doc_id)
    
    return result
