#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Knowledge Graph với câu hỏi về RELATIONSHIPS
Chỉ có thể trả lời nếu query được relationship từ Neo4j
"""
import requests
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8001/api/v1"

def test_relationship_query():
    """Test với câu hỏi chỉ KG mới trả lời được"""
    print("\n" + "="*80)
    print("TEST: KNOWLEDGE GRAPH RELATIONSHIPS (KHÔNG CÓ TRONG VECTOR DB)")
    print("="*80)
    
    # Query về relationships - chỉ có trong Neo4j graph
    # Từ check_neo4j.py ta biết có các relationship types:
    # MENTIONS, YEU_CAU, BELONGS_TO, QUY_DINH_DIEU_KIEN, AP_DUNG_CHO, etc.
    payload = {
        "query": "Các điều trong quy chế có mối quan hệ YEU_CAU hoặc QUY_DINH_DIEU_KIEN với nhau như thế nào? Liệt kê các cặp điều có liên quan.",
        "use_rag": True,
        "rag_top_k": 5,
        "stream": False
    }
    
    print(f"\n📤 Query: {payload['query']}")
    print(f"🎯 Mục đích: Query relationship types - CHỈ CÓ trong Neo4j KG")
    print(f"Use RAG: {payload['use_rag']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=180  # Tăng timeout vì IRCoT có thể chậm
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
            print(f"  Complexity: {stats.get('plan_complexity', 'N/A')} (score: {stats.get('plan_complexity_score', 0) or 0:.1f})")
            
            # RAG context
            rag_context = data.get('rag_context')
            if rag_context:
                print(f"\n📚 RAG CONTEXT:")
                print(f"  Total Documents: {rag_context.get('total_documents', 0)}")
                print(f"  Use KG: {rag_context.get('use_knowledge_graph', False)}")
                print(f"  Use Vector: {rag_context.get('use_vector_search', True)}")
                
                docs = rag_context.get('documents', [])
                if docs:
                    print(f"\n  📄 Top Documents:")
                    for i, doc in enumerate(docs[:5], 1):
                        title = doc.get('title', 'No title')[:80]
                        score = doc.get('score', 0)
                        print(f"    {i}. {title} (score: {score:.3f})")
                        
            # Kiểm tra có Graph Reasoning Context không
            if rag_context and docs:
                has_graph_context = any('Graph Reasoning' in doc.get('title', '') for doc in docs)
                has_ircot = any('IRCoT' in doc.get('title', '') for doc in docs)
                
                print(f"\n🔍 VERIFICATION:")
                print(f"  ✅ Has Graph Reasoning Context: {has_graph_context}")
                print(f"  ✅ Has IRCoT Reasoning: {has_ircot}")
                print(f"  ✅ LLM Calls > 2: {stats.get('llm_calls', 0) > 2}")
                
                if has_graph_context or has_ircot:
                    print(f"\n  🎉 CONFIRMED: Knowledge Graph WAS USED!")
                else:
                    print(f"\n  ⚠️ WARNING: No clear KG evidence in response")
                    
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_relationship_query()
    print("\n" + "="*80)
    print("Test completed!")
    print("="*80)
