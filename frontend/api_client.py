# frontend/api_client.py
"""
Thin API client for communicating with backend services.
Wraps requests calls and returns raw dicts — no business logic here.
"""

from __future__ import annotations

import requests
from typing import Any, Dict, Iterator, Optional

from config import ORCHESTRATOR_URL, RAG_SERVICE_URL, REQUEST_TIMEOUT


# ═══════════════════════════════════════════════════════
# Orchestrator API  (port 8001)
# ═══════════════════════════════════════════════════════

def send_chat_message(
    query: str,
    session_id: str,
    *,
    use_rag: bool = True,
    use_knowledge_graph: Optional[bool] = None,
    rag_top_k: int = 5,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """POST /chat  →  non-streaming response."""
    payload: Dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "use_rag": use_rag,
        "rag_top_k": rag_top_k,
        "stream": stream,
    }
    if use_knowledge_graph is not None:
        payload["use_knowledge_graph"] = use_knowledge_graph
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    resp = requests.post(
        f"{ORCHESTRATOR_URL}/chat",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def send_chat_stream(
    query: str,
    session_id: str,
    *,
    use_rag: bool = True,
    use_knowledge_graph: Optional[bool] = None,
    rag_top_k: int = 5,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """POST /chat  →  SSE streaming, yields parsed JSON events."""
    import json

    payload: Dict[str, Any] = {
        "query": query,
        "session_id": session_id,
        "use_rag": use_rag,
        "rag_top_k": rag_top_k,
        "stream": True,
    }
    if use_knowledge_graph is not None:
        payload["use_knowledge_graph"] = use_knowledge_graph
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    with requests.post(
        f"{ORCHESTRATOR_URL}/chat",
        json=payload,
        stream=True,
        timeout=REQUEST_TIMEOUT,
    ) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue
            data_str = raw_line[6:]
            if data_str == "[DONE]":
                break
            try:
                yield json.loads(data_str)
            except json.JSONDecodeError:
                continue


def check_health() -> Dict[str, Any]:
    """GET /health"""
    resp = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_conversations() -> Dict[str, Any]:
    """GET /conversations"""
    resp = requests.get(f"{ORCHESTRATOR_URL}/conversations", timeout=10)
    resp.raise_for_status()
    return resp.json()


def delete_conversation(session_id: str) -> Dict[str, Any]:
    """DELETE /conversations/{session_id}"""
    resp = requests.delete(
        f"{ORCHESTRATOR_URL}/conversations/{session_id}", timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_agents_info() -> Dict[str, Any]:
    """GET /agents/info"""
    resp = requests.get(f"{ORCHESTRATOR_URL}/agents/info", timeout=10)
    resp.raise_for_status()
    return resp.json()


def test_agents() -> Dict[str, Any]:
    """POST /agents/test"""
    resp = requests.post(f"{ORCHESTRATOR_URL}/agents/test", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════════════
# RAG Service API  (port 8002)
# ═══════════════════════════════════════════════════════

def rag_health() -> Dict[str, Any]:
    """GET /v1/health"""
    resp = requests.get(f"{RAG_SERVICE_URL}/v1/health", timeout=10)
    resp.raise_for_status()
    return resp.json()


def upload_for_ingest(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """POST /v1/ingest/upload  — upload a document for ingestion."""
    files = {"file": (filename, file_bytes)}
    resp = requests.post(
        f"{RAG_SERVICE_URL}/v1/ingest/upload",
        files=files,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_ingest_status(job_id: str) -> Dict[str, Any]:
    """GET /v1/ingest/status/{job_id}"""
    resp = requests.get(
        f"{RAG_SERVICE_URL}/v1/ingest/status/{job_id}", timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def upload_for_extraction(
    file_bytes: bytes,
    filename: str,
    category: str = "Quy chế Đào tạo",
    push_to_neo4j: bool = False,
) -> Dict[str, Any]:
    """POST /v1/extraction/upload"""
    files = {"file": (filename, file_bytes)}
    resp = requests.post(
        f"{RAG_SERVICE_URL}/v1/extraction/upload",
        files=files,
        params={"category": category, "push_to_neo4j": push_to_neo4j},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_extraction_status(job_id: str) -> Dict[str, Any]:
    """GET /v1/extraction/status/{job_id}"""
    resp = requests.get(
        f"{RAG_SERVICE_URL}/v1/extraction/status/{job_id}", timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_extraction_result(job_id: str) -> Dict[str, Any]:
    """GET /v1/extraction/result/{job_id}"""
    resp = requests.get(
        f"{RAG_SERVICE_URL}/v1/extraction/result/{job_id}", timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def get_neo4j_stats() -> Dict[str, Any]:
    """GET /v1/extraction/neo4j/stats"""
    resp = requests.get(
        f"{RAG_SERVICE_URL}/v1/extraction/neo4j/stats", timeout=10
    )
    resp.raise_for_status()
    return resp.json()
