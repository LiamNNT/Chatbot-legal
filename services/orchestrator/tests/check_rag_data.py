#!/usr/bin/env python3
"""
Script kiểm tra dữ liệu RAG và test search
"""

import requests
import json

RAG_URL = "http://localhost:8000"

def check_index_stats():
    """Kiểm tra thống kê index"""
    print("="*80)
    print("1. KIỂM TRA INDEX STATS")
    print("="*80)
    
    try:
        # Gọi API để lấy thống kê
        response = requests.get(f"{RAG_URL}/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ RAG Service đang chạy")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"⚠️  Health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def test_search_queries():
    """Test nhiều query khác nhau"""
    print("\n" + "="*80)
    print("2. TEST SEARCH VỚI CÁC QUERY KHÁC NHAU")
    print("="*80)
    
    queries = [
        "điều kiện tốt nghiệp",
        "chương trình đào tạo",
        "học phần bắt buộc",
        "quy định",
        "KHMT",
        "UIT",
    ]
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        print("-" * 80)
        
        try:
            # Test vector search
            response = requests.post(
                f"{RAG_URL}/v1/search",
                json={
                    "query": query,
                    "top_k": 3,
                    "search_mode": "vector"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                print(f"✅ Vector Search: {len(results)} kết quả")
                
                for i, result in enumerate(results[:2], 1):
                    print(f"  [{i}] Score: {result.get('score', 0):.4f}")
                    print(f"      Text: {result.get('text', '')[:150]}...")
            else:
                print(f"❌ Vector Search lỗi: {response.status_code}")
                print(response.text[:200])
                
        except Exception as e:
            print(f"❌ Lỗi: {e}")

def test_keyword_search():
    """Test keyword search"""
    print("\n" + "="*80)
    print("3. TEST KEYWORD SEARCH")
    print("="*80)
    
    query = "điều kiện tốt nghiệp"
    print(f"\n📝 Query: '{query}'")
    
    try:
        response = requests.post(
            f"{RAG_URL}/v1/search",
            json={
                "query": query,
                "top_k": 5,
                "search_mode": "keyword"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Keyword Search: {len(results)} kết quả")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n[{i}] Score: {result.get('score', 0):.4f}")
                metadata = result.get('metadata', {})
                print(f"    Source: {metadata.get('source', 'N/A')}")
                print(f"    Text: {result.get('text', '')[:200]}...")
        else:
            print(f"❌ Keyword Search lỗi: {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def test_hybrid_search():
    """Test hybrid search"""
    print("\n" + "="*80)
    print("4. TEST HYBRID SEARCH")
    print("="*80)
    
    query = "điều kiện tốt nghiệp ngành khoa học máy tính"
    print(f"\n📝 Query: '{query}'")
    
    try:
        response = requests.post(
            f"{RAG_URL}/v1/search",
            json={
                "query": query,
                "top_k": 5,
                "search_mode": "hybrid"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Hybrid Search: {len(results)} kết quả")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n[{i}] Score: {result.get('score', 0):.4f}")
                metadata = result.get('metadata', {})
                print(f"    Source: {metadata.get('source', 'N/A')}")
                print(f"    Title: {metadata.get('title', 'N/A')}")
                print(f"    Text: {result.get('text', '')[:200]}...")
        else:
            print(f"❌ Hybrid Search lỗi: {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def main():
    print("\n" + "="*80)
    print("KIỂM TRA DỮ LIỆU RAG & TEST SEARCH".center(80))
    print("="*80 + "\n")
    
    check_index_stats()
    test_search_queries()
    test_keyword_search()
    test_hybrid_search()
    
    print("\n" + "="*80)
    print("HOÀN THÀNH".center(80))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
