#!/usr/bin/env python3
"""
Test RAG retrieval - câu hỏi KHÔNG trigger KG
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
from app.core.domain import OrchestrationRequest


async def test_rag_only():
    """Test RAG retrieval without KG"""
    
    print("=" * 80)
    print("TEST: RAG Retrieval (không dùng KG)")
    print("=" * 80)
    
    # Câu hỏi tổng quát về UIT - không phải "Điều X"
    queries = [
        "UIT là trường gì?",
        "Học phí tại UIT như thế nào?",
        "Các ngành đào tạo tại UIT có gì?"
    ]
    
    try:
        print("\n🔧 Khởi tạo Orchestrator...")
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        for idx, query in enumerate(queries, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {idx}/{len(queries)}: {query}")
            print(f"{'=' * 80}")
            
            request = OrchestrationRequest(
                user_query=query,
                session_id=f"test-rag-{idx}",
                use_rag=True
            )
            
            print("\n⏳ Processing...")
            result = await orchestrator.process_request(request)
            
            if result and result.response:
                print(f"\n✅ Response ({len(result.response)} chars):")
                print("-" * 80)
                print(result.response[:400])
                if len(result.response) > 400:
                    print(f"... ({len(result.response) - 400} chars more)")
                print("-" * 80)
                
                # Check sources
                print(f"\n🔍 NGUỒN DỮ LIỆU:")
                
                if result.rag_context and hasattr(result.rag_context, 'retrieved_documents'):
                    docs = result.rag_context.retrieved_documents
                    print(f"   📊 Total Documents: {len(docs)}")
                    
                    # Check for different source types
                    graph_docs = [d for d in docs if d.get('metadata', {}).get('source_type') == 'graph_reasoning']
                    rag_docs = [d for d in docs if d.get('metadata', {}).get('source_type') != 'graph_reasoning' 
                               and d.get('metadata', {}).get('source_type') != 'ircot_reasoning']
                    ircot_docs = [d for d in docs if d.get('metadata', {}).get('source_type') == 'ircot_reasoning']
                    
                    print(f"   🔗 Graph documents: {len(graph_docs)}")
                    print(f"   📚 RAG documents: {len(rag_docs)}")
                    print(f"   🔄 IRCoT documents: {len(ircot_docs)}")
                    
                    if len(rag_docs) > 0:
                        print(f"\n   ✅ LLM ĐÃ DÙNG RAG (Vector Search)!")
                        print(f"\n   📄 Sample RAG Documents:")
                        for i, doc in enumerate(rag_docs[:3], 1):
                            print(f"\n      [{i}] {doc.get('title', 'No title')}")
                            print(f"          Score: {doc.get('score', 'N/A')}")
                            print(f"          Source: {doc.get('source', 'N/A')}")
                            content = doc.get('content', '')[:150]
                            print(f"          Content: {content}...")
                    else:
                        print(f"\n   ❌ KHÔNG có RAG documents!")
                    
                    if len(graph_docs) > 0:
                        print(f"\n   ⚠️  Có Graph documents (không mong đợi cho câu này)")
                    
                else:
                    print("   ❌ Không có RAG Context!")
                
                # Processing stats
                if result.processing_stats:
                    print(f"\n   📊 Stats:")
                    print(f"      - Documents retrieved: {result.processing_stats.get('documents_retrieved', 'N/A')}")
                    print(f"      - Use KG: {result.processing_stats.get('use_knowledge_graph', False)}")
                    print(f"      - Complexity: {result.processing_stats.get('complexity', 'N/A')}")
                
            else:
                print("\n❌ No response")
            
            if idx < len(queries):
                print("\n⏸️  Waiting 2 seconds...")
                await asyncio.sleep(2)
        
        print(f"\n{'=' * 80}")
        print("TEST COMPLETED")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Testing RAG Retrieval\n")
    asyncio.run(test_rag_only())
