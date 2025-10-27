#!/usr/bin/env python3
"""
DEMO HỎI ĐÁP TƯƠNG TÁC
Cho phép người dùng hỏi các câu hỏi và nhận câu trả lời từ Agent + OpenSearch
"""

import requests
from opensearchpy import OpenSearch
import sys

# URLs
ORCHESTRATOR_URL = "http://localhost:8001"

# OpenSearch connection
os_client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

def search_opensearch(query, top_k=3):
    """Tìm kiếm trong OpenSearch"""
    try:
        response = os_client.search(
            index="rag_documents",
            body={
                "query": {"match": {"text": query}},
                "size": top_k,
                "_source": ["text", "title", "doc_type"]
            }
        )
        
        hits = response['hits']['hits']
        results = []
        
        for hit in hits:
            results.append({
                "text": hit['_source'].get('text', ''),
                "score": hit['_score']
            })
        
        return results
    except Exception as e:
        print(f"⚠️  Lỗi tìm kiếm: {e}")
        return []

def ask_agent(query, use_context=True):
    """Hỏi agent"""
    try:
        # Nếu dùng context, tìm kiếm trước
        if use_context:
            print("🔍 Đang tìm kiếm thông tin liên quan...")
            results = search_opensearch(query, top_k=3)
            
            if results:
                print(f"📚 Tìm thấy {len(results)} tài liệu liên quan\n")
                
                # Tạo context từ kết quả
                context = "\n\n".join([r['text'][:500] for r in results])
                
                full_query = f"""Dựa trên thông tin sau đây, hãy trả lời câu hỏi: "{query}"

Thông tin tham khảo:
{context}

Hãy trả lời một cách chi tiết và chính xác dựa trên thông tin đã cung cấp."""
            else:
                print("⚠️  Không tìm thấy thông tin liên quan, Agent sẽ trả lời dựa trên kiến thức chung\n")
                full_query = query
        else:
            full_query = query
        
        print("🤖 Agent đang xử lý...\n")
        
        # Gọi API
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/v1/chat",
            json={
                "query": full_query,
                "session_id": "interactive-demo",
                "use_rag": False  # Đã có context rồi
            },
            timeout=90
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('response', 'Không có câu trả lời')
            return answer
        else:
            return f"❌ Lỗi: {response.status_code}"
    
    except Exception as e:
        return f"❌ Lỗi: {e}"

def print_banner():
    """In banner"""
    print("\n" + "="*80)
    print("💬 DEMO HỎI ĐÁP TƯƠNG TÁC - CHATBOT UIT".center(80))
    print("="*80)
    print("\n📌 Hướng dẫn:")
    print("   • Nhập câu hỏi của bạn và nhấn Enter")
    print("   • Gõ 'quit' hoặc 'exit' để thoát")
    print("   • Gõ 'help' để xem gợi ý câu hỏi")
    print("\n" + "="*80 + "\n")

def show_suggestions():
    """Hiển thị gợi ý câu hỏi"""
    print("\n💡 GỢI Ý CÂU HỎI:")
    print("\n📚 Về quy định đào tạo:")
    print("   • Điều kiện tốt nghiệp của UIT là gì?")
    print("   • Quy định về đăng ký học phần như thế nào?")
    print("   • Số tín chỉ tối thiểu để tốt nghiệp?")
    print("\n👋 Câu hỏi thông thường:")
    print("   • Bạn là ai?")
    print("   • Bạn có thể giúp gì cho tôi?")
    print("   • UIT là gì?")
    print()

def main():
    """Main function"""
    print_banner()
    
    # Test kết nối
    print("🔄 Kiểm tra kết nối...")
    try:
        # Test Orchestrator
        response = requests.get(f"{ORCHESTRATOR_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Orchestrator đang chạy")
        else:
            print("⚠️  Orchestrator có vấn đề")
    except:
        print("❌ Không kết nối được Orchestrator")
        print("   Hãy chắc chắn service đang chạy trên port 8001")
        return
    
    try:
        # Test OpenSearch
        os_client.info()
        print("✅ OpenSearch đang chạy")
    except:
        print("⚠️  Không kết nối được OpenSearch")
    
    print("\n" + "="*80)
    print("✅ SẴN SÀNG! Bạn có thể bắt đầu hỏi đáp".center(80))
    print("="*80 + "\n")
    
    # Main loop
    while True:
        try:
            # Nhận input
            user_input = input("👤 Bạn: ").strip()
            
            # Kiểm tra commands
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q', 'thoát']:
                print("\n👋 Tạm biệt! Cảm ơn bạn đã sử dụng Chatbot UIT\n")
                break
            
            if user_input.lower() in ['help', 'h', 'gợi ý']:
                show_suggestions()
                continue
            
            print()  # Dòng trống
            
            # Xử lý câu hỏi
            # Kiểm tra nếu câu hỏi về quy định/đào tạo thì dùng context
            keywords = ['quy định', 'điều kiện', 'tốt nghiệp', 'học phần', 'tín chỉ', 
                       'đăng ký', 'chương trình', 'đào tạo', 'UIT', 'KHMT']
            use_context = any(kw.lower() in user_input.lower() for kw in keywords)
            
            # Hỏi agent
            answer = ask_agent(user_input, use_context=use_context)
            
            # In câu trả lời
            print("─" * 80)
            print("🤖 Chatbot UIT:")
            print()
            print(answer)
            print()
            print("─" * 80)
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt! Cảm ơn bạn đã sử dụng Chatbot UIT\n")
            break
        
        except Exception as e:
            print(f"\n❌ Lỗi: {e}\n")

if __name__ == "__main__":
    main()
