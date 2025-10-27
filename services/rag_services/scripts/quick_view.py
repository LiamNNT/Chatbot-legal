#!/usr/bin/env python3
"""
Script nhanh để xem data trong index rag_documents
"""
import requests
import json

OPENSEARCH_URL = "http://localhost:9200"
INDEX_NAME = "rag_documents"

print("🔍 Xem dữ liệu trong index: rag_documents")
print("=" * 80)

# 1. Thống kê
print("\n📊 THỐNG KÊ:")
response = requests.get(f"{OPENSEARCH_URL}/{INDEX_NAME}/_stats")
if response.status_code == 200:
    stats = response.json()
    total_docs = stats['_all']['primaries']['docs']['count']
    size_in_bytes = stats['_all']['primaries']['store']['size_in_bytes']
    size_in_mb = size_in_bytes / (1024 * 1024)
    print(f"  📄 Tổng số documents: {total_docs}")
    print(f"  💾 Kích thước: {size_in_mb:.2f} MB")

# 2. Xem 3 documents mẫu
print("\n📝 DOCUMENTS MẪU (3 documents đầu tiên):")
print("=" * 80)

query = {
    "query": {"match_all": {}},
    "size": 3
}

response = requests.post(
    f"{OPENSEARCH_URL}/{INDEX_NAME}/_search",
    headers={"Content-Type": "application/json"},
    json=query
)

if response.status_code == 200:
    results = response.json()
    hits = results['hits']['hits']
    
    for i, hit in enumerate(hits, 1):
        print(f"\n{'─' * 80}")
        print(f"📄 Document #{i} (ID: {hit['_id']})")
        print(f"{'─' * 80}")
        
        doc = hit['_source']
        for key, value in doc.items():
            if key == 'embedding':
                if isinstance(value, list):
                    print(f"  🔢 {key}: [vector có {len(value)} dimensions]")
            elif isinstance(value, str) and len(value) > 300:
                print(f"  📝 {key}: {value[:300]}...")
            elif isinstance(value, dict):
                print(f"  📦 {key}:")
                for k, v in value.items():
                    if isinstance(v, str) and len(v) > 200:
                        print(f"      {k}: {v[:200]}...")
                    else:
                        print(f"      {k}: {v}")
            else:
                print(f"  ✓ {key}: {value}")

print("\n" + "=" * 80)
print("💡 Để xem thêm, chạy: python scripts/view_indexed_data.py")
print("   hoặc mở OpenSearch Dashboards: http://localhost:5601")
