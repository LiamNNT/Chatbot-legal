#!/usr/bin/env python3
"""
Quick test RAG with crawled data - Direct query without server.
"""

import asyncio
import logging
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

import sys
sys.path.insert(0, str(project_root))

from infrastructure.container import get_search_service
from core.domain.models import SearchQuery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_search():
    """Test search with crawled data."""
    logger.info("="*80)
    logger.info("TEST RAG SEARCH WITH CRAWLED DATA (Direct - No Server)")
    logger.info("="*80)
    
    try:
        # Get search service
        search_service = get_search_service()
        
        # Create search query
        query = SearchQuery(
            text="Chương trình đào tạo Khoa học Máy tính 2024",
            top_k=3,
            filters={}
        )
        
        logger.info(f"\n🔍 Query: {query.text}\n")
        
        # Search
        results = await search_service.search(query)
        
        # Extract actual results list from SearchResponse
        if hasattr(results, 'results'):
            result_list = results.results
        else:
            result_list = results if isinstance(results, list) else []
        
        logger.info(f"📊 Found {len(result_list)} results:\n")
        
        for i, result in enumerate(result_list, 1):
            logger.info(f"--- Result #{i} (Score: {result.score:.4f}) ---")
            logger.info(f"Title: {result.metadata.title}")
            logger.info(f"Subject: {result.metadata.subject}")
            logger.info(f"Year: {result.metadata.year}")
            logger.info(f"Source: {result.source_type}")
            logger.info(f"\nContent Preview (first 200 chars):")
            logger.info(f"{result.text[:200]}...\n")
        
        return result_list
        
    except Exception as e:
        logger.error(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        return []


async def main():
    """Main function."""
    results = await test_search()
    
    if results:
        logger.info("\n" + "="*80)
        logger.info("✅ TEST SUCCESSFUL! RAG is working with crawled data!")
        logger.info("="*80)
    else:
        logger.error("\n" + "="*80)
        logger.error("❌ NO RESULTS FOUND!")
        logger.error("="*80)


if __name__ == "__main__":
    asyncio.run(main())
