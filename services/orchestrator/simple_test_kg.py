#!/usr/bin/env python3
"""
Simple test to check if LLM uses Knowledge Graph
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


async def simple_kg_test():
    """Simple test to verify KG integration"""
    
    print("=" * 80)
    print("SIMPLE TEST: LLM với Knowledge Graph")
    print("=" * 80)
    
    # Test queries
    test_queries = [
        "Điều 19 quy định về vấn đề gì?",
        "Điều kiện chuyển ngành là gì?",
    ]
    
    try:
        print("\n🔧 Khởi tạo Orchestrator...")
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        # Check Graph Agent
        if orchestrator.graph_reasoning_agent:
            print("✅ Graph Reasoning Agent: AVAILABLE")
        else:
            print("⚠️  Graph Reasoning Agent: NOT AVAILABLE")
        
        print("\n" + "=" * 80)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {i}/{len(test_queries)}: {query}")
            print(f"{'=' * 80}")
            
            try:
                print("\n⏳ Processing...")
                
                # Create request
                request = OrchestrationRequest(
                    user_query=query,
                    session_id="test-session",
                    use_rag=True
                )
                
                # Process request
                result = await orchestrator.process_request(request)
                
                if result and result.response:
                    response = result.response
                    print(f"\n✅ Response received ({len(response)} chars)")
                    print("\n📝 Response:")
                    print("-" * 80)
                    print(response)
                    print("-" * 80)
                    
                    # Check RAG Context - KIỂM TRA NGUỒN DỮ LIỆU
                    print("\n" + "=" * 80)
                    print("🔍 KIỂM TRA NGUỒN DỮ LIỆU (RAG Context)")
                    print("=" * 80)
                    
                    if result.rag_context:
                        rag = result.rag_context
                        print(f"\n✅ RAG Context có dữ liệu:")
                        
                        # Check retrieved documents
                        if hasattr(rag, 'retrieved_documents') and rag.retrieved_documents:
                            print(f"\n📊 Total Documents: {len(rag.retrieved_documents)}")
                            
                            # Check for Graph Reasoning documents
                            graph_docs = [doc for doc in rag.retrieved_documents 
                                        if doc.get('metadata', {}).get('source_type') == 'graph_reasoning']
                            
                            if graph_docs:
                                print(f"\n🔗 Graph Reasoning Documents: {len(graph_docs)}")
                                print("✅ LLM ĐÃ DÙNG KNOWLEDGE GRAPH!")
                                for idx, doc in enumerate(graph_docs[:3], 1):
                                    print(f"\n  [{idx}] Graph Document:")
                                    print(f"      Title: {doc.get('title', 'N/A')}")
                                    print(f"      Source: {doc.get('source', 'N/A')}")
                                    content = doc.get('content', '')[:300]
                                    print(f"      Content: {content}...")
                            else:
                                print("\n❌ KHÔNG có Graph Reasoning documents!")
                                print("⚠️  LLM chỉ dùng vector search, KHÔNG dùng KG!")
                            
                            # Show first few regular documents
                            print(f"\n📄 Sample Documents:")
                            for idx, doc in enumerate(rag.retrieved_documents[:3], 1):
                                print(f"\n  [{idx}] Score: {doc.get('score', 'N/A')}")
                                print(f"      Source: {doc.get('source', 'N/A')}")
                                content = doc.get('content', '')[:150]
                                print(f"      Content: {content}...")
                        else:
                            print("\n❌ KHÔNG có retrieved_documents!")
                        
                        # Check metadata
                        if hasattr(rag, 'search_metadata') and rag.search_metadata:
                            print(f"\n📋 Search Metadata: {rag.search_metadata}")
                    else:
                        print("\n❌ KHÔNG có RAG Context!")
                        print("⚠️  LLM trả lời từ knowledge riêng - có thể HALLUCINATION!")
                    
                    # Show processing stats
                    if result.processing_stats:
                        print(f"\n📊 Processing Stats:")
                        print(f"   - LLM calls: {result.processing_stats.get('llm_calls', 'N/A')}")
                        if 'pipeline_steps' in result.processing_stats:
                            steps = result.processing_stats['pipeline_steps']
                            print(f"   - Pipeline steps: {steps}")
                    
                    # Check for KG usage indicators in response
                    kg_keywords = ["graph", "knowledge graph", "Điều", "Article"]
                    found = [kw for kw in kg_keywords if kw.lower() in response.lower()]
                    
                    if found:
                        print(f"\n🔍 KG keywords in response: {', '.join(found[:3])}")
                    
                else:
                    print("\n❌ No response received")
                    
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            # Wait between queries
            if i < len(test_queries):
                print("\n⏸️  Waiting 2 seconds...")
                await asyncio.sleep(2)
        
        print(f"\n{'=' * 80}")
        print("TEST COMPLETED")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 Starting KG Integration Test\n")
    asyncio.run(simple_kg_test())
