#!/usr/bin/env python3
"""
Test search trực tiếp với OpenSearch không dùng analyzer đặc biệt
"""

from opensearchpy import OpenSearch
import json

# OpenSearch connection
client = OpenSearch(
    hosts=[{'host': 'localhost', 'port': 9200}],
    http_auth=('admin', 'admin'),
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

def test_simple_match():
    """Test với simple match query không cần analyzer"""
    print("="*80)
    print("TEST: SIMPLE MATCH QUERY (NO CUSTOM ANALYZER)")
    print("="*80)
    
    query = "tốt nghiệp"
    
    search_body = {
        "query": {
            "match": {
                "text": query
            }
        },
        "size": 5
    }
    
    print(f"\nQuery: '{query}'")
    print(f"Search body: {json.dumps(search_body, indent=2, ensure_ascii=False)}\n")
    
    try:
        response = client.search(
            index="rag_documents",
            body=search_body
        )
        
        hits = response['hits']['hits']
        total = response['hits']['total']['value']
        
        print(f"✅ Tìm thấy: {total} kết quả")
        print(f"📊 Trả về: {len(hits)} documents\n")
        
        for i, hit in enumerate(hits, 1):
            print(f"[{i}] Score: {hit['_score']:.4f}")
            print(f"    ID: {hit['_id']}")
            print(f"    Text: {hit['_source'].get('text', '')[:150]}...\n")
        
        return len(hits) > 0
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_match()
