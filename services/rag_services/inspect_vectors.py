"""
Detailed vector inspection script.
This will actually retrieve and examine the vector data.
"""

import weaviate
from weaviate.classes.query import MetadataQuery

# Connect to Weaviate
client = weaviate.connect_to_local(host="localhost", port=8090)

try:
    collection = client.collections.get("VietnameseDocumentV3")
    
    # Query with vector metadata
    response = collection.query.fetch_objects(
        limit=2,
        include_vector=True,
        return_metadata=MetadataQuery(distance=True)
    )
    
    print("\n" + "=" * 80)
    print("DETAILED VECTOR INSPECTION")
    print("=" * 80)
    
    for i, obj in enumerate(response.objects, 1):
        print(f"\nObject {i}:")
        print(f"  UUID: {obj.uuid}")
        print(f"  Has vector: {obj.vector is not None}")
        
        if obj.vector:
            # The vector might be stored under different keys
            print(f"  Vector type: {type(obj.vector)}")
            
            if isinstance(obj.vector, dict):
                print(f"  Vector is a dict with keys: {list(obj.vector.keys())}")
                for key, value in obj.vector.items():
                    if isinstance(value, list):
                        print(f"    '{key}': list with {len(value)} elements")
                        if len(value) > 0:
                            print(f"      First 5 values: {value[:5]}")
                    else:
                        print(f"    '{key}': {type(value)}")
            elif isinstance(obj.vector, list):
                print(f"  Vector is a list with {len(obj.vector)} elements")
                if len(obj.vector) > 0:
                    print(f"  First 10 values: {obj.vector[:10]}")
            else:
                print(f"  Vector has unexpected type: {type(obj.vector)}")
                print(f"  Vector value: {obj.vector}")
        
        # Show text preview
        text = obj.properties.get("text", "")
        print(f"  Text: {text[:100]}...")
        print(f"  chunk_index: {obj.properties.get('chunk_index')}")
        
finally:
    client.close()

print("\n" + "=" * 80)
