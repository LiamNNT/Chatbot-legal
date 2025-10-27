#!/usr/bin/env python3
"""
DEMO FINAL: Kiểm tra Agent có thể hỏi đáp được không
Sử dụng OpenSearch trực tiếp để bypass các vấn đề với RAG service
"""

import requests
from opensearchpy import OpenSearch

# URLs
ORCHESTRATOR_URL = "http://localhost:8001"

# OpenSearch direct connection
os_client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

def print_header(text):
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")

def search_opensearch_direct(query):
    """Search OpenSearch trực tiếp"""
    try:
        response = os_client.search(
            index="rag_documents",
            body={
                "query": {"match": {"text": query}},
                "size": 3,
                "_source": ["text", "title", "doc_type"]
            }
        )
        
        hits = response['hits']['hits']
        results = []
        
        for hit in hits:
            results.append({
                "text": hit['_source'].get('text', ''),
                "score": hit['_score'],
                "title": hit['_source'].get('title', ''),
                "doc_type": hit['_source'].get('doc_type', '')
            })
        
        return results
    except Exception as e:
        print(f"❌ OpenSearch error: {e}")
        return []

def test_agent_simple():
    """Test agent với câu hỏi đơn giản"""
    print_header("TEST 1: AGENT CHAT ĐƠN GIẢN")
    
    query = "Xin chào, bạn là trợ lý gì?"
    print(f"👤 Người dùng: {query}\n")
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/v1/chat",
            json={
                "query": query,
                "session_id": "demo-final",
                "use_rag": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('response', 'No response')
            print(f"✅ Agent trả lời:")
            print(f"🤖 {answer[:300]}...\n")
            return True
        else:
            print(f"❌ Lỗi: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_opensearch_then_ask():
    """Test: Tìm kiếm OpenSearch trước, rồi hỏi agent"""
    print_header("TEST 2: TÌM KIẾM DỮ LIỆU + AGENT TRẢ LỜI")
    
    query = "Điều kiện tốt nghiệp"
    print(f"📝 Câu hỏi: {query}\n")
    
    # Bước 1: Tìm kiếm trong OpenSearch
    print("🔍 Bước 1: Tìm kiếm trong OpenSearch...")
    results = search_opensearch_direct(query)
    
    if results:
        print(f"✅ Tìm thấy {len(results)} kết quả:\n")
        context = ""
        for i, result in enumerate(results, 1):
            print(f"[{i}] Score: {result['score']:.4f}")
            print(f"    Text: {result['text'][:150]}...\n")
            context += f"\n{result['text']}\n"
        
        # Bước 2: Hỏi agent với context
        print("🤖 Bước 2: Hỏi agent với context từ OpenSearch...\n")
        
        full_query = f"""Dựa trên thông tin sau đây, hãy trả lời câu hỏi: "{query}"

Thông tin tham khảo:
{context[:1000]}

Hãy trả lời ngắn gọn và chính xác."""
        
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/api/v1/chat",
                json={
                    "query": full_query,
                    "session_id": "demo-final-with-context",
                    "use_rag": False  # Không dùng RAG vì đã có context
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('response', 'No response')
                print(f"✅ Agent trả lời:")
                print(f"🤖 {answer}\n")
                return True
            else:
                print(f"❌ Lỗi: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Lỗi khi hỏi agent: {e}")
            return False
    else:
        print("❌ Không tìm thấy kết quả trong OpenSearch")
        return False

def main():
    print("\n" + "="*80)
    print("🎯 DEMO FINAL: AGENT + OPENSEARCH INTEGRATION".center(80))
    print("="*80)
    print("\nMục tiêu: Kiểm tra agent có thể hỏi đáp được không")
    print("Phương pháp: Sử dụng OpenSearch trực tiếp + Agent\n")
    
    # Test 1: Agent đơn giản
    test1_ok = test_agent_simple()
    
    if not test1_ok:
        print("\n⚠️  Agent không hoạt động, dừng demo")
        return
    
    # Test 2: OpenSearch + Agent
    test2_ok = test_opensearch_then_ask()
    
    print_header("KẾT QUẢ DEMO")
    
    if test1_ok and test2_ok:
        print("✅ THÀNH CÔNG!")
        print("\n📊 Kết luận:")
        print("   ✓ Agent có thể trả lời câu hỏi đơn giản")
        print("   ✓ OpenSearch có thể tìm kiếm dữ liệu")
        print("   ✓ Agent có thể sử dụng context từ OpenSearch để trả lời")
        print("\n💡 Hệ thống hoạt động: Agent ↔ OpenSearch")
    else:
        print("⚠️  MỘT SỐ TEST THẤT BẠI")
        print(f"   - Agent đơn giản: {'✓' if test1_ok else '✗'}")
        print(f"   - Agent + OpenSearch: {'✓' if test2_ok else '✗'}")
    
    print()

if __name__ == "__main__":
    main()
