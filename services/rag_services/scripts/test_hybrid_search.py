#!/usr/bin/env python3
# scripts/test_hybrid_search.py
#
# Description:
# Script to test hybrid search functionality with sample queries.
# Compares vector-only, BM25-only, and hybrid search results.

import os
import sys
import json
import time
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings
from app.api.schemas.search import SearchRequest
from retrieval.engine import get_query_engine

def test_search_modes():
    """Test different search modes with sample queries."""
    
    # Sample test queries
    test_queries = [
        "học tập tại trường đại học",
        "thông tin tuyển sinh",
        "quy định học vụ", 
        "điểm số và đánh giá",
        "hoạt động sinh viên"
    ]
    
    engine = get_query_engine()
    
    print("🔍 Testing Hybrid Search System")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test Query {i}: '{query}'")
        print("-" * 40)
        
        # Test different search modes
        modes = ["vector", "bm25", "hybrid"]
        
        for mode in modes:
            print(f"\n🔸 {mode.upper()} Search:")
            
            try:
                # Create search request
                request = SearchRequest(
                    query=query,
                    top_k=3,
                    search_mode=mode,
                    use_rerank=True,
                    use_hybrid=True if mode == "hybrid" else False
                )
                
                # Measure search time
                start_time = time.time()
                hits = engine.search(request)
                search_time = (time.time() - start_time) * 1000
                
                print(f"  ⏱️  Time: {search_time:.2f}ms")
                print(f"  📊 Results: {len(hits)} hits")
                
                # Show top results
                for j, hit in enumerate(hits[:2], 1):
                    print(f"    {j}. Score: {hit.score:.4f} | Source: {hit.source_type or 'N/A'}")
                    print(f"       Text: {hit.text[:100]}...")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Hybrid Search Test Completed!")

def compare_fusion_methods():
    """Compare different fusion methods."""
    print("\n🔬 Testing Fusion Methods")
    print("=" * 60)
    
    query = "thông tin tuyển sinh đại học"
    engine = get_query_engine()
    
    # Test with different weight combinations
    weight_combinations = [
        (0.3, 0.7),  # More emphasis on vector
        (0.5, 0.5),  # Equal weights
        (0.7, 0.3),  # More emphasis on BM25
    ]
    
    for bm25_weight, vector_weight in weight_combinations:
        print(f"\n⚖️  BM25 Weight: {bm25_weight}, Vector Weight: {vector_weight}")
        
        try:
            request = SearchRequest(
                query=query,
                top_k=5,
                search_mode="hybrid",
                use_rerank=True,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight
            )
            
            hits = engine.search(request)
            
            print(f"  📊 Total hits: {len(hits)}")
            for i, hit in enumerate(hits[:3], 1):
                print(f"    {i}. Score: {hit.score:.4f} | Fusion Rank: {hit.fusion_rank}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

def check_system_status():
    """Check the status of all system components."""
    print("🔧 System Status Check")
    print("=" * 60)
    
    # Check vector index
    try:
        engine = get_query_engine()
        print("✅ Vector Index: Available")
    except Exception as e:
        print(f"❌ Vector Index: Error - {e}")
    
    # Check OpenSearch
    try:
        from store.opensearch.client import get_opensearch_client
        client = get_opensearch_client()
        if client.health_check():
            stats = client.get_index_stats()
            print(f"✅ OpenSearch: Healthy ({stats['total_docs']} documents)")
        else:
            print("⚠️  OpenSearch: Connected but unhealthy")
    except Exception as e:
        print(f"❌ OpenSearch: Error - {e}")
    
    # Check cross-encoder
    try:
        from sentence_transformers import CrossEncoder
        print("✅ Cross-Encoder: Available")
    except Exception as e:
        print(f"❌ Cross-Encoder: Error - {e}")
    
    # Show configuration
    print("\n📋 Configuration:")
    print(f"  • Vector Backend: {settings.vector_backend}")
    print(f"  • Embedding Model: {settings.emb_model}")
    print(f"  • Rerank Model: {settings.rerank_model}")
    print(f"  • OpenSearch Host: {settings.opensearch_host}:{settings.opensearch_port}")
    print(f"  • Hybrid Search: {settings.use_hybrid_search}")
    print(f"  • BM25 Weight: {settings.bm25_weight}")
    print(f"  • Vector Weight: {settings.vector_weight}")

def main():
    """Main function."""
    print("🚀 Hybrid Search System Test Suite")
    print("=" * 60)
    
    # System status check
    check_system_status()
    
    # Test search modes
    test_search_modes()
    
    # Test fusion methods
    compare_fusion_methods()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main()
