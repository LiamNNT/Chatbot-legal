#!/usr/bin/env python3
"""
Test to check which LLM models are being called
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_with_logging():
    """Test and check which models are used"""
    print("\n" + "="*80)
    print("LLM MODEL CHECK TEST")
    print("="*80)
    
    payload = {
        "query": "Học phí của UIT là bao nhiêu?",
        "use_rag": False,  # No RAG to isolate LLM pipeline
        "stream": False
    }
    
    print(f"\n📤 Query: {payload['query']}")
    print(f"Use RAG: {payload['use_rag']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=120
        )
        
        print(f"\n📥 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Answer preview
            print(f"\n✅ ANSWER (first 400 chars):")
            print("-" * 80)
            answer = data.get('response', '')
            print(answer[:400])
            if len(answer) > 400:
                print(f"... ({len(answer)} total chars)")
            print("-" * 80)
            
            # Processing stats
            stats = data.get('processing_stats', {})
            print(f"\n⚡ PROCESSING STATS:")
            print(f"  Total Time: {stats.get('total_time', 0):.2f}s")
            print(f"  LLM Calls: {stats.get('llm_calls', 0)}")
            print(f"  Pipeline: {stats.get('pipeline', 'N/A')}")
            print(f"  Planning Time: {stats.get('planning_time', 0):.2f}s")
            print(f"  Answer Gen Time: {stats.get('answer_generation_time', 0):.2f}s")
            print(f"  Complexity: {stats.get('plan_complexity', 'N/A')} (score: {stats.get('plan_complexity_score', 0):.1f})")
            
            # Agent metadata
            metadata = data.get('agent_metadata', {})
            if metadata:
                print(f"\n🔧 AGENT METADATA:")
                print(json.dumps(metadata, indent=2, ensure_ascii=False)[:500])
            
            # Model used
            model_used = data.get('model_used')
            print(f"\n🤖 MODEL USED (from response): {model_used}")
            
            # Try to get pipeline info
            pipeline_steps = stats.get('pipeline_steps')
            if pipeline_steps:
                print(f"\n📋 PIPELINE STEPS INFO:")
                agents_used = pipeline_steps.get('agents_used', {})
                print(f"  Agents Used:")
                for agent_name, agent_info in agents_used.items():
                    if agent_info and isinstance(agent_info, dict):
                        model = agent_info.get('model', 'N/A')
                        print(f"    • {agent_name}: {model}")
                    else:
                        print(f"    • {agent_name}: {agent_info}")
            
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_with_logging()
    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)
