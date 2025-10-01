# retrieval/clean_engine.py
#
# Description:
# Clean implementation of the search engine following Ports & Adapters architecture.
# This engine is completely decoupled from external frameworks and technologies.

import logging
from typing import List

from app.api.schemas.search import SearchRequest, SearchHit
from adapters.api_facade import get_search_facade

logger = logging.getLogger(__name__)


class CleanSearchEngine:
    """
    Clean search engine implementation following Ports & Adapters architecture.
    
    This engine acts as a thin adapter layer between the API routes and the 
    domain services. It delegates all business logic to the core domain layer
    through the API facade.
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
            response = self.api_facade.search(req)
            
            # Return just the hits as expected by the current API
            return response.hits
            
        except Exception as e:
            logger.error(f"Error in clean search engine: {e}")
            # Return empty results on error to maintain API contract
            return []


# Factory function to create the clean engine
def get_clean_search_engine() -> CleanSearchEngine:
    """
    Factory function to get the clean search engine instance.
    
    Returns:
        CleanSearchEngine: A clean, architecture-compliant search engine.
    """
    return CleanSearchEngine()
