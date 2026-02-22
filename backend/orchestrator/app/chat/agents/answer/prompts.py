"""
Prompt builder for Answer Agent.

Constructs the user prompt that is sent alongside the system prompt
loaded from YAML config at runtime.
"""

from typing import Dict, Any, List

from .utils import filter_amended_documents


def build_answer_prompt(
    query: str,
    context_documents: List[Dict[str, Any]],
    rewritten_queries: List[str],
    previous_context: str,
    previous_feedback: str = "",
) -> str:
    """Build the full user prompt for the answer generation LLM call."""
    parts: List[str] = []

    # Feedback section at top if this is a retry
    if previous_feedback:
        parts.append("=" * 60)
        parts.append("⚠️ IMPROVEMENT REQUEST - PLEASE REVISE YOUR PREVIOUS ANSWER")
        parts.append("=" * 60)
        parts.append("")
        parts.append("Your previous answer was evaluated and needs improvement.")
        parts.append("Please carefully read the feedback below and generate a better answer:")
        parts.append("")
        parts.append(previous_feedback)
        parts.append("")
        parts.append("=" * 60)
        parts.append("Now, please provide an improved answer addressing the feedback above.")
        parts.append("=" * 60)
        parts.append("")

    parts.append(f"Query: {query}")

    if rewritten_queries:
        parts.append(f"Query Variations: {', '.join(rewritten_queries)}")

    if previous_context:
        parts.append(f"Context: {previous_context}")

    # Filter documents to remove old versions when amendments exist
    filtered = filter_amended_documents(context_documents)

    if filtered:
        parts.append("\nDocuments:")
        for i, doc in enumerate(filtered, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "") or doc.get("text", "")
            score = doc.get("score", 0.0)
            is_amended = doc.get("is_amended", False)
            marker = " [UPDATED VERSION]" if is_amended else ""
            parts.append(f"[{i}] {title}{marker} (Score: {score:.2f})")
            parts.append(content)

    return "\n".join(parts)
