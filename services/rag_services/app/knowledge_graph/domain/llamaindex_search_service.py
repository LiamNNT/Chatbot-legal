"""
DEPRECATED — Backward-compatibility re-export wrapper.

The canonical implementation has moved to ``adapters.llamaindex.search_service``
to respect Clean Architecture's Dependency Rule (domain must not depend on
external frameworks like LlamaIndex).

All symbols are re-exported so that existing ``from core.domain.llamaindex_search_service import …``
statements continue to work.
"""

from app.search.adapters.llamaindex.search_service import LlamaIndexSearchService  # noqa: F401
