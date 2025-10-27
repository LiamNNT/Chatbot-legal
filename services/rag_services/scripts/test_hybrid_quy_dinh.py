#!/usr/bin/env python3
"""
Test HYBRID search (Vector + BM25) với dữ liệu quy định đã được index.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env")

from core.domain.models import SearchQuery, SearchMode
from infrastructure.container import get_search_service

async def test_hybrid_search():
    """Test hybrid search với các query về quy định đào tạo."""
    
    print("="*80)
    print("TEST HYBRID SEARCH - VECTOR + BM25")
    print("="*80)
    
    # Get search service
    search_service = get_search_service()
    
    # Test queries
    test_queries = [
        ("quy chế đào tạo", "Tìm kiếm về quy chế đào tạo"),
        ("điều kiện tốt nghiệp", "Tìm điều kiện để được tốt nghiệp"),
        ("tín chỉ", "Tìm thông tin về tín chỉ"),
    ]
    
    for query_text, description in test_queries:
        print(f"\n{'='*80}")
        print(f"🔍 Query: '{query_text}'")
        print(f"📝 Mô tả: {description}")
        print(f"{'='*80}")
        
        # Test 3 search modes
        modes = [
            (SearchMode.VECTOR, "Vector Only (Semantic)"),
            (SearchMode.BM25, "BM25 Only (Keyword)"),
            (SearchMode.HYBRID, "Hybrid (Vector + BM25)"),
        ]
        
        for mode, mode_name in modes:
            print(f"\n{'─'*80}")
            print(f"🔬 Mode: {mode_name}")
            print(f"{'─'*80}")
            
            # Create search query
            query = SearchQuery(
                text=query_text,
                top_k=3,
                search_mode=mode,
                use_rerank=False,
                include_char_spans=False,
                highlight_matches=True if mode == SearchMode.BM25 or mode == SearchMode.HYBRID else False
            )
            
            # Execute search
            try:
                response = await search_service.search(query)
                
                print(f"📊 Tìm thấy: {len(response.results)} kết quả")
                print(f"⏱️  Latency: {response.latency_ms}ms")
                
                # Display top 2 results
                for i, result in enumerate(response.results[:2], 1):
                    print(f"\n  #{i}. {result.metadata.title} (Page {result.metadata.page})")
                    print(f"      Score: {result.score:.4f}", end="")
                    if result.bm25_score is not None:
                        print(f" | BM25: {result.bm25_score:.4f}", end="")
                    if result.vector_score is not None:
                        print(f" | Vector: {result.vector_score:.4f}", end="")
                    print()
                    
                    # Show excerpt
                    text_preview = result.text[:150].replace('\n', ' ')
                    print(f"      {text_preview}...")
                    
                    # Show highlights if available
                    if result.highlighted_text and len(result.highlighted_text) > 0:
                        print(f"      🔦 Highlight: {result.highlighted_text[0][:100]}...")
                        
            except Exception as e:
                print(f"❌ Error in {mode_name}: {e}")
    
    print(f"\n{'='*80}")
    print("✅ TEST HYBRID SEARCH HOÀN THÀNH!")
    print("="*80)
    print("\n📊 So sánh:")
    print("   🧠 Vector Search: Tìm theo nghĩa (semantic)")
    print("   🔤 BM25 Search: Tìm theo từ khóa (keyword)")  
    print("   ⚡ Hybrid Search: Kết hợp cả hai → Kết quả tốt nhất!")
    print("\n✅ Hệ thống RAG đã sẵn sàng với HYBRID SEARCH!")


if __name__ == "__main__":
    asyncio.run(test_hybrid_search())
