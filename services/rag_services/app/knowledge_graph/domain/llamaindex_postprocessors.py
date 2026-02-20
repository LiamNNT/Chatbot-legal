"""
DEPRECATED — Backward-compatibility re-export wrapper.

The canonical implementation has moved to ``adapters.llamaindex.postprocessors``
to respect Clean Architecture's Dependency Rule (domain must not depend on
external frameworks like LlamaIndex).

All symbols are re-exported so that existing ``from core.domain.llamaindex_postprocessors import …``
statements continue to work.
"""

from app.search.adapters.llamaindex.postprocessors import (     # noqa: F401
    PostprocessorPipeline,
    DeduplicationPostprocessor,
    CrossEncoderRerankPostprocessor,
    MetadataFilterPostprocessor,
    ScoreThresholdPostprocessor,
    CitationPostprocessor,
    TopKPostprocessor,
    create_default_pipeline,
)
