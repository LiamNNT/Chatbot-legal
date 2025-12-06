"""
Check Weaviate data directly
"""
import weaviate
from weaviate.classes.init import Auth

# Connect to Weaviate
client = weaviate.connect_to_local(
    host="localhost",
    port=8090,
    grpc_port=50051
)

try:
    print("=" * 80)
    print("Checking Weaviate Collections")
    print("=" * 80)
    
    # List all collections
    collections = client.collections.list_all()
    print(f"\nAvailable collections: {list(collections.keys())}")
    
    # Check VietnameseDocumentV3 collection
    collection_name = "VietnameseDocumentV3"
    if collection_name in collections:
        collection = client.collections.get(collection_name)
        
        # Get total count
        response = collection.aggregate.over_all(total_count=True)
        print(f"\n{collection_name} collection:")
        print(f"  Total objects: {response.total_count}")
        
        # Get some sample objects with vectors
        if response.total_count > 0:
            results = collection.query.fetch_objects(limit=5, include_vector=True)
            print(f"\n  Sample objects:")
            for i, obj in enumerate(results.objects, 1):
                print(f"\n  Object {i}:")
                print(f"    UUID: {obj.uuid}")
                print(f"    Has vector: {obj.vector is not None and len(obj.vector) > 0 if obj.vector else False}")
                if obj.vector:
                    print(f"    Vector dimensions: {len(obj.vector)}")
                print(f"    Properties: {list(obj.properties.keys())}")
                if 'text' in obj.properties:
                    text = obj.properties['text']
                    print(f"    Text ({len(text)} chars): {text[:300]}..." if len(text) > 300 else f"    Text: {text}")
                if 'doc_id' in obj.properties:
                    print(f"    doc_id: {obj.properties['doc_id']}")
                if 'article_number' in obj.properties:
                    print(f"    article_number: {obj.properties['article_number']}")
                if 'chunk_index' in obj.properties:
                    print(f"    chunk_index: {obj.properties['chunk_index']}")
    else:
        print(f"\n{collection_name} collection NOT FOUND!")
        print("Available collections:", list(collections.keys()))
        
finally:
    client.close()
