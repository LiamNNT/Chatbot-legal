# retrieval/engine.py
#
# Description:
# Clean architecture-compliant search engine interface.
# This module provides a simplified interface that delegates to the clean Ports & Adapters architecture.

import logging
from typing import List
import asyncio

# Clean architecture imports
from adapters.api_facade import get_search_facade
from app.api.schemas.search import SearchRequest, SearchHit

logger = logging.getLogger(__name__)


class CleanSearchEngine:
    """
    Clean search engine that uses the Ports & Adapters architecture exclusively.
    
    This engine acts as a thin wrapper around the API facade, providing
    a synchronous interface while delegating all business logic to the 
    clean architecture implementation.
    """
    
    def __init__(self):
        self.api_facade = get_search_facade()
    
    def search(self, req: SearchRequest) -> List[SearchHit]:
        """
        Perform search using the clean architecture approach.
        
        Args:
            req (SearchRequest): The search request from the API.
            
        Returns:
            List[SearchHit]: A list of formatted search results.
        """
        try:
            # Delegate to the API facade which handles all domain interaction
            response = asyncio.run(self.api_facade.search(req))
            
            # Return just the hits as expected by the current API
            return response.hits
            
        except Exception as e:
            logger.error(f"Error in clean search engine: {e}")
            # Return empty results on error to maintain API contract
            return []


# Factory function for getting the clean search engine
_clean_engine = None

def get_query_engine() -> CleanSearchEngine:
    """
    Factory function to get the clean search engine instance.
    
    Returns:
        CleanSearchEngine: A clean, architecture-compliant search engine.
    """
    global _clean_engine
    if _clean_engine is None:
        _clean_engine = CleanSearchEngine()
        logger.info("Created clean search engine using Ports & Adapters architecture")
    return _clean_engine


# Legacy compatibility - these functions are deprecated
def get_clean_search_engine() -> CleanSearchEngine:
    """
    DEPRECATED: Use get_query_engine() instead.
    
    Factory function to get the clean search engine instance.
    
    Returns:
        CleanSearchEngine: A clean, architecture-compliant search engine.
    """
    logger.warning("get_clean_search_engine() is deprecated. Use get_query_engine() instead.")
    return get_query_engine()


# Import legacy engine for backward compatibility during transition
try:
    from retrieval.engine_legacy import get_legacy_engine, HybridEngine
    logger.info("Legacy engine available for backward compatibility")
except ImportError:
    logger.info("Legacy engine not available")
    
    # Provide stub implementations
    def get_legacy_engine():
        logger.error("Legacy engine not available. Use clean architecture instead.")
        raise NotImplementedError("Legacy engine has been removed. Use get_query_engine() instead.")
    
    class HybridEngine:
        def __init__(self):
            logger.error("HybridEngine is deprecated. Use CleanSearchEngine instead.")
            raise NotImplementedError("HybridEngine has been removed. Use get_query_engine() instead.")