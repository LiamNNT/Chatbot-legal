# app/core/extraction/deprecated/__init__.py
"""
DEPRECATED EXTRACTION MODULES

These modules use VLM (Vision Language Model) for document extraction and are
no longer recommended for use. They have been deprecated in favor of:

1. VietnamLegalDocxParser - For DOCX/DOC files
2. LlamaIndexExtractionService - For PDF files with LlamaParse

The modules in this folder are kept for backward compatibility only and will
be removed in a future version.

Migration Guide:
================

Old approach (VLM - requires GPU):
    from app.extraction import StructureExtractor, run_pipeline
    result, nodes, rels = run_pipeline(pdf_path=pdf_path)

New approach (LlamaIndex - cloud-based):
    # For PDF files
    from app.extraction import LlamaIndexExtractionService
    service = LlamaIndexExtractionService.from_env()
    result = await service.extract_from_pdf(pdf_path)
    nodes, rels = result.to_graph_models()
    
    # For DOCX/DOC files
    from app.ingest.loaders.vietnam_legal_docx_parser import VietnamLegalDocxParser
    parser = VietnamLegalDocxParser()
    result = parser.parse(docx_path)
    chunks = result.chunks  # List[LegalChunk]

Environment Variable:
    Set USE_LLAMAINDEX_EXTRACTION=true to use the new implementation.
"""

import warnings

warnings.warn(
    "The app.core.extraction.deprecated module contains deprecated VLM extractors. "
    "Please migrate to LlamaIndexExtractionService for PDF files or "
    "VietnamLegalDocxParser for DOCX files.",
    DeprecationWarning,
    stacklevel=2
)
