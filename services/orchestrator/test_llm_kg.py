# -*- coding: utf-8 -*-
"""
Test LLM với Multi-Agent Orchestrator - kiểm tra có lấy kiến thức từ KG không
"""
import asyncio
import sys
import os
from pathlib import Path

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(current_dir) / ".env"
    load_dotenv(env_path, override=True)
except:
    pass

# Import container
import importlib.util
spec = importlib.util.spec_from_file_location(
    "container",
    os.path.join(current_dir, 'app', 'core', 'container.py')
)
container_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(container_module)
get_container = container_module.get_container


async def test_llm_with_kg():
    """Test LLM có sử dụng Knowledge Graph để trả lời không"""
    
    print("=" * 80)
    print("TEST LLM VỚI KNOWLEDGE GRAPH")
    print("=" * 80)
    
    # Các câu hỏi test - tập trung vào quy chế (có trong KG)
    test_queries = [
        {
            "query": "Điều 19 quy định về vấn đề gì?",
            "expect_kg": True,
            "description": "Query về Article cụ thể - nên dùng KG"
        },
        {
            "query": "Điều kiện chuyển ngành là gì?",
            "expect_kg": True,
            "description": "Query về quy định - có thể dùng KG"
        },
        {
            "query": "Sinh viên cần điều kiện gì để chuyển ngành?",
            "expect_kg": True,
            "description": "Query về entity và quy định"
        },
        {
            "query": "Xin chào, bạn là ai?",
            "expect_kg": False,
            "description": "Greeting - không cần KG"
        }
    ]
    
    try:
        # Khởi tạo orchestrator
        print("\n🔧 Đang khởi tạo Multi-Agent Orchestrator...")
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        # Kiểm tra Graph Agent có được load không
        if orchestrator.graph_reasoning_agent:
            print("✅ Graph Reasoning Agent đã được load")
        else:
            print("❌ Graph Reasoning Agent KHÔNG có - test sẽ không đầy đủ")
        
        print("\n" + "=" * 80)
        
        for i, test in enumerate(test_queries, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {i}/{len(test_queries)}")
            print(f"Query: {test['query']}")
            print(f"Description: {test['description']}")
            print(f"Expected KG usage: {'YES' if test['expect_kg'] else 'NO'}")
            print(f"{'=' * 80}")
            
            try:
                # Gọi orchestrator
                print("\n⏳ Đang xử lý query...")
                response = await orchestrator.process_query(
                    query=test['query'],
                    conversation_history=[]
                )
                
                if response:
                    print(f"\n✅ Nhận được response (length: {len(response)})")
                    
                    # Hiển thị response
                    print(f"\n📝 Response:")
                    print("-" * 80)
                    print(response[:500])  # Hiển thị 500 ký tự đầu
                    if len(response) > 500:
                        print("...")
                        print(f"(Total length: {len(response)} characters)")
                    print("-" * 80)
                    
                    # Phân tích xem có dùng KG không
                    kg_indicators = [
                        "knowledge graph",
                        "đồ thị tri thức",
                        "graph",
                        "Điều 19",
                        "Điều 20",
                        "Article",
                        "entity"
                    ]
                    
                    found_indicators = [ind for ind in kg_indicators if ind.lower() in response.lower()]
                    
                    if found_indicators:
                        print(f"\n🔍 Có dấu hiệu sử dụng KG:")
                        for ind in found_indicators[:3]:
                            print(f"   - Tìm thấy: '{ind}'")
                    
                    # Kiểm tra độ dài response
                    if len(response) > 100:
                        print(f"\n✅ Response có nội dung chi tiết ({len(response)} chars)")
                    else:
                        print(f"\n⚠️  Response ngắn ({len(response)} chars)")
                        
                else:
                    print("\n❌ Không nhận được response từ orchestrator")
                    
            except Exception as e:
                print(f"\n❌ LỖI khi xử lý query: {e}")
                import traceback
                traceback.print_exc()
            
            # Delay giữa các queries
            if i < len(test_queries):
                print("\n⏸️  Chờ 2 giây...")
                await asyncio.sleep(2)
        
        print(f"\n{'=' * 80}")
        print("KẾT THÚC TEST")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n❌ LỖI NGHIÊM TRỌNG: {e}")
        import traceback
        traceback.print_exc()


async def test_planner_kg_decision():
    """Test xem Smart Planner có quyết định dùng KG đúng không"""
    
    print("\n" + "=" * 80)
    print("TEST SMART PLANNER - KG DECISION")
    print("=" * 80)
    
    test_queries = [
        "Điều 19 quy định về vấn đề gì?",
        "Môn Nhập môn lập trình có khó không?",
        "Điều kiện chuyển ngành",
        "Xin chào"
    ]
    
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        
        # Access smart planner
        if hasattr(orchestrator, 'smart_planner'):
            planner = orchestrator.smart_planner
            
            for query in test_queries:
                print(f"\n--- Query: {query} ---")
                
                try:
                    # Call planner to get plan
                    plan = await planner.process(query, {})
                    
                    if plan:
                        use_kg = plan.get('use_knowledge_graph', False)
                        intent = plan.get('intent', 'unknown')
                        complexity = plan.get('complexity_score', 0)
                        
                        print(f"✓ Intent: {intent}")
                        print(f"✓ Complexity: {complexity}")
                        print(f"✓ Use KG: {'YES ✅' if use_kg else 'NO ❌'}")
                        
                        if 'reasoning' in plan:
                            print(f"✓ Reasoning: {plan['reasoning'][:100]}...")
                    else:
                        print("❌ No plan returned")
                        
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
        else:
            print("❌ Smart Planner không có trong orchestrator")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🚀 BẮT ĐẦU TEST LLM VỚI KNOWLEDGE GRAPH\n")
    
    # Test 1: LLM end-to-end
    asyncio.run(test_llm_with_kg())
    
    # Test 2: Smart Planner decision
    print("\n\n")
    asyncio.run(test_planner_kg_decision())
