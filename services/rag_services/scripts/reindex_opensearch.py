#!/usr/bin/env python3
"""Re-index OpenSearch from Weaviate V3."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.store.vector.weaviate_store import get_weaviate_client
from infrastructure.store.opensearch.client import get_opensearch_client

print("\n" + "="*80)
print("🔄 RE-INDEX OPENSEARCH FROM WEAVIATE V3")
print("="*80)

# Connect
print("\n📡 Connecting...")
weaviate = get_weaviate_client("http://localhost:8090")
opensearch_client = get_opensearch_client()
collection = weaviate.collections.get("VietnameseDocumentV3")

# Clear old data first - DELETE ENTIRE INDEX
print("\n🗑️  Clearing old OpenSearch data...")
try:
    index_name = opensearch_client.index_name  # Use actual index name from settings
    if opensearch_client.client.indices.exists(index=index_name):
        opensearch_client.client.indices.delete(index=index_name)
        print(f"   ✅ Deleted old index: {index_name}")
    else:
        print(f"   ℹ️  No old index to delete ({index_name})")
except Exception as e:
    print(f"   ⚠️  Error clearing: {e}")

# Get all docs from Weaviate V3
print("\n📥 Fetching from Weaviate V3...")
all_docs = []
offset = 0
while True:
    response = collection.query.fetch_objects(limit=50, offset=offset)
    if not response.objects:
        break
    all_docs.extend(response.objects)
    offset += 50
    if len(all_docs) % 50 == 0:
        print(f"   Fetched {len(all_docs)} docs...")

print(f"✅ Total docs from Weaviate: {len(all_docs)}")

# Convert to OpenSearch format
print("\n📤 Indexing to OpenSearch...")
documents = []
for obj in all_docs:
    p = obj.properties
    # Create doc_id from filename and article if available
    filename = p.get('filename', '')
    article = p.get('article', '')
    doc_id = f"{filename}_{article}" if article else filename
    
    doc = {
        'doc_id': doc_id,  # Required by bulk_index_documents
        'text': p.get('text', ''),
        'chunk_id': p.get('chunk_id', ''),
        'title': p.get('title', ''),
        'structure_type': p.get('structure_type', ''),
        'chapter': p.get('chapter', ''),
        'article': p.get('article', ''),
        'article_number': p.get('article_number', 0),
        'filename': filename,
        'metadata_json': p.get('metadata_json', '{}')
    }
    documents.append(doc)

# Bulk index
success, failed = opensearch_client.bulk_index_documents(documents)

print(f"\n✅ Indexed {success} documents to OpenSearch")
if failed > 0:
    print(f"⚠️  Failed: {failed} documents")

# Verify
stats = opensearch_client.get_index_stats()
print(f"✅ Total docs in OpenSearch: {stats.get('total_docs', 0)}")

weaviate.close()
print("\n🎉 OpenSearch re-indexing complete!\n")
