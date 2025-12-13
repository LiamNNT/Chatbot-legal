"""Test the search_with_amendments method via the adapter directly."""
import asyncio
import sys
sys.path.insert(0, r"c:\Users\admin\Downloads\Khiem\Chatbot-UIT\services\rag_services")

from adapters.graph.neo4j_adapter import Neo4jGraphAdapter

async def test_search_with_amendments():
    adapter = Neo4jGraphAdapter(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="uitchatbot"
    )
    
    print("="*70)
    print("Testing search_with_amendments with 'học kỳ hè, đăng ký'")
    print("="*70)
    
    results = await adapter.search_with_amendments(["học kỳ hè", "đăng ký"], limit=5)
    
    for i, r in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(f"Title: {r.get('title', 'N/A')}")
        print(f"Is Amended: {r.get('is_amended', False)}")
        if r.get('_replaced_from'):
            print(f"Replaced From: {r.get('_replaced_from')}")
        print(f"Text (first 400 chars):")
        text = r.get('text', '')[:400]
        print(text)
    
    print("\n" + "="*70)
    print("CHECKING: Does the result mention 'ĐTBC' or 'điểm trung bình'?")
    print("(If yes, it's OLD content. If no, it's NEW content)")
    print("="*70)
    
    for i, r in enumerate(results):
        text = r.get('text', '')
        has_dtbc = 'ĐTBC' in text or 'điểm trung bình' in text or '7,0' in text
        print(f"Result {i+1}: {'❌ OLD CONTENT (has ĐTBC/7,0)' if has_dtbc else '✓ NEW CONTENT'}")
    
    adapter.close()

asyncio.run(test_search_with_amendments())
