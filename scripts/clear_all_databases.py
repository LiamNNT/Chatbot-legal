#!/usr/bin/env python3
"""
Script to clear ALL data from Qdrant, Neo4j, and OpenSearch.
Use this to start fresh with clean databases.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def clear_qdrant():
    """Clear all data from Qdrant."""
    print("\n" + "="*60)
    print("🔵 CLEARING QDRANT")
    print("="*60)
    
    try:
        import os
        from qdrant_client import QdrantClient

        qdrant_url = os.getenv("QDRANT_URL", "https://2ee9a81c-be7d-484a-93cf-2f229545d6a4.us-east-1-1.aws.cloud.qdrant.io/")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key or None)
        collections = client.get_collections().collections

        if collections:
            for col in collections:
                info = client.get_collection(col.name)
                count = info.points_count
                print(f"📊 Collection '{col.name}': {count} points")
                if count and count > 0:
                    print(f"🗑️  Deleting collection '{col.name}'...")
                    client.delete_collection(col.name)
                    print(f"✅ Deleted collection '{col.name}'")
                else:
                    print(f"✅ Collection '{col.name}' already empty")
        else:
            print("⚠️  No collections found in Qdrant")

        client.close()
        print("✅ Qdrant cleared successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing Qdrant: {e}")
        return False


def clear_neo4j():
    """Clear all data from Neo4j."""
    print("\n" + "="*60)
    print("🟢 CLEARING NEO4J")
    print("="*60)
    
    try:
        from neo4j import GraphDatabase
        import os
        
        uri = os.getenv("NEO4J_URI", "")
        user = os.getenv("NEO4J_USERNAME", "")
        password = os.getenv("NEO4J_PASSWORD", "")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Count current nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            total = result.single()["count"]
            print(f"📊 Current nodes: {total}")
            
            if total > 0:
                # Delete all nodes and relationships
                session.run("MATCH (n) DETACH DELETE n")
                print(f"✅ Deleted {total} nodes and their relationships")
            else:
                print("✅ Database already empty")
        
        driver.close()
        print("✅ Neo4j cleared successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing Neo4j: {e}")
        return False


def clear_opensearch():
    """Clear all data from OpenSearch."""
    print("\n" + "="*60)
    print("🟡 CLEARING OPENSEARCH")
    print("="*60)
    
    try:
        from app.ingest.store.opensearch.client import OpenSearchClient
        
        client = OpenSearchClient()
        
        # Count documents before deletion
        try:
            count_result = client.client.count(index=client.index_name)
            doc_count = count_result.get("count", 0)
            print(f"📊 Current documents in '{client.index_name}': {doc_count}")
        except Exception:
            doc_count = 0
            print("📊 Index may not exist or is empty")
        
        if doc_count > 0:
            # Delete all documents
            result = client.client.delete_by_query(
                index=client.index_name,
                body={"query": {"match_all": {}}}
            )
            deleted = result.get("deleted", 0)
            print(f"✅ Deleted {deleted} documents")
            
            # Refresh index
            client.client.indices.refresh(index=client.index_name)
        else:
            print("✅ Index already empty")
        
        print("✅ OpenSearch cleared successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing OpenSearch: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("🧹 CLEARING ALL DATABASES")
    print("="*60)
    print("\n⚠️  This will DELETE ALL data from:")
    print("   - Qdrant (Vector Store)")
    print("   - Neo4j (Graph Database)")
    print("   - OpenSearch (Text Search)")
    
    response = input("\n❓ Are you sure? (y/yes): ")
    
    if response.lower() not in ('yes', 'y'):
        print("\n❌ Cancelled.")
        return
    
    print("\n🚀 Starting cleanup...\n")
    
    results = {
        "Qdrant": clear_qdrant(),
        "Neo4j": clear_neo4j(),
        "OpenSearch": clear_opensearch()
    }
    
    print("\n" + "="*60)
    print("📋 SUMMARY")
    print("="*60)
    
    for db, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"   {db}: {status}")
    
    all_success = all(results.values())
    
    if all_success:
        print("\n🎉 All databases cleared successfully!")
    else:
        print("\n⚠️  Some databases failed to clear. Check errors above.")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
