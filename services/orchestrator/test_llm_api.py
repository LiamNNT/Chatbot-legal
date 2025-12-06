# -*- coding: utf-8 -*-
"""
Test LLM qua API - kiểm tra có lấy kiến thức từ KG không
"""
import requests
import json
import time

def test_llm_via_api():
    """Test LLM qua orchestrator API"""
    
    print("=" * 80)
    print("TEST LLM QUA API - KNOWLEDGE GRAPH USAGE")
    print("=" * 80)
    
    # API endpoint
    base_url = "http://localhost:8001"
    
    # Test queries
    test_queries = [
        {
            "query": "Điều 19 quy định về vấn đề gì?",
            "expect_kg": True,
            "description": "Query về Article - nên dùng KG"
        },
        {
            "query": "Điều kiện để chuyển ngành là gì?",
            "expect_kg": True,
            "description": "Query về quy định chuyển ngành"
        },
        {
            "query": "Sinh viên cần điều kiện gì để chuyển chương trình đào tạo?",
            "expect_kg": True,
            "description": "Query về entity và quy định"
        },
        {
            "query": "Xin chào, bạn khỏe không?",
            "expect_kg": False,
            "description": "Greeting - không cần KG"
        }
    ]
    
    # Check service health
    print("\n🔍 Kiểm tra service...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Service đang chạy: {response.json()}")
    except Exception as e:
        print(f"❌ Không thể kết nối service: {e}")
        return
    
    print("\n" + "=" * 80)
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(test_queries)}")
        print(f"Query: {test['query']}")
        print(f"Description: {test['description']}")
        print(f"Expected KG: {'YES' if test['expect_kg'] else 'NO'}")
        print(f"{'=' * 80}")
        
        try:
            # Call API
            print("\n⏳ Gọi API...")
            payload = {
                "query": test['query'],
                "conversation_history": []
            }
            
            response = requests.post(
                f"{base_url}/api/v1/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract response
                answer = result.get('response', '')
                metadata = result.get('metadata', {})
                
                print(f"\n✅ Status: {response.status_code}")
                print(f"\n📝 Response:")
                print("-" * 80)
                print(answer[:500] if answer else "No response")
                if len(answer) > 500:
                    print("...")
                    print(f"(Total: {len(answer)} chars)")
                print("-" * 80)
                
                # Check metadata for KG usage
                if metadata:
                    print(f"\n📊 Metadata:")
                    print(f"   - Strategy: {metadata.get('strategy', 'N/A')}")
                    print(f"   - Use KG: {metadata.get('use_knowledge_graph', 'N/A')}")
                    print(f"   - Intent: {metadata.get('intent', 'N/A')}")
                    print(f"   - Complexity: {metadata.get('complexity', 'N/A')}")
                    
                    # Check if KG was used
                    kg_used = metadata.get('use_knowledge_graph', False)
                    if kg_used:
                        print(f"\n✅ KG ĐƯỢC SỬ DỤNG!")
                    else:
                        print(f"\n⚠️  KG KHÔNG được sử dụng")
                        if test['expect_kg']:
                            print(f"   (Mong đợi: nên dùng KG)")
                
                # Analyze response content
                kg_keywords = ['Điều 19', 'Điều 20', 'Article', 'quy chế', 'quy định']
                found = [kw for kw in kg_keywords if kw.lower() in answer.lower()]
                
                if found:
                    print(f"\n🔍 Response chứa keywords KG:")
                    for kw in found[:3]:
                        print(f"   - '{kw}'")
                
            else:
                print(f"\n❌ Error: Status {response.status_code}")
                print(response.text[:200])
                
        except Exception as e:
            print(f"\n❌ LỖI: {e}")
        
        # Delay
        if i < len(test_queries):
            print("\n⏸️  Chờ 2 giây...")
            time.sleep(2)
    
    print(f"\n{'=' * 80}")
    print("KẾT THÚC TEST")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    print("\n🚀 BẮT ĐẦU TEST LLM QUA API\n")
    test_llm_via_api()
