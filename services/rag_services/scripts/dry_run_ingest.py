#!/usr/bin/env python3
"""
scripts/dry_run_ingest.py

Dry-run script to verify ingest pipeline configuration without actually indexing.
Shows:
- Number of chunks parsed
- Target Weaviate collection name
- Target OpenSearch index name
- Sample chunk metadata (first 2)
- Connection status for both databases
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.shared.config.settings import settings
from app.ingest.store.vector.weaviate_store import (
    get_weaviate_client, 
    get_collection_name,
    ensure_collection_exists
)
from app.ingest.store.opensearch.client import get_opensearch_client
from app.ingest.loaders.vietnam_legal_docx_parser import VietnamLegalDocxParser


def check_weaviate_connection() -> dict:
    """Check Weaviate connection and collection status."""
    result = {
        "connected": False,
        "url": settings.weaviate_url,
        "collection_name": get_collection_name(),
        "collection_exists": False,
        "document_count": 0,
        "error": None
    }
    
    try:
        client = get_weaviate_client(url=settings.weaviate_url)
        
        if client.is_ready():
            result["connected"] = True
            
            coll_name = get_collection_name()
            if client.collections.exists(coll_name):
                result["collection_exists"] = True
                collection = client.collections.get(coll_name)
                count = collection.aggregate.over_all(total_count=True).total_count
                result["document_count"] = count
            else:
                result["error"] = f"Collection '{coll_name}' does not exist. Will be created on first index."
        else:
            result["error"] = "Weaviate not ready"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def check_opensearch_connection() -> dict:
    """Check OpenSearch connection and index status."""
    result = {
        "connected": False,
        "host": f"{settings.opensearch_host}:{settings.opensearch_port}",
        "index_name": settings.opensearch_index,
        "index_exists": False,
        "document_count": 0,
        "error": None
    }
    
    try:
        os_client = get_opensearch_client()
        
        # OpenSearchClient wraps the actual client - use .client for raw access
        raw_client = os_client.client if hasattr(os_client, 'client') else os_client
        
        if raw_client.ping():
            result["connected"] = True
            
            if raw_client.indices.exists(index=settings.opensearch_index):
                result["index_exists"] = True
                count_resp = raw_client.count(index=settings.opensearch_index)
                result["document_count"] = count_resp.get("count", 0)
            else:
                result["error"] = f"Index '{settings.opensearch_index}' does not exist. Will be created on first index."
        else:
            result["error"] = "OpenSearch not responding"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


def dry_run_parse(file_path: str, law_id: str = None) -> dict:
    """Parse a file and return summary without indexing."""
    result = {
        "success": False,
        "file": file_path,
        "chunk_count": 0,
        "chapters_count": 0,
        "articles_count": 0,
        "sample_chunks": [],
        "chapters_found": [],
        "error": None
    }
    
    try:
        parser = VietnamLegalDocxParser()
        parse_result = parser.parse(Path(file_path), law_id=law_id)
        
        if not parse_result.success:
            result["error"] = f"Parse failed: {parse_result.errors}"
            return result
        
        result["success"] = True
        result["chunk_count"] = len(parse_result.chunks)
        result["chapters_count"] = parse_result.statistics.get("chapters", 0)
        result["articles_count"] = parse_result.statistics.get("articles", 0)
        
        # Get unique chapters
        chapters = set()
        for chunk in parse_result.chunks:
            ch = chunk.metadata.get("chapter_id")
            if ch:
                chapters.add(ch)
        result["chapters_found"] = sorted(chapters)
        
        # Sample first 2 chunks
        for chunk in parse_result.chunks[:2]:
            result["sample_chunks"].append({
                "chunk_id": chunk.chunk_id,
                "embedding_prefix": chunk.embedding_prefix,
                "metadata": {k: v for k, v in chunk.metadata.items() if v is not None},
                "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
            })
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def main():
    print("=" * 70)
    print("RAG PIPELINE DRY-RUN CHECK")
    print("=" * 70)
    
    # Check settings
    print("\n📋 CONFIGURATION:")
    print(f"   Vector Backend: {settings.vector_backend}")
    print(f"   Dual Index Enabled: {getattr(settings, 'enable_dual_index', False)}")
    
    # Check Weaviate
    print("\n🔷 WEAVIATE STATUS:")
    weaviate_status = check_weaviate_connection()
    print(f"   URL: {weaviate_status['url']}")
    print(f"   Collection: {weaviate_status['collection_name']}")
    print(f"   Connected: {'✅' if weaviate_status['connected'] else '❌'}")
    print(f"   Collection Exists: {'✅' if weaviate_status['collection_exists'] else '❌'}")
    print(f"   Document Count: {weaviate_status['document_count']}")
    if weaviate_status['error']:
        print(f"   ⚠️  Warning: {weaviate_status['error']}")
    
    # Check OpenSearch
    print("\n🔶 OPENSEARCH STATUS:")
    opensearch_status = check_opensearch_connection()
    print(f"   Host: {opensearch_status['host']}")
    print(f"   Index: {opensearch_status['index_name']}")
    print(f"   Connected: {'✅' if opensearch_status['connected'] else '❌'}")
    print(f"   Index Exists: {'✅' if opensearch_status['index_exists'] else '❌'}")
    print(f"   Document Count: {opensearch_status['document_count']}")
    if opensearch_status['error']:
        print(f"   ⚠️  Warning: {opensearch_status['error']}")
    
    # Parse test file if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        law_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        print(f"\n📄 PARSING FILE: {file_path}")
        parse_result = dry_run_parse(file_path, law_id)
        
        if parse_result["success"]:
            print(f"   ✅ Parse successful")
            print(f"   Chunks: {parse_result['chunk_count']}")
            print(f"   Chapters: {parse_result['chapters_count']} ({', '.join(parse_result['chapters_found'])})")
            print(f"   Articles: {parse_result['articles_count']}")
            
            print("\n   📝 SAMPLE CHUNKS:")
            for i, sample in enumerate(parse_result["sample_chunks"], 1):
                print(f"\n   --- Chunk {i} ---")
                print(f"   ID: {sample['chunk_id']}")
                print(f"   Prefix: {sample['embedding_prefix']}")
                print(f"   Metadata: {json.dumps(sample['metadata'], ensure_ascii=False, indent=6)}")
                print(f"   Content: {sample['content_preview']}")
        else:
            print(f"   ❌ Parse failed: {parse_result['error']}")
    else:
        print("\n💡 TIP: Pass a DOCX file path to test parsing:")
        print("   python scripts/dry_run_ingest.py /path/to/file.docx [law_id]")
    
    print("\n" + "=" * 70)
    
    # Return exit code based on connection status
    if not weaviate_status["connected"] and settings.vector_backend == "weaviate":
        print("❌ FAILED: Weaviate not connected but is configured as vector backend")
        return 1
    
    print("✅ Configuration looks good!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
