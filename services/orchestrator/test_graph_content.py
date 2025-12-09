"""
Test để xem Graph Reasoning Agent có trả về content của Article không.
"""

import os
import sys
import asyncio
from pathlib import Path

# Set UTF-8 encoding
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

if not os.getenv("OPENROUTER_API_KEY"):
    print("ERROR: OPENROUTER_API_KEY not set!")
    sys.exit(1)


async def test_graph_reasoning_raw():
    """Test trực tiếp Graph Reasoning Agent để xem nó trả về gì"""
    
    print("\n" + "="*80)
    print("🔬 TEST GRAPH REASONING AGENT TRỰC TIẾP")
    print("="*80)
    
    from app.core.container import ServiceContainer
    from app.agents.graph_reasoning_agent import GraphQueryType
    
    container = ServiceContainer()
    
    # Get graph adapter
    graph_adapter = container.get_graph_adapter()
    if not graph_adapter:
        print("\n❌ Graph adapter not initialized!")
        return
    
    print("\n✅ Graph adapter OK!")
    
    # Get orchestrator to access graph reasoning agent
    orchestrator = container.get_multi_agent_orchestrator()
    graph_agent = orchestrator.graph_reasoning_agent
    
    if not graph_agent:
        print("\n❌ Graph reasoning agent not initialized!")
        return
    
    print("✅ Graph reasoning agent OK!")
    
    # Test query
    query = "Điều 19 quy định gì?"
    
    print(f"\n📝 Testing query: {query}")
    print("-" * 80)
    
    # Call graph reasoning agent directly
    print("\n1. Calling GraphReasoningAgent.reason()...")
    
    result = await graph_agent.reason(
        query=query,
        query_type=GraphQueryType.LOCAL,
        context={}
    )
    
    print(f"\n2. Graph Reasoning Result:")
    print(f"   - Nodes found: {len(result.nodes)}")
    print(f"   - Paths found: {len(result.paths)}")
    print(f"   - Confidence: {result.confidence}")
    print(f"   - Context length: {len(result.synthesized_context) if result.synthesized_context else 0} chars")
    
    # Show nodes detail
    if result.nodes:
        print(f"\n3. Nodes Detail:")
        for i, node in enumerate(result.nodes[:3], 1):
            print(f"\n   Node {i}:")
            print(f"   {node}")
            print("-" * 60)
    
    # Show paths detail
    if result.paths:
        print(f"\n4. Paths Detail:")
        for i, path in enumerate(result.paths[:3], 1):
            print(f"\n   Path {i}:")
            print(f"   {path}")
            print("-" * 60)
    
    # Show synthesized context
    if result.synthesized_context:
        print(f"\n5. Synthesized Context:")
        print("-" * 80)
        context_preview = result.synthesized_context[:1000]
        print(context_preview)
        if len(result.synthesized_context) > 1000:
            print(f"\n... (showing first 1000 of {len(result.synthesized_context)} chars)")
        print("-" * 80)
        
        # Check if context contains actual content
        if "điều 19" in result.synthesized_context.lower():
            print(f"\n✅✅ Context contains 'Điều 19'!")
        
        if len(result.synthesized_context) > 200:
            print(f"✅✅ Context is substantial ({len(result.synthesized_context)} chars)!")
        else:
            print(f"⚠️ Context is too short - only {len(result.synthesized_context)} chars!")
    else:
        print(f"\n❌❌ NO SYNTHESIZED CONTEXT!")
        print("   Graph Reasoning không tạo ra context để LLM sử dụng!")


async def test_search_articles_direct():
    """Test search_articles_by_keyword để xem có trả về content không"""
    
    print("\n" + "="*80)
    print("🔍 TEST SEARCH ARTICLES TRỰC TIẾP")
    print("="*80)
    
    from app.core.container import ServiceContainer
    
    container = ServiceContainer()
    adapter = container.get_graph_adapter()
    
    if not adapter:
        print("\n❌ Adapter not found!")
        return
    
    print("\n✅ Adapter OK!")
    
    # Search for Điều 19
    print("\n📝 Searching for 'Điều 19'...")
    
    results = await adapter.search_articles_by_keyword(
        keywords=["điều 19"],
        limit=5
    )
    
    if results:
        print(f"\n✅ Found {len(results)} results!")
        
        for i, article in enumerate(results, 1):
            print(f"\n{'='*80}")
            print(f"Article {i}:")
            print(f"   - ID: {article.get('article_id')}")
            print(f"   - Title: {article.get('title')}")
            content = article.get('content', '')
            print(f"   - Content length: {len(content)} chars")
            
            if content:
                print(f"\n   Content preview (first 500 chars):")
                print("-" * 80)
                print(content[:500])
                print("-" * 80)
                
                if len(content) > 100:
                    print(f"   ✅✅ Article HAS CONTENT! ({len(content)} chars)")
                else:
                    print(f"   ⚠️ Article content too short: {len(content)} chars")
            else:
                print(f"   ❌❌ NO CONTENT in article!")
    else:
        print(f"\n❌ No results found!")


async def test_get_article_with_entities():
    """Test get_article_with_entities để xem method này trả về gì"""
    
    print("\n" + "="*80)
    print("📄 TEST GET_ARTICLE_WITH_ENTITIES")
    print("="*80)
    
    from app.core.container import ServiceContainer
    
    container = ServiceContainer()
    adapter = container.get_graph_adapter()
    
    if not adapter:
        print("\n❌ Adapter not found!")
        return
    
    # Try to get article 19
    print("\n📝 Getting article with entities for number 19...")
    
    try:
        result = await adapter.get_article_with_entities(article_number=19)
        
        if result:
            print(f"\n✅ Got result!")
            print(f"   Keys: {list(result.keys())}")
            
            for key, value in result.items():
                if isinstance(value, str):
                    val_preview = value[:200] if len(value) > 200 else value
                    print(f"   - {key}: {val_preview}...")
                else:
                    print(f"   - {key}: {value}")
        else:
            print(f"\n❌ No result returned!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 DEBUG: TẠI SAO LLM KHÔNG LẤY ĐƯỢC CONTENT")
    print("="*80)
    
    # Test 1: Direct article search
    await test_search_articles_direct()
    
    # Test 2: get_article_with_entities
    await test_get_article_with_entities()
    
    # Test 3: Graph Reasoning Agent
    await test_graph_reasoning_raw()
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
