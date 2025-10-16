#!/usr/bin/env python3
"""
Test search with newly indexed crawled data.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

sys.path.insert(0, str(project_root))

from core.container import DIContainer
from core.domain.models import SearchQuery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_search(query: str):
    """Test search with a query."""
    logger.info(f"\n{'='*80}")
    logger.info(f"🔍 Query: {query}")
    logger.info(f"{'='*80}")
    
    try:
        # Get vector repository from container
        container = DIContainer()
        vector_repo = container.get_vector_repository()
        
        # Create search query object
        search_query = SearchQuery(
            text=query,
            top_k=3,
            filters={}
        )
        
        # Search
        results = await vector_repo.search(search_query)
        
        logger.info(f"\n📊 Found {len(results)} results:\n")
        
        for i, result in enumerate(results, 1):
            logger.info(f"--- Result #{i} (Score: {result.score:.4f}) ---")
            logger.info(f"Title: {result.metadata.title}")
            logger.info(f"Subject: {result.metadata.subject}")
            logger.info(f"Year: {result.metadata.year}")
            logger.info(f"Cohort: {result.metadata.extra.get('cohort', 'N/A')}")
            logger.info(f"Doc Type: {result.metadata.doc_type}")
            logger.info(f"URL: {result.metadata.extra.get('url', 'N/A')}")
            logger.info(f"\nContent Preview (first 300 chars):")
            logger.info(f"{result.text[:300]}...")
            logger.info("")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error during search: {e}")
        import traceback
        traceback.print_exc()
        return []


async def main():
    """Main function."""
    logger.info("="*80)
    logger.info("TEST SEARCH WITH CRAWLED DATA")
    logger.info("="*80)
    
    # Test queries about KHMT 2024
    test_queries = [
        "Chương trình đào tạo Khoa học Máy tính khóa 19",
        "Cấu trúc chương trình đào tạo KHMT 2024",
        "Học phần bắt buộc ngành Khoa học Máy tính",
        "Điều kiện tốt nghiệp ngành KHMT",
    ]
    
    for query in test_queries:
        results = await test_search(query)
        
        # Wait a bit between queries
        await asyncio.sleep(1)
    
    logger.info("\n" + "="*80)
    logger.info("✅ TESTING COMPLETE!")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
