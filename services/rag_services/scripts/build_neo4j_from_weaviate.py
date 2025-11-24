#!/usr/bin/env python3
"""Build Neo4j graph from Weaviate V3 structures."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.store.vector.weaviate_store import get_weaviate_client
from neo4j import GraphDatabase

print("\n" + "="*80)
print("🏗️  BUILD NEO4J KNOWLEDGE GRAPH FROM WEAVIATE V3")
print("="*80)

# Connect
print("\n�� Connecting...")
weaviate = get_weaviate_client("http://localhost:8090")
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "uitchatbot"))
collection = weaviate.collections.get("VietnameseDocumentV3")

# Get all objects
print("📥 Fetching from Weaviate V3...")
all_docs = []
offset = 0
while True:
    response = collection.query.fetch_objects(limit=50, offset=offset)
    if not response.objects:
        break
    all_docs.extend(response.objects)
    offset += 50

print(f"✅ Total: {len(all_docs)} structural elements")

# Build graph
print(f"\n🏗️  Building Neo4j graph...")

with neo4j_driver.session() as session:
    # Create nodes
    article_count = 0
    chapter_count = 0
    
    for obj in all_docs:
        p = obj.properties
        struct_type = p.get('structure_type', '')
        
        if struct_type == 'article':
            # Create Article node
            session.run("""
                MERGE (a:Article {id: $article_id})
                SET a.title = $title,
                    a.text = $text,
                    a.article_number = $article_number,
                    a.chapter = $chapter,
                    a.doc_id = $doc_id,
                    a.filename = $filename
            """, 
                article_id=p.get('article', ''),
                title=p.get('title', ''),
                text=p.get('text', ''),
                article_number=p.get('article_number', 0),
                chapter=p.get('chapter', ''),
                doc_id=p.get('doc_id', ''),
                filename=p.get('filename', '')
            )
            article_count += 1
            
        elif struct_type == 'chapter':
            # Create Chapter node
            session.run("""
                MERGE (c:Chapter {id: $chapter_id})
                SET c.title = $title,
                    c.text = $text,
                    c.doc_id = $doc_id,
                    c.filename = $filename
            """,
                chapter_id=p.get('chapter', ''),
                title=p.get('title', ''),
                text=p.get('text', ''),
                doc_id=p.get('doc_id', ''),
                filename=p.get('filename', '')
            )
            chapter_count += 1
        
        if (article_count + chapter_count) % 10 == 0:
            print(f"   Created {article_count} articles, {chapter_count} chapters...")
    
    print(f"\n✅ Created {article_count} Article nodes")
    print(f"✅ Created {chapter_count} Chapter nodes")
    
    # Create relationships
    print(f"\n🔗 Building relationships...")
    
    # PART_OF: Article -> Chapter
    result = session.run("""
        MATCH (a:Article), (c:Chapter)
        WHERE a.chapter = c.id
        MERGE (a)-[r:PART_OF]->(c)
        RETURN count(r) as count
    """)
    part_of_count = result.single()['count']
    print(f"✅ Created {part_of_count} PART_OF relationships")

# Verify
with neo4j_driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as count")
    total_nodes = result.single()['count']
    
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    total_rels = result.single()['count']
    
    print(f"\n📊 Neo4j Graph Statistics:")
    print(f"   Total nodes: {total_nodes}")
    print(f"   Total relationships: {total_rels}")

neo4j_driver.close()
weaviate.close()

print("\n🎉 Neo4j graph built successfully!\n")
