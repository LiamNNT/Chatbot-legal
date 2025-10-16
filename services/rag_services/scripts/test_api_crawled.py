#!/usr/bin/env python3
"""
Test RAG API with crawled data.
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_search(query: str, top_k: int = 3):
    """Test search endpoint."""
    print(f"\n{'='*80}")
    print(f"🔍 Query: {query}")
    print(f"{'='*80}")
    
    endpoint = f"{BASE_URL}/api/search"
    payload = {
        "query": query,
        "top_k": top_k,
        "search_mode": "hybrid"  # hybrid, vector, or keyword
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            results = data.get("results", [])
            print(f"\n📊 Found {len(results)} results:\n")
            
            for i, result in enumerate(results, 1):
                print(f"--- Result #{i} (Score: {result['score']:.4f}) ---")
                print(f"Title: {result['metadata']['title']}")
                print(f"Subject: {result['metadata'].get('subject', 'N/A')}")
                print(f"Year: {result['metadata'].get('year', 'N/A')}")
                print(f"Source: {result.get('source_type', 'N/A')}")
                print(f"\nContent Preview (first 300 chars):")
                print(f"{result['text'][:300]}...")
                print("")
        else:
            print(f"❌ Error: {data.get('error', 'Unknown error')}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_health():
    """Test health endpoint."""
    print("\n🏥 Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ Status: {data.get('status')}")
        print(f"   Environment: {data.get('environment')}")
        print(f"   Vector Backend: {data.get('vector_backend')}")
        print(f"   Timestamp: {data.get('timestamp')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def main():
    """Main function."""
    print("="*80)
    print("TEST RAG API WITH CRAWLED DATA")
    print("="*80)
    
    # Test health first
    if not test_health():
        print("\n❌ Server is not healthy. Please check the server.")
        return
    
    # Test queries about KHMT 2024
    test_queries = [
        "Chương trình đào tạo Khoa học Máy tính khóa 19",
        "Cấu trúc chương trình đào tạo KHMT 2024",
        "Học phần bắt buộc ngành Khoa học Máy tính",
        "Điều kiện tốt nghiệp ngành KHMT",
    ]
    
    for query in test_queries:
        test_search(query, top_k=3)
        print()  # Spacing
    
    print("="*80)
    print("✅ TESTING COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
