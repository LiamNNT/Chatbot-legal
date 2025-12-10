#!/usr/bin/env python3
"""
Test thực tế chatbot với câu hỏi về quy chế đào tạo UIT
Xem cách LLM sử dụng RAG và Knowledge Graph
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path FIRST
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup rag_services path
rag_services_path = Path(__file__).parent.parent.parent / "rag_services"
sys.path.insert(0, str(rag_services_path))

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)

# Đảm bảo password Neo4j đúng
os.environ["NEO4J_PASSWORD"] = "uitchatbot"


def print_separator(title):
    print(f"\n{'='*70}")
    print(f"🧪 {title}")
    print(f"{'='*70}")


async def test_real_questions():
    """Test với câu hỏi thực tế"""
    
    print("\n" + "🚀"*35)
    print("    REAL CHATBOT TEST - UIT Quy chế đào tạo")
    print("🚀"*35)
    
    # Import container
    from app.core.container import get_container
    
    print_separator("Initializing Services")
    
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        print("✅ Orchestrator initialized successfully")
        print(f"   - Graph Reasoning: {'Enabled' if orchestrator.graph_reasoning_agent else 'Disabled'}")
        print(f"   - IRCoT: {'Enabled' if orchestrator.ircot_config.enabled else 'Disabled'}")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Các câu hỏi test
    test_questions = [
        # Câu hỏi đơn giản - nên dùng RAG
        "Điều kiện để sinh viên được xét tốt nghiệp là gì?",
        
        # Câu hỏi về quy định cụ thể
        # "Sinh viên cần đạt bao nhiêu tín chỉ để tốt nghiệp?",
        
        # Câu hỏi về mối quan hệ - nên dùng KG
        # "Điều 14 quy định những gì về đăng ký học phần?",
    ]
    
    for i, question in enumerate(test_questions, 1):
        print_separator(f"Question {i}: {question[:50]}...")
        print(f"\n📝 Full question: {question}\n")
        
        try:
            # Gọi orchestrator
            from app.core.domain import OrchestrationRequest
            
            request = OrchestrationRequest(
                query=question,
                conversation_id=f"test_{i}",
                user_id="test_user"
            )
            
            print("⏳ Processing query...")
            print("-" * 50)
            
            result = await orchestrator.process_query(request)
            
            print("\n" + "="*50)
            print("📊 RESULT ANALYSIS")
            print("="*50)
            
            # Hiển thị thông tin về sources
            if hasattr(result, 'metadata') and result.metadata:
                meta = result.metadata
                print(f"\n🔍 Data Sources Used:")
                
                # Kiểm tra RAG context
                if 'rag_context' in meta:
                    rag = meta['rag_context']
                    print(f"   📚 RAG: {len(rag.get('chunks', []))} chunks retrieved")
                    if rag.get('chunks'):
                        print(f"      - Top chunk score: {rag['chunks'][0].get('score', 'N/A')}")
                
                # Kiểm tra KG context  
                if 'kg_context' in meta:
                    kg = meta['kg_context']
                    print(f"   🔗 Knowledge Graph: {kg.get('nodes_found', 0)} nodes")
                    print(f"      - Query type: {kg.get('query_type', 'N/A')}")
                    print(f"      - Confidence: {kg.get('confidence', 'N/A')}")
                
                # Planning info
                if 'planning' in meta:
                    plan = meta['planning']
                    print(f"\n📋 Smart Planner Decision:")
                    print(f"   - Complexity: {plan.get('complexity', 'N/A')}")
                    print(f"   - Use RAG: {plan.get('use_rag', 'N/A')}")
                    print(f"   - Use KG: {plan.get('use_kg', 'N/A')}")
                    print(f"   - Query type: {plan.get('query_type', 'N/A')}")
            
            # Hiển thị câu trả lời
            print(f"\n💬 ANSWER:")
            print("-" * 50)
            answer = result.response if hasattr(result, 'response') else str(result)
            # Giới hạn độ dài hiển thị
            if len(answer) > 1000:
                print(answer[:1000] + "\n... [truncated]")
            else:
                print(answer)
            print("-" * 50)
            
            # Hiển thị citations nếu có
            if hasattr(result, 'citations') and result.citations:
                print(f"\n📎 Citations: {len(result.citations)}")
                for c in result.citations[:3]:
                    print(f"   - {c}")
                    
        except Exception as e:
            print(f"❌ Error processing question: {e}")
            import traceback
            traceback.print_exc()
    
    print_separator("TEST COMPLETED")


if __name__ == "__main__":
    asyncio.run(test_real_questions())
