#!/usr/bin/env python3
"""
Demo với keyword search thay vì vector search
"""

import requests
import json

# URLs
ORCHESTRATOR_URL = "http://localhost:8001"
RAG_URL = "http://localhost:8000"

def print_header(text):
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")

def test_rag_keyword():
    """Test RAG service với keyword search"""
    print_header("TEST: RAG VỚI KEYWORD SEARCH")
    
    query = "Điều kiện tốt nghiệp ngành KHMT"
    print(f"📝 Câu hỏi: {query}\n")
    
    try:
        response = requests.post(
            f"{RAG_URL}/v1/search",
            json={
                "query": query,
                "top_k": 5,
                "search_mode": "keyword"  # Use keyword instead of vector
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', data.get('hits', []))
            print(f"✅ Thành công!")
            print(f"📊 Tìm thấy: {len(results)} kết quả\n")
            
            for i, result in enumerate(results[:5], 1):
                score = result.get('score', result.get('_score', 0))
                text = result.get('text', result.get('_source', {}).get('text', ''))
                print(f"[{i}] Score: {score:.4f}")
                print(f"    Text: {text[:200]}...\n")
            
            return len(results) > 0
        else:
            print(f"❌ Lỗi: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_agent_with_rag_keyword():
    """Test agent với RAG sử dụng keyword search"""
    print_header("TEST: AGENT + RAG (KEYWORD MODE)")
    
    queries = [
        "Điều kiện tốt nghiệp ngành Khoa học Máy tính là gì?",
        "Quy định về đào tạo tại UIT",
        "Chương trình học bắt buộc"
    ]
    
    for query in queries:
        print(f"\n👤 Người dùng: {query}\n")
        
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/api/v1/chat",
                json={
                    "query": query,
                    "session_id": "test-keyword",
                    "use_rag": True,
                    "rag_top_k": 5,
                    "rag_search_mode": "keyword"  # Force keyword mode
                },
                timeout=None
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Thành công!")
                response_text = data.get('response', 'No response')
                print(f"🤖 Agent: {response_text[:400]}...\n")
                
                # Check RAG context
                if 'rag_context' in data and data['rag_context']:
                    rag_ctx = data['rag_context']
                    docs = rag_ctx.get('documents', [])
                    print(f"📚 RAG Context: {len(docs)} documents")
                    print(f"   Mode: {rag_ctx.get('search_mode', 'N/A')}")
                else:
                    print(f"⚠️  Không có RAG context")
                
                print("-" * 80)
            else:
                print(f"❌ Lỗi: {response.status_code}")
                print(response.text[:200])
                
        except Exception as e:
            print(f"❌ Lỗi: {e}")

def main():
    print("\n" + "="*80)
    print("DEMO: RAG VỚI KEYWORD SEARCH (FIX EMBEDDING ISSUE)".center(80))
    print("="*80)
    
    # Test RAG trực tiếp
    rag_ok = test_rag_keyword()
    
    if rag_ok:
        print("\n✅ RAG keyword search hoạt động! Tiếp tục test với Agent...")
        # Test agent
        test_agent_with_rag_keyword()
    else:
        print("\n❌ RAG keyword search không hoạt động")
    
    print_header("HOÀN THÀNH")

if __name__ == "__main__":
    main()
