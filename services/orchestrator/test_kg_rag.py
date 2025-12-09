#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test with both Knowledge Graph and RAG enabled
"""
import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8001/api/v1"

def test_kg_and_rag():
    """Test with both KG and RAG"""
    print("\n" + "="*80)
    print("TEST: KNOWLEDGE GRAPH + RAG RETRIEVAL")
    print("="*80)
    
    # Query phức tạp để kích hoạt IRCoT (complexity > 6.5)
    # TEST 1: Query về quan hệ giữa các điều (should trigger KG)
    payload = {
        "query": "Liệt kê tất cả các điều có mối quan hệ YEU_CAU hoặc QUY_DINH_DIEU_KIEN với nhau trong quy chế",
        "use_rag": True,  # Enable RAG
        "rag_top_k": 5,
        "stream": False
    }
    
    print(f"\n📤 Query: {payload['query']}")
    print(f"Use RAG: {payload['use_rag']}")
    print(f"Top K: {payload['rag_top_k']}")
    
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
            answer = data.get('response', '')
            print(answer)
            print("-" * 80)
            
            # Processing stats
            stats = data.get('processing_stats', {})
            print(f"\n⚡ PROCESSING STATS:")
            print(f"  Total Time: {stats.get('total_time', 0):.2f}s")
            print(f"  LLM Calls: {stats.get('llm_calls', 0)}")
            print(f"  Pipeline: {stats.get('pipeline', 'N/A')}")
            print(f"  Planning Time: {stats.get('planning_time', 0) or 0:.2f}s")
            rag_time = stats.get('rag_time')
            print(f"  RAG Time: {rag_time:.2f}s" if rag_time is not None else "  RAG Time: N/A")
            print(f"  Answer Gen Time: {stats.get('answer_generation_time', 0) or 0:.2f}s")
            print(f"  Complexity: {stats.get('plan_complexity', 'N/A')} (score: {stats.get('plan_complexity_score', 0) or 0:.1f})")
            
            # RAG context info
            rag_context = data.get('rag_context')
            if rag_context:
                print(f"\n📚 RAG CONTEXT:")
                print(f"  Total Documents: {rag_context.get('total_documents', 0)}")
                print(f"  Search Mode: {rag_context.get('search_mode', 'N/A')}")
                print(f"  Use KG: {rag_context.get('use_knowledge_graph', False)}")
                print(f"  Use Vector: {rag_context.get('use_vector_search', True)}")
                print(f"  Strategy: {rag_context.get('strategy', 'N/A')}")
                
                docs = rag_context.get('documents', [])
                if docs:
                    print(f"\n  📄 Top Documents:")
                    for i, doc in enumerate(docs[:3], 1):
                        title = doc.get('title', 'N/A')
                        score = doc.get('score', 0)
                        print(f"    {i}. {title} (score: {score:.3f})")
            
            # Check if KG was used
            print(f"\n🔍 SEARCH STRATEGY:")
            if rag_context:
                kg_used = rag_context.get('use_knowledge_graph', False)
                vec_used = rag_context.get('use_vector_search', True)
                strategy = rag_context.get('strategy', 'N/A')
                
                print(f"  Strategy: {strategy}")
                print(f"  KG Enabled: {kg_used}")
                print(f"  Vector Enabled: {vec_used}")
                
                if kg_used and vec_used:
                    print(f"  ✅ HYBRID: Knowledge Graph + Vector Search")
                elif kg_used:
                    print(f"  🔗 Knowledge Graph only")
                elif vec_used:
                    print(f"  📊 Vector Search only")
                else:
                    print(f"  ❌ No search performed")
                
                # Check if Graph Reasoning or IRCoT docs are present
                docs = rag_context.get('documents', [])
                has_graph_doc = any('Graph Reasoning' in doc.get('title', '') for doc in docs)
                has_ircot_doc = any('IRCoT' in doc.get('title', '') for doc in docs)
                
                print(f"\n  📝 Special Documents:")
                print(f"  - Graph Reasoning Doc: {has_graph_doc}")
                print(f"  - IRCoT Doc: {has_ircot_doc}")
                
                if (has_graph_doc or has_ircot_doc) and not kg_used:
                    print(f"  ⚠️  WARNING: Found KG-related docs but KG flag is False!")
                    print(f"     This might be KG context injected during RAG processing.")
            
            
        else:
            print(f"\n❌ Error: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_simple_kg_query():
    """Test với query đơn giản về môn học"""
    print("\n" + "="*80)
    print("TEST: SIMPLE KNOWLEDGE GRAPH QUERY")
    print("="*80)
    
    payload = {
        "query": "Các môn học của ngành Khoa học máy tính?",
        "use_rag": True,
        "rag_top_k": 8,
        "stream": False
    }
    
    print(f"\n📤 Query: {payload['query']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Answer (first 500 chars):")
            print("-" * 80)
            print(data.get('response', '')[:500])
            print("...")
            print("-" * 80)
            
            stats = data.get('processing_stats', {})
            print(f"\n⏱️ Time: {stats.get('total_time', 0):.2f}s")
            print(f"📊 LLM Calls: {stats.get('llm_calls', 0)}")
            
            rag_context = data.get('rag_context')
            if rag_context:
                print(f"🔍 KG Used: {rag_context.get('use_knowledge_graph', False)}")
                print(f"📚 Docs: {rag_context.get('total_documents', 0)}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")


if __name__ == "__main__":
    # Test 1: Query phức tạp với quan hệ
    test_kg_and_rag()
    
    # Test 2: Query đơn giản
    # test_simple_kg_query()
    
    print("\n" + "="*80)
    print("All tests completed!")
    print("="*80)
