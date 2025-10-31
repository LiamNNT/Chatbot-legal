#!/usr/bin/env python3
"""
Demo script to test debug logging functionality
Chạy script này sau khi start backend với --debug mode
"""

import requests
import json
import time

# Configuration
ORCHESTRATOR_URL = "http://localhost:8001/api/v1"
RAG_URL = "http://localhost:8000/v1"

def check_services():
    """Check if services are running"""
    print("🔍 Checking services...")
    
    try:
        # Check Orchestrator (quick check with short timeout)
        resp = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ Orchestrator: Running")
        else:
            print("❌ Orchestrator: Not healthy")
            return False
    except Exception as e:
        print(f"❌ Orchestrator: Not running - {e}")
        return False
    
    try:
        # Check RAG (quick check with short timeout)
        resp = requests.get(f"{RAG_URL}/health", timeout=5)
        if resp.status_code == 200:
            print("✅ RAG Service: Running")
        else:
            print("❌ RAG Service: Not healthy")
            return False
    except Exception as e:
        print(f"❌ RAG Service: Not running - {e}")
        return False
    
    return True

def test_chat_query(query: str, use_rag: bool = True):
    """Test a chat query and show the response"""
    print("\n" + "="*80)
    print(f"📝 Testing Query: {query}")
    print("="*80)
    
    payload = {
        "query": query,  # Changed from "message" to "query"
        "use_rag": use_rag,
        "rag_top_k": 5,
        "session_id": f"test-{int(time.time())}"  # Changed from "conversation_id" to "session_id"
    }
    
    print("\n🚀 Sending request...")
    print(f"   With RAG: {use_rag}")
    print(f"   Top K: {payload['rag_top_k']}")
    print("⏳ Waiting for response (no timeout - will wait indefinitely)...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{ORCHESTRATOR_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=None  # No timeout - wait indefinitely
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Response received in {elapsed:.2f}s")
            print("\n📨 Response:")
            print("-" * 80)
            print(data.get("response", "No response"))
            print("-" * 80)
            
            if "metadata" in data:
                meta = data["metadata"]
                print("\n📊 Metadata:")
                if "processing_stats" in meta:
                    stats = meta["processing_stats"]
                    print(f"   - Planning time: {stats.get('planning_time', 0):.3f}s")
                    print(f"   - RAG time: {stats.get('rag_time', 0):.3f}s")
                    print(f"   - Answer generation: {stats.get('answer_generation_time', 0):.3f}s")
                    print(f"   - Verification: {stats.get('verification_time', 0):.3f}s")
                    print(f"   - Total time: {stats.get('total_time', 0):.3f}s")
                    print(f"   - Documents retrieved: {stats.get('documents_retrieved', 0)}")
            
            print("\n💡 Tip: Check the terminal running start_backend.py")
            print("   to see detailed agent input/output logs (debug mode is ON by default)!")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        print(f"\n❌ Request failed: {e}")

def main():
    print("\n" + "="*80)
    print("🤖 Chatbot-UIT Debug Logging Demo")
    print("="*80)
    print("\nThis script tests the chatbot and shows how to view debug logs.")
    print("Make sure you've started the backend with: python start_backend.py")
    print("(Debug mode is ON by default - no need for --debug flag)")
    print("\n⚠️  NOTE: Queries will wait indefinitely for response (no timeout)")
    print("\n" + "="*80)
    
    # Check services
    if not check_services():
        print("\n❌ Services are not running!")
        print("\nPlease start the backend first:")
        print("   conda activate chatbot-UIT")
        print("   python start_backend.py")
        return
    
    # Test queries
    test_queries = [
        "Điều kiện tốt nghiệp của trường là gì?",
        "Học phí của UIT là bao nhiêu?",
        "Thời gian đào tạo đại học là bao lâu?"
    ]
    
    print("\n" + "="*80)
    print("🧪 Running Test Queries")
    print("="*80)
    print("\nℹ️  Watch the terminal running 'start_backend.py' to see:")
    print("   - 📋 Planning step")
    print("   - 🔍 Query rewriting & RAG retrieval")
    print("   - 💡 Answer generation")
    print("   - ✅ Verification")
    print("   - 🎯 Response formatting")
    print("   - 🔵 Agent inputs")
    print("   - 🟢 Agent outputs")
    print("\n⏰ Each query will wait indefinitely until response is received")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'='*80}")
        print(f"Test {i}/{len(test_queries)}")
        test_chat_query(query, use_rag=True)
        
        if i < len(test_queries):
            print("\n⏳ Waiting 2 seconds before next query...")
            time.sleep(2)
    
    print("\n\n" + "="*80)
    print("✅ Demo Complete!")
    print("="*80)
    print("\n📚 For more information, see:")
    print("   - DEBUG_LOGGING_GUIDE.md")
    print("   - README.md")
    print("\n💡 Tips:")
    print("   - Debug logging is ON by default (use --no-debug to disable)")
    print("   - Logs show input/output of each agent")
    print("   - Check processing times to find bottlenecks")
    print("   - Monitor token usage to optimize costs")
    print("   - Queries have no timeout - will wait until completion")
    print("\n")

if __name__ == "__main__":
    main()
