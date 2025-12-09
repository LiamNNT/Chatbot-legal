#!/usr/bin/env python3
"""
Detailed test to check LLM calls and pipeline logic
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_chat_detailed():
    """Test chat with detailed output"""
    print("\n" + "="*80)
    print("DETAILED CHAT TEST - Check LLM Calls & Pipeline")
    print("="*80)
    
    payload = {
        "query": "Điều kiện tốt nghiệp của sinh viên UIT?",
        "use_rag": False,  # No RAG to see pure LLM pipeline
        "stream": False
    }
    
    print(f"\n📤 REQUEST:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=60
        )
        
        print(f"\n📥 RESPONSE STATUS: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ SUCCESS!")
            print(f"\n📝 ANSWER (first 500 chars):")
            print("-" * 80)
            print(data.get('response', '')[:500])
            print("-" * 80)
            
            # Check metadata
            print(f"\n🔍 AGENT METADATA:")
            metadata = data.get('agent_metadata', {})
            print(f"  Pipeline: {metadata.get('pipeline', 'unknown')}")
            print(f"  Answer Confidence: {metadata.get('answer_confidence', 0):.2f}")
            
            plan_result = metadata.get('plan_result')
            if plan_result:
                print(f"\n📋 PLAN RESULT:")
                print(f"  Intent: {plan_result.get('intent', 'N/A')}")
                print(f"  Complexity: {plan_result.get('complexity', 'N/A')} (score: {plan_result.get('complexity_score', 0):.1f})")
                print(f"  Requires RAG: {plan_result.get('requires_rag', False)}")
                print(f"  Strategy: {plan_result.get('strategy', 'N/A')}")
                print(f"  Rewritten Queries: {plan_result.get('rewritten_queries', [])}")
            
            # Check processing stats
            print(f"\n⚡ PROCESSING STATS:")
            stats = data.get('processing_stats', {})
            print(f"  Total Time: {stats.get('total_time', 0):.2f}s")
            print(f"  LLM Calls: {stats.get('llm_calls', 0)}")
            print(f"  Planning Time: {stats.get('planning_time', 0):.2f}s")
            print(f"  Answer Gen Time: {stats.get('answer_generation_time', 0):.2f}s")
            
            pipeline_steps = stats.get('pipeline_steps', {})
            if pipeline_steps:
                print(f"\n🔧 PIPELINE INFO:")
                print(f"  Type: {pipeline_steps.get('pipeline_type', 'N/A')}")
                
                steps_enabled = pipeline_steps.get('steps_enabled', {})
                print(f"  Steps Enabled:")
                for step, enabled in steps_enabled.items():
                    status = "✅" if enabled else "❌"
                    print(f"    {status} {step}")
                
                agents_used = pipeline_steps.get('agents_used', {})
                print(f"  Agents Used:")
                for agent_name, agent_info in agents_used.items():
                    if agent_info:
                        print(f"    • {agent_name}: {agent_info.get('model', 'N/A')}")
                
                cost_info = pipeline_steps.get('cost_info', {})
                if cost_info:
                    print(f"\n💰 COST INFO:")
                    print(f"  Base LLM Calls: {cost_info.get('base_llm_calls', 0)}")
                    print(f"  Original Pipeline: {cost_info.get('original_pipeline_calls', 0)} calls")
                    print(f"  V2 Optimized: {cost_info.get('v2_optimized_calls', 0)} calls")
                    print(f"  Savings: {cost_info.get('savings_vs_original', 'N/A')}")
                    print(f"  Latency Improvement: {cost_info.get('latency_improvement', 'N/A')}")
            
            # Check detailed sources
            detailed_sources = metadata.get('detailed_sources', [])
            if detailed_sources:
                print(f"\n📚 DETAILED SOURCES: {len(detailed_sources)} sources")
                for i, source in enumerate(detailed_sources[:3], 1):
                    print(f"  {i}. {source.get('title', 'N/A')} (score: {source.get('score', 0):.3f})")
            
        else:
            print(f"\n❌ ERROR:")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_chat_detailed()
    print("\n" + "="*80)
