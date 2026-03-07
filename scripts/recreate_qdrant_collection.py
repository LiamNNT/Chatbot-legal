"""
Recreate Qdrant collection with proper vector configuration.
This script deletes the existing collection and creates a new one with explicit vector dimensions.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "rag"))

from app.ingest.store.vector.qdrant_store import (
    get_qdrant_client,
    create_document_collection,
    DOCUMENT_COLLECTION,
)


def main():
    """Recreate Qdrant collection with proper configuration."""

    print("=" * 80)
    print("RECREATING QDRANT COLLECTION WITH PROPER VECTOR CONFIGURATION")
    print("=" * 80)

    # Connect to Qdrant
    print("\n1. Connecting to Qdrant...")
    qdrant_url = os.getenv("QDRANT_URL", "https://2ee9a81c-be7d-484a-93cf-2f229545d6a4.us-east-1-1.aws.cloud.qdrant.io/")
    qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
    client = get_qdrant_client(url=qdrant_url, api_key=qdrant_api_key or None)
    print("✓ Connected to Qdrant")

    # Check if collection exists
    collections = [c.name for c in client.get_collections().collections]
    exists = DOCUMENT_COLLECTION in collections
    print(f"\n2. Collection '{DOCUMENT_COLLECTION}' exists: {exists}")

    # Delete if exists
    if exists:
        print("   Deleting existing collection...")
        client.delete_collection(DOCUMENT_COLLECTION)
        print("   ✓ Collection deleted successfully")

    # Create new collection
    print(f"\n3. Creating new collection '{DOCUMENT_COLLECTION}'...")
    success = create_document_collection(client)

    if success:
        print("   ✓ Collection created successfully")

        # Verify collection
        info = client.get_collection(DOCUMENT_COLLECTION)
        print(f"\n4. Collection Configuration:")
        print(f"   - Name: {DOCUMENT_COLLECTION}")
        print(f"   - Points count: {info.points_count}")
        print(f"   - Vectors config: {info.config.params.vectors}")
        print(f"   - Optimizer: {info.config.optimizer_config}")
    else:
        print("   ✗ Failed to create collection")

    client.close()
    print(f"\n✓ DONE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
