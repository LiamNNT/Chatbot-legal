#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test with explicit Knowledge Graph flag in request
"""
import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8001/api/v1"

def test_with_kg_flag():
    """Test with use_knowledge_graph explicitly set to True"""
    print("\n" + "="*80)
    print("TEST: FORCE KNOWLEDGE GRAPH VIA API PARAMETER")
    print("="*80)
    
    payload = {
        "query": "Liệt kê tất cả các điều có mối quan hệ YEU_CAU hoặc QUY_DINH_DIEU_KIEN với nhau trong quy chế",
        "use_rag": True,
        "use_knowledge_graph": True,  # FORCE KG usage
        "rag_top_k": 5,
        "stream": False
    }
    
    print(f"\n📤 Query: {payload['query']}")
    print(f"🔧 FORCE use_knowledge_graph: True")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=120
        )
        
        print(f"\n📥 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Answer
            print(f"\n✅ ANSWER:")
            print("-" * 80)
            print(data.get('response', '')[:500])
            print("-" * 80)
            
            # Stats
            stats = data.get('processing_stats', {})
            print(f"\n⚡ STATS:")
            print(f"  Time: {stats.get('total_time', 0):.2f}s")
            print(f"  Pipeline: {stats.get('pipeline', 'N/A')}")
            print(f"  Complexity: {stats.get('complexity', 'N/A')} (score: {stats.get('plan_complexity_score', 0):.1f})")
            
            # Check KG usage
            rag_context = data.get('rag_context', {})
            kg_used = rag_context.get('use_knowledge_graph', False)
            
            # Check processing stats too
            stats_kg = stats.get('use_knowledge_graph', False)
            graph_nodes = stats.get('graph_nodes_found', 0)
            graph_paths = stats.get('graph_paths_found', 0)
            
            print(f"\n🔍 KNOWLEDGE GRAPH STATUS:")
            print(f"  RAG Context KG Flag: {kg_used}")
            print(f"  Processing Stats KG Flag: {stats_kg}")
            print(f"  Graph Nodes Found: {graph_nodes}")
            print(f"  Graph Paths Found: {graph_paths}")
            
            if kg_used or stats_kg:
                print(f"\n  ✅ SUCCESS: Knowledge Graph WAS USED!")
            else:
                print(f"\n  ❌ FAILED: Knowledge Graph NOT USED despite explicit flag!")
                
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")


if __name__ == "__main__":
    test_with_kg_flag()
