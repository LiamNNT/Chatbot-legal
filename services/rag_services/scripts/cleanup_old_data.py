#!/usr/bin/env python3
"""
Script to clean up old data from Weaviate and Neo4j before re-indexing.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.store.vector.weaviate_store import get_weaviate_client
from neo4j import GraphDatabase
import weaviate.classes as wvc


def cleanup_weaviate():
    """Delete old Weaviate collections."""
    print("\n" + "="*80)
    print("🧹 CLEANING UP WEAVIATE")
    print("="*80)
    
    try:
        client = get_weaviate_client("http://localhost:8090")
        
        # List all collections
        collections = client.collections.list_all()
        collection_names = [name for name in collections.keys()]
        
        print(f"\n📋 Found {len(collection_names)} collections:")
        for name in collection_names:
            print(f"  - {name}")
        
        # Delete old collections (keep V3 if it exists)
        deleted = []
        for name in collection_names:
            if name != "VietnameseDocumentV3":
                try:
                    client.collections.delete(name)
                    deleted.append(name)
                    print(f"  ✅ Deleted: {name}")
                except Exception as e:
                    print(f"  ⚠️  Failed to delete {name}: {e}")
        
        # If VietnameseDocumentV3 exists, clear its data
        if "VietnameseDocumentV3" in collection_names:
            try:
                collection = client.collections.get("VietnameseDocumentV3")
                
                # Delete all objects
                collection.data.delete_many(
                    where=wvc.query.Filter.by_property("document_id").like("*")
                )
                print(f"  ✅ Cleared all objects from: VietnameseDocumentV3")
            except Exception as e:
                print(f"  ⚠️  Failed to clear VietnameseDocumentV3: {e}")
                # If clearing fails, delete and we'll recreate
                try:
                    client.collections.delete("VietnameseDocumentV3")
                    deleted.append("VietnameseDocumentV3")
                    print(f"  ✅ Deleted: VietnameseDocumentV3 (will recreate)")
                except Exception as e2:
                    print(f"  ❌ Failed to delete VietnameseDocumentV3: {e2}")
        
        client.close()
        
        print(f"\n✅ Weaviate cleanup complete!")
        print(f"   Deleted {len(deleted)} collections")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Weaviate cleanup failed: {e}")
        return False


def cleanup_neo4j():
    """Delete all nodes and relationships from Neo4j."""
    print("\n" + "="*80)
    print("🧹 CLEANING UP NEO4J")
    print("="*80)
    
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "uitchatbot")
        )
        
        with driver.session() as session:
            # Count before deletion
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            print(f"\n📊 Current state:")
            print(f"   Nodes: {node_count:,}")
            print(f"   Relationships: {rel_count:,}")
            
            if node_count == 0 and rel_count == 0:
                print("\n✅ Neo4j is already empty!")
                driver.close()
                return True
            
            # Delete all relationships first
            print(f"\n🗑️  Deleting relationships...")
            session.run("MATCH ()-[r]->() DELETE r")
            
            # Delete all nodes
            print(f"🗑️  Deleting nodes...")
            session.run("MATCH (n) DELETE n")
            
            # Verify deletion
            result = session.run("MATCH (n) RETURN count(n) as count")
            final_count = result.single()["count"]
            
            if final_count == 0:
                print(f"\n✅ Neo4j cleanup complete!")
                print(f"   Deleted {node_count:,} nodes")
                print(f"   Deleted {rel_count:,} relationships")
            else:
                print(f"\n⚠️  Warning: {final_count} nodes still remain")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Neo4j cleanup failed: {e}")
        return False


def main():
    """Main cleanup function."""
    print("\n" + "="*80)
    print("🧹 CLEANUP OLD DATA BEFORE RE-INDEXING")
    print("="*80)
    print("\nThis will DELETE ALL data from:")
    print("  - Weaviate (all collections except VietnameseDocumentV3 schema)")
    print("  - Neo4j (all nodes and relationships)")
    print("\n⚠️  THIS CANNOT BE UNDONE!")
    
    # Ask for confirmation
    response = input("\nProceed with cleanup? [y/N]: ").strip().lower()
    if response != 'y':
        print("\n❌ Cleanup cancelled.")
        return
    
    # Cleanup Weaviate
    weaviate_success = cleanup_weaviate()
    
    # Cleanup Neo4j
    neo4j_success = cleanup_neo4j()
    
    # Summary
    print("\n" + "="*80)
    print("📊 CLEANUP SUMMARY")
    print("="*80)
    print(f"Weaviate: {'✅ Success' if weaviate_success else '❌ Failed'}")
    print(f"Neo4j:    {'✅ Success' if neo4j_success else '❌ Failed'}")
    
    if weaviate_success and neo4j_success:
        print("\n✅ Cleanup complete! Ready for re-indexing.")
        print("\nNext steps:")
        print("  1. python scripts/improve_weaviate_schema.py")
        print("  2. python scripts/reindex_with_improvements.py")
        print("  3. python scripts/build_cross_references.py")
    else:
        print("\n⚠️  Some cleanup operations failed. Check errors above.")


if __name__ == "__main__":
    main()
