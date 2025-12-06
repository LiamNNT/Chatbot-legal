#!/usr/bin/env python3
"""
Test RAG service HTTP API directly
"""
import asyncio
import aiohttp


async def test_rag_http():
    """Test RAG service qua HTTP"""
    
    print("=" * 80)
    print("TEST RAG SERVICE HTTP API")
    print("=" * 80)
    
    url = "http://localhost:8000/v1/search"
    
    payload = {
        "query": "Học phí tại UIT",
        "top_k": 5,
        "search_mode": "hybrid",
        "use_rerank": True
    }
    
    try:
        print(f"\n⏳ Calling {url}...")
        print(f"Payload: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                status = response.status
                print(f"\n📊 HTTP Status: {status}")
                
                if status == 200:
                    data = await response.json()
                    print(f"\n✅ Response received:")
                    print(f"   Documents: {len(data.get('retrieved_documents', []))}")
                    
                    if data.get('retrieved_documents'):
                        print(f"\n   📄 Sample documents:")
                        for idx, doc in enumerate(data['retrieved_documents'][:3], 1):
                            print(f"\n      [{idx}]")
                            print(f"          Title: {doc.get('title', 'N/A')}")
                            print(f"          Score: {doc.get('score', 'N/A')}")
                            content = doc.get('text', doc.get('content', ''))[:150]
                            print(f"          Content: {content}...")
                    else:
                        print(f"\n   ❌ No documents returned!")
                        print(f"   Response: {data}")
                else:
                    text = await response.text()
                    print(f"\n❌ HTTP Error:")
                    print(text[:500])
                    
    except aiohttp.ClientConnectorError:
        print("\n❌ CANNOT CONNECT TO RAG SERVICE!")
        print("   Make sure RAG service is running on http://localhost:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_rag_http())
