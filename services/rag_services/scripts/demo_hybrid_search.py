#!/usr/bin/env python3
# scripts/demo_hybrid_search.py
#
# Description:
# Complete demo of the Vietnamese Hybrid RAG system with BM25 + Vector + Cross-Encoder

import sys
import json
import time
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from typing import List, Dict, Any

class HybridSearchDemo:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.colors = {
            'header': '\033[95m',
            'blue': '\033[94m', 
            'cyan': '\033[96m',
            'green': '\033[92m',
            'warning': '\033[93m',
            'fail': '\033[91m',
            'end': '\033[0m',
            'bold': '\033[1m',
            'underline': '\033[4m'
        }
        
    def print_colored(self, text: str, color: str = 'end'):
        """Print colored text."""
        print(f"{self.colors.get(color, '')}{text}{self.colors['end']}")
        
    def check_services(self) -> bool:
        """Check if all services are running."""
        self.print_colored("🔍 Checking services...", 'blue')
        
        try:
            # Check RAG service
            response = requests.get(f"{self.base_url}/v1/health", timeout=5)
            if response.status_code == 200:
                self.print_colored("✅ RAG service is running", 'green')
            else:
                self.print_colored("❌ RAG service unhealthy", 'fail')
                return False
                
            # Check OpenSearch
            response = requests.get(f"{self.base_url}/v1/opensearch/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                self.print_colored(f"✅ OpenSearch is {health['status']}", 'green')
            else:
                self.print_colored("❌ OpenSearch unhealthy", 'fail')
                return False
                
        except Exception as e:
            self.print_colored(f"❌ Service check failed: {e}", 'fail')
            self.print_colored("Please run: make start", 'warning')
            return False
            
        return True
        
    def get_index_stats(self) -> Dict[str, Any]:
        """Get OpenSearch index statistics."""
        try:
            response = requests.get(f"{self.base_url}/v1/opensearch/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.print_colored(f"❌ Could not get stats: {e}", 'fail')
        return {}
        
    def demo_search_modes(self):
        """Demo different search modes."""
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("🔍 HYBRID SEARCH MODES DEMO", 'header')
        self.print_colored("="*80, 'header')
        
        query = "tuyển sinh đại học công nghệ thông tin"
        
        search_modes = [
            ("BM25 Only", "bm25"),
            ("Vector Only", "vector"), 
            ("Hybrid (BM25 + Vector)", "hybrid"),
            ("Hybrid + Cross-Encoder Reranking", "hybrid_rerank")
        ]
        
        for mode_name, mode_type in search_modes:
            self.print_colored(f"\n📊 {mode_name}", 'cyan')
            self.print_colored("-" * 50, 'cyan')
            
            try:
                if mode_type == "bm25":
                    response = requests.post(
                        f"{self.base_url}/v1/opensearch/search",
                        json={
                            "query": query,
                            "size": 3,
                            "language": "vi",
                            "highlight_matches": True
                        },
                        timeout=10
                    )
                else:
                    response = requests.post(
                        f"{self.base_url}/v1/search",
                        json={
                            "query": query,
                            "search_mode": mode_type,
                            "size": 3,
                            "language": "vi"
                        },
                        timeout=15
                    )
                
                if response.status_code == 200:
                    results = response.json()
                    hits = results.get('hits', results.get('results', []))
                    
                    for i, hit in enumerate(hits[:3], 1):
                        title = hit.get('title', hit.get('chunk_id', 'Unknown'))
                        score = hit.get('score', hit.get('bm25_score', 0))
                        faculty = hit.get('faculty', 'N/A')
                        doc_type = hit.get('doc_type', 'N/A')
                        
                        self.print_colored(f"  {i}. {title}", 'green')
                        self.print_colored(f"     📍 {faculty}/{doc_type} | Score: {score:.3f}", 'blue')
                        
                        # Show text snippet
                        text = hit.get('text', '')
                        if text:
                            snippet = text[:100] + "..." if len(text) > 100 else text
                            print(f"     💬 {snippet}")
                            
                else:
                    self.print_colored(f"❌ {mode_name} failed: {response.status_code}", 'fail')
                    
            except Exception as e:
                self.print_colored(f"❌ {mode_name} error: {e}", 'fail')
                
            time.sleep(1)  # Brief pause between requests
            
    def demo_vietnamese_features(self):
        """Demo Vietnamese language features."""
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("🇻🇳 VIETNAMESE LANGUAGE FEATURES DEMO", 'header')
        self.print_colored("="*80, 'header')
        
        vietnamese_queries = [
            ("Diacritics Handling", "điều kiện", "dieu kien"),
            ("Stopwords Filtering", "và các quy định", "quy định"),
            ("ICU Tokenization", "công nghệ thông tin", "CNTT"),
            ("Compound Words", "tốt nghiệp", "tốt-nghiệp")
        ]
        
        for feature_name, query, variant in vietnamese_queries:
            self.print_colored(f"\n🧪 {feature_name}", 'cyan')
            self.print_colored(f"Query: '{query}' vs '{variant}'", 'blue')
            
            for test_query in [query, variant]:
                try:
                    response = requests.post(
                        f"{self.base_url}/v1/opensearch/search",
                        json={
                            "query": test_query,
                            "size": 2,
                            "language": "vi",
                            "highlight_matches": True
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        hits = results.get('hits', [])
                        
                        self.print_colored(f"  '{test_query}': {len(hits)} results", 'green')
                        
                        if hits:
                            top_hit = hits[0]
                            score = top_hit.get('bm25_score', 0)
                            highlights = top_hit.get('highlights', [])
                            
                            print(f"    💎 Top score: {score:.3f}")
                            if highlights:
                                print(f"    ✨ Highlighted: {highlights[0][:80]}...")
                    else:
                        self.print_colored(f"  '{test_query}': Failed", 'fail')
                        
                except Exception as e:
                    self.print_colored(f"  '{test_query}': Error - {e}", 'fail')
                    
    def demo_field_filters(self):
        """Demo field-based filtering."""
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("🏷️  FIELD FILTERING DEMO", 'header')
        self.print_colored("="*80, 'header')
        
        base_query = "quy định"
        
        filter_tests = [
            ("No Filter", {}),
            ("Faculty Filter", {"faculty": "CNTT"}),
            ("Document Type Filter", {"doc_type": "regulation"}),
            ("Year Filter", {"year": 2024}),
            ("Multi-Filter", {"faculty": "CNTT", "doc_type": "regulation"})
        ]
        
        for test_name, filters in filter_tests:
            self.print_colored(f"\n🔍 {test_name}", 'cyan')
            if filters:
                filter_str = ", ".join([f"{k}={v}" for k, v in filters.items()])
                self.print_colored(f"Filters: {filter_str}", 'blue')
                
            try:
                request_body = {
                    "query": base_query,
                    "size": 3,
                    "language": "vi"
                }
                request_body.update(filters)
                
                response = requests.post(
                    f"{self.base_url}/v1/search",
                    json=request_body,
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json()
                    hits = results.get('hits', results.get('results', []))
                    
                    self.print_colored(f"  📄 Found {len(hits)} results", 'green')
                    
                    for hit in hits:
                        faculty = hit.get('faculty', 'N/A')
                        doc_type = hit.get('doc_type', 'N/A')
                        year = hit.get('year', 'N/A')
                        score = hit.get('score', 0)
                        
                        print(f"    • {faculty}/{doc_type}/{year} (Score: {score:.3f})")
                        
                else:
                    self.print_colored(f"❌ {test_name} failed: {response.status_code}", 'fail')
                    
            except Exception as e:
                self.print_colored(f"❌ {test_name} error: {e}", 'fail')
                
    def demo_fusion_algorithms(self):
        """Demo different fusion algorithms."""
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("🔬 FUSION ALGORITHMS DEMO", 'header')
        self.print_colored("="*80, 'header')
        
        query = "chương trình đào tạo"
        
        fusion_methods = [
            ("Reciprocal Rank Fusion (RRF)", {"fusion_method": "rrf", "k": 60}),
            ("Weighted Score Fusion", {"fusion_method": "weighted", "bm25_weight": 0.7, "vector_weight": 0.3}),
            ("Interleaved Results", {"fusion_method": "interleave"})
        ]
        
        for method_name, params in fusion_methods:
            self.print_colored(f"\n⚗️  {method_name}", 'cyan')
            if params:
                param_str = ", ".join([f"{k}={v}" for k, v in params.items() if k != "fusion_method"])
                if param_str:
                    self.print_colored(f"Parameters: {param_str}", 'blue')
                    
            try:
                request_body = {
                    "query": query,
                    "search_mode": "hybrid",
                    "size": 5,
                    "language": "vi"
                }
                request_body.update(params)
                
                response = requests.post(
                    f"{self.base_url}/v1/search",
                    json=request_body,
                    timeout=15
                )
                
                if response.status_code == 200:
                    results = response.json()
                    hits = results.get('hits', results.get('results', []))
                    
                    for i, hit in enumerate(hits[:3], 1):
                        title = hit.get('title', hit.get('chunk_id', 'Unknown'))
                        score = hit.get('score', 0)
                        bm25_score = hit.get('bm25_score', 0)
                        vector_score = hit.get('vector_score', 0)
                        
                        self.print_colored(f"  {i}. {title}", 'green')
                        print(f"     🎯 Final: {score:.3f} | BM25: {bm25_score:.3f} | Vector: {vector_score:.3f}")
                        
                else:
                    self.print_colored(f"❌ {method_name} failed: {response.status_code}", 'fail')
                    
            except Exception as e:
                self.print_colored(f"❌ {method_name} error: {e}", 'fail')
                
    def demo_citation_spans(self):
        """Demo character span citation."""
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("📍 CHARACTER SPAN CITATION DEMO", 'header')
        self.print_colored("="*80, 'header')
        
        query = "điểm trung bình tích lũy"
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/search",
                json={
                    "query": query,
                    "search_mode": "hybrid",
                    "size": 2,
                    "language": "vi",
                    "include_citation_spans": True
                },
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                hits = results.get('hits', results.get('results', []))
                
                for i, hit in enumerate(hits, 1):
                    title = hit.get('title', 'Unknown')
                    text = hit.get('text', '')
                    citation_spans = hit.get('citation_spans', [])
                    
                    self.print_colored(f"\n📄 Result {i}: {title}", 'green')
                    
                    if citation_spans:
                        self.print_colored("🎯 Citation spans found:", 'cyan')
                        for span in citation_spans:
                            start = span.get('start', 0)
                            end = span.get('end', 0)
                            cited_text = text[start:end]
                            
                            print(f"  📍 [{start}:{end}] \"{cited_text}\"")
                            
                            # Show context around citation
                            context_start = max(0, start - 50)
                            context_end = min(len(text), end + 50)
                            context = text[context_start:context_end]
                            
                            # Highlight the citation within context
                            relative_start = start - context_start
                            relative_end = end - context_start
                            
                            highlighted_context = (
                                context[:relative_start] + 
                                f"**{context[relative_start:relative_end]}**" + 
                                context[relative_end:]
                            )
                            
                            print(f"  💬 Context: ...{highlighted_context}...")
                    else:
                        print("  ⚠️  No citation spans found")
                        
            else:
                self.print_colored(f"❌ Citation demo failed: {response.status_code}", 'fail')
                
        except Exception as e:
            self.print_colored(f"❌ Citation demo error: {e}", 'fail')
            
    def run_full_demo(self):
        """Run the complete demo."""
        self.print_colored("🚀 VIETNAMESE HYBRID RAG SYSTEM DEMO", 'header')
        self.print_colored("=" * 80, 'header')
        
        # Check services
        if not self.check_services():
            return False
            
        # Show index stats
        stats = self.get_index_stats()
        if stats:
            self.print_colored(f"\n📊 Index contains {stats.get('total_documents', 0)} documents", 'blue')
            
        # Run demo sections
        self.demo_search_modes()
        self.demo_vietnamese_features()
        self.demo_field_filters()
        self.demo_fusion_algorithms()
        self.demo_citation_spans()
        
        # Summary
        self.print_colored("\n" + "="*80, 'header')
        self.print_colored("✅ DEMO COMPLETED SUCCESSFULLY!", 'green')
        self.print_colored("="*80, 'header')
        
        self.print_colored("\n🎯 Features demonstrated:", 'cyan')
        print("  ✅ Hybrid search (BM25 + Vector + Cross-Encoder)")
        print("  ✅ Vietnamese text analysis with ICU tokenizer")
        print("  ✅ Field-based filtering (faculty, doc_type, year)")
        print("  ✅ Multiple fusion algorithms (RRF, Weighted, Interleaved)")
        print("  ✅ Character span citation for precise references")
        print("  ✅ Diacritic handling and stopword filtering")
        
        self.print_colored("\n🚀 Next steps:", 'warning')
        print("  • Integrate with your application")
        print("  • Tune fusion weights for your data")
        print("  • Add more Vietnamese documents")
        print("  • Configure cross-encoder model for domain")
        
        return True

def main():
    """Main function."""
    demo = HybridSearchDemo()
    
    try:
        success = demo.run_full_demo()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        demo.print_colored("\n\n⚠️  Demo interrupted by user", 'warning')
        return 1
        
    except Exception as e:
        demo.print_colored(f"\n\n❌ Demo failed: {e}", 'fail')
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
