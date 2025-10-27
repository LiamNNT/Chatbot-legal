#!/usr/bin/env python3
"""
Script để xem data đã được indexing trong OpenSearch
"""
import requests
import json
from typing import Optional

OPENSEARCH_URL = "http://localhost:9200"


def list_all_indices():
    """Liệt kê tất cả các indices trong OpenSearch"""
    print("=" * 80)
    print("📋 DANH SÁCH CÁC INDICES")
    print("=" * 80)
    
    response = requests.get(f"{OPENSEARCH_URL}/_cat/indices?v")
    if response.status_code == 200:
        print(response.text)
    else:
        print(f"❌ Lỗi: {response.status_code}")
        print(response.text)


def get_index_stats(index_name: str):
    """Lấy thống kê của một index"""
    print(f"\n{'=' * 80}")
    print(f"📊 THỐNG KÊ INDEX: {index_name}")
    print("=" * 80)
    
    response = requests.get(f"{OPENSEARCH_URL}/{index_name}/_stats")
    if response.status_code == 200:
        stats = response.json()
        total_docs = stats['_all']['primaries']['docs']['count']
        size_in_bytes = stats['_all']['primaries']['store']['size_in_bytes']
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        print(f"📄 Tổng số documents: {total_docs}")
        print(f"💾 Kích thước: {size_in_mb:.2f} MB ({size_in_bytes:,} bytes)")
    else:
        print(f"❌ Lỗi: {response.status_code}")
        print(response.text)


def get_index_mapping(index_name: str):
    """Xem mapping (schema) của index"""
    print(f"\n{'=' * 80}")
    print(f"🗺️  MAPPING CỦA INDEX: {index_name}")
    print("=" * 80)
    
    response = requests.get(f"{OPENSEARCH_URL}/{index_name}/_mapping")
    if response.status_code == 200:
        mapping = response.json()
        print(json.dumps(mapping, indent=2, ensure_ascii=False))
    else:
        print(f"❌ Lỗi: {response.status_code}")


def view_sample_documents(index_name: str, size: int = 5):
    """Xem một số documents mẫu"""
    print(f"\n{'=' * 80}")
    print(f"📝 DOCUMENTS MẪU TỪ INDEX: {index_name} (hiển thị {size} documents)")
    print("=" * 80)
    
    query = {
        "query": {
            "match_all": {}
        },
        "size": size
    }
    
    response = requests.post(
        f"{OPENSEARCH_URL}/{index_name}/_search",
        headers={"Content-Type": "application/json"},
        json=query
    )
    
    if response.status_code == 200:
        results = response.json()
        hits = results['hits']['hits']
        total = results['hits']['total']['value']
        
        print(f"\n🔢 Tổng số documents trong index: {total}")
        print(f"📄 Đang hiển thị {len(hits)} documents:\n")
        
        for i, hit in enumerate(hits, 1):
            print(f"\n{'─' * 80}")
            print(f"Document #{i} (ID: {hit['_id']})")
            print(f"{'─' * 80}")
            
            # Pretty print document source
            doc = hit['_source']
            for key, value in doc.items():
                if key == 'embedding':
                    # Không hiển thị toàn bộ embedding vector (quá dài)
                    if isinstance(value, list):
                        print(f"  {key}: [vector có {len(value)} dimensions]")
                    else:
                        print(f"  {key}: {str(value)[:100]}...")
                elif isinstance(value, str) and len(value) > 200:
                    print(f"  {key}: {value[:200]}...")
                else:
                    print(f"  {key}: {value}")
    else:
        print(f"❌ Lỗi: {response.status_code}")
        print(response.text)


def search_documents(index_name: str, query_text: str, size: int = 3):
    """Tìm kiếm documents theo keyword"""
    print(f"\n{'=' * 80}")
    print(f"🔍 TÌM KIẾM: '{query_text}' TRONG INDEX: {index_name}")
    print("=" * 80)
    
    query = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["content", "text", "title", "metadata.*"]
            }
        },
        "size": size
    }
    
    response = requests.post(
        f"{OPENSEARCH_URL}/{index_name}/_search",
        headers={"Content-Type": "application/json"},
        json=query
    )
    
    if response.status_code == 200:
        results = response.json()
        hits = results['hits']['hits']
        total = results['hits']['total']['value']
        
        print(f"\n🔢 Tìm thấy {total} kết quả, hiển thị top {len(hits)}:\n")
        
        for i, hit in enumerate(hits, 1):
            print(f"\n{'─' * 80}")
            print(f"Kết quả #{i} (Score: {hit['_score']:.4f})")
            print(f"{'─' * 80}")
            doc = hit['_source']
            
            # Hiển thị các trường quan trọng
            for key in ['title', 'content', 'text', 'metadata']:
                if key in doc:
                    value = doc[key]
                    if isinstance(value, str) and len(value) > 300:
                        print(f"  {key}: {value[:300]}...")
                    else:
                        print(f"  {key}: {value}")
    else:
        print(f"❌ Lỗi: {response.status_code}")
        print(response.text)


def main():
    """Main function với menu tương tác"""
    import sys
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🔍 OPENSEARCH DATA VIEWER                                  ║
║                   Xem dữ liệu đã được indexing                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra kết nối
    try:
        response = requests.get(f"{OPENSEARCH_URL}")
        if response.status_code != 200:
            print(f"❌ Không thể kết nối đến OpenSearch tại {OPENSEARCH_URL}")
            print("Đảm bảo OpenSearch đang chạy (docker-compose up)")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        print("Đảm bảo OpenSearch đang chạy (docker-compose up)")
        sys.exit(1)
    
    print("✅ Đã kết nối thành công đến OpenSearch\n")
    
    # Hiển thị tất cả indices
    list_all_indices()
    
    # Nhập tên index muốn xem
    print("\n" + "=" * 80)
    index_name = input("📝 Nhập tên index muốn xem (hoặc Enter để thoát): ").strip()
    
    if not index_name:
        print("👋 Tạm biệt!")
        return
    
    # Menu chức năng
    while True:
        print(f"\n{'=' * 80}")
        print(f"📂 INDEX: {index_name}")
        print("=" * 80)
        print("1. Xem thống kê")
        print("2. Xem mapping (schema)")
        print("3. Xem documents mẫu")
        print("4. Tìm kiếm theo keyword")
        print("5. Chọn index khác")
        print("0. Thoát")
        print("=" * 80)
        
        choice = input("Chọn chức năng (0-5): ").strip()
        
        if choice == "1":
            get_index_stats(index_name)
        elif choice == "2":
            get_index_mapping(index_name)
        elif choice == "3":
            size = input("Số documents muốn xem (mặc định 5): ").strip()
            size = int(size) if size.isdigit() else 5
            view_sample_documents(index_name, size)
        elif choice == "4":
            query_text = input("Nhập từ khóa tìm kiếm: ").strip()
            if query_text:
                search_documents(index_name, query_text)
        elif choice == "5":
            list_all_indices()
            index_name = input("\n📝 Nhập tên index muốn xem: ").strip()
            if not index_name:
                print("👋 Tạm biệt!")
                break
        elif choice == "0":
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ!")


if __name__ == "__main__":
    main()
