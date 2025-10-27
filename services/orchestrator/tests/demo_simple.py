#!/usr/bin/env python3
"""
Demo đơn giản để test Agent + RAG
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

def test_rag_direct():
    """Test RAG service trực tiếp"""
    print_header("TEST 1: RAG SERVICE TRỰC TIẾP")
    
    query = "Điều kiện tốt nghiệp ngành KHMT"
    print(f"📝 Câu hỏi: {query}\n")
    
    try:
        response = requests.post(
            f"{RAG_URL}/v1/search",
            json={
                "query": query,
                "top_k": 3,
                "search_mode": "vector"
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Thành công!")
            print(f"📊 Tìm thấy: {len(data.get('results', []))} kết quả\n")
            
            for i, result in enumerate(data.get('results', [])[:3], 1):
                print(f"[{i}] Score: {result.get('score', 0):.4f}")
                print(f"    Text: {result.get('text', '')[:200]}...\n")
            
            return True
        else:
            print(f"❌ Lỗi: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_agent_simple():
    """Test agent với câu hỏi đơn giản (không cần RAG)"""
    print_header("TEST 2: AGENT CHAT ĐƠN GIẢN (KHÔNG RAG)")
    
    query = "Xin chào! Bạn là ai?"
    print(f"👤 Người dùng: {query}\n")
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/v1/chat",
            json={
                "query": query,
                "session_id": "test-simple",
                "use_rag": False
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Thành công!")
            print(f"🤖 Agent: {data.get('response', 'No response')}\n")
            print(f"📊 Model: {data.get('model_used', 'Unknown')}")
            print(f"⏱️  Time: {data.get('processing_stats', {}).get('total_time', 0):.2f}s")
            return True
        else:
            print(f"❌ Lỗi: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_agent_with_rag():
    """Test agent với RAG"""
    print_header("TEST 3: AGENT VỚI RAG")
    
    query = "Điều kiện tốt nghiệp ngành Khoa học Máy tính là gì?"
    print(f"👤 Người dùng: {query}\n")
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/v1/chat",
            json={
                "query": query,
                "session_id": "test-with-rag",
                "use_rag": True,
                "rag_top_k": 3
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Thành công!")
            print(f"🤖 Agent: {data.get('response', 'No response')[:300]}...\n")
            print(f"📊 Model: {data.get('model_used', 'Unknown')}")
            print(f"⏱️  Time: {data.get('processing_stats', {}).get('total_time', 0):.2f}s")
            
            # Check if RAG was used
            if 'rag_context' in data:
                rag_ctx = data['rag_context']
                if rag_ctx:
                    print(f"\n📚 RAG Context:")
                    print(f"   - Documents: {len(rag_ctx.get('documents', []))}")
                    print(f"   - Mode: {rag_ctx.get('search_mode', 'N/A')}")
                else:
                    print(f"\n⚠️  RAG context trống")
            else:
                print(f"\n⚠️  Không có RAG context trong response")
            
            return True
        else:
            print(f"❌ Lỗi: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("DEMO: KIỂM TRA AGENT + RAG INTEGRATION".center(80))
    print("="*80)
    
    # Test 1: RAG trực tiếp
    rag_ok = test_rag_direct()
    
    if not rag_ok:
        print("\n⚠️  RAG service có vấn đề, bỏ qua các test khác")
        return
    
    # Test 2: Agent đơn giản
    agent_ok = test_agent_simple()
    
    if not agent_ok:
        print("\n⚠️  Orchestrator có vấn đề, bỏ qua test RAG")
        return
    
    # Test 3: Agent với RAG
    test_agent_with_rag()
    
    print_header("HOÀN THÀNH DEMO")

if __name__ == "__main__":
    main()
