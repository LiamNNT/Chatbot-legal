# indexing/loaders/__init__.py
"""
Document loaders for the RAG indexing pipeline.

Available parsers:
- LlamaIndexLegalParser: Recommended parser using LlamaIndex (supports PDF, DOCX)
- VietnamLegalDocxParser: Legacy regex-based parser (DOCX only)
"""

# New LlamaIndex-based parser (RECOMMENDED)
from .llamaindex_legal_parser import (
    LlamaIndexLegalParser,
    ParserConfig,
    LegalChunk,
    LegalNodeType,
    ParseResult,
    parse_legal_document,
    parse_legal_document_async,
)

# Legacy parser (DEPRECATED - use LlamaIndexLegalParser instead)
from .vietnam_legal_docx_parser import (
    VietnamLegalDocxParser,
    LegalChunk as LegacyLegalChunk,
    LegalNode,
    LegalNodeType as LegacyLegalNodeType,
    ParseResult as LegacyParseResult,
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
    # Legacy parser (deprecated)
    "VietnamLegalDocxParser",
    "LegacyLegalChunk",
    "LegalNode",
    "LegacyLegalNodeType",
    "LegacyParseResult",
]
