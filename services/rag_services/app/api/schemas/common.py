# app/api/schemas/common.py
#
# Description:
# This file defines common Pydantic models that are reused across multiple API endpoints.
# Centralizing these shared schemas promotes code reuse and consistency.

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SourceMeta(BaseModel):
    """
    Defines the metadata structure for a retrieved document source.
    This provides context about where a piece of information originated.
    """
    doc_id: str
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class CitationSpan(BaseModel):
    """
    Defines the structure for a citation, pointing to a specific part of a source document.
    """
    doc_id: str
    page: Optional[int] = None
    span: Optional[List[int]] = None  # [start, end] character offsets if available

class Pagination(BaseModel):
    """
    Defines a standard pagination schema for list-based API responses.
    """
    offset: int = 0
    limit: int = 10