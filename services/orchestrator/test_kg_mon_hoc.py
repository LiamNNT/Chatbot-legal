# -*- coding: utf-8 -*-
"""
Test nhanh để kiểm tra GraphReasoningAgent có lấy được thông tin môn học từ KG không
"""
import asyncio
import sys
import os

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, '..', 'rag_services'))

# Direct import without module path issues
import importlib.util

# Import Neo4j adapter from rag_services
spec = importlib.util.spec_from_file_location(
    "neo4j_adapter",
    os.path.join(current_dir, '..', 'rag_services', 'adapters', 'graph', 'neo4j_adapter.py')
)
neo4j_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(neo4j_module)
Neo4jGraphAdapter = neo4j_module.Neo4jGraphAdapter

# Import GraphReasoningAgent from orchestrator
spec2 = importlib.util.spec_from_file_location(
    "graph_reasoning_agent",
    os.path.join(current_dir, 'app', 'agents', 'graph_reasoning_agent.py')
)
graph_module = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(graph_module)
GraphReasoningAgent = graph_module.GraphReasoningAgent
GraphQueryType = graph_module.GraphQueryType


async def test_mon_hoc_queries():
    """Test các query về môn học"""
    
    print("=" * 80)
    print("TEST GRAPH REASONING AGENT - MÔN HỌC")
    print("=" * 80)
    
    # Khởi tạo adapter
    adapter = Neo4jGraphAdapter(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="uitchatbot"
    )
    
    # Khởi tạo agent
    agent = GraphReasoningAgent(
        graph_adapter=adapter,  # Sử dụng graph_adapter thay vì neo4j_adapter
        llm_port=None  # Không cần LLM cho test cơ bản
    )
    
    # Các test queries
    test_cases = [
        {
            "name": "Test 1: Query với mã môn",
            "query": "IT001 cần học trước những môn nào?",
            "expected": "Tìm thấy môn IT001 và các môn tiên quyết"
        },
        {
            "name": "Test 2: Query với tên môn tiếng Việt",
            "query": "Môn Nhập môn lập trình có khó không?",
            "expected": "Tìm thấy môn 'Nhập môn lập trình' qua tên"
        },
        {
            "name": "Test 3: Query tiên quyết bằng tên",
            "query": "Học Cấu trúc dữ liệu cần học gì trước?",
            "expected": "Tìm thấy môn 'Cấu trúc dữ liệu' và các tiên quyết"
        },
        {
            "name": "Test 4: Query chung về môn học",
            "query": "các môn học về lập trình",
            "expected": "Tìm thấy danh sách môn học liên quan đến lập trình"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"{test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}")
        print(f"{'=' * 80}")
        
        try:
            # Gọi agent với LOCAL reasoning
            result = await agent.reason(
                query=test['query'],
                query_type=GraphQueryType.LOCAL,
                context={}
            )
            
            # Kiểm tra kết quả
            if result:
                print(f"\n✅ Agent đã xử lý query")
                
                # Hiển thị reasoning steps
                if hasattr(result, 'reasoning_steps') and result.reasoning_steps:
                    print(f"\n📋 Reasoning Steps:")
                    for step in result.reasoning_steps:
                        print(f"   - {step}")
                
                # Hiển thị nodes tìm được
                nodes = result.nodes if hasattr(result, 'nodes') else []
                if nodes:
                    print(f"\n✅ Tìm thấy {len(nodes)} nodes từ KG:")
                    for j, node in enumerate(nodes[:5], 1):
                        node_name = node.get('name') or node.get('ten_mon') or node.get('title', 'Unknown')
                        node_type = node.get('type', 'Unknown')
                        ma_mon = node.get('ma_mon', '')
                        print(f"   {j}. [{node_type}] {node_name} {f'({ma_mon})' if ma_mon else ''}")
                else:
                    print(f"\n❌ KHÔNG tìm thấy nodes từ KG")
                
                # Hiển thị paths nếu có
                paths = result.paths if hasattr(result, 'paths') else []
                if paths:
                    print(f"\n🔗 Tìm thấy {len(paths)} paths (tiên quyết):")
                    for j, path in enumerate(paths[:3], 1):
                        path_nodes = path.get('node_names', [])
                        print(f"   {j}. {' → '.join(path_nodes)}")
                
                # Hiển thị confidence
                confidence = result.confidence if hasattr(result, 'confidence') else 0
                print(f"\n📊 Confidence: {confidence:.2f}")
                
            else:
                print(f"\n❌ Agent không trả về kết quả")
                
        except Exception as e:
            print(f"\n❌ LỖI: {e}")
            import traceback
            traceback.print_exc()
        
        # Delay giữa các tests
        if i < len(test_cases):
            await asyncio.sleep(1)
    
    print(f"\n{'=' * 80}")
    print("KẾT THÚC TEST")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(test_mon_hoc_queries())
