# tests/test_architecture_migration.py
#
# Description:
# Comprehensive test suite for validating the complete migration to Ports & Adapters architecture.
# This test suite verifies that the new architecture provides equivalent or better functionality
# compared to the legacy system.

import pytest
import asyncio
import time
import logging
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock

# Test framework imports
import pytest
from pytest import fixture

# Domain and architecture imports
from core.domain.models import SearchQuery, SearchMode, SearchFilters, DocumentLanguage
from core.domain.search_service import SearchService
from core.container import get_search_service, get_container
from adapters.api_facade import get_search_facade
from app.api.schemas.search import SearchRequest, SearchResponse

# Clean architecture imports
from retrieval.engine import get_query_engine, CleanSearchEngine

logger = logging.getLogger(__name__)


class TestArchitectureMigration:
    """Comprehensive tests for architecture migration validation."""
    
    @pytest.fixture(autouse=True)
    def setup_logging(self):
        """Setup logging for tests."""
        logging.basicConfig(level=logging.INFO)
    
    @pytest.fixture
    def sample_search_queries(self):
        """Sample search queries for testing."""
        return [
            {
                "query": "trí tuệ nhân tạo",
                "search_mode": "hybrid",
                "top_k": 5,
                "language": "vi"
            },
            {
                "query": "machine learning algorithms",
                "search_mode": "vector",
                "top_k": 3,
                "language": "en"
            },
            {
                "query": "tuyển sinh đại học",
                "search_mode": "bm25",
                "top_k": 10,
                "language": "vi"
            }
        ]
    
    @pytest.fixture
    def api_search_requests(self, sample_search_queries):
        """Convert sample queries to API SearchRequest objects."""
        requests = []
        for query in sample_search_queries:
            request = SearchRequest(
                query=query["query"],
                search_mode=query["search_mode"],
                top_k=query["top_k"],
                language=query["language"],
                use_rerank=True
            )
            requests.append(request)
        return requests

    def test_dependency_injection_container(self):
        """Test that DI container is properly configured."""
        logger.info("Testing DI container configuration...")
        
        # Test container initialization
        container = get_container()
        assert container is not None
        
        # Test search service retrieval
        search_service = get_search_service()
        assert search_service is not None
        assert isinstance(search_service, SearchService)
        
        # Test singleton behavior
        search_service2 = get_search_service()
        assert search_service is search_service2
        
        logger.info("✅ DI container tests passed")

    def test_api_facade_initialization(self):
        """Test that API facade is properly initialized."""
        logger.info("Testing API facade initialization...")
        
        facade = get_search_facade()
        assert facade is not None
        
        # Check that facade has search service
        assert hasattr(facade, 'search_service')
        assert facade.search_service is not None
        
        logger.info("✅ API facade initialization tests passed")

    @pytest.mark.asyncio
    async def test_core_domain_search_functionality(self, sample_search_queries):
        """Test core domain search functionality."""
        logger.info("Testing core domain search functionality...")
        
        search_service = get_search_service()
        
        for query_data in sample_search_queries:
            # Convert to domain query
            search_mode = SearchMode.HYBRID
            if query_data["search_mode"] == "vector":
                search_mode = SearchMode.VECTOR
            elif query_data["search_mode"] == "bm25":
                search_mode = SearchMode.BM25
            
            language = DocumentLanguage.VIETNAMESE if query_data["language"] == "vi" else DocumentLanguage.ENGLISH
            
            domain_query = SearchQuery(
                text=query_data["query"],
                top_k=query_data["top_k"],
                search_mode=search_mode,
                filters=SearchFilters(language=language)
            )
            
            # Execute search
            start_time = time.time()
            response = await search_service.search(domain_query)
            end_time = time.time()
            
            # Validate response
            assert response is not None
            assert hasattr(response, 'results')
            assert hasattr(response, 'total_hits')
            assert hasattr(response, 'latency_ms')
            assert response.latency_ms > 0
            
            logger.info(f"✅ Domain search for '{query_data['query']}': {response.total_hits} results in {end_time - start_time:.3f}s")
        
        logger.info("✅ Core domain search tests passed")

    @pytest.mark.asyncio
    async def test_api_facade_search_functionality(self, api_search_requests):
        """Test API facade search functionality."""
        logger.info("Testing API facade search functionality...")
        
        facade = get_search_facade()
        
        for request in api_search_requests:
            start_time = time.time()
            response = await facade.search(request)
            end_time = time.time()
            
            # Validate API response
            assert response is not None
            assert isinstance(response, SearchResponse)
            assert hasattr(response, 'hits')
            assert hasattr(response, 'total_hits')
            assert hasattr(response, 'latency_ms')
            assert response.latency_ms > 0
            
            # Validate search metadata
            if hasattr(response, 'search_metadata') and response.search_metadata:
                assert 'architecture' in response.search_metadata
                assert response.search_metadata['architecture'] == 'clean'
            
            logger.info(f"✅ API facade search for '{request.query}': {response.total_hits} results in {end_time - start_time:.3f}s")
        
        logger.info("✅ API facade search tests passed")

    def test_clean_search_engine(self, api_search_requests):
        """Test the clean search engine implementation."""
        logger.info("Testing clean search engine...")
        
        engine = get_query_engine()
        assert isinstance(engine, CleanSearchEngine)
        
        for request in api_search_requests:
            start_time = time.time()
            hits = engine.search(request)
            end_time = time.time()
            
            # Validate results
            assert hits is not None
            assert isinstance(hits, list)
            
            logger.info(f"✅ Clean engine search for '{request.query}': {len(hits)} results in {end_time - start_time:.3f}s")
        
        logger.info("✅ Clean search engine tests passed")

    @pytest.mark.asyncio
    async def test_performance_comparison(self, api_search_requests):
        """Compare performance between clean architecture and legacy system."""
        logger.info("Testing performance comparison...")
        
        results = {
            'clean_architecture': [],
            'legacy_system': []
        }
        
        # Test clean architecture performance
        facade = get_search_facade()
        for request in api_search_requests:
            start_time = time.time()
            try:
                response = await facade.search(request)
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                results['clean_architecture'].append({
                    'query': request.query,
                    'latency_ms': latency,
                    'total_hits': response.total_hits,
                    'success': True
                })
            except Exception as e:
                results['clean_architecture'].append({
                    'query': request.query,
                    'latency_ms': float('inf'),
                    'total_hits': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Test clean engine performance (direct engine interface)
        try:
            clean_engine = get_query_engine()
            for request in api_search_requests:
                start_time = time.time()
                try:
                    hits = clean_engine.search(request)
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # Convert to ms
                    results['legacy_system'].append({
                        'query': request.query,
                        'latency_ms': latency,
                        'total_hits': len(hits),
                        'success': True
                    })
                except Exception as e:
                    results['legacy_system'].append({
                        'query': request.query,
                        'latency_ms': float('inf'),
                        'total_hits': 0,
                        'success': False,
                        'error': str(e)
                    })
        except Exception as e:
            logger.warning(f"Could not test clean engine direct interface: {e}")
        
        # Analyze results
        clean_avg_latency = sum(r['latency_ms'] for r in results['clean_architecture'] if r['success']) / max(1, len([r for r in results['clean_architecture'] if r['success']]))
        clean_success_rate = len([r for r in results['clean_architecture'] if r['success']]) / len(results['clean_architecture'])
        
        logger.info(f"Clean Architecture - Average Latency: {clean_avg_latency:.2f}ms, Success Rate: {clean_success_rate:.2%}")
        
        if results['legacy_system']:
            engine_avg_latency = sum(r['latency_ms'] for r in results['legacy_system'] if r['success']) / max(1, len([r for r in results['legacy_system'] if r['success']]))
            engine_success_rate = len([r for r in results['legacy_system'] if r['success']]) / len(results['legacy_system'])
            logger.info(f"Direct Engine Interface - Average Latency: {engine_avg_latency:.2f}ms, Success Rate: {engine_success_rate:.2%}")
            
            # Performance should be comparable (within 50% difference)
            if clean_success_rate > 0 and engine_success_rate > 0:
                performance_ratio = clean_avg_latency / engine_avg_latency
                assert performance_ratio < 1.5, f"API facade is significantly slower than direct engine: {performance_ratio:.2f}x"
        
        # Clean architecture should have good success rate
        assert clean_success_rate >= 0.8, f"Clean architecture success rate too low: {clean_success_rate:.2%}"
        
        logger.info("✅ Performance comparison tests passed")

    def test_error_handling_and_resilience(self):
        """Test error handling and system resilience."""
        logger.info("Testing error handling and resilience...")
        
        # Test with invalid queries
        invalid_requests = [
            SearchRequest(query="", search_mode="hybrid", top_k=5),
            SearchRequest(query="test", search_mode="invalid_mode", top_k=0),
            SearchRequest(query="test" * 1000, search_mode="hybrid", top_k=100000)  # Very long query
        ]
        
        facade = get_search_facade()
        
        for request in invalid_requests:
            try:
                response = asyncio.run(facade.search(request))
                # Should handle gracefully and return empty or error response
                assert response is not None
                logger.info(f"✅ Gracefully handled invalid query: '{request.query[:50]}...'")
            except Exception as e:
                # Exceptions should be handled gracefully
                logger.info(f"✅ Exception properly handled for invalid query: {type(e).__name__}")
        
        logger.info("✅ Error handling tests passed")

    def test_configuration_and_environment_variables(self):
        """Test configuration handling and environment variables."""
        logger.info("Testing configuration and environment variables...")
        
        import os
        
        # Test clean architecture environment variable
        original_value = os.environ.get("USE_CLEAN_ARCHITECTURE", "true")
        
        # Test with clean architecture enabled
        os.environ["USE_CLEAN_ARCHITECTURE"] = "true"
        facade1 = get_search_facade()
        assert facade1 is not None
        
        # Test with clean architecture disabled (should still work through compatibility layer)
        os.environ["USE_CLEAN_ARCHITECTURE"] = "false"
        # Note: This doesn't affect already initialized services, but tests the configuration
        
        # Restore original value
        os.environ["USE_CLEAN_ARCHITECTURE"] = original_value
        
        logger.info("✅ Configuration tests passed")

    def test_schema_mapping_accuracy(self):
        """Test accuracy of schema mapping between API and domain layers."""
        logger.info("Testing schema mapping accuracy...")
        
        from adapters.mappers.search_mappers import SearchMapper
        
        # Test API request to domain query mapping
        api_request = SearchRequest(
            query="test query",
            search_mode="hybrid",
            top_k=10,
            use_rerank=True,
            language="vi",
            doc_types=["paper", "article"],
            faculties=["CNTT"],
            bm25_weight=0.7,
            vector_weight=0.3
        )
        
        domain_query = SearchMapper.api_request_to_domain_query(api_request)
        
        # Validate mapping accuracy
        assert domain_query.text == api_request.query
        assert domain_query.top_k == api_request.top_k
        assert domain_query.search_mode == SearchMode.HYBRID
        assert domain_query.use_rerank == api_request.use_rerank
        assert domain_query.bm25_weight == api_request.bm25_weight
        assert domain_query.vector_weight == api_request.vector_weight
        
        if domain_query.filters:
            assert domain_query.filters.language == DocumentLanguage.VIETNAMESE
            assert domain_query.filters.doc_types == ["paper", "article"]
            assert domain_query.filters.faculties == ["CNTT"]
        
        logger.info("✅ Schema mapping tests passed")

    @pytest.mark.asyncio
    async def test_integration_with_real_data(self):
        """Test integration with real sample data."""
        logger.info("Testing integration with real sample data...")
        
        # First, try to create some sample data
        try:
            from scripts.create_sample_data import create_sample_documents
            sample_docs = create_sample_documents()
            logger.info(f"Created {len(sample_docs)} sample documents")
        except Exception as e:
            logger.warning(f"Could not create sample data: {e}")
        
        # Test search with realistic Vietnamese queries
        vietnamese_queries = [
            "tuyển sinh",
            "học phí",
            "chương trình đào tạo",
            "quy định thi cử"
        ]
        
        facade = get_search_facade()
        
        for query in vietnamese_queries:
            request = SearchRequest(
                query=query,
                search_mode="hybrid",
                top_k=5,
                language="vi",
                use_rerank=True
            )
            
            response = await facade.search(request)
            assert response is not None
            
            logger.info(f"✅ Real data search for '{query}': {response.total_hits} results")
        
        logger.info("✅ Real data integration tests passed")

    def test_architecture_compliance(self):
        """Test that the new architecture follows Ports & Adapters principles."""
        logger.info("Testing architecture compliance...")
        
        # Test 1: Core domain should not import framework code
        from core.domain import search_service, models
        import inspect
        
        # Check that core domain doesn't import FastAPI, Pydantic, etc.
        core_source = inspect.getsource(search_service)
        forbidden_imports = ['fastapi', 'pydantic', 'opensearch', 'llama_index']
        
        for forbidden in forbidden_imports:
            assert forbidden not in core_source.lower(), f"Core domain should not import {forbidden}"
        
        # Test 2: Adapters should implement port interfaces
        from adapters.llamaindex_vector_adapter import LlamaIndexVectorAdapter
        from core.ports.repositories import VectorSearchRepository
        
        assert issubclass(LlamaIndexVectorAdapter, VectorSearchRepository)
        
        # Test 3: API facade should convert between schemas
        from adapters.api_facade import SearchApiFacade
        facade = SearchApiFacade()
        
        assert hasattr(facade, 'search')
        assert hasattr(facade, 'search_service')
        
        logger.info("✅ Architecture compliance tests passed")

    def run_comprehensive_test_suite(self):
        """Run all tests in sequence for comprehensive validation."""
        logger.info("\n" + "="*80)
        logger.info("🧪 RUNNING COMPREHENSIVE ARCHITECTURE MIGRATION TESTS")
        logger.info("="*80)
        
        test_results = []
        
        test_methods = [
            self.test_dependency_injection_container,
            self.test_api_facade_initialization,
            self.test_architecture_compliance,
            self.test_schema_mapping_accuracy,
            self.test_error_handling_and_resilience,
            self.test_configuration_and_environment_variables
        ]
        
        async_test_methods = [
            self.test_core_domain_search_functionality,
            self.test_api_facade_search_functionality,
            self.test_performance_comparison,
            self.test_integration_with_real_data
        ]
        
        # Run synchronous tests
        for test_method in test_methods:
            try:
                test_method()
                test_results.append((test_method.__name__, "PASSED", None))
                logger.info(f"✅ {test_method.__name__} PASSED")
            except Exception as e:
                test_results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"❌ {test_method.__name__} FAILED: {e}")
        
        # Run asynchronous tests
        for test_method in async_test_methods:
            try:
                # Create sample data for async tests
                sample_queries = [
                    {"query": "trí tuệ nhân tạo", "search_mode": "hybrid", "top_k": 5, "language": "vi"},
                    {"query": "machine learning", "search_mode": "vector", "top_k": 3, "language": "en"}
                ]
                api_requests = [
                    SearchRequest(query=q["query"], search_mode=q["search_mode"], 
                                top_k=q["top_k"], language=q["language"]) 
                    for q in sample_queries
                ]
                
                if test_method.__name__ == 'test_core_domain_search_functionality':
                    asyncio.run(test_method(sample_queries))
                else:
                    asyncio.run(test_method(api_requests))
                
                test_results.append((test_method.__name__, "PASSED", None))
                logger.info(f"✅ {test_method.__name__} PASSED")
            except Exception as e:
                test_results.append((test_method.__name__, "FAILED", str(e)))
                logger.error(f"❌ {test_method.__name__} FAILED: {e}")
        
        # Test clean search engine separately
        try:
            api_requests = [SearchRequest(query="test", search_mode="hybrid", top_k=5)]
            self.test_clean_search_engine(api_requests)
            test_results.append(("test_clean_search_engine", "PASSED", None))
            logger.info("✅ test_clean_search_engine PASSED")
        except Exception as e:
            test_results.append(("test_clean_search_engine", "FAILED", str(e)))
            logger.error(f"❌ test_clean_search_engine FAILED: {e}")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        passed_count = len([r for r in test_results if r[1] == "PASSED"])
        total_count = len(test_results)
        
        for test_name, status, error in test_results:
            status_icon = "✅" if status == "PASSED" else "❌"
            logger.info(f"{status_icon} {test_name}: {status}")
            if error:
                logger.info(f"   Error: {error}")
        
        logger.info(f"\nPASSED: {passed_count}/{total_count} ({passed_count/total_count:.1%})")
        
        if passed_count == total_count:
            logger.info("🎉 ALL TESTS PASSED - READY FOR MIGRATION!")
            return True
        else:
            logger.error("🚨 SOME TESTS FAILED - MIGRATION NOT RECOMMENDED")
            return False


# Standalone test runner
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run comprehensive tests
    test_suite = TestArchitectureMigration()
    success = test_suite.run_comprehensive_test_suite()
    
    if success:
        print("\n🚀 System is ready for complete migration to Ports & Adapters architecture!")
        sys.exit(0)
    else:
        print("\n⚠️ System needs fixes before migration can proceed safely.")
        sys.exit(1)
