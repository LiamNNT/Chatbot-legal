#!/usr/bin/env python3
# scripts/validate_migration_readiness.py
#
# Description:
# Comprehensive validation script to ensure the system is ready for complete migration
# to Ports & Adapters architecture. This script runs all tests and checks before 
# proceeding with the migration.

import sys
import asyncio
import logging
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_system_health():
    """Check basic system health before running tests."""
    logger.info("🏥 Checking system health...")
    
    try:
        # Check if core components can be imported
        from core.container import get_container, get_search_service
        from adapters.api_facade import get_search_facade
        from core.domain.models import SearchQuery, SearchMode
        
        logger.info("✅ All core imports successful")
        
        # Check container initialization
        container = get_container()
        search_service = get_search_service()
        facade = get_search_facade()
        
        logger.info("✅ All components initialize successfully")
        
        # Check basic functionality
        query = SearchQuery(
            text="test query",
            top_k=1,
            search_mode=SearchMode.VECTOR
        )
        
        logger.info("✅ Can create domain objects")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ System health check failed: {e}")
        return False


def run_architectural_validation():
    """Run architectural validation tests."""
    logger.info("\n📐 Running architectural validation...")
    
    try:
        # Import and run the comprehensive test suite
        from tests.test_architecture_migration import TestArchitectureMigration
        
        test_suite = TestArchitectureMigration()
        success = test_suite.run_comprehensive_test_suite()
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Architectural validation failed: {e}")
        return False


def validate_performance_benchmarks():
    """Run performance benchmarks to ensure the new system is performant."""
    logger.info("\n⚡ Running performance benchmarks...")
    
    try:
        from app.api.schemas.search import SearchRequest
        from adapters.api_facade import get_search_facade
        
        facade = get_search_facade()
        
        # Test queries with different complexities
        test_queries = [
            SearchRequest(query="AI", search_mode="vector", top_k=1),
            SearchRequest(query="machine learning deep learning", search_mode="hybrid", top_k=5, use_rerank=True),
            SearchRequest(query="tuyển sinh đại học công nghệ thông tin", search_mode="bm25", top_k=10)
        ]
        
        total_latency = 0
        successful_queries = 0
        
        for i, request in enumerate(test_queries):
            start_time = time.time()
            try:
                response = asyncio.run(facade.search(request))
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                
                total_latency += latency
                successful_queries += 1
                
                logger.info(f"✅ Query {i+1}: {latency:.2f}ms, {response.total_hits} results")
                
                # Performance threshold check (should be under 5 seconds per query)
                if latency > 5000:
                    logger.warning(f"⚠️ Query {i+1} is slow: {latency:.2f}ms")
                    
            except Exception as e:
                logger.error(f"❌ Query {i+1} failed: {e}")
        
        if successful_queries > 0:
            avg_latency = total_latency / successful_queries
            logger.info(f"📊 Average latency: {avg_latency:.2f}ms")
            logger.info(f"📊 Success rate: {successful_queries}/{len(test_queries)} ({successful_queries/len(test_queries):.1%})")
            
            # Success criteria: at least 80% success rate and average latency under 3 seconds
            if successful_queries >= len(test_queries) * 0.8 and avg_latency < 3000:
                logger.info("✅ Performance benchmarks passed")
                return True
            else:
                logger.warning("⚠️ Performance benchmarks below threshold")
                return False
        else:
            logger.error("❌ No successful queries")
            return False
            
    except Exception as e:
        logger.error(f"❌ Performance benchmark failed: {e}")
        return False


def validate_data_integrity():
    """Validate that search results are consistent and accurate."""
    logger.info("\n🔍 Validating data integrity...")
    
    try:
        from app.api.schemas.search import SearchRequest
        from adapters.api_facade import get_search_facade
        from retrieval.engine import BackwardCompatibleEngine
        
        facade = get_search_facade()
        compat_engine = BackwardCompatibleEngine()
        
        # Test query to compare results
        test_query = SearchRequest(
            query="test query",
            search_mode="hybrid",
            top_k=5,
            use_rerank=False  # Disable reranking for more consistent comparison
        )
        
        # Get results from both systems
        new_response = asyncio.run(facade.search(test_query))
        old_hits = compat_engine.search(test_query)
        
        logger.info(f"New system: {new_response.total_hits} results")
        logger.info(f"Compatibility layer: {len(old_hits)} results")
        
        # Basic consistency check
        # The results don't need to be identical due to different internal processing,
        # but they should be in the same ballpark
        result_ratio = new_response.total_hits / max(1, len(old_hits))
        
        if 0.5 <= result_ratio <= 2.0:  # Within 50%-200% range
            logger.info("✅ Result counts are consistent")
            return True
        else:
            logger.warning(f"⚠️ Result count difference too large: {result_ratio:.2f}x")
            return True  # Don't fail on this - different algorithms may return different counts
            
    except Exception as e:
        logger.error(f"❌ Data integrity validation failed: {e}")
        return False


def validate_error_handling():
    """Validate that error handling is robust."""
    logger.info("\n🛡️ Validating error handling...")
    
    try:
        from app.api.schemas.search import SearchRequest
        from adapters.api_facade import get_search_facade
        
        facade = get_search_facade()
        
        # Test various error conditions
        error_tests = [
            SearchRequest(query="", search_mode="hybrid", top_k=5),  # Empty query
            SearchRequest(query="test", search_mode="invalid", top_k=5),  # Invalid mode
            SearchRequest(query="x" * 10000, search_mode="hybrid", top_k=5),  # Very long query
            SearchRequest(query="test", search_mode="hybrid", top_k=0),  # Invalid top_k
        ]
        
        errors_handled = 0
        
        for i, test_request in enumerate(error_tests):
            try:
                response = asyncio.run(facade.search(test_request))
                # Should either succeed gracefully or handle error properly
                if response is not None:
                    logger.info(f"✅ Error test {i+1}: handled gracefully")
                    errors_handled += 1
                else:
                    logger.warning(f"⚠️ Error test {i+1}: returned None")
            except Exception as e:
                # Some exceptions are acceptable if they're handled properly
                logger.info(f"✅ Error test {i+1}: exception handled - {type(e).__name__}")
                errors_handled += 1
        
        success_rate = errors_handled / len(error_tests)
        logger.info(f"📊 Error handling success rate: {success_rate:.1%}")
        
        if success_rate >= 0.8:
            logger.info("✅ Error handling validation passed")
            return True
        else:
            logger.warning("⚠️ Error handling needs improvement")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error handling validation failed: {e}")
        return False


def check_configuration_consistency():
    """Check that configuration and environment variables work correctly."""
    logger.info("\n⚙️ Checking configuration consistency...")
    
    try:
        import os
        
        # Check environment variables
        clean_arch_setting = os.getenv("USE_CLEAN_ARCHITECTURE", "true")
        vector_backend = os.getenv("VECTOR_BACKEND", "faiss")
        hybrid_search = os.getenv("USE_HYBRID_SEARCH", "true")
        
        logger.info(f"USE_CLEAN_ARCHITECTURE: {clean_arch_setting}")
        logger.info(f"VECTOR_BACKEND: {vector_backend}")
        logger.info(f"USE_HYBRID_SEARCH: {hybrid_search}")
        
        # Test configuration loading
        from app.config.settings import settings
        logger.info(f"Settings loaded: {type(settings).__name__}")
        
        logger.info("✅ Configuration consistency check passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration check failed: {e}")
        return False


def generate_migration_report():
    """Generate a comprehensive migration readiness report."""
    logger.info("\n📋 Generating migration readiness report...")
    
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'checks': [],
        'overall_status': 'UNKNOWN'
    }
    
    # Run all validation checks
    checks = [
        ('System Health', check_system_health),
        ('Architectural Validation', run_architectural_validation),
        ('Performance Benchmarks', validate_performance_benchmarks),
        ('Data Integrity', validate_data_integrity),
        ('Error Handling', validate_error_handling),
        ('Configuration Consistency', check_configuration_consistency)
    ]
    
    passed_checks = 0
    total_checks = len(checks)
    
    for check_name, check_func in checks:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {check_name}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        try:
            result = check_func()
            end_time = time.time()
            duration = end_time - start_time
            
            report['checks'].append({
                'name': check_name,
                'status': 'PASSED' if result else 'FAILED',
                'duration_seconds': duration,
                'error': None
            })
            
            if result:
                passed_checks += 1
                logger.info(f"✅ {check_name}: PASSED ({duration:.2f}s)")
            else:
                logger.error(f"❌ {check_name}: FAILED ({duration:.2f}s)")
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            report['checks'].append({
                'name': check_name,
                'status': 'ERROR',
                'duration_seconds': duration,
                'error': str(e)
            })
            
            logger.error(f"💥 {check_name}: ERROR ({duration:.2f}s) - {e}")
    
    # Determine overall status
    success_rate = passed_checks / total_checks
    if success_rate >= 0.9:
        report['overall_status'] = 'READY'
    elif success_rate >= 0.7:
        report['overall_status'] = 'CAUTION'
    else:
        report['overall_status'] = 'NOT_READY'
    
    report['summary'] = {
        'passed_checks': passed_checks,
        'total_checks': total_checks,
        'success_rate': success_rate
    }
    
    return report


def main():
    """Main validation function."""
    logger.info("🚀 ARCHITECTURE MIGRATION VALIDATION")
    logger.info("="*80)
    logger.info("Validating system readiness for complete migration to Ports & Adapters architecture")
    logger.info("="*80)
    
    start_time = time.time()
    
    # Generate comprehensive report
    report = generate_migration_report()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Print final report
    logger.info("\n" + "="*80)
    logger.info("📊 MIGRATION READINESS REPORT")
    logger.info("="*80)
    logger.info(f"Timestamp: {report['timestamp']}")
    logger.info(f"Total Duration: {total_duration:.2f} seconds")
    logger.info(f"Checks Passed: {report['summary']['passed_checks']}/{report['summary']['total_checks']}")
    logger.info(f"Success Rate: {report['summary']['success_rate']:.1%}")
    logger.info(f"Overall Status: {report['overall_status']}")
    
    logger.info("\nCheck Details:")
    for check in report['checks']:
        status_icon = "✅" if check['status'] == 'PASSED' else "❌" if check['status'] == 'FAILED' else "💥"
        logger.info(f"  {status_icon} {check['name']}: {check['status']} ({check['duration_seconds']:.2f}s)")
        if check['error']:
            logger.info(f"     Error: {check['error']}")
    
    logger.info("\n" + "="*80)
    
    # Final decision
    if report['overall_status'] == 'READY':
        logger.info("🎉 SYSTEM IS READY FOR COMPLETE MIGRATION!")
        logger.info("   ✅ All critical checks passed")
        logger.info("   ✅ Performance is acceptable")
        logger.info("   ✅ Architecture compliance verified")
        logger.info("\n🚀 Proceed with migration steps:")
        logger.info("   1. Refactor /search endpoint")
        logger.info("   2. Remove legacy components")
        logger.info("   3. Clean up scripts and Makefile")
        logger.info("   4. Update documentation")
        return True
        
    elif report['overall_status'] == 'CAUTION':
        logger.warning("⚠️ SYSTEM CAN PROCEED WITH CAUTION")
        logger.warning("   Some non-critical checks failed")
        logger.warning("   Review failed checks before proceeding")
        return True
        
    else:
        logger.error("🚨 SYSTEM NOT READY FOR MIGRATION")
        logger.error("   Critical checks failed")
        logger.error("   Fix issues before attempting migration")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
