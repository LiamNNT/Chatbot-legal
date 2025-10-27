#!/usr/bin/env python3
"""
Script để debug vấn đề search không trả về kết quả
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

def check_index_exists():
    """Kiểm tra index có tồn tại không"""
    print("="*80)
    print("1. KIỂM TRA INDEX TỒN TẠI")
    print("="*80)
    
    indices = client.indices.get_alias(index="*")
    print(f"Tất cả indices: {list(indices.keys())}")
    
    if 'rag_documents' in indices:
        print("✅ Index 'rag_documents' tồn tại")
        return True
    else:
        print("❌ Index 'rag_documents' KHÔNG tồn tại")
        return False

def check_document_count():
    """Đếm số documents"""
    print("\n" + "="*80)
    print("2. ĐẾM SỐ DOCUMENTS")
    print("="*80)
    
    count = client.count(index="rag_documents")
    print(f"Tổng số documents: {count['count']}")
    return count['count']

def view_sample_documents():
    """Xem mẫu documents"""
    print("\n" + "="*80)
    print("3. XEM MẪU DOCUMENTS")
    print("="*80)
    
    response = client.search(
        index="rag_documents",
        body={
            "query": {"match_all": {}},
            "size": 3
        }
    )
    
    hits = response['hits']['hits']
    print(f"Lấy được {len(hits)} documents mẫu:\n")
    
    for i, hit in enumerate(hits, 1):
        print(f"Document {i}:")
        print(f"  ID: {hit['_id']}")
        source = hit['_source']
        print(f"  Text: {source.get('text', '')[:150]}...")
        print(f"  Title: {source.get('title', 'N/A')}")
        print(f"  Doc Type: {source.get('doc_type', 'N/A')}")
        print(f"  All fields: {list(source.keys())}")
        print()

def check_mapping():
    """Xem mapping của index"""
    print("\n" + "="*80)
    print("4. KIỂM TRA MAPPING")
    print("="*80)
    
    mapping = client.indices.get_mapping(index="rag_documents")
    print(json.dumps(mapping, indent=2, ensure_ascii=False))

def test_simple_search():
    """Test search đơn giản"""
    print("\n" + "="*80)
    print("5. TEST SEARCH ĐƠN GIẢN")
    print("="*80)
    
    # Test 1: Match all
    print("\nTest 1: Match All")
    response = client.search(
        index="rag_documents",
        body={
            "query": {"match_all": {}},
            "size": 3
        }
    )
    print(f"  Kết quả: {response['hits']['total']['value']} documents")
    
    # Test 2: Match query
    print("\nTest 2: Match query 'tốt nghiệp'")
    response = client.search(
        index="rag_documents",
        body={
            "query": {
                "match": {
                    "text": "tốt nghiệp"
                }
            },
            "size": 3
        }
    )
    print(f"  Kết quả: {response['hits']['total']['value']} documents")
    
    if response['hits']['total']['value'] > 0:
        for i, hit in enumerate(response['hits']['hits'], 1):
            print(f"  [{i}] Score: {hit['_score']:.4f}")
            print(f"      Text: {hit['_source'].get('text', '')[:150]}...")
    
    # Test 3: Simple query string
    print("\nTest 3: Simple query string 'điều kiện'")
    response = client.search(
        index="rag_documents",
        body={
            "query": {
                "simple_query_string": {
                    "query": "điều kiện",
                    "fields": ["text", "title"]
                }
            },
            "size": 3
        }
    )
    print(f"  Kết quả: {response['hits']['total']['value']} documents")

def test_vector_field():
    """Kiểm tra vector field"""
    print("\n" + "="*80)
    print("6. KIỂM TRA VECTOR FIELD")
    print("="*80)
    
    response = client.search(
        index="rag_documents",
        body={
            "query": {"match_all": {}},
            "size": 1,
            "_source": ["text", "embedding"]
        }
    )
    
    if response['hits']['total']['value'] > 0:
        source = response['hits']['hits'][0]['_source']
        if 'embedding' in source:
            print(f"✅ Vector field 'embedding' tồn tại")
            print(f"   Kích thước: {len(source['embedding'])}")
        else:
            print(f"❌ Vector field 'embedding' KHÔNG tồn tại")
            print(f"   Các fields có sẵn: {list(source.keys())}")

def main():
    print("\n" + "="*80)
    print("DEBUG: OPENSEARCH SEARCH ISSUE".center(80))
    print("="*80 + "\n")
    
    try:
        if not check_index_exists():
            return
        
        count = check_document_count()
        if count == 0:
            print("❌ Không có documents trong index!")
            return
        
        view_sample_documents()
        check_mapping()
        test_simple_search()
        test_vector_field()
        
    except Exception as e:
        print(f"\n❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("HOÀN THÀNH".center(80))
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
