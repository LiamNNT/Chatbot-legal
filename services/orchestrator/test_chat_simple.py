#!/usr/bin/env python3
"""
Simple test script for chat endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_chat_no_rag():
    """Test chat without RAG (just LLM)"""
    print("\n" + "="*70)
    print("TEST 1: Chat without RAG")
    print("="*70)
    
    payload = {
        "query": "UIT là gì? Giới thiệu ngắn gọn.",
        "use_rag": False,
        "stream": False
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=30
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success!")
            print(f"Response: {data.get('response', '')[:200]}...")
            print(f"Session ID: {data.get('session_id')}")
            if data.get('processing_stats'):
                stats = data['processing_stats']
                print(f"Processing time: {stats.get('total_time', 0):.2f}s")
                print(f"LLM calls: {stats.get('llm_calls', 0)}")
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def test_chat_with_rag():
    """Test chat with RAG"""
    print("\n" + "="*70)
    print("TEST 2: Chat with RAG")
    print("="*70)
    
    payload = {
        "query": "Các bước đăng ký học phần tại UIT?",
        "use_rag": True,
        "rag_top_k": 5,
        "stream": False
    }
    
    print(f"Request: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=60
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success!")
            print(f"Response: {data.get('response', '')[:300]}...")
            
            if data.get('rag_context'):
                rag = data['rag_context']
                print(f"\nDocuments retrieved: {len(rag.get('documents', []))}")
                
            if data.get('processing_stats'):
                stats = data['processing_stats']
                print(f"Processing time: {stats.get('total_time', 0):.2f}s")
                print(f"LLM calls: {stats.get('llm_calls', 0)}")
                print(f"Pipeline: {stats.get('pipeline', 'unknown')}")
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")


def test_health():
    """Test health endpoint"""
    print("\n" + "="*70)
    print("TEST 0: Health Check")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Services: {json.dumps(data.get('services', {}), indent=2)}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    print("\n🚀 Testing Orchestrator Service")
    print(f"Base URL: {BASE_URL}")
    
    # Test health first
    test_health()
    
    # Test chat without RAG (faster, no dependencies)
    test_chat_no_rag()
    
    # Test chat with RAG (requires RAG service)
    # test_chat_with_rag()  # Uncomment when RAG service is running
    
    print("\n" + "="*70)
    print("✅ Tests completed!")
    print("="*70)
