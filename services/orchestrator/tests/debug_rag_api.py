#!/usr/bin/env python3
"""
Debug RAG API response
"""

import requests
import json

RAG_URL = "http://localhost:8000"

def test_search_detailed():
    """Test search và xem chi tiết response"""
    print("="*80)
    print("DEBUG RAG API RESPONSE")
    print("="*80)
    
    query = "điều kiện tốt nghiệp"
    
    # Test với keyword mode
    print(f"\n📝 Query: '{query}'")
    print(f"🔍 Mode: keyword\n")
    
    try:
        response = requests.post(
            f"{RAG_URL}/v1/search",
            json={
                "query": query,
                "top_k": 5,
                "search_mode": "keyword"
            },
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"\nResponse Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search_detailed()
