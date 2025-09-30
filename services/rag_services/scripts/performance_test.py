#!/usr/bin/env python3
# scripts/performance_test.py
#
# Simple performance test for the Vietnamese Hybrid RAG system

import time
import requests

def run_performance_test():
    queries = ['tuyển sinh', 'điều kiện', 'chương trình']
    times = []
    
    print("⚡ Running performance tests...")
    
    for query in queries:
        try:
            start = time.time()
            response = requests.post(
                'http://localhost:8000/v1/search', 
                json={'query': query, 'search_mode': 'hybrid'},
                timeout=10
            )
            duration = time.time() - start
            times.append(duration)
            
            if response.status_code == 200:
                results = response.json()
                hits = len(results.get('hits', []))
                print(f"  {query}: {duration:.3f}s ({hits} results)")
            else:
                print(f"  {query}: {duration:.3f}s (Error: {response.status_code})")
                
        except Exception as e:
            print(f"  {query}: Error - {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        print(f"\n📊 Average response time: {avg_time:.3f}s")
    else:
        print("❌ No successful queries")

if __name__ == "__main__":
    run_performance_test()
