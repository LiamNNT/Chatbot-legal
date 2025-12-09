#!/usr/bin/env python3
"""
Quick test with shorter timeout
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_simple():
    print("Testing simple query...")
    
    payload = {
        "query": "Hello",
        "use_rag": False,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=120  # Increase timeout
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Answer preview:")
            print(data.get('response', '')[:300])
            
            # Print full response structure
            print(f"\n📦 Full Response Keys: {list(data.keys())}")
            
            stats = data.get('processing_stats', {})
            print(f"\n📊 Processing Stats Keys: {list(stats.keys())}")
            print(f"  Total Time: {stats.get('total_time', 0):.2f}s")
            print(f"  LLM Calls: {stats.get('llm_calls', 0)}")
            print(f"  Planning Time: {stats.get('planning_time', 0):.2f}s")
            print(f"  Answer Time: {stats.get('answer_generation_time', 0):.2f}s")
            print(f"  Pipeline: {stats.get('pipeline', 'N/A')}")
            
            metadata = data.get('agent_metadata', {})
            print(f"\n🔧 Agent Metadata:")
            print(f"  Pipeline: {metadata.get('pipeline', 'N/A')}")
            print(f"  Confidence: {metadata.get('answer_confidence', 0):.2f}")
        else:
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️ Request timed out!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple()
