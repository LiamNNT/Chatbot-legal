#!/usr/bin/env python3
"""
Improve Weaviate Schema - Flatten Metadata for Better Filtering

This script updates the Weaviate schema to move important metadata fields
from the JSON string `metadata_json` to top-level properties.

Benefits:
- Enable efficient filtering (e.g., WHERE chapter = "Chương 1")
- Improve hybrid search with structured filters
- Better performance for faceted search

Author: Data Quality Improvement Team
Date: November 21, 2025
"""

import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from infrastructure.store.vector.weaviate_store import get_weaviate_client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# New collection name with improved schema
NEW_COLLECTION = "VietnameseDocumentV3"


def create_improved_schema(client: weaviate.WeaviateClient) -> bool:
    """
    Create improved Weaviate schema with flattened metadata.
    
    Key changes from V2:
    1. Flatten important metadata from JSON string to top-level properties
    2. Add filterable fields for chapter_title, article_number, structure_type
    3. Maintain backward compatibility with existing fields
    
    Args:
        client: Connected Weaviate client
        
    Returns:
        True if schema was created successfully
    """
    try:
        # Delete existing collection if it exists
        if client.collections.exists(NEW_COLLECTION):
            logger.warning(f"Collection '{NEW_COLLECTION}' already exists. Deleting...")
            client.collections.delete(NEW_COLLECTION)
            logger.info(f"Deleted existing collection '{NEW_COLLECTION}'")
        
        # Create collection with improved schema
        client.collections.create(
            name=NEW_COLLECTION,
            description="Vietnamese academic documents - V3 with flattened metadata",
            
            # Vectorizer configuration
            vectorizer_config=Configure.Vectorizer.none(),
            
            # Properties
            properties=[
                # ============ CORE TEXT FIELDS ============
                Property(
                    name="text",
                    data_type=DataType.TEXT,
                    description="Document chunk text content",
                    skip_vectorization=True
                ),
                Property(
                    name="doc_id",
                    data_type=DataType.TEXT,
                    description="Document identifier",
                    index_filterable=True,  # Enable filtering
                    index_searchable=False  # Not for text search
                ),
                Property(
                    name="chunk_id",
                    data_type=DataType.TEXT,
                    description="Unique chunk identifier",
                    index_filterable=True,
                    index_searchable=False
                ),
                Property(
                    name="chunk_index",
                    data_type=DataType.INT,
                    description="Chunk position in document"
                ),
                
                # ============ DOCUMENT METADATA ============
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Document title"
                ),
                Property(
                    name="page",
                    data_type=DataType.INT,
                    description="Page number in original document"
                ),
                Property(
                    name="doc_type",
                    data_type=DataType.TEXT,
                    description="Document type (syllabus, regulation, program)",
                    index_filterable=True  # Enable filtering by doc_type
                ),
                Property(
                    name="faculty",
                    data_type=DataType.TEXT,
                    description="Faculty/department (UIT, KHTN, etc.)",
                    index_filterable=True  # Enable filtering by faculty
                ),
                Property(
                    name="year",
                    data_type=DataType.INT,
                    description="Academic year"
                ),
                Property(
                    name="subject",
                    data_type=DataType.TEXT,
                    description="Subject or course code"
                ),
                Property(
                    name="language",
                    data_type=DataType.TEXT,
                    description="Document language (vi, en)"
                ),
                
                # ============ STRUCTURE FIELDS (Flattened from metadata_json) ============
                Property(
                    name="structure_type",
                    data_type=DataType.TEXT,
                    description="Structure type: article, chapter, section, clause",
                    index_filterable=True  # CRITICAL for filtering
                ),
                Property(
                    name="chapter",
                    data_type=DataType.TEXT,
                    description="Chapter identifier (e.g., 'Chương 1')",
                    index_filterable=True  # Enable chapter-based filtering
                ),
                Property(
                    name="chapter_title",
                    data_type=DataType.TEXT,
                    description="Full chapter title"
                ),
                Property(
                    name="article",
                    data_type=DataType.TEXT,
                    description="Article identifier (e.g., 'Điều 6')",
                    index_filterable=True  # Enable article-based filtering
                ),
                Property(
                    name="article_number",
                    data_type=DataType.INT,
                    description="Article number as integer (for sorting/filtering)"
                ),
                Property(
                    name="article_title",
                    data_type=DataType.TEXT,
                    description="Full article title"
                ),
                Property(
                    name="parent_id",
                    data_type=DataType.TEXT,
                    description="Parent structure ID (chapter for article, etc.)",
                    index_filterable=True
                ),
                Property(
                    name="level",
                    data_type=DataType.INT,
                    description="Hierarchy level (1=chapter, 2=article, 3=clause)"
                ),
                
                # ============ KNOWLEDGE GRAPH INTEGRATION ============
                Property(
                    name="kg_node_type",
                    data_type=DataType.TEXT,
                    description="Knowledge Graph node type",
                    index_filterable=True
                ),
                Property(
                    name="kg_node_id",
                    data_type=DataType.TEXT,
                    description="Knowledge Graph node identifier",
                    index_filterable=True
                ),
                
                # ============ ADMINISTRATIVE METADATA ============
                Property(
                    name="source",
                    data_type=DataType.TEXT,
                    description="Data source (pdf_upload, web_scrape, etc.)"
                ),
                Property(
                    name="filename",
                    data_type=DataType.TEXT,
                    description="Original filename"
                ),
                Property(
                    name="issuer",
                    data_type=DataType.TEXT,
                    description="Issuing authority (for regulations)"
                ),
                
                # ============ LEGACY FIELD (for backward compatibility) ============
                Property(
                    name="metadata_json",
                    data_type=DataType.TEXT,
                    description="Full metadata as JSON (for backward compatibility)"
                ),
            ]
        )
        
        logger.info(f"✅ Created collection '{NEW_COLLECTION}' with improved schema")
        logger.info("📊 Key improvements:")
        logger.info("   - Flattened metadata for efficient filtering")
        logger.info("   - Indexed chapter, article, structure_type for hybrid search")
        logger.info("   - Added article_number (INT) for range queries")
        logger.info("   - KG integration fields for Neo4j connectivity")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create improved schema: {e}")
        return False


def print_schema_comparison():
    """Print comparison between old and new schema."""
    
    print("\n" + "="*80)
    print("SCHEMA COMPARISON: V2 vs V3")
    print("="*80)
    
    print("\n🔴 OLD SCHEMA (V2) Issues:")
    print("   ❌ metadata_json is a JSON STRING")
    print("   ❌ Cannot filter by chapter: WHERE chapter = 'Chương 1'")
    print("   ❌ Cannot filter by article_number: WHERE article_number > 10")
    print("   ❌ Cannot filter by structure_type: WHERE structure_type = 'article'")
    print("   ❌ Poor performance for faceted search")
    
    print("\n✅ NEW SCHEMA (V3) Benefits:")
    print("   ✓ Flattened metadata → structured fields")
    print("   ✓ Filterable chapter, article, structure_type")
    print("   ✓ article_number as INT → range queries")
    print("   ✓ Fast hybrid search: Vector + Structured filters")
    print("   ✓ Example: Get all articles in 'Chương 1' about 'học phí'")
    
    print("\n📝 Example Queries Enabled:")
    print("   1. WHERE chapter = 'Chương 1' AND structure_type = 'article'")
    print("   2. WHERE article_number BETWEEN 5 AND 10")
    print("   3. WHERE doc_type = 'regulation' AND issuer = 'Hiệu trưởng'")
    print("   4. Hybrid: vector_search('học phí') + filter(chapter='Chương 2')")
    
    print("\n" + "="*80 + "\n")


def main():
    """Main execution."""
    
    print("\n🚀 Weaviate Schema Improvement")
    print("="*80)
    
    try:
        # Connect to Weaviate
        print("\n📡 Connecting to Weaviate...")
        client = get_weaviate_client('http://localhost:8090')
        
        # Print comparison
        print_schema_comparison()
        
        # Confirm action
        response = input("\n⚠️  Create NEW collection 'VietnameseDocumentV3'? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return
        
        # Create improved schema
        print("\n🔧 Creating improved schema...")
        success = create_improved_schema(client)
        
        if success:
            print("\n✅ SUCCESS! Schema V3 created")
            print("\n📋 Next Steps:")
            print("   1. Run re-indexing script to migrate data from V2 → V3")
            print("   2. Update application code to use new filterable fields")
            print("   3. Test hybrid search with filters")
            print("   4. Deprecate old 'VietnameseDocument' collection")
        else:
            print("\n❌ FAILED to create schema")
        
        # Close client
        client.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
