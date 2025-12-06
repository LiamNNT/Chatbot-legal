#!/usr/bin/env python3
"""
Debug RAG retrieval
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except:
    pass

from app.core.container import get_container


async def debug_rag():
    """Debug why RAG not retrieving"""
    
    query = "Học phí tại UIT như thế nào?"
    
    print("=" * 80)
    print("DEBUG RAG RETRIEVAL")
    print("=" * 80)
    print(f"\nQuery: {query}")
    
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        planner = orchestrator.smart_planner
        
        print("\n⏳ Calling Smart Planner...")
        plan_input = {"query": query, "context": {}, "user_profile": {}}
        plan_result = await planner.process(plan_input)
        
        print(f"\n📊 PLANNER DECISION:")
        print(f"   requires_rag: {plan_result.requires_rag}")
        print(f"   complexity: {plan_result.complexity}")
        print(f"   complexity_score: {plan_result.complexity_score}")
        print(f"   strategy: {plan_result.strategy}")
        print(f"   use_knowledge_graph: {plan_result.use_knowledge_graph}")
        print(f"   use_vector_search: {plan_result.use_vector_search}")
        print(f"   rewritten_queries: {plan_result.rewritten_queries}")
        print(f"   top_k: {plan_result.top_k}")
        
        if not plan_result.requires_rag:
            print("\n❌ PLANNER SAYS: NO RAG NEEDED!")
            print(f"   Reason: {plan_result.reasoning}")
        else:
            print("\n✅ PLANNER SAYS: USE RAG")
            
            # Try calling RAG service directly
            print("\n⏳ Testing RAG service call...")
            rag_port = orchestrator.rag_port
            
            search_query = plan_result.rewritten_queries[0] if plan_result.rewritten_queries else query
            
            try:
                rag_result = await rag_port.search(
                    query=search_query,
                    top_k=plan_result.top_k,
                    filters={}
                )
                
                print(f"\n📊 RAG SERVICE RESPONSE:")
                print(f"   Documents returned: {len(rag_result.get('retrieved_documents', []))}")
                
                if rag_result.get('retrieved_documents'):
                    print(f"\n   📄 Sample documents:")
                    for idx, doc in enumerate(rag_result['retrieved_documents'][:3], 1):
                        print(f"\n      [{idx}]")
                        print(f"          Title: {doc.get('title', 'N/A')}")
                        print(f"          Score: {doc.get('score', 'N/A')}")
                        content = doc.get('text', doc.get('content', ''))[:100]
                        print(f"          Content: {content}...")
                else:
                    print("\n   ❌ No documents from RAG service!")
                    print(f"   Response: {rag_result}")
                    
            except Exception as e:
                print(f"\n❌ RAG SERVICE ERROR: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_rag())
