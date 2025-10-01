#!/usr/bin/env python3
# test_api.py
# Test Vietnamese Hybrid RAG API endpoints

import requests
import json
import time
from typing import Dict, Any

def test_api_endpoint(url: str, method: str = "GET", data: Dict[Any, Any] = None) -> Dict[Any, Any]:
    """Test an API endpoint and return response."""
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        }

def main():
    """Test Vietnamese Hybrid RAG API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Vietnamese Hybrid RAG API")
    print("=" * 50)
    
    # Wait a moment for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    # Test 1: Root endpoint
    print("\n1️⃣ Testing root endpoint...")
    result = test_api_endpoint(f"{base_url}/")
    if result["success"]:
        print("✅ Root endpoint working")
        print(f"   Service: {result['data']['service']}")
        print(f"   Version: {result['data']['version']}")
        print(f"   Features: {len(result['data']['features'])} features")
    else:
        print(f"❌ Root endpoint failed: {result['error']}")
        return
    
    # Test 2: Health check
    print("\n2️⃣ Testing health check...")
    result = test_api_endpoint(f"{base_url}/v1/health")
    if result["success"]:
        print("✅ Health check working")
        print(f"   Status: {result['data']['status']}")
        print(f"   Components: {len(result['data']['components'])} components")
    else:
        print(f"❌ Health check failed: {result['error']}")
    
    # Test 3: OpenSearch stats
    print("\n3️⃣ Testing OpenSearch stats...")
    result = test_api_endpoint(f"{base_url}/v1/opensearch/stats")
    if result["success"]:
        print("✅ OpenSearch stats working")
        print(f"   Documents: {result['data']['total_documents']}")
        print(f"   Demo mode: {result['data']['demo_mode']}")
    else:
        print(f"❌ OpenSearch stats failed: {result['error']}")
    
    # Test 4: Simple Vietnamese search
    print("\n4️⃣ Testing Vietnamese search...")
    search_request = {
        "query": "tuyển sinh đại học",
        "search_mode": "hybrid",
        "size": 3,
        "language": "vi"
    }
    result = test_api_endpoint(f"{base_url}/v1/search", "POST", search_request)
    if result["success"]:
        print("✅ Vietnamese search working")
        search_data = result["data"]
        print(f"   Query: {search_data['query']}")
        print(f"   Mode: {search_data['search_mode']}")
        print(f"   Results: {search_data['total']}")
        for i, hit in enumerate(search_data["hits"][:2]):
            print(f"   [{i+1}] {hit['title'][:50]}... (score: {hit['score']:.3f})")
    else:
        print(f"❌ Vietnamese search failed: {result['error']}")
    
    # Test 5: Faculty filter search
    print("\n5️⃣ Testing faculty filter search...")
    search_request = {
        "query": "công nghệ thông tin",
        "search_mode": "hybrid", 
        "size": 5,
        "language": "vi",
        "faculty": "CNTT"
    }
    result = test_api_endpoint(f"{base_url}/v1/search", "POST", search_request)
    if result["success"]:
        print("✅ Faculty filter search working")
        search_data = result["data"]
        print(f"   Query: {search_data['query']}")
        print(f"   Results: {search_data['total']}")
        for i, hit in enumerate(search_data["hits"][:2]):
            print(f"   [{i+1}] {hit['title'][:50]}... (score: {hit['score']:.3f})")
    else:
        print(f"❌ Faculty filter search failed: {result['error']}")
    
    # Test 6: Document type filter
    print("\n6️⃣ Testing document type filter...")
    search_request = {
        "query": "quy định",
        "search_mode": "hybrid",
        "size": 5,
        "language": "vi",
        "doc_type": "regulation"
    }
    result = test_api_endpoint(f"{base_url}/v1/search", "POST", search_request)
    if result["success"]:
        print("✅ Document type filter working")
        search_data = result["data"]
        print(f"   Query: {search_data['query']}")
        print(f"   Results: {search_data['total']}")
        for i, hit in enumerate(search_data["hits"][:2]):
            print(f"   [{i+1}] {hit['title'][:50]}... (score: {hit['score']:.3f})")
    else:
        print(f"❌ Document type filter failed: {result['error']}")
    
    # Summary
    print("\n" + "="*50)
    print("🎉 API Testing Complete!")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔍 Interactive search: http://localhost:8000/v1/search")
    print("\n💡 To test with real data:")
    print("   1. Install Docker: sudo apt install docker.io docker-compose")
    print("   2. Run full system: make start")
    print("   3. Index documents: make demo")

if __name__ == "__main__":
    main()
