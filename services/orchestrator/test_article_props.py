#!/usr/bin/env python3
"""Check Article node properties and test actual query"""
import sys
import os
import asyncio
from pathlib import Path

orchestrator_path = Path(__file__).parent
rag_services_path = orchestrator_path.parent / "rag_services"
sys.path.insert(0, str(rag_services_path))

from dotenv import load_dotenv
env_path = rag_services_path / ".env"
load_dotenv(env_path)


async def main():
    from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
    
    adapter = Neo4jGraphAdapter(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        username=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "uitchatbot"),
        database=os.getenv("NEO4J_DATABASE", "neo4j")
    )
    
    print("="*80)
    print("TEST: Check Article properties")
    print("="*80)
    
    # Get all properties of Article nodes
    cypher = """
    MATCH (a:Article)
    RETURN properties(a) as props
    LIMIT 3
    """
    result = await adapter.execute_cypher(cypher, {})
    if result:
        print(f"\n✅ Sample Article properties:")
        for i, r in enumerate(result, 1):
            print(f"\nArticle {i}:")
            props = r['props']
            for key, value in props.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
    
    # Now test with correct property names
    print("\n" + "="*80)
    print("TEST: Get ALL YEU_CAU and QUY_DINH_DIEU_KIEN relationships (any node types)")
    print("="*80)
    
    cypher = """
    MATCH (a1)-[r:YEU_CAU|QUY_DINH_DIEU_KIEN]->(a2)
    RETURN labels(a1) as from_labels,
           a1.id as from_id, 
           a1.title as from_title,
           type(r) as relationship, 
           labels(a2) as to_labels,
           a2.id as to_id,
           a2.title as to_title
    LIMIT 20
    """
    result = await adapter.execute_cypher(cypher, {})
    if result:
        print(f"\n✅ Found {len(result)} relationships:")
        for r in result:
            from_label = r['from_labels'][0] if r['from_labels'] else 'Unknown'
            to_label = r['to_labels'][0] if r['to_labels'] else 'Unknown'
            from_id = r['from_id'] or 'N/A'
            to_id = r['to_id'] or 'N/A'
            
            print(f"\n  [{from_label}] {from_id} --[{r['relationship']}]--> [{to_label}] {to_id}")
            if r['from_title']:
                print(f"    From: {r['from_title'][:70]}")
            if r['to_title']:
                print(f"    To: {r['to_title'][:70]}")
    else:
        print("❌ No relationships found!")


if __name__ == "__main__":
    asyncio.run(main())
