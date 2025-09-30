#!/usr/bin/env python3
# scripts/sync_to_opensearch.py
#
# Description:
# Script to synchronize documents from the vector store to OpenSearch for BM25 indexing.
# This script extracts documents from LlamaIndex and indexes them in OpenSearch.

import os
import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings
from retrieval.engine import _load_or_create_index, _ensure_settings

try:
    from store.opensearch.client import get_opensearch_client
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    print("OpenSearch dependencies not available. Install with: pip install opensearch-py")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_documents_to_opensearch():
    """
    Sync all documents from the vector index to OpenSearch.
    """
    if not OPENSEARCH_AVAILABLE:
        logger.error("OpenSearch not available")
        return False
    
    try:
        # Initialize components
        logger.info("Initializing vector index...")
        _ensure_settings()
        vector_index = _load_or_create_index()
        
        logger.info("Initializing OpenSearch client...")
        opensearch_client = get_opensearch_client()
        
        # Check OpenSearch health
        if not opensearch_client.health_check():
            logger.error("OpenSearch is not healthy")
            return False
        
        # Get documents from vector store
        logger.info("Extracting documents from vector store...")
        
        # Get all document IDs from the index
        docstore = vector_index.storage_context.docstore
        all_docs = docstore.docs
        
        if not all_docs:
            logger.warning("No documents found in vector store")
            return True
        
        logger.info(f"Found {len(all_docs)} documents in vector store")
        
        # Prepare documents for OpenSearch
        opensearch_docs = []
        for doc_id, doc in all_docs.items():
            metadata = doc.metadata or {}
            
            # Extract relevant information
            doc_name = metadata.get("file_name", doc_id)
            chunk_id = metadata.get("chunk_id", doc_id)
            page = metadata.get("page")
            
            opensearch_doc = {
                "doc_id": doc_name,
                "chunk_id": chunk_id,
                "text": doc.get_content(),
                "metadata": {
                    "file_name": doc_name,
                    "page": page,
                    "doc_id": doc_id,
                    **{k: v for k, v in metadata.items() if k not in ["file_name", "page", "doc_id"]}
                }
            }
            opensearch_docs.append(opensearch_doc)
        
        # Bulk index documents
        logger.info(f"Indexing {len(opensearch_docs)} documents to OpenSearch...")
        success_count, failed_count = opensearch_client.bulk_index_documents(opensearch_docs)
        
        logger.info(f"Indexing completed: {success_count} successful, {failed_count} failed")
        
        # Show index statistics
        stats = opensearch_client.get_index_stats()
        logger.info(f"Index now contains {stats['total_docs']} documents")
        
        return failed_count == 0
        
    except Exception as e:
        logger.error(f"Error syncing documents to OpenSearch: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting document synchronization to OpenSearch...")
    
    success = sync_documents_to_opensearch()
    
    if success:
        logger.info("✅ Document synchronization completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Document synchronization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
