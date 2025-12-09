#!/usr/bin/env python3
"""Check Entity relationships"""
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
    print("TEST: Check Entity properties")
    print("="*80)
    
    # Get Entity properties
    cypher = """
    MATCH (e:Entity)
    RETURN properties(e) as props
    LIMIT 3
    """
    result = await adapter.execute_cypher(cypher, {})
    if result:
        print(f"\n✅ Sample Entity properties:")
        for i, r in enumerate(result, 1):
            print(f"\nEntity {i}:")
            props = r['props']
            for key, value in props.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
    
    # Get Entity relationships with actual data
    print("\n" + "="*80)
    print("TEST: Entity YEU_CAU and QUY_DINH_DIEU_KIEN relationships")
    print("="*80)
    
    cypher = """
    MATCH (e1:Entity)-[r:YEU_CAU|QUY_DINH_DIEU_KIEN]->(e2:Entity)
    RETURN e1.name as from_name,
           e1.type as from_type,
           type(r) as relationship,
           e2.name as to_name,
           e2.type as to_type,
           properties(r) as rel_props
    LIMIT 15
    """
    result = await adapter.execute_cypher(cypher, {})
    if result:
        print(f"\n✅ Found {len(result)} Entity relationships:\n")
        for r in result:
            print(f"  [{r['from_type'] or 'Entity'}] {r['from_name'] or 'Unknown'}")
            print(f"    --[{r['relationship']}]-->")
            print(f"  [{r['to_type'] or 'Entity'}] {r['to_name'] or 'Unknown'}")
            if r['rel_props']:
                print(f"    Properties: {r['rel_props']}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
