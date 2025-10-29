#!/usr/bin/env python3
"""
Script để xóa và tạo lại OpenSearch index với cấu hình mới
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from opensearchpy import OpenSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_opensearch_index():
    """Reset OpenSearch index"""
    
    # Connect to OpenSearch
    client = OpenSearch(
        hosts=[{'host': 'localhost', 'port': 9200}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    
    index_name = "vietnamese_documents"
    
    print("🔄 Resetting OpenSearch index...")
    print(f"   Index: {index_name}")
    print()
    
    # Check if index exists
    if client.indices.exists(index=index_name):
        print(f"🗑️  Deleting old index: {index_name}")
        client.indices.delete(index=index_name)
        print(f"   ✓ Deleted")
    else:
        print(f"ℹ️  Index {index_name} does not exist")
    
    print()
    print("✅ Index reset complete!")
    print()
    print("📝 Next steps:")
    print("   1. Restart backend: python start_backend.py")
    print("   2. Re-index documents: python services/rag_services/scripts/index_quy_dinh.py")
    print()

if __name__ == "__main__":
    try:
        reset_opensearch_index()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
