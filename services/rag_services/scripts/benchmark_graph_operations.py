#!/usr/bin/env python3
"""
Performance Benchmark for Neo4j GraphRepository - Week 1 Task A5

Benchmarks:
1. Node operations (create, read, update, delete)
2. Relationship operations (create, read, delete)
3. Graph traversal (shortest path, prerequisite chains)
4. Batch operations (bulk insert)
5. Full-text search

Created: November 14, 2025
Owner: Team A - Infrastructure
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import List, Dict, Any
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.graph.neo4j_adapter import create_neo4j_adapter
from core.domain.graph_models import (
    GraphNode,
    GraphRelationship,
    NodeCategory,
    RelationshipType
)


class PerformanceBenchmark:
    """Performance benchmark runner"""
    
    def __init__(self):
        self.adapter = create_neo4j_adapter()
        self.results: Dict[str, Any] = {}
    
    async def setup(self):
        """Setup test environment"""
        print("=" * 70)
        print("🔧 Performance Benchmark - CatRAG GraphRepository")
        print("=" * 70)
        print()
        
        # Check connection
        if not await self.adapter.health_check():
            print("❌ Cannot connect to Neo4j!")
            sys.exit(1)
        
        print("✅ Connected to Neo4j")
        print()
    
    async def cleanup(self):
        """Cleanup after tests"""
        # Note: Not clearing DB to preserve sample data
        self.adapter.close()
    
    def time_async(self, func):
        """Decorator to time async functions"""
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            duration = (end - start) * 1000  # Convert to ms
            return result, duration
        return wrapper
    
    # ========== Benchmark 1: Single Node Operations ==========
    
    async def benchmark_node_create(self, iterations: int = 100) -> Dict[str, float]:
        """Benchmark single node creation"""
        print(f"📝 Benchmark 1: Single Node Creation ({iterations} iterations)")
        
        durations = []
        created_ids = []
        
        for i in range(iterations):
            node = GraphNode(
                category=NodeCategory.MON_HOC,
                properties={
                    "code": f"BENCH_{i:04d}",  # Required by validation
                    "ma_mon": f"BENCH_{i:04d}",
                    "name": f"Benchmark Course {i}",  # Required
                    "ten_mon": f"Benchmark Course {i}",
                    "credits": 4,  # Required
                    "so_tin_chi": 4,
                    "khoa": "CNTT"
                }
            )
            
            start = time.perf_counter()
            node_id = await self.adapter.add_node(node)
            end = time.perf_counter()
            
            durations.append((end - start) * 1000)  # ms
            created_ids.append(node_id)
        
        avg = statistics.mean(durations)
        median = statistics.median(durations)
        min_time = min(durations)
        max_time = max(durations)
        
        print(f"  ✓ Average: {avg:.2f} ms")
        print(f"  ✓ Median: {median:.2f} ms")
        print(f"  ✓ Min: {min_time:.2f} ms, Max: {max_time:.2f} ms")
        print()
        
        # Cleanup
        for node_id in created_ids:
            await self.adapter.delete_node(node_id, cascade=True)
        
        return {
            "operation": "node_create_single",
            "iterations": iterations,
            "avg_ms": avg,
            "median_ms": median,
            "min_ms": min_time,
            "max_ms": max_time
        }
    
    # ========== Benchmark 2: Batch Node Operations ==========
    
    async def benchmark_batch_nodes(self, batch_size: int = 1000) -> Dict[str, float]:
        """Benchmark batch node creation"""
        print(f"📦 Benchmark 2: Batch Node Creation ({batch_size} nodes)")
        
        # Create batch
        nodes = []
        for i in range(batch_size):
            nodes.append(GraphNode(
                category=NodeCategory.MON_HOC,
                properties={
                    "code": f"BATCH_{i:05d}",
                    "ma_mon": f"BATCH_{i:05d}",
                    "name": f"Batch Course {i}",
                    "ten_mon": f"Batch Course {i}",
                    "credits": 4,
                    "so_tin_chi": 4
                }
            ))
        
        start = time.perf_counter()
        node_ids = await self.adapter.add_nodes_batch(nodes)
        end = time.perf_counter()
        
        duration = (end - start) * 1000  # ms
        throughput = batch_size / (duration / 1000)  # nodes/sec
        
        print(f"  ✓ Total time: {duration:.2f} ms")
        print(f"  ✓ Per node: {duration/batch_size:.2f} ms")
        print(f"  ✓ Throughput: {throughput:.0f} nodes/sec")
        print()
        
        # Cleanup
        for node_id in node_ids:
            await self.adapter.delete_node(node_id, cascade=True)
        
        return {
            "operation": "node_create_batch",
            "batch_size": batch_size,
            "total_ms": duration,
            "per_node_ms": duration/batch_size,
            "throughput_nodes_sec": throughput
        }
    
    # ========== Benchmark 3: Relationship Operations ==========
    
    async def benchmark_relationships(self, count: int = 100) -> Dict[str, float]:
        """Benchmark relationship creation"""
        print(f"🔗 Benchmark 3: Relationship Creation ({count} relationships)")
        
        # Create source and target nodes
        sources = []
        targets = []
        
        for i in range(count):
            source = GraphNode(
                category=NodeCategory.MON_HOC,
                properties={
                    "code": f"SRC_{i}",
                    "ma_mon": f"SRC_{i}",
                    "name": f"Source {i}",
                    "credits": 4
                }
            )
            target = GraphNode(
                category=NodeCategory.MON_HOC,
                properties={
                    "code": f"TGT_{i}",
                    "ma_mon": f"TGT_{i}",
                    "name": f"Target {i}",
                    "credits": 4
                }
            )
            
            source_id = await self.adapter.add_node(source)
            target_id = await self.adapter.add_node(target)
            
            sources.append(source_id)
            targets.append(target_id)
        
        # Benchmark relationship creation
        durations = []
        
        for i in range(count):
            rel = GraphRelationship(
                source_id=sources[i],
                target_id=targets[i],
                rel_type=RelationshipType.DIEU_KIEN_TIEN_QUYET,
                properties={"loai": "bat_buoc"}
            )
            
            start = time.perf_counter()
            await self.adapter.add_relationship(rel)
            end = time.perf_counter()
            
            durations.append((end - start) * 1000)
        
        avg = statistics.mean(durations)
        
        print(f"  ✓ Average: {avg:.2f} ms")
        print()
        
        # Cleanup
        for source_id in sources:
            await self.adapter.delete_node(source_id, cascade=True)
        for target_id in targets:
            await self.adapter.delete_node(target_id, cascade=True)
        
        return {
            "operation": "relationship_create",
            "count": count,
            "avg_ms": avg
        }
    
    # ========== Benchmark 4: Graph Traversal ==========
    
    async def benchmark_traversal(self) -> Dict[str, float]:
        """Benchmark shortest path and prerequisite chain queries"""
        print(f"🚶 Benchmark 4: Graph Traversal (using existing data)")
        
        # Test prerequisite chain for SE363
        durations = []
        
        for _ in range(10):  # Run 10 times
            start = time.perf_counter()
            paths = await self.adapter.find_prerequisites_chain("SE363", max_depth=10)
            end = time.perf_counter()
            
            durations.append((end - start) * 1000)
        
        avg = statistics.mean(durations)
        
        print(f"  ✓ Prerequisite chain query: {avg:.2f} ms")
        print(f"  ✓ Paths found: {len(paths)}")
        print()
        
        return {
            "operation": "prerequisite_chain",
            "avg_ms": avg,
            "paths_found": len(paths)
        }
    
    # ========== Benchmark 5: Full-text Search ==========
    
    async def benchmark_search(self) -> Dict[str, float]:
        """Benchmark full-text search"""
        print(f"🔍 Benchmark 5: Full-text Search")
        
        queries = [
            "cấu trúc dữ liệu",
            "lập trình",
            "trí tuệ nhân tạo",
            "database",
            "web"
        ]
        
        durations = []
        
        for query in queries:
            start = time.perf_counter()
            results = await self.adapter.search_nodes(query, [NodeCategory.MON_HOC], limit=10)
            end = time.perf_counter()
            
            durations.append((end - start) * 1000)
            print(f"  ✓ '{query}': {len(results)} results in {durations[-1]:.2f} ms")
        
        avg = statistics.mean(durations)
        
        print(f"  ✓ Average search time: {avg:.2f} ms")
        print()
        
        return {
            "operation": "fulltext_search",
            "queries": len(queries),
            "avg_ms": avg
        }
    
    # ========== Run All Benchmarks ==========
    
    async def run_all(self):
        """Run all benchmarks"""
        await self.setup()
        
        # Benchmark 1: Single node operations
        result1 = await self.benchmark_node_create(iterations=100)
        self.results["single_node_create"] = result1
        
        # Benchmark 2: Batch operations
        result2 = await self.benchmark_batch_nodes(batch_size=1000)
        self.results["batch_node_create"] = result2
        
        # Benchmark 3: Relationships
        result3 = await self.benchmark_relationships(count=100)
        self.results["relationship_create"] = result3
        
        # Benchmark 4: Graph traversal
        result4 = await self.benchmark_traversal()
        self.results["graph_traversal"] = result4
        
        # Benchmark 5: Full-text search
        result5 = await self.benchmark_search()
        self.results["fulltext_search"] = result5
        
        # Print summary
        self.print_summary()
        
        await self.cleanup()
    
    def print_summary(self):
        """Print benchmark summary"""
        print("=" * 70)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 70)
        print()
        
        print("🎯 Target Performance Goals (Week 1):")
        print("  • Single node create: < 50 ms")
        print("  • Batch create: > 500 nodes/sec")
        print("  • Relationship create: < 100 ms")
        print("  • Graph traversal: < 200 ms")
        print("  • Full-text search: < 300 ms")
        print()
        
        print("✅ Actual Results:")
        
        # Single node
        single = self.results.get("single_node_create", {})
        if single:
            status = "✅" if single["avg_ms"] < 50 else "⚠️"
            print(f"  {status} Single node create: {single['avg_ms']:.2f} ms (target: < 50 ms)")
        
        # Batch
        batch = self.results.get("batch_node_create", {})
        if batch:
            status = "✅" if batch["throughput_nodes_sec"] > 500 else "⚠️"
            print(f"  {status} Batch create: {batch['throughput_nodes_sec']:.0f} nodes/sec (target: > 500)")
        
        # Relationships
        rel = self.results.get("relationship_create", {})
        if rel:
            status = "✅" if rel["avg_ms"] < 100 else "⚠️"
            print(f"  {status} Relationship create: {rel['avg_ms']:.2f} ms (target: < 100 ms)")
        
        # Traversal
        trav = self.results.get("graph_traversal", {})
        if trav:
            status = "✅" if trav["avg_ms"] < 200 else "⚠️"
            print(f"  {status} Graph traversal: {trav['avg_ms']:.2f} ms (target: < 200 ms)")
        
        # Search
        search = self.results.get("fulltext_search", {})
        if search:
            status = "✅" if search["avg_ms"] < 300 else "⚠️"
            print(f"  {status} Full-text search: {search['avg_ms']:.2f} ms (target: < 300 ms)")
        
        print()
        print("=" * 70)
        print("✅ Week 1 Task A5: Performance Baseline COMPLETE")
        print("=" * 70)


async def main():
    """Main entry point"""
    benchmark = PerformanceBenchmark()
    await benchmark.run_all()


if __name__ == "__main__":
    asyncio.run(main())
