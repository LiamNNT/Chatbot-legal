#!/usr/bin/env python3
"""
Test Graph Reasoning Agent directly
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except:
    pass

from app.core.container import get_container
from app.agents.graph_reasoning_agent import GraphQueryType


async def test_graph_agent():
    """Test Graph Reasoning Agent trực tiếp"""
    
    print("=" * 80)
    print("TEST GRAPH REASONING AGENT")
    print("=" * 80)
    
    query = "Điều 19 có liên quan gì đến Điều 20?"
    
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        if not orchestrator.graph_reasoning_agent:
            print("❌ Graph Reasoning Agent not available!")
            return
        
        graph_agent = orchestrator.graph_reasoning_agent
        print("✅ Graph Reasoning Agent found")
        
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")
        
        print("\n⏳ Calling Graph Reasoning Agent...")
        result = await graph_agent.reason(
            query=query,
            query_type=GraphQueryType.LOCAL,
            context={
                "search_terms": ["Điều 19", "Điều 20", "liên quan"]
            }
        )
        
        print(f"\n📊 RESULTS:")
        print(f"   Nodes found: {len(result.nodes)}")
        print(f"   Paths found: {len(result.paths)}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Context length: {len(result.synthesized_context)} chars")
        
        if result.nodes:
            print(f"\n📝 Nodes ({len(result.nodes)}):")
            for idx, node in enumerate(result.nodes[:5], 1):
                print(f"   [{idx}] {node}")
        else:
            print("\n❌ No nodes found!")
        
        if result.paths:
            print(f"\n🔗 Paths ({len(result.paths)}):")
            for idx, path in enumerate(result.paths[:3], 1):
                print(f"   [{idx}] {path}")
        
        if result.synthesized_context:
            print(f"\n📄 Synthesized Context:")
            print("-" * 80)
            print(result.synthesized_context[:500])
            if len(result.synthesized_context) > 500:
                print(f"... ({len(result.synthesized_context) - 500} more chars)")
            print("-" * 80)
        else:
            print("\n❌ No synthesized context!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_graph_agent())
