#!/usr/bin/env python3
"""Clear ALL data from Neo4j to start fresh."""
from neo4j import GraphDatabase
import sys

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "uitchatbot"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("\n" + "="*80)
print("🧹 CLEAR ALL DATA FROM NEO4J")
print("="*80)

with driver.session() as session:
    # Count current nodes
    result = session.run("MATCH (n) RETURN count(n) as count")
    total = result.single()["count"]
    
    print(f"\n📊 Current state:")
    print(f"   Total nodes: {total}")
    
    if total == 0:
        print("\n✅ Database already empty!")
        driver.close()
        sys.exit(0)
    
    # Ask for confirmation
    print(f"\n⚠️  This will DELETE ALL {total} nodes and relationships!")
    response = input("\nProceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n❌ Cancelled.")
        driver.close()
        sys.exit(0)
    
    # Delete everything
    print("\n🗑️  Deleting all nodes and relationships...")
    session.run("MATCH (n) DETACH DELETE n")
    
    # Verify
    result = session.run("MATCH (n) RETURN count(n) as count")
    remaining = result.single()["count"]
    
    print(f"\n✅ Deleted all data!")
    print(f"   Remaining nodes: {remaining}")

driver.close()
print("\n" + "="*80)
print("✅ Neo4j is now empty and ready for fresh extraction!")
print("="*80 + "\n")
