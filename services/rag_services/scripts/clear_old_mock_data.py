#!/usr/bin/env python3
"""Clear old mock data from Neo4j, keep only new extracted data."""
from neo4j import GraphDatabase
import sys

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "uitchatbot"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("\n" + "="*80)
print("🧹 CLEAR OLD MOCK DATA FROM NEO4J")
print("="*80)

# Labels to remove (old mock data)
OLD_LABELS = [
    'MON_HOC', 
    'CHUONG_TRINH_DAO_TAO', 
    'KHOA', 
    'GIANG_VIEN', 
    'QUY_DINH', 
    'HOC_KY',
    'CATEGORY', 
    'ENTITY_MENTION', 
    'TAG', 
    'DIEU_KIEN', 
    'NGANH',
    'Chapter'  # Old Chapter nodes, we only keep Article, Entity, Rule
]

with driver.session() as session:
    print("\n📊 Current state:")
    for label in OLD_LABELS:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = result.single()["count"]
        if count > 0:
            print(f"   {label}: {count} nodes")
    
    # Count new nodes
    result = session.run("MATCH (n:Article) RETURN count(n) as count")
    articles = result.single()["count"]
    result = session.run("MATCH (n:Entity) RETURN count(n) as count")
    entities = result.single()["count"]
    result = session.run("MATCH (n:Rule) RETURN count(n) as count")
    rules = result.single()["count"]
    
    print(f"\n✅ New extracted data (will be kept):")
    print(f"   Article: {articles}")
    print(f"   Entity: {entities}")
    print(f"   Rule: {rules}")
    
    # Ask for confirmation
    print(f"\n⚠️  This will DELETE all old mock data nodes!")
    print(f"⚠️  New Article, Entity, Rule nodes will be preserved.")
    response = input("\nProceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n❌ Cancelled.")
        driver.close()
        sys.exit(0)
    
    # Delete old nodes
    print("\n🗑️  Deleting old mock data...")
    deleted_total = 0
    total_deleted_nodes = 0
    for label in OLD_LABELS:
        # First count, then delete
        count_result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
        count = count_result.single()["count"]
        if count > 0:
            session.run(f"MATCH (n:{label}) DETACH DELETE n")
            print(f"   ✓ Deleted {count} {label} nodes")
            total_deleted_nodes += count
            deleted_total += 1
        else:
            print(f"   - No {label} nodes to delete")
    
    print(f"\n✅ Deleted {total_deleted_nodes} nodes from {deleted_total} label types")
    
    # Verify
    print("\n📊 After cleanup:")
    result = session.run("MATCH (n:Article) RETURN count(n) as count")
    print(f"   Article: {result.single()['count']}")
    result = session.run("MATCH (n:Entity) RETURN count(n) as count")
    print(f"   Entity: {result.single()['count']}")
    result = session.run("MATCH (n:Rule) RETURN count(n) as count")
    print(f"   Rule: {result.single()['count']}")
    
    # Check remaining labels
    print("\n📋 Remaining labels:")
    result = session.run("CALL db.labels()")
    labels = [record[0] for record in result]
    print(f"   {labels}")

driver.close()
print("\n" + "="*80)
print("✅ Cleanup Complete!")
print("="*80)
print("\n💡 Now open http://localhost:7474 and you should see only Article, Entity, Rule nodes")
print("\n")
