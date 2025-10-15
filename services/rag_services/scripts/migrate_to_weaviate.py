#!/usr/bin/env python3
"""
Migration script from FAISS/Chroma to Weaviate.

This script helps migrate existing document embeddings from the old
FAISS/Chroma storage to the new Weaviate vector database.

Usage:
    python scripts/migrate_to_weaviate.py --source ./storage --batch-size 100
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.domain.models import DocumentChunk, DocumentMetadata, DocumentLanguage
from infrastructure.container import get_container

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_legacy_documents(storage_dir: Path) -> List[DocumentChunk]:
    """
    Load documents from legacy FAISS/Chroma storage.
    
    This is a placeholder - you'll need to implement based on your
    actual legacy storage format.
    
    Args:
        storage_dir: Path to legacy storage directory
        
    Returns:
        List of document chunks
    """
    chunks = []
    
    # Example: Load from JSON metadata files
    metadata_dir = storage_dir / "metadata"
    if metadata_dir.exists():
        for json_file in metadata_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Convert to DocumentChunk
                    # Adjust this based on your actual data format
                    for item in data:
                        metadata = DocumentMetadata(
                            doc_id=item.get('doc_id', 'unknown'),
                            chunk_id=item.get('chunk_id'),
                            title=item.get('title'),
                            page=item.get('page'),
                            doc_type=item.get('doc_type'),
                            faculty=item.get('faculty'),
                            year=item.get('year'),
                            subject=item.get('subject'),
                            language=DocumentLanguage(item.get('language', 'vi'))
                        )
                        
                        chunk = DocumentChunk(
                            text=item.get('text', ''),
                            metadata=metadata,
                            chunk_index=item.get('chunk_index', 0)
                        )
                        chunks.append(chunk)
                        
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
                continue
    
    logger.info(f"Loaded {len(chunks)} chunks from legacy storage")
    return chunks


async def migrate_to_weaviate(
    source_dir: str,
    batch_size: int = 100,
    dry_run: bool = False
):
    """
    Migrate documents from legacy storage to Weaviate.
    
    Args:
        source_dir: Source directory containing legacy data
        batch_size: Number of documents to process in each batch
        dry_run: If True, only simulate migration without writing
    """
    logger.info(f"Starting migration from {source_dir}")
    logger.info(f"Batch size: {batch_size}, Dry run: {dry_run}")
    
    # Load legacy documents
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return False
    
    chunks = load_legacy_documents(source_path)
    if not chunks:
        logger.warning("No documents found to migrate")
        return True
    
    # Get Weaviate vector repository
    container = get_container()
    vector_repo = container.get_vector_repository()
    
    # Process in batches
    total_chunks = len(chunks)
    successful = 0
    failed = 0
    
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total_chunks + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would index {len(batch)} chunks")
            successful += len(batch)
        else:
            try:
                result = await vector_repo.index_documents(batch)
                if result:
                    successful += len(batch)
                    logger.info(f"Successfully indexed batch {batch_num}")
                else:
                    failed += len(batch)
                    logger.error(f"Failed to index batch {batch_num}")
            except Exception as e:
                failed += len(batch)
                logger.error(f"Error indexing batch {batch_num}: {e}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info("=" * 60)
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Success rate: {successful/total_chunks*100:.2f}%")
    
    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Migrate documents from FAISS/Chroma to Weaviate"
    )
    parser.add_argument(
        '--source',
        type=str,
        default='./storage',
        help='Source directory containing legacy data'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of documents to process in each batch'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without writing to Weaviate'
    )
    
    args = parser.parse_args()
    
    # Run migration
    success = asyncio.run(migrate_to_weaviate(
        source_dir=args.source,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
