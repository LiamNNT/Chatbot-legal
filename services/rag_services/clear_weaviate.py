"""
Script to clear all objects from VietnameseDocumentV3 collection in Weaviate
"""
import weaviate
from weaviate.classes.init import Auth
import os

def clear_collection():
    """Clear all objects from VietnameseDocumentV3 collection"""
    
    # Connect to Weaviate
    client = weaviate.connect_to_local(
        host="localhost",
        port=8090,
        grpc_port=50051
    )
    
    try:
        collection = client.collections.get("VietnameseDocumentV3")
        
        # Get current count
        response = collection.aggregate.over_all(total_count=True)
        count_before = response.total_count
        print(f"Objects before deletion: {count_before}")
        
        if count_before > 0:
            # Delete all objects by fetching UUIDs
            from weaviate.classes.query import Filter
            
            # Fetch all object UUIDs
            objects = collection.query.fetch_objects(limit=count_before)
            
            # Delete each object by UUID
            deleted_count = 0
            for obj in objects.objects:
                collection.data.delete_by_id(obj.uuid)
                deleted_count += 1
            
            print(f"✓ Deleted {deleted_count} objects from VietnameseDocumentV3")
        else:
            print("Collection is already empty")
            
        # Verify deletion
        response = collection.aggregate.over_all(total_count=True)
        count_after = response.total_count
        print(f"Objects after deletion: {count_after}")
        
    finally:
        client.close()

if __name__ == "__main__":
    clear_collection()
