# indexing/__init__.py
"""
Indexing module for the RAG services.

This module contains components for:
- Document loaders (DOCX, PDF, etc.)
- Text chunkers (hierarchical, semantic)
- Embedding generators
"""

from .loaders import (
    VietnamLegalDocxParser,
    LegalChunk,
    LegalNode,
    LegalNodeType,
    ParseResult,
)

__all__ = [
    "VietnamLegalDocxParser",
    "LegalChunk",
    "LegalNode",
    "LegalNodeType",
    "ParseResult",
]
