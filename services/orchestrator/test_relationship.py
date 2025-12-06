#!/usr/bin/env python3
"""
Test query về mối quan hệ giữa các điều
"""
import asyncio
import sys
import os
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except:
    pass

# Import after path is set
from app.core.container import get_container
from app.core.domain import OrchestrationRequest


async def test_relationship_query():
    """Test query về mối quan hệ giữa các điều"""
    
    print("=" * 80)
    print("TEST: Mối quan hệ giữa các điều")
    print("=" * 80)
    
    # Test với câu hỏi về mối quan hệ
    query = "Điều 19 có liên quan gì đến Điều 20?"
    
    try:
        print("\n🔧 Khởi tạo Orchestrator...")
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        if orchestrator.graph_reasoning_agent:
            print("✅ Graph Reasoning Agent: AVAILABLE")
        else:
            print("❌ Graph Reasoning Agent: NOT AVAILABLE")
            return
        
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")
        
        # Create request
        request = OrchestrationRequest(
            user_query=query,
            session_id="test-relationship",
            use_rag=True
        )
        
        print("\n⏳ Processing...")
        result = await orchestrator.process_request(request)
        
        if result and result.response:
            response = result.response
            print(f"\n✅ Response received ({len(response)} chars)")
            print("\n📝 Response:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            
            # Check RAG Context
            print("\n" + "=" * 80)
            print("🔍 KIỂM TRA NGUỒN DỮ LIỆU")
            print("=" * 80)
            
            if result.rag_context and hasattr(result.rag_context, 'retrieved_documents'):
                docs = result.rag_context.retrieved_documents
                print(f"\n📊 Total Documents: {len(docs)}")
                
                # Check for Graph documents
                graph_docs = [doc for doc in docs 
                            if doc.get('metadata', {}).get('source_type') == 'graph_reasoning']
                
                if graph_docs:
                    print(f"\n🔗 Graph Reasoning Documents: {len(graph_docs)}")
                    print("✅ DÙNG KNOWLEDGE GRAPH!")
                    for idx, doc in enumerate(graph_docs, 1):
                        print(f"\n  [{idx}] Graph Document:")
                        print(f"      Title: {doc.get('title', 'N/A')}")
                        content = doc.get('content', '')
                        print(f"      Content preview:")
                        print(f"      {content[:400]}...")
                else:
                    print("\n❌ KHÔNG có Graph Reasoning documents!")
                
                # Show all documents
                print(f"\n📄 All Documents ({len(docs)}):")
                for idx, doc in enumerate(docs[:5], 1):
                    print(f"\n  [{idx}]")
                    print(f"      Source: {doc.get('source', 'N/A')}")
                    print(f"      Score: {doc.get('score', 'N/A')}")
                    content = doc.get('content', '')[:150]
                    print(f"      Content: {content}...")
            else:
                print("\n❌ Không có RAG Context!")
            
            # Show processing stats
            if result.processing_stats:
                print(f"\n📊 Processing Stats:")
                print(f"   - LLM calls: {result.processing_stats.get('llm_calls', 'N/A')}")
                if 'use_knowledge_graph' in result.processing_stats:
                    print(f"   - Use KG: {result.processing_stats['use_knowledge_graph']}")
                if 'graph_nodes_found' in result.processing_stats:
                    print(f"   - Graph nodes found: {result.processing_stats['graph_nodes_found']}")
                if 'graph_paths_found' in result.processing_stats:
                    print(f"   - Graph paths found: {result.processing_stats['graph_paths_found']}")
        else:
            print("\n❌ No response received")
        
        print(f"\n{'=' * 80}")
        print("TEST COMPLETED")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Testing Relationship Query\n")
    asyncio.run(test_relationship_query())
