#!/usr/bin/env python3
# scripts/demo_clean_architecture.py
#
# Description:
# Demo script to showcase the new Ports & Adapters architecture
# and compare it with the legacy implementation.

import asyncio
import time
import logging
from pathlib import Path

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.container import get_search_service, get_container
from core.domain.models import SearchQuery, SearchMode, SearchFilters, DocumentLanguage
from adapters.api_facade import get_search_facade
from app.api.schemas.search import SearchRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_core_domain():
    """Demo the pure core domain functionality."""
    print("\n" + "="*60)
    print("🏗️  DEMO: Core Domain Service (Pure Business Logic)")
    print("="*60)
    
    try:
        # Get the search service from DI container
        search_service = get_search_service()
        
        # Create a domain query
        query = SearchQuery(
            text="machine learning algorithms",
            top_k=5,
            search_mode=SearchMode.VECTOR,
            use_rerank=False,
            filters=SearchFilters(
                doc_types=["research", "tutorial"],
                language=DocumentLanguage.VIETNAMESE
            )
        )
        
        print(f"📝 Query: {query.text}")
        print(f"🔍 Mode: {query.search_mode.value}")
        print(f"📊 Top K: {query.top_k}")
        
        # Execute search
        start_time = time.time()
        response = await search_service.search(query)
        end_time = time.time()
        
        print(f"✅ Results: {response.total_hits} hits in {response.latency_ms}ms")
        print(f"⏱️  Total time: {(end_time - start_time) * 1000:.2f}ms")
        
        # Show first result
        if response.results:
            first_result = response.results[0]
            print(f"🎯 Top result: {first_result.text[:100]}...")
            print(f"📈 Score: {first_result.score:.4f}")
            print(f"🏷️  Source: {first_result.source_type}")
        
    except Exception as e:
        print(f"❌ Error in core domain demo: {e}")


async def demo_api_facade():
    """Demo the API facade layer."""
    print("\n" + "="*60)
    print("🌐 DEMO: API Facade (API ↔ Domain Bridge)")
    print("="*60)
    
    try:
        # Get the API facade
        facade = get_search_facade()
        
        # Create API request (using FastAPI schemas)
        request = SearchRequest(
            query="artificial intelligence research",
            top_k=3,
            search_mode="hybrid",
            use_rerank=True,
            doc_types=["paper", "article"],
            language="vi"
        )
        
        print(f"📝 API Request: {request.query}")
        print(f"🔍 Mode: {request.search_mode}")
        print(f"🎛️  Rerank: {request.use_rerank}")
        
        # Execute through facade
        start_time = time.time()
        api_response = await facade.search(request)
        end_time = time.time()
        
        print(f"✅ API Response: {api_response.total_hits} hits")
        print(f"⏱️  Facade time: {(end_time - start_time) * 1000:.2f}ms")
        print(f"🏛️  Architecture: {'clean' if api_response.search_metadata else 'unknown'}")
        
        # Show API response format
        if api_response.hits:
            hit = api_response.hits[0]
            print(f"🎯 API Hit: {hit.text[:80]}...")
            print(f"📊 Score: {hit.score:.4f}")
            print(f"🏷️  Meta: doc_id={hit.meta.doc_id}")
        
    except Exception as e:
        print(f"❌ Error in API facade demo: {e}")


def demo_dependency_injection():
    """Demo the dependency injection container."""
    print("\n" + "="*60)
    print("🔌 DEMO: Dependency Injection Container")
    print("="*60)
    
    try:
        container = get_container()
        
        print("📦 Available Components:")
        
        # Vector repository
        vector_repo = container.get_vector_repository()
        print(f"   🔍 Vector Repository: {type(vector_repo).__name__}")
        
        # Keyword repository
        keyword_repo = container.get_keyword_repository()
        if keyword_repo:
            print(f"   📝 Keyword Repository: {type(keyword_repo).__name__}")
        else:
            print("   📝 Keyword Repository: Not configured")
        
        # Reranking service
        rerank_service = container.get_reranking_service()
        if rerank_service:
            print(f"   🎯 Reranking Service: {type(rerank_service).__name__}")
            print(f"       Available: {rerank_service.is_available()}")
        else:
            print("   🎯 Reranking Service: Not configured")
        
        # Fusion service
        fusion_service = container.get_fusion_service()
        if fusion_service:
            print(f"   🔀 Fusion Service: {type(fusion_service).__name__}")
        else:
            print("   🔀 Fusion Service: Not configured")
        
        # Main search service
        search_service = container.get_search_service()
        print(f"   🚀 Search Service: {type(search_service).__name__}")
        
        print("✅ All dependencies successfully resolved!")
        
    except Exception as e:
        print(f"❌ Error in DI demo: {e}")


def demo_architecture_comparison():
    """Compare new vs legacy architecture."""
    print("\n" + "="*60)
    print("⚖️  DEMO: Architecture Comparison")
    print("="*60)
    
    # Test query
    query_text = "deep learning neural networks"
    
    print(f"📝 Test Query: {query_text}")
    print("\n🆚 Comparing implementations:")
    
    # Test clean architecture
    try:
        print("\n🏗️  Clean Architecture:")
        import asyncio
        from adapters.integration_adapter import get_integration_adapter
        
        adapter = get_integration_adapter()
        request = SearchRequest(query=query_text, top_k=3)
        
        start_time = time.time()
        clean_results = adapter.search(request)
        clean_time = (time.time() - start_time) * 1000
        
        print(f"   ✅ Results: {len(clean_results)}")
        print(f"   ⏱️  Time: {clean_time:.2f}ms")
        print(f"   🧹 Clean separation of concerns")
        print(f"   🔌 Dependency injection")
        print(f"   🧪 Testable components")
        
    except Exception as e:
        print(f"   ❌ Clean architecture error: {e}")
    
    # Test legacy architecture  
    try:
        print("\n🏚️  Legacy Architecture:")
        from retrieval.engine import get_legacy_engine
        
        legacy_engine = get_legacy_engine()
        request = SearchRequest(query=query_text, top_k=3)
        
        start_time = time.time()
        legacy_results = legacy_engine.search(request)
        legacy_time = (time.time() - start_time) * 1000
        
        print(f"   ✅ Results: {len(legacy_results)}")
        print(f"   ⏱️  Time: {legacy_time:.2f}ms")
        print(f"   ⚠️  Tightly coupled")
        print(f"   🌐 Framework dependencies in core")
        print(f"   🧪 Hard to test")
        
    except Exception as e:
        print(f"   ❌ Legacy architecture error: {e}")


async def main():
    """Run all demos."""
    print("🚀 Ports & Adapters Architecture Demo")
    print("="*60)
    
    # Demo individual components
    await demo_core_domain()
    await demo_api_facade()
    demo_dependency_injection()
    demo_architecture_comparison()
    
    print("\n" + "="*60)
    print("🎉 Demo completed!")
    print("="*60)
    
    print("\n💡 Key Benefits Demonstrated:")
    print("   ✅ Clean separation between domain and infrastructure")
    print("   ✅ Framework-independent business logic")  
    print("   ✅ Dependency injection for testability")
    print("   ✅ Multiple implementation support")
    print("   ✅ Backward compatibility maintained")
    
    print("\n📚 Next Steps:")
    print("   1. Run integration tests: pytest tests/")
    print("   2. Check API documentation: /docs")
    print("   3. Monitor logs for architecture usage")
    print("   4. Gradually migrate remaining components")


if __name__ == "__main__":
    asyncio.run(main())
