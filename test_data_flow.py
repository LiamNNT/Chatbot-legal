#!/usr/bin/env python3
"""
Test script để verify luồng dữ liệu rewritten_queries
"""

import requests
import json
import time

# Test với query cần query rewriting
test_query = "Đăng ký HP thế nào?"

print("=" * 70)
print("Testing Data Flow: rewritten_queries propagation")
print("=" * 70)
print(f"\nTest Query: '{test_query}'")
print("\nExpected flow:")
print("  1. Query Rewriter generates rewritten_queries")
print("  2. RAG retrieval uses rewritten_queries")
print("  3. RAGContext contains rewritten_queries")
print("  4. Answer Agent receives rewritten_queries")
print("\n" + "-" * 70)

# Send request
url = "http://localhost:8001/api/v1/chat"
payload = {
    "query": test_query,
    "use_rag": True,
    "rag_top_k": 5
}

print(f"\nSending POST {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=None)
    
    print(f"\nHTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\n✅ Response received successfully!")
        print("\n" + "=" * 70)
        print("Response Analysis:")
        print("=" * 70)
        
        # Check processing stats
        stats = data.get('processing_stats', {})
        print(f"\n📊 Processing Stats:")
        print(f"  - Total Time: {stats.get('total_time', 0):.2f}s")
        print(f"  - RAG Time: {stats.get('rag_time', 0):.4f}s")
        print(f"  - Documents Retrieved: {stats.get('documents_retrieved', 0)}")
        
        # Check for rewritten queries in stats
        if 'rewritten_queries_count' in stats:
            print(f"  - Rewritten Queries Count: {stats.get('rewritten_queries_count')}")
            print("  ✅ Query Rewriter WAS EXECUTED!")
        else:
            print("  ⚠️  No 'rewritten_queries_count' in stats")
        
        # Check RAG context
        rag_ctx = data.get('rag_context', {})
        if rag_ctx:
            print(f"\n📚 RAG Context:")
            print(f"  - Query: {rag_ctx.get('query', 'N/A')}")
            print(f"  - Total Documents: {rag_ctx.get('total_documents', 0)}")
            print(f"  - Search Mode: {rag_ctx.get('search_mode', 'N/A')}")
            
            # Check if documents were retrieved
            docs = rag_ctx.get('documents', [])
            if docs:
                print(f"\n  📄 Sample Document Titles:")
                for i, doc in enumerate(docs[:3], 1):
                    print(f"    {i}. {doc.get('title', 'Untitled')[:60]}...")
        
        # Check final response
        final_response = data.get('response', '')
        if final_response:
            print(f"\n💬 Final Response Preview:")
            print(f"  {final_response[:200]}...")
            print(f"\n  Response Length: {len(final_response)} chars")
        
        print("\n" + "=" * 70)
        print("✅ TEST COMPLETED - Check logs above for data flow")
        print("=" * 70)
        
        # Save full response for detailed analysis
        with open('/tmp/test_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n📝 Full response saved to: /tmp/test_response.json")
        
    else:
        print(f"\n❌ HTTP Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("\n❌ Request timeout (>60s)")
except requests.exceptions.ConnectionError:
    print("\n❌ Connection error - Is backend running?")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 70)
print("To verify rewritten_queries in Answer Agent input:")
print("  1. Check orchestrator logs for agent processing")
print("  2. Look for 'rewritten_queries' in RAG context")
print("  3. Verify Answer Agent received the queries")
print("=" * 70)
