# app/core/extraction/__init__.py
"""
Extraction module for Knowledge Graph extraction pipeline.

This module provides LlamaIndex-based extraction capabilities for Vietnamese legal documents.

IMPORTANT: The VLM-based extractors (StructureExtractor, SemanticExtractor) have been 
deprecated and moved to `app/core/extraction/deprecated/`. Please use the new 
LlamaIndex-based extractors instead:

    - For DOCX files: Use VietnamLegalDocxParser from indexing/loaders/
    - For PDF files: Use LlamaIndexExtractionService from this module

Migration:
    # Old (DEPRECATED - VLM based)
    from app.core.extraction import StructureExtractor, run_pipeline
    result = run_pipeline(pdf_path=pdf_path)
    
    # New (LlamaIndex based)
    from app.core.extraction import LlamaIndexExtractionService
    service = LlamaIndexExtractionService.from_env()
    result = await service.extract_from_pdf(pdf_path)
"""

import warnings

# Schema definitions (still used)
from app.core.extraction.schemas import (
    # Enums
    StructureNodeType,
    VLMProvider,
    # Structural models (for legacy compatibility)
    StructureNode,
    StructureRelation,
    StructureExtractionResult,
    # Semantic models
    SemanticNode,
    SemanticRelation,
    SemanticExtractionResult,
    # Combined models
    HybridExtractionResult,
    PageContext,
    # Config models
    VLMConfig,
    LLMConfig,
    # Schema definitions
    VALID_ENTITY_TYPES,
    VALID_RELATION_TYPES,
    UNIFIED_ACADEMIC_SCHEMA,
    STRUCTURE_EXTRACTION_PROMPT,
    SEMANTIC_EXTRACTION_PROMPT,
)

# LlamaIndex-based extractors (NEW - recommended)
from app.core.extraction.llamaindex_extractor import (
    # Configuration
    ExtractionConfig,
    # Domain models
    EntityType,
    RelationType,
    ExtractedEntity,
    ExtractedRelation,
    ParsedDocument,
    ExtractionResult,
    # Extractors
    LlamaParseDocumentParser,
    PropertyGraphKGExtractor,
    LlamaIndexExtractionService,
)


# Deprecated VLM extractors - lazy import with warning
def _deprecated_import(name: str):
    """Lazy import deprecated extractors with warning."""
    warnings.warn(
        f"{name} is deprecated and moved to app.core.extraction.deprecated. "
        f"Use LlamaIndexExtractionService instead. "
        f"Set USE_LLAMAINDEX_EXTRACTION=true in your environment.",
        DeprecationWarning,
        stacklevel=3
    )
    from app.core.extraction.deprecated.hybrid_extractor import (
        StructureExtractor,
        SemanticExtractor,
        ParallelSemanticExtractor,
        convert_to_graph_models,
        run_pipeline,
    )
    return {
        "StructureExtractor": StructureExtractor,
        "SemanticExtractor": SemanticExtractor,
        "ParallelSemanticExtractor": ParallelSemanticExtractor,
        "convert_to_graph_models": convert_to_graph_models,
        "run_pipeline": run_pipeline,
    }[name]


def __getattr__(name: str):
    """Lazy load deprecated modules with deprecation warnings."""
    deprecated_names = {
        "StructureExtractor",
        "SemanticExtractor", 
        "ParallelSemanticExtractor",
        "convert_to_graph_models",
        "run_pipeline",
    }
    if name in deprecated_names:
        return _deprecated_import(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # === Schema (legacy compatibility) ===
    "StructureNodeType",
    "VLMProvider",
    "StructureNode",
    "StructureRelation",
    "StructureExtractionResult",
    "SemanticNode",
    "SemanticRelation",
    "SemanticExtractionResult",
    "HybridExtractionResult",
    "PageContext",
    "VLMConfig",
    "LLMConfig",
    "VALID_ENTITY_TYPES",
    "VALID_RELATION_TYPES",
    "UNIFIED_ACADEMIC_SCHEMA",
    "STRUCTURE_EXTRACTION_PROMPT",
    "SEMANTIC_EXTRACTION_PROMPT",
    
    # === LlamaIndex Extraction (NEW - recommended) ===
    "ExtractionConfig",
    "EntityType",
    "RelationType",
    "ExtractedEntity",
    "ExtractedRelation",
    "ParsedDocument",
    "ExtractionResult",
    "LlamaParseDocumentParser",
    "PropertyGraphKGExtractor",
    "LlamaIndexExtractionService",
    
    # === Deprecated (will emit warnings) ===
    "StructureExtractor",  # DEPRECATED
    "SemanticExtractor",   # DEPRECATED
    "ParallelSemanticExtractor",  # DEPRECATED
    "convert_to_graph_models",    # DEPRECATED
    "run_pipeline",               # DEPRECATED
]
