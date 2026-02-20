# core/domain/models.py
#
# Re-export canonical RAG domain models from the shared package.
# All definitions now live in ``shared.domain.rag_models``.
# This module exists only for backward-compatibility.

from shared.domain.rag_models import (        # noqa: F401
    SearchMode,
    DocumentLanguage,
    CharacterSpan,
    DocumentMetadata,
    SearchFilters,
    RerankingMetadata,
    SearchQuery,
    SearchResult,
    SearchResponse,
    Document,
    DocumentChunk,
)
