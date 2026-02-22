"""
Response mappers for the orchestrator API.

Extract response transformation logic from route handlers into pure
mapping functions, keeping controllers thin per Clean Architecture.
"""

from datetime import datetime
from typing import Optional

from ..shared.schemas import (
    ChatResponse,
    DocumentInfo,
    RAGContextInfo,
    ProcessingStats,
)


def build_rag_context_info(
    rag_context,
    processing_stats: dict,
    *,
    search_mode_fallback: str = "unknown",
) -> Optional[RAGContextInfo]:
    """Map domain RAGContext to the API RAGContextInfo schema."""
    if rag_context is None:
        return None

    documents = [
        DocumentInfo(
            title=doc.get("title", "Untitled"),
            content=doc.get("text", doc.get("content", "")),
            score=doc.get("score", 0.0),
            metadata=doc.get("metadata", {}),
        )
        for doc in rag_context.retrieved_documents
    ]

    search_mode = search_mode_fallback
    if rag_context.search_metadata:
        search_mode = rag_context.search_metadata.get("search_mode", search_mode_fallback)

    # KG / vector indicators
    use_knowledge_graph = processing_stats.get("use_knowledge_graph", False)
    use_vector_search = processing_stats.get("use_vector_search", True)
    complexity = processing_stats.get("complexity")
    strategy = processing_stats.get("strategy")

    return RAGContextInfo(
        query=rag_context.query,
        documents=documents,
        total_documents=len(documents),
        search_mode=search_mode,
        processing_time=processing_stats.get("rag_time"),
        use_knowledge_graph=use_knowledge_graph,
        use_vector_search=use_vector_search,
        complexity=complexity,
        strategy=strategy,
    )


def build_processing_stats(raw: dict) -> ProcessingStats:
    """Map a raw stats dict to the API ProcessingStats schema."""
    return ProcessingStats(
        total_time=raw.get("total_time", 0.0),
        rag_time=raw.get("rag_time"),
        agent_time=raw.get("agent_time"),
        documents_retrieved=raw.get("documents_retrieved"),
        tokens_used=raw.get("tokens_used"),
        rag_error=raw.get("rag_error"),
        llm_calls=raw.get("llm_calls"),
        pipeline=raw.get("pipeline"),
        planning_time=raw.get("planning_time"),
        answer_generation_time=raw.get("answer_generation_time"),
        plan_complexity=raw.get("plan_complexity"),
        plan_complexity_score=raw.get("plan_complexity_score"),
    )


def build_chat_response(
    response,
    *,
    search_mode_fallback: str = "unknown",
) -> ChatResponse:
    """Map domain OrchestrationResponse → API ChatResponse."""
    rag_context_info = build_rag_context_info(
        response.rag_context,
        response.processing_stats,
        search_mode_fallback=search_mode_fallback,
    )
    processing_stats = build_processing_stats(response.processing_stats)

    model_used = None
    if response.agent_metadata:
        model_used = response.agent_metadata.get("model_used")

    return ChatResponse(
        response=response.response,
        session_id=response.session_id,
        timestamp=response.timestamp or datetime.now(),
        rag_context=rag_context_info,
        processing_stats=processing_stats,
        model_used=model_used,
    )
