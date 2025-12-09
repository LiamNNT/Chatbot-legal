#!/usr/bin/env python3
"""Test if Neo4j has data and can be queried"""
import sys
import os
import asyncio
from pathlib import Path

# Add rag_services to path
orchestrator_path = Path(__file__).parent
rag_services_path = orchestrator_path.parent / "rag_services"
sys.path.insert(0, str(rag_services_path))

# Load env from rag_services
from dotenv import load_dotenv
env_path = rag_services_path / ".env"
load_dotenv(env_path)

print(f"🔍 Loading env from: {env_path}")
print(f"🔍 Neo4j URI: {os.getenv('NEO4J_URI')}\n")


async def main():
    try:
        from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
        
        # Connect to Neo4j
        adapter = Neo4jGraphAdapter(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "uitchatbot"),
            database=os.getenv("NEO4J_DATABASE", "neo4j")
        )
        
        print("✅ Neo4j connected!\n")
        
        # Test 1: Count all nodes
        print("="*80)
        print("TEST 1: Count all nodes in Neo4j")
        print("="*80)
        
        cypher = "MATCH (n) RETURN count(n) as total"
        result = await adapter.execute_cypher(cypher, {})
        if result:
            total = result[0]['total']
            print(f"✅ Total nodes: {total}\n")
        else:
            print("❌ No results\n")
        
        # Test 2: Get node labels
        print("="*80)
        print("TEST 2: Get all node labels (types)")
        print("="*80)
        
        cypher = "CALL db.labels() YIELD label RETURN label"
        result = await adapter.execute_cypher(cypher, {})
        labels = []
        if result:
            labels = [r['label'] for r in result]
            print(f"✅ Found {len(labels)} node types:")
            for label in labels:
                print(f"   - {label}")
        
        # Test 3: Count nodes by label
        print("\n" + "="*80)
        print("TEST 3: Count nodes by type")
        print("="*80)
        
        for label in labels[:10]:  # Show first 10
            cypher = f"MATCH (n:{label}) RETURN count(n) as count"
            result = await adapter.execute_cypher(cypher, {})
            if result:
                count = result[0]['count']
                print(f"   {label}: {count} nodes")
        
        # Test 4: Get relationship types
        print("\n" + "="*80)
        print("TEST 4: Get all relationship types")
        print("="*80)
        
        cypher = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        result = await adapter.execute_cypher(cypher, {})
        rel_types = []
        if result:
            rel_types = [r['relationshipType'] for r in result]
            print(f"✅ Found {len(rel_types)} relationship types:")
            for rel in rel_types:
                print(f"   - {rel}")
        
        # Test 5: Sample articles with YEU_CAU or QUY_DINH_DIEU_KIEN relationships
        print("\n" + "="*80)
        print("TEST 5: Find articles with YEU_CAU or QUY_DINH_DIEU_KIEN relationships")
        print("="*80)
        
        cypher = """
        MATCH (a1)-[r:YEU_CAU|QUY_DINH_DIEU_KIEN]->(a2)
        RETURN a1.number as from_article, type(r) as relationship, a2.number as to_article
        LIMIT 10
        """
        result = await adapter.execute_cypher(cypher, {})
        if result:
            print(f"✅ Found {len(result)} relationships:")
            for r in result:
                print(f"   Điều {r['from_article']} --[{r['relationship']}]--> Điều {r['to_article']}")
        else:
            print("❌ No YEU_CAU or QUY_DINH_DIEU_KIEN relationships found!")
            print("   This is why KG returns empty results!")
        
        # Test 6: Sample ANY article relationships
        print("\n" + "="*80)
        print("TEST 6: Sample ANY article relationships (first 10)")
        print("="*80)
        
        cypher = """
        MATCH (a1:Article)-[r]->(a2:Article)
        RETURN a1.number as from_article, type(r) as relationship, a2.number as to_article
        LIMIT 10
        """
        result = await adapter.execute_cypher(cypher, {})
        if result:
            print(f"✅ Found {len(result)} article relationships:")
            for r in result:
                print(f"   Điều {r['from_article']} --[{r['relationship']}]--> Điều {r['to_article']}")
        else:
            print("❌ No article relationships at all!")
        
        # Test 7: Get sample articles
        print("\n" + "="*80)
        print("TEST 7: Sample articles")
        print("="*80)
        
        cypher = """
        MATCH (a:Article)
        RETURN a.number as number, a.title as title
        LIMIT 5
        """
        result = await adapter.execute_cypher(cypher, {})
        if result:
            print(f"✅ Sample articles:")
            for r in result:
                print(f"   Điều {r['number']}: {r['title']}")
        
        print("\n" + "="*80)
        print("📊 SUMMARY")
        print("="*80)
        print("✅ Neo4j is connected and has data")
        print(f"📊 Node types: {len(labels)}")
        print(f"🔗 Relationship types: {len(rel_types)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
