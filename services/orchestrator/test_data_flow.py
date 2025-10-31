#!/usr/bin/env python3
"""
Test script to verify data flow in the orchestrator
Tests that rewritten_queries are properly passed through the pipeline
"""
import requests
import json

def test_data_flow():
    """Test the complete data flow through the orchestrator"""
    
    # Test query
    query = "UIT có những chuyên ngành nào?"
    
    print("🧪 Testing data flow in orchestrator...")
    print(f"📝 Query: {query}\n")
    
    # Send request to orchestrator
    url = "http://localhost:8001/api/v1/chat"
    payload = {
        "query": query,
        "session_id": "test-session-123",
        "context": {},
        "config": {}
    }
    
    print(f"📤 Sending request to {url}")
    print(f"   Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"📥 Response status: {response.status_code}\n")
        
        if response.status_code == 200:
            result = response.json()
            
            # Print response structure
            print("✅ Success! Response structure:")
            print(f"   - Answer: {result.get('answer', 'N/A')[:100]}...")
            print(f"   - Session ID: {result.get('session_id', 'N/A')}")
            
            # Check processing stats
            stats = result.get('processing_stats', {})
            print(f"\n📊 Processing Stats:")
            print(f"   - Total time: {stats.get('total_time_ms', 'N/A')} ms")
            print(f"   - Number of steps: {stats.get('num_steps', 'N/A')}")
            
            # Check for rewritten_queries_count (KEY METRIC)
            rewritten_count = stats.get('rewritten_queries_count', 0)
            print(f"   - Rewritten queries count: {rewritten_count}")
            
            if rewritten_count > 0:
                print(f"\n✅ SUCCESS: Data flow is working! {rewritten_count} rewritten queries detected.")
            else:
                print(f"\n⚠️  WARNING: No rewritten queries detected in stats. Data flow may not be working.")
            
            # Print detailed step info if available
            steps = result.get('steps', [])
            if steps:
                print(f"\n📋 Steps executed ({len(steps)}):")
                for step in steps:
                    step_name = step.get('name', 'Unknown')
                    step_status = step.get('status', 'Unknown')
                    print(f"   - {step_name}: {step_status}")
            
            # Save full response for inspection
            with open('/tmp/test_data_flow_response.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Full response saved to: /tmp/test_data_flow_response.json")
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out after 60 seconds")
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the orchestrator running on port 8001?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_data_flow()
