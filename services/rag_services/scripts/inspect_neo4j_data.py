#!/usr/bin/env python3
"""Inspect Neo4j data in detail to verify real vs mock data."""
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "uitchatbot"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("\n" + "="*80)
print("🔍 DETAILED NEO4J DATA INSPECTION")
print("="*80)

with driver.session() as session:
    # Check all node labels
    print("\n📊 All Node Labels:")
    result = session.run("""
        CALL db.labels()
    """)
    labels = [record[0] for record in result]
    print(f"   Labels found: {labels}")
    
    # Check a few actual Article nodes with full properties
    print("\n📄 Sample Article Nodes (with full properties):")
    result = session.run("""
        MATCH (a:Article)
        RETURN a
        LIMIT 5
    """)
    for i, record in enumerate(result, 1):
        article = record['a']
        print(f"\n   Article {i}:")
        for key, value in dict(article).items():
            if isinstance(value, str) and len(value) > 100:
                print(f"      {key}: {value[:100]}...")
            else:
                print(f"      {key}: {value}")
    
    # Check for mock data patterns
    print("\n🔍 Checking for Mock Data Patterns:")
    result = session.run("""
        MATCH (a:Article)
        WHERE a.id CONTAINS 'mock' OR a.title CONTAINS 'mock' OR a.title CONTAINS 'Mock'
        RETURN count(a) as count
    """)
    mock_articles = result.single()["count"]
    print(f"   Articles with 'mock' in id or title: {mock_articles}")
    
    # Check actual article IDs
    print("\n📋 All Article IDs:")
    result = session.run("""
        MATCH (a:Article)
        RETURN a.id as id, a.title as title
        ORDER BY a.id
    """)
    for record in result:
        title = record['title'][:50] + "..." if record['title'] and len(record['title']) > 50 else record['title']
        print(f"   {record['id']}: {title}")
    
    # Check if there are any relationships
    print("\n🔗 Relationship Details:")
    result = session.run("""
        MATCH (a:Article)-[r]->(x)
        RETURN type(r) as rel_type, labels(x)[0] as target_label, count(*) as count
    """)
    for record in result:
        print(f"   Article -[{record['rel_type']}]-> {record['target_label']}: {record['count']}")
    
    # Check specific entities with their source article
    print("\n👥 Entities with their source Articles:")
    result = session.run("""
        MATCH (a:Article)-[:MENTIONS]->(e:Entity)
        RETURN a.id as article_id, e.name as entity_name, e.type as entity_type
        LIMIT 10
    """)
    for record in result:
        print(f"   {record['article_id']} -> {record['entity_name']} ({record['entity_type']})")

driver.close()
print("\n" + "="*80)
print("✅ Inspection Complete!")
print("="*80 + "\n")
