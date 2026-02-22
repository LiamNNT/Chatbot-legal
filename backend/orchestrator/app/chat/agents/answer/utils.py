"""
Utility functions for Answer Agent.

Pure functions extracted from AnswerAgent class for testability and reuse.
"""

import json
import re
from typing import Dict, Any, List, Optional

from ..base import DetailedSource


# ---------------------------------------------------------------------------
# Document filtering
# ---------------------------------------------------------------------------

def filter_amended_documents(context_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out superseded document versions when amendments exist.

    When both old and amended versions of the same Điều (article) are
    retrieved, keep only the amended version.
    """
    if not context_documents:
        return []

    article_map: Dict[str, tuple] = {}  # article_number -> (doc, is_amended)
    other_docs: List[Dict[str, Any]] = []

    for doc in context_documents:
        if doc is None:
            continue

        title = doc.get("title", "") or ""
        content = doc.get("content", "") or doc.get("text", "") or ""
        article_match = re.search(r"Điều\s*(\d+)", title, re.IGNORECASE)

        if not article_match:
            other_docs.append(doc)
            continue

        article_num = article_match.group(1)

        old_markers = [
            "ĐTBC ≥ 7" in content or "ĐTBC >= 7" in content,
            "điểm trung bình chung ≥ 7" in content.lower(),
            "học vượt chỉ dành cho sinh viên có ĐTBC" in content,
        ]
        has_old_markers = any(old_markers)

        new_markers = [
            doc.get("is_amended", False),
            "Mục" in title and "Điều" in title,
            doc.get("source", "") == "knowledge_graph",
        ]
        is_new_content = any(new_markers)

        if article_num in article_map:
            _, existing_is_amended = article_map[article_num]
            if is_new_content and not existing_is_amended:
                article_map[article_num] = (doc, is_new_content)
            # Otherwise keep existing
        else:
            if not has_old_markers or is_new_content:
                article_map[article_num] = (doc, is_new_content)

    return [doc for doc, _ in article_map.values()] + other_docs


# ---------------------------------------------------------------------------
# Source extraction
# ---------------------------------------------------------------------------

def create_detailed_sources(context_documents: List[Dict[str, Any]]) -> List[DetailedSource]:
    """Create detailed source citations from context documents."""
    detailed_sources: List[DetailedSource] = []

    for doc in context_documents:
        title = doc.get("title", "Unknown")
        score = doc.get("score", 0.0)

        meta = doc.get("meta", doc.get("metadata", {}))
        doc_id = meta.get("doc_id")
        chunk_id = meta.get("chunk_id")

        citation = doc.get("citation", {})
        char_spans = doc.get("char_spans", [])
        highlighted_text = doc.get("highlighted_text", [])

        if isinstance(citation, dict):
            if not char_spans and citation.get("char_spans"):
                char_spans = citation["char_spans"]
            if not highlighted_text and citation.get("highlighted_text"):
                highlighted_text = citation["highlighted_text"]

        doc_type = doc.get("doc_type")
        faculty = doc.get("faculty")
        year = doc.get("year")
        subject = doc.get("subject")

        citation_text: Optional[str] = None
        if highlighted_text:
            citation_text = highlighted_text[0] if isinstance(highlighted_text, list) else highlighted_text
        elif char_spans and isinstance(char_spans, list) and len(char_spans) > 0:
            first_span = char_spans[0]
            if isinstance(first_span, dict):
                citation_text = first_span.get("text", "")

        detailed_sources.append(
            DetailedSource(
                title=title,
                doc_id=doc_id,
                chunk_id=chunk_id,
                score=score,
                citation_text=citation_text,
                char_spans=char_spans or None,
                highlighted_text=highlighted_text or None,
                doc_type=doc_type,
                faculty=faculty,
                year=year,
                subject=subject,
            )
        )

    return detailed_sources


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def extract_answer_from_text(text: str, min_answer_length: int = 50) -> str:
    """Extract the main answer from a raw text response."""
    # Try JSON blocks first
    json_pattern = r"```json\s*({.*?})\s*```|({.*?})"
    matches = re.findall(json_pattern, text, re.DOTALL)
    if matches:
        json_str = next((m for group in matches for m in group if m), None)
        if json_str:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and "answer" in data:
                    return data["answer"]
            except json.JSONDecodeError:
                pass

    # Fallback: strip markdown fences, preserve newlines
    answer = text.strip()
    answer = re.sub(r"^```[a-zA-Z]*\s*\n", "", answer)
    answer = re.sub(r"\n\s*```\s*$", "", answer)

    if len(answer) < min_answer_length:
        answer = f"Dựa trên thông tin có sẵn: {answer}"

    return answer


# ---------------------------------------------------------------------------
# Confidence & analysis
# ---------------------------------------------------------------------------

def estimate_confidence(context_documents: List[Dict[str, Any]], answer: str) -> float:
    """Estimate confidence based on context quality and answer characteristics."""
    confidence = 0.5

    if context_documents:
        doc_count = len(context_documents)
        confidence += min(0.2, doc_count * 0.05)
        avg_score = sum(doc.get("score", 0) for doc in context_documents) / doc_count
        confidence += avg_score * 0.3

    if len(answer) > 100:
        confidence += 0.1

    if any(kw in answer.lower() for kw in ["uit", "trường", "đại học", "quy định"]):
        confidence += 0.1

    return min(0.95, max(0.1, confidence))


def analyze_answer_type(query: str) -> str:
    """Analyze the type of answer expected for a query."""
    q = query.lower()
    if any(w in q for w in ["làm thế nào", "hướng dẫn", "cách", "thủ tục", "quy trình"]):
        return "procedural"
    if any(w in q for w in ["so sánh", "khác nhau", "giống", "phân biệt"]):
        return "comparative"
    return "informative"


def assess_completeness(answer: str, context_documents: List[Dict[str, Any]], min_answer_length: int = 50) -> str:
    """Assess the completeness of the generated answer."""
    if not context_documents:
        return "insufficient_data"

    min_partial = min_answer_length * 2
    min_complete = min_answer_length * 6

    if len(answer) < min_partial:
        return "partial"

    aspect_indicators = ["đầu tiên", "thứ hai", "cuối cùng", "ngoài ra", "bên cạnh đó"]
    if any(ind in answer.lower() for ind in aspect_indicators):
        return "complete"

    return "partial" if len(answer) < min_complete else "complete"
