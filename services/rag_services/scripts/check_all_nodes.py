#!/usr/bin/env python3
"""Check all nodes in Neo4j to see what's really there."""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "uitchatbot"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("\n" + "="*80)
print("🔍 CHECKING ALL NODES IN NEO4J")
print("="*80)

with driver.session() as session:
    # Get all labels
    print("\n📋 All labels in database:")
    result = session.run("CALL db.labels()")
    all_labels = [record[0] for record in result]
    print(f"   {all_labels}")
    
    # Count nodes for each label
    print("\n📊 Node counts by label:")
    total_nodes = 0
    for label in all_labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        if count > 0:
            print(f"   ✓ {label}: {count} nodes")
            total_nodes += count
        else:
            print(f"   - {label}: 0 nodes (label exists but empty)")
    
    print(f"\n📊 Total nodes: {total_nodes}")
    
    # Sample from each non-empty label
    print("\n🔍 Sample data from non-empty labels:")
    for label in all_labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        if count > 0:
            print(f"\n   {label} (showing 3 samples):")
            sample = session.run(f"""
                MATCH (n:{label})
                RETURN n
                LIMIT 3
            """)
            for i, record in enumerate(sample, 1):
                node = record["n"]
                # Get all properties
                props = dict(node.items())
                print(f"      {i}. {props}")

driver.close()
print("\n" + "="*80)
print("✅ Done!")
print("="*80 + "\n")
