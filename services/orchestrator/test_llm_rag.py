"""
Test LLM với RAG - kiểm tra xem LLM có sử dụng context từ RAG không
"""

import requests
import json

def test_llm_with_rag():
    print("\n" + "=" * 80)
    print("TEST LLM VỚI RAG")
    print("=" * 80)
    
    # Câu hỏi cần thông tin từ RAG
    query = "Học phí học kỳ hè tính như thế nào?"
    
    print(f"\nCâu hỏi: {query}\n")
    
    # Gọi orchestrator API
    url = "http://localhost:8001/api/v1/chat"
    
    payload = {
        "query": query,
        "conversation_id": "test-rag-123",
        "user_id": "test-user"
    }
    
    print("Đang gọi Orchestrator API...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            
            print("=" * 80)
            print("KẾT QUẢ TỪ LLM:")
            print("=" * 80)
            print(f"\n{result.get('response', 'No response')}\n")
            
            # Kiểm tra metadata
            if 'metadata' in result:
                print("=" * 80)
                print("METADATA:")
                print("=" * 80)
                metadata = result['metadata']
                
                # Kiểm tra có dùng RAG không
                if 'rag_contexts' in metadata:
                    rag_contexts = metadata['rag_contexts']
                    print(f"\n✅ RAG được sử dụng! Tìm thấy {len(rag_contexts)} context(s)")
                    for i, ctx in enumerate(rag_contexts, 1):
                        print(f"\nRAG Context {i}:")
                        print(f"  - Score: {ctx.get('score', 'N/A')}")
                        print(f"  - Text: {ctx.get('text', '')[:200]}...")
                else:
                    print("\n❌ Không thấy RAG contexts trong metadata")
                
                # Kiểm tra KG
                if 'kg_results' in metadata:
                    kg_results = metadata['kg_results']
                    print(f"\n✅ Knowledge Graph được sử dụng! Tìm thấy {len(kg_results)} node(s)")
                
                # Agent info
                if 'agent_type' in metadata:
                    print(f"\nAgent: {metadata['agent_type']}")
                
                if 'reasoning_steps' in metadata:
                    print(f"Reasoning steps: {len(metadata['reasoning_steps'])}")
            
            print("\n" + "=" * 80)
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Không thể kết nối tới Orchestrator!")
        print("Hãy chắc chắn Orchestrator đang chạy ở port 8001")
        print("\nĐể khởi động:")
        print("  cd services/orchestrator")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    test_llm_with_rag()
