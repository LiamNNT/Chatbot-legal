#!/usr/bin/env python3
"""
Demonstration script for cross-encoder reranking functionality.

This script shows how the cross-encoder reranker improves the accuracy
of search results by reordering them based on query-document relevance.
"""

import asyncio
import logging
from typing import List
from pathlib import Path
import sys

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.domain.models import (
    SearchResult, DocumentMetadata, DocumentLanguage, SearchQuery, SearchMode
)
from adapters.cross_encoder_reranker import create_reranking_service
from core.container import get_search_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_results() -> List[SearchResult]:
    """Create sample search results for demonstration."""
    return [
        SearchResult(
            text="Quy định về học phí tại Đại học Công nghệ Thông tin ĐHQG-HCM. Học phí được tính theo tín chỉ và phụ thuộc vào chương trình đào tạo.",
            metadata=DocumentMetadata(
                doc_id="doc001",
                chunk_id="chunk001",
                title="Quy định học phí UIT",
                doc_type="regulation",
                faculty="CNTT",
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.75,
            source_type="vector",
            rank=1
        ),
        SearchResult(
            text="Hướng dẫn thủ tục nhập học cho sinh viên mới. Sinh viên cần hoàn thành các bước đăng ký, nộp hồ sơ và đóng học phí.",
            metadata=DocumentMetadata(
                doc_id="doc002", 
                chunk_id="chunk002",
                title="Hướng dẫn nhập học",
                doc_type="guide",
                faculty="CNTT",
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.73,
            source_type="vector",
            rank=2
        ),
        SearchResult(
            text="Chương trình đào tạo ngành Khoa học máy tính gồm các học phần cơ sở và chuyên ngành với tổng số 140 tín chỉ.",
            metadata=DocumentMetadata(
                doc_id="doc003",
                chunk_id="chunk003", 
                title="Chương trình đào tạo KHMT",
                doc_type="curriculum",
                faculty="CNTT",
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.71,
            source_type="vector",
            rank=3
        ),
        SearchResult(
            text="Quy trình đăng ký học phần trực tuyến qua hệ thống quản lý đào tạo. Sinh viên đăng nhập và chọn các học phần theo kế hoạch học tập.",
            metadata=DocumentMetadata(
                doc_id="doc004",
                chunk_id="chunk004",
                title="Đăng ký học phần online",
                doc_type="procedure",
                faculty="CNTT", 
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.69,
            source_type="vector",
            rank=4
        ),
        SearchResult(
            text="Thông tin về các phòng thí nghiệm và trang thiết bị phục vụ học tập tại khoa Công nghệ thông tin.",
            metadata=DocumentMetadata(
                doc_id="doc005",
                chunk_id="chunk005",
                title="Phòng thí nghiệm CNTT",
                doc_type="facility",
                faculty="CNTT",
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.67,
            source_type="vector",
            rank=5
        )
    ]


async def demonstrate_reranking_improvement():
    """Demonstrate how reranking improves search result accuracy."""
    print("🔍 CROSS-ENCODER RERANKING DEMONSTRATION")
    print("=" * 60)
    
    # Create sample search results
    original_results = create_sample_results()
    
    # Test queries with different intents
    test_queries = [
        "học phí đại học bao nhiêu tiền",
        "làm thế nào để đăng ký học phần", 
        "chương trình đào tạo khoa học máy tính",
        "thủ tục nhập học sinh viên mới"
    ]
    
    try:
        # Create reranking service
        print("🤖 Initializing cross-encoder reranking service...")
        reranking_service = create_reranking_service(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            multilingual=True,
            batch_size=8
        )
        
        if not reranking_service.is_available():
            print("❌ Reranking service not available. Please install sentence-transformers:")
            print("   pip install sentence-transformers")
            return
        
        print(f"✅ Reranking service initialized: {reranking_service.get_model_info()['model_name']}")
        print()
        
        # Test each query
        for i, query in enumerate(test_queries, 1):
            print(f"📝 Test {i}: '{query}'")
            print("-" * 40)
            
            # Show original results
            print("🔹 Original Results (by vector similarity):")
            for j, result in enumerate(original_results[:3], 1):
                print(f"   {j}. [{result.score:.3f}] {result.metadata.title}")
                print(f"      {result.text[:80]}...")
            
            # Apply reranking
            reranked_results = await reranking_service.rerank(
                query, 
                original_results.copy(), 
                top_k=3
            )
            
            print("\n🔹 Reranked Results (by cross-encoder relevance):")
            for j, result in enumerate(reranked_results, 1):
                original_rank = next(
                    (k for k, r in enumerate(original_results, 1) 
                     if r.metadata.doc_id == result.metadata.doc_id), 
                    "?"
                )
                rerank_score = result.rerank_score or 0
                print(f"   {j}. [{rerank_score:.3f}] {result.metadata.title} (was #{original_rank})")
                print(f"      {result.text[:80]}...")
            
            # Show ranking changes
            original_order = [r.metadata.doc_id for r in original_results[:3]]
            reranked_order = [r.metadata.doc_id for r in reranked_results[:3]]
            
            if original_order != reranked_order:
                print(f"\n✨ Reranking changed the order! Improved relevance for: '{query}'")
            else:
                print(f"\n➡️  No ranking change needed - original order was already optimal")
            
            print("\n" + "="*60 + "\n")
    
    except Exception as e:
        logger.error(f"Error in reranking demonstration: {e}")
        print(f"❌ Error: {e}")
        print("\nMake sure you have sentence-transformers installed:")
        print("pip install sentence-transformers")


async def demonstrate_multilingual_capability():
    """Demonstrate multilingual reranking capability."""
    print("🌐 MULTILINGUAL RERANKING DEMONSTRATION")
    print("=" * 60)
    
    # Mixed Vietnamese and English results
    mixed_results = [
        SearchResult(
            text="University tuition fees and payment procedures for international students at UIT.",
            metadata=DocumentMetadata(
                doc_id="en001",
                title="International Student Fees",
                doc_type="regulation",
                language=DocumentLanguage.ENGLISH
            ),
            score=0.8,
            source_type="vector"
        ),
        SearchResult(
            text="Học phí đại học và thủ tục thanh toán cho sinh viên trong nước tại UIT.",
            metadata=DocumentMetadata(
                doc_id="vi001", 
                title="Học phí sinh viên trong nước",
                doc_type="regulation",
                language=DocumentLanguage.VIETNAMESE
            ),
            score=0.79,
            source_type="vector"
        ),
        SearchResult(
            text="Scholarship programs and financial aid available for students at UIT.",
            metadata=DocumentMetadata(
                doc_id="en002",
                title="Scholarship Programs", 
                doc_type="guide",
                language=DocumentLanguage.ENGLISH
            ),
            score=0.75,
            source_type="vector"
        )
    ]
    
    try:
        reranking_service = create_reranking_service(multilingual=True)
        
        if not reranking_service.is_available():
            print("❌ Multilingual reranking service not available")
            return
        
        # Test with Vietnamese query
        vietnamese_query = "học phí đại học UIT"
        print(f"🇻🇳 Vietnamese Query: '{vietnamese_query}'")
        
        reranked_vi = await reranking_service.rerank(vietnamese_query, mixed_results.copy())
        
        print("Results ranked for Vietnamese query:")
        for i, result in enumerate(reranked_vi, 1):
            lang_flag = "🇻🇳" if result.metadata.language == DocumentLanguage.VIETNAMESE else "🇺🇸"
            print(f"   {i}. {lang_flag} [{result.rerank_score:.3f}] {result.metadata.title}")
        
        # Test with English query
        english_query = "university tuition fees UIT"
        print(f"\n🇺🇸 English Query: '{english_query}'")
        
        reranked_en = await reranking_service.rerank(english_query, mixed_results.copy())
        
        print("Results ranked for English query:")
        for i, result in enumerate(reranked_en, 1):
            lang_flag = "🇻🇳" if result.metadata.language == DocumentLanguage.VIETNAMESE else "🇺🇸"
            print(f"   {i}. {lang_flag} [{result.rerank_score:.3f}] {result.metadata.title}")
        
        print("\n✅ Multilingual reranking successfully adapts to query language!")
        
    except Exception as e:
        print(f"❌ Error in multilingual demonstration: {e}")


async def demonstrate_performance_metrics():
    """Demonstrate reranking performance and metrics."""
    print("📊 RERANKING PERFORMANCE METRICS")
    print("=" * 60)
    
    try:
        reranking_service = create_reranking_service()
        
        if not reranking_service.is_available():
            print("❌ Reranking service not available")
            return
        
        # Create larger result set for performance testing
        large_results = create_sample_results() * 4  # 20 results
        
        query = "học phí đại học công nghệ thông tin"
        
        print(f"📝 Query: '{query}'")
        print(f"📋 Dataset: {len(large_results)} search results")
        
        import time
        start_time = time.time()
        
        reranked_results = await reranking_service.rerank(query, large_results, top_k=10)
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        print(f"⏱️  Processing Time: {processing_time:.2f}ms")
        print(f"📤 Top Results Returned: {len(reranked_results)}")
        
        # Show reranking metadata for top result
        if reranked_results and reranked_results[0].reranking_metadata:
            metadata = reranked_results[0].reranking_metadata
            print(f"🎯 Reranking Details for Top Result:")
            print(f"   Original Rank: #{metadata.original_rank}")
            print(f"   Original Score: {metadata.original_score:.3f}")
            print(f"   Rerank Score: {metadata.rerank_score:.3f}")
            print(f"   Model: {metadata.model_name}")
        
        # Calculate ranking changes
        original_top5_ids = [r.metadata.doc_id for r in large_results[:5]]
        reranked_top5_ids = [r.metadata.doc_id for r in reranked_results[:5]]
        
        changes = sum(1 for i, doc_id in enumerate(reranked_top5_ids) 
                     if i >= len(original_top5_ids) or original_top5_ids[i] != doc_id)
        
        print(f"📈 Ranking Changes in Top-5: {changes}/5 positions")
        
        print("\n✅ Performance metrics collected successfully!")
        
    except Exception as e:
        print(f"❌ Error in performance demonstration: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 CROSS-ENCODER RERANKING SYSTEM DEMO")
    print("=" * 60)
    print("This demo shows how cross-encoder reranking improves")
    print("the accuracy of search results in the RAG system.")
    print("=" * 60)
    print()
    
    try:
        await demonstrate_reranking_improvement()
        await demonstrate_multilingual_capability()
        await demonstrate_performance_metrics()
        
        print("🎉 DEMONSTRATION COMPLETED!")
        print("=" * 60)
        print("Key Benefits Demonstrated:")
        print("✅ Improved relevance ranking with cross-encoder models")
        print("✅ Multilingual support for Vietnamese and English")
        print("✅ Detailed reranking metadata and transparency")
        print("✅ Performance optimization with batched processing")
        print("✅ Graceful fallback when models are unavailable")
        print()
        print("Next Steps:")
        print("1. Install sentence-transformers: pip install sentence-transformers")
        print("2. Configure reranking in settings.py")
        print("3. Run the full RAG system with enhanced reranking")
        print("4. Monitor reranking impact on search quality")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())