#!/usr/bin/env python3
"""
Build Neo4j Knowledge Graph from Weaviate indexed data.

Creates:
1. Chapter nodes
2. Article nodes
3. Hierarchical relationships: Chapter -[HAS_ARTICLE]-> Article
4. Sequential relationships: Article -[NEXT_ARTICLE]-> Article
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.store.vector.weaviate_store import get_weaviate_client
from neo4j import GraphDatabase
from weaviate.classes.query import Filter
from collections import defaultdict

print("\n" + "="*80)
print("📊 BUILD NEO4J GRAPH FROM WEAVIATE DATA")
print("="*80)

# Connect
print("\n📡 Connecting to databases...")
weaviate = get_weaviate_client("http://localhost:8090")
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "uitchatbot"))
collection = weaviate.collections.get("VietnameseDocumentV3")

# Fetch all articles
print("\n📥 Fetching articles from Weaviate V3...")
all_docs = []
offset = 0
while True:
    response = collection.query.fetch_objects(
        limit=50,
        offset=offset,
        filters=Filter.by_property("structure_type").equal("article")
    )
    if not response.objects:
        break
    all_docs.extend(response.objects)
    offset += 50

articles = [obj for obj in all_docs if obj.properties.get('structure_type') == 'article']
print(f"✅ Found {len(articles)} articles")

# Group by chapter
chapters_map = defaultdict(list)
for obj in articles:
    chapter = obj.properties.get('chapter', 'Unknown')
    chapters_map[chapter].append(obj)

print(f"✅ Found {len(chapters_map)} chapters")

# Build graph
print("\n🏗️  Building Neo4j graph...")
with neo4j_driver.session() as session:
    # Create Chapter nodes
    print("\n1️⃣  Creating Chapter nodes...")
    for chapter_name in sorted(chapters_map.keys()):
        session.run("""
            MERGE (c:Chapter {name: $chapter_name})
            SET c.title = $chapter_name
        """, {'chapter_name': chapter_name})
    print(f"   ✅ Created {len(chapters_map)} chapters")
    
    # Create Article nodes and relationships
    print("\n2️⃣  Creating Article nodes and HAS_ARTICLE relationships...")
    article_count = 0
    for chapter_name, chapter_articles in chapters_map.items():
        for obj in chapter_articles:
            p = obj.properties
            session.run("""
                MERGE (a:Article {id: $article_id})
                SET a.title = $title,
                    a.text = $text,
                    a.article_number = $article_number,
                    a.chapter = $chapter,
                    a.filename = $filename,
                    a.doc_id = $doc_id
                
                MERGE (c:Chapter {name: $chapter})
                MERGE (c)-[:HAS_ARTICLE]->(a)
            """, {
                'article_id': p.get('article', 'Unknown'),
                'title': p.get('title', ''),
                'text': p.get('text', ''),
                'article_number': p.get('article_number', 0),
                'chapter': p.get('chapter', ''),
                'filename': p.get('filename', ''),
                'doc_id': p.get('doc_id', '')
            })
            article_count += 1
    print(f"   ✅ Created {article_count} articles with HAS_ARTICLE links")
    
    # Create NEXT_ARTICLE relationships
    print("\n3️⃣  Creating NEXT_ARTICLE sequential relationships...")
    next_count = 0
    for chapter_name, chapter_articles in chapters_map.items():
        # Sort by article number
        sorted_articles = sorted(
            chapter_articles,
            key=lambda x: x.properties.get('article_number', 0)
        )
        
        # Create NEXT links
        for i in range(len(sorted_articles) - 1):
            curr_id = sorted_articles[i].properties.get('article', 'Unknown')
            next_id = sorted_articles[i+1].properties.get('article', 'Unknown')
            
            session.run("""
                MATCH (a1:Article {id: $curr_id})
                MATCH (a2:Article {id: $next_id})
                MERGE (a1)-[:NEXT_ARTICLE]->(a2)
            """, {'curr_id': curr_id, 'next_id': next_id})
            next_count += 1
    print(f"   ✅ Created {next_count} NEXT_ARTICLE links")

# Verify
print("\n📊 Verification:")
with neo4j_driver.session() as session:
    result = session.run("MATCH (c:Chapter) RETURN count(c) as count")
    print(f"   Chapters: {result.single()['count']}")
    
    result = session.run("MATCH (a:Article) RETURN count(a) as count")
    print(f"   Articles: {result.single()['count']}")
    
    result = session.run("MATCH ()-[r:HAS_ARTICLE]->() RETURN count(r) as count")
    print(f"   HAS_ARTICLE: {result.single()['count']}")
    
    result = session.run("MATCH ()-[r:NEXT_ARTICLE]->() RETURN count(r) as count")
    print(f"   NEXT_ARTICLE: {result.single()['count']}")

neo4j_driver.close()
weaviate.close()

print("\n" + "="*80)
print("✅ GRAPH STRUCTURE BUILT SUCCESSFULLY!")
print("="*80 + "\n")
