# indexing/__init__.py
"""
Indexing module for the RAG services.

This module contains components for:
- Document loaders (DOCX, PDF, etc.)
- Text chunkers (hierarchical, semantic)
- Embedding generators

RECOMMENDED: Use LlamaIndexLegalParser for parsing Vietnamese legal documents.
"""

# New LlamaIndex-based parser (RECOMMENDED)
from .loaders import (
    LlamaIndexLegalParser,
    ParserConfig,
    LegalChunk,
    LegalNodeType,
    ParseResult,
    parse_legal_document,
    parse_legal_document_async,
)

# Legacy parser (for backward compatibility)
from .loaders import (
    VietnamLegalDocxParser,
    LegalNode,
)

__all__ = [
    # New parser (recommended)
    "LlamaIndexLegalParser",
    "ParserConfig",
    "LegalChunk",
    "LegalNodeType",
    "ParseResult",
    "parse_legal_document",
    "parse_legal_document_async",
    # Legacy (deprecated)
    "VietnamLegalDocxParser",
    "LegalNode",
]
