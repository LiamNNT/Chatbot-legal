#!/usr/bin/env python3
"""
Create cross-reference relationships in Neo4j graph.

Detects patterns like:
- "theo Điều 5"
- "quy định tại Điều 10"
- "căn cứ Điều 3"

And creates REFERENCES relationships: Article -[REFERENCES]-> Article
"""

import sys
import os
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from neo4j import GraphDatabase

print("\n" + "="*80)
print("🔗 CREATE CROSS-REFERENCE RELATIONSHIPS")
print("="*80)

# Cross-reference patterns
CROSS_REF_PATTERNS = [
    r'theo\s+Điều\s+(\d+)',
    r'Điều\s+(\d+)\s+của\s+Quy\s+chế',
    r'quy\s+định\s+tại\s+Điều\s+(\d+)',
    r'căn\s+cứ\s+Điều\s+(\d+)',
    r'như\s+quy\s+định\s+tại\s+Điều\s+(\d+)',
    r'được\s+quy\s+định\s+tại\s+Điều\s+(\d+)',
]

# Connect
print("\n📡 Connecting to Neo4j...")
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "uitchatbot"))

# Get all articles
print("\n📥 Fetching articles from Neo4j...")
with neo4j_driver.session() as session:
    result = session.run("MATCH (a:Article) RETURN a.id as id, a.text as text")
    articles = [(record['id'], record['text']) for record in result]

print(f"✅ Found {len(articles)} articles")

# Extract cross-references
print("\n🔍 Extracting cross-references...")
references = []
for article_id, text in articles:
    if not text:
        continue
    
    for pattern in CROSS_REF_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            ref_number = int(match)
            ref_id = f"Điều {ref_number}"
            references.append((article_id, ref_id, pattern))

print(f"✅ Found {len(references)} cross-references")

# Create REFERENCES relationships
print("\n🔗 Creating REFERENCES relationships...")
created_count = 0
with neo4j_driver.session() as session:
    for source_id, target_id, pattern in references:
        # Check if target exists
        result = session.run("""
            MATCH (target:Article {id: $target_id})
            RETURN count(target) as count
        """, {'target_id': target_id})
        
        if result.single()['count'] > 0:
            session.run("""
                MATCH (source:Article {id: $source_id})
                MATCH (target:Article {id: $target_id})
                MERGE (source)-[r:REFERENCES]->(target)
                SET r.pattern = $pattern
            """, {
                'source_id': source_id,
                'target_id': target_id,
                'pattern': pattern
            })
            created_count += 1

print(f"✅ Created {created_count} REFERENCES relationships")

# Verify
print("\n📊 Verification:")
with neo4j_driver.session() as session:
    result = session.run("MATCH ()-[r:REFERENCES]->() RETURN count(r) as count")
    print(f"   Total REFERENCES: {result.single()['count']}")
    
    result = session.run("""
        MATCH (a:Article)-[r:REFERENCES]->(target:Article)
        RETURN a.id as source, target.id as target
        LIMIT 5
    """)
    print("\n   Sample references:")
    for record in result:
        print(f"      {record['source']} -> {record['target']}")

neo4j_driver.close()

print("\n" + "="*80)
print("✅ CROSS-REFERENCES CREATED SUCCESSFULLY!")
print("="*80 + "\n")
