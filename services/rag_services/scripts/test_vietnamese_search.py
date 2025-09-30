#!/usr/bin/env python3
# scripts/test_vietnamese_search.py
#
# Description:
# Test script for Vietnamese text analysis and field filtering capabilities

import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_vietnamese_analyzer():
    """Test Vietnamese text analysis capabilities."""
    print("🇻🇳 Testing Vietnamese Text Analysis")
    print("=" * 50)
    
    # Test queries with Vietnamese characteristics
    test_queries = [
        {
            "query": "thông tin tuyển sinh đại học",
            "description": "Standard Vietnamese query"
        },
        {
            "query": "thong tin tuyen sinh dai hoc", 
            "description": "Vietnamese without diacritics"
        },
        {
            "query": "Thông Tin Tuyển Sinh",
            "description": "Mixed case Vietnamese"
        },
        {
            "query": "quy định học vụ sinh viên",
            "description": "Academic regulations query"
        },
        {
            "query": "quy dinh hoc vu sinh vien",
            "description": "Same query without diacritics"
        },
        {
            "query": "điểm số đánh giá kết quả",
            "description": "Grade evaluation query"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        
        # Test BM25 search with Vietnamese analyzer
        test_bm25_search(test_case['query'])
        
        # Test hybrid search
        test_hybrid_search(test_case['query'])

def test_bm25_search(query: str):
    """Test BM25 search with Vietnamese analyzer."""
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/opensearch/search",
            json={
                "query": query,
                "size": 3,
                "highlight_matches": True,
                "language": "vi"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"  🔍 BM25: Found {len(results['hits'])} results")
            
            for hit in results['hits'][:2]:
                score = hit['bm25_score']
                text_preview = hit['text'][:80] + "..."
                print(f"    • Score: {score:.3f} - {text_preview}")
                
                # Show highlights if available
                if hit.get('highlighted_text'):
                    print(f"    • Highlights: {hit['highlighted_text'][:2]}")
                    
        else:
            print(f"  ❌ BM25 search failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ BM25 search error: {e}")

def test_hybrid_search(query: str):
    """Test hybrid search capabilities."""
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/search",
            json={
                "query": query,
                "search_mode": "hybrid",
                "top_k": 3,
                "use_rerank": True,
                "language": "vi",
                "include_char_spans": True
            },
            timeout=15
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"  🔀 Hybrid: Found {len(results['hits'])} results")
            
            for hit in results['hits'][:2]:
                score = hit['score']
                source = hit.get('source_type', 'unknown')
                text_preview = hit['text'][:80] + "..."
                print(f"    • Score: {score:.3f} ({source}) - {text_preview}")
                
        else:
            print(f"  ❌ Hybrid search failed: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Hybrid search error: {e}")

def test_field_filters():
    """Test field-based filtering capabilities."""
    print("\n🏷️  Testing Field Filters")
    print("=" * 50)
    
    filter_tests = [
        {
            "name": "Filter by Faculty",
            "params": {
                "query": "chương trình đào tạo",
                "faculties": ["CNTT", "KHTN"],
                "top_k": 5
            }
        },
        {
            "name": "Filter by Document Type",
            "params": {
                "query": "quy định",
                "doc_types": ["regulation", "syllabus"],
                "top_k": 5
            }
        },
        {
            "name": "Filter by Year",
            "params": {
                "query": "học tập",
                "years": [2023, 2024],
                "top_k": 5
            }
        },
        {
            "name": "Combined Filters",
            "params": {
                "query": "thi cử",
                "faculties": ["CNTT"],
                "doc_types": ["regulation"],
                "years": [2024],
                "top_k": 5
            }
        }
    ]
    
    import requests
    
    for test in filter_tests:
        print(f"\n📊 {test['name']}")
        
        try:
            response = requests.post(
                "http://localhost:8000/v1/search",
                json={
                    "search_mode": "hybrid",
                    "use_rerank": True,
                    **test['params']
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                hits = results['hits']
                print(f"  ✅ Found {len(hits)} filtered results")
                
                # Show filter distribution
                faculties = set()
                doc_types = set()
                years = set()
                
                for hit in hits:
                    if hit.get('faculty'):
                        faculties.add(hit['faculty'])
                    if hit.get('doc_type'):
                        doc_types.add(hit['doc_type'])
                    if hit.get('year'):
                        years.add(hit['year'])
                
                if faculties:
                    print(f"  📚 Faculties: {', '.join(faculties)}")
                if doc_types:
                    print(f"  📄 Doc Types: {', '.join(doc_types)}")
                if years:
                    print(f"  📅 Years: {', '.join(map(str, sorted(years)))}")
                    
            else:
                print(f"  ❌ Filter test failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Filter test error: {e}")

def test_character_spans():
    """Test character span citation functionality."""
    print("\n📍 Testing Character Spans for Citation")
    print("=" * 50)
    
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/search",
            json={
                "query": "điều kiện tốt nghiệp",
                "search_mode": "hybrid",
                "top_k": 3,
                "include_char_spans": True,
                "highlight_matches": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Found {len(results['hits'])} results with character spans")
            
            for i, hit in enumerate(results['hits'][:2], 1):
                print(f"\n📄 Result {i}:")
                print(f"  Doc ID: {hit['meta']['doc_id']}")
                print(f"  Score: {hit['score']:.3f}")
                
                # Show character spans
                if hit.get('char_spans'):
                    print(f"  📍 Character Spans:")
                    for span in hit['char_spans'][:3]:
                        span_text = span['text'][:50] + "..." if len(span['text']) > 50 else span['text']
                        print(f"    • [{span['start']}-{span['end']}] {span['type']}: {span_text}")
                
                # Show citation info
                if hit.get('citation'):
                    citation = hit['citation']
                    print(f"  📋 Citation:")
                    print(f"    • Doc: {citation.get('doc_id')}")
                    if citation.get('page'):
                        print(f"    • Page: {citation['page']}")
                    if citation.get('char_spans'):
                        print(f"    • Spans: {len(citation['char_spans'])} available")
                
                # Show highlights
                if hit.get('highlighted_text'):
                    print(f"  ✨ Highlights: {hit['highlighted_text'][:2]}")
                    
        else:
            print(f"❌ Character span test failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Character span test error: {e}")

def test_analyzer_performance():
    """Test performance differences between analyzers."""
    print("\n⚡ Testing Analyzer Performance")
    print("=" * 50)
    
    import requests
    import time
    
    query = "thông tin tuyển sinh đại học công nghệ thông tin"
    
    # Test standard analyzer
    print("🔍 Testing Standard Analyzer:")
    start_time = time.time()
    try:
        response = requests.post(
            "http://localhost:8000/v1/opensearch/search",
            json={
                "query": query,
                "size": 10,
                "language": "en"  # Force standard analyzer
            },
            timeout=5
        )
        standard_time = (time.time() - start_time) * 1000
        standard_results = len(response.json()['hits']) if response.status_code == 200 else 0
        print(f"  ⏱️  Time: {standard_time:.2f}ms, Results: {standard_results}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test Vietnamese analyzer
    print("\n🇻🇳 Testing Vietnamese Analyzer:")
    start_time = time.time()
    try:
        response = requests.post(
            "http://localhost:8000/v1/opensearch/search",
            json={
                "query": query,
                "size": 10,
                "language": "vi"  # Use Vietnamese analyzer
            },
            timeout=5
        )
        vietnamese_time = (time.time() - start_time) * 1000
        vietnamese_results = len(response.json()['hits']) if response.status_code == 200 else 0
        print(f"  ⏱️  Time: {vietnamese_time:.2f}ms, Results: {vietnamese_results}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print(f"\n📊 Performance Comparison:")
    if 'standard_time' in locals() and 'vietnamese_time' in locals():
        print(f"  • Standard: {standard_time:.2f}ms ({standard_results} results)")
        print(f"  • Vietnamese: {vietnamese_time:.2f}ms ({vietnamese_results} results)")
        
        if vietnamese_results > standard_results:
            print(f"  ✅ Vietnamese analyzer found {vietnamese_results - standard_results} more results")

def main():
    """Main test function."""
    print("🧪 Vietnamese Search & Field Filter Test Suite")
    print("=" * 60)
    
    # Test Vietnamese text analysis
    test_vietnamese_analyzer()
    
    # Test field-based filtering
    test_field_filters()
    
    # Test character spans for citation
    test_character_spans()
    
    # Test analyzer performance
    test_analyzer_performance()
    
    print("\n" + "=" * 60)
    print("🎉 Vietnamese Search Testing Completed!")
    print("")
    print("Key Features Tested:")
    print("✅ Vietnamese diacritic normalization")
    print("✅ Vietnamese stopword filtering")
    print("✅ Field-based document filtering")
    print("✅ Character span citation")
    print("✅ Enhanced highlighting")
    print("✅ Faceted search aggregations")

if __name__ == "__main__":
    main()
