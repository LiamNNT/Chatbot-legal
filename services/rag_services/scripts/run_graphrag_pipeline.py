#!/usr/bin/env python3
"""
GraphRAG Pipeline Runner

This script runs the complete GraphRAG indexing and testing pipeline:
1. Build hierarchical index with Bottom-Up Summarization
2. Test the query engine with Local and Global queries

Usage:
    python run_graphrag_pipeline.py [--index-only] [--test-only]
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from indexing.graphrag_indexer import GraphRAGIndexer
from indexing.graphrag_query_engine import GraphRAGQueryEngine, QueryMode


def setup_environment():
    """Load environment variables"""
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path, override=True)
    
    # Support both OPENROUTER_API_KEY and OPENAI_API_KEY (legacy)
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Missing API key. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
        sys.exit(1)
    
    neo4j_vars = ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
    missing = [v for v in neo4j_vars if not os.getenv(v)]
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print(f"   Please check {env_path}")
        sys.exit(1)
    
    return {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
        "openrouter_api_key": api_key,
        "model": os.getenv("GRAPHRAG_MODEL", "openai/gpt-4o-mini")
    }


async def run_indexing(config: dict):
    """Run the GraphRAG indexing pipeline"""
    print("\n" + "=" * 70)
    print("🚀 GRAPHRAG INDEXING PIPELINE")
    print("=" * 70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📦 Model: {config['model']}")
    print("=" * 70)
    
    indexer = GraphRAGIndexer(
        neo4j_uri=config["neo4j_uri"],
        neo4j_user=config["neo4j_user"],
        neo4j_password=config["neo4j_password"],
        openrouter_api_key=config["openrouter_api_key"],
        model=config["model"]
    )
    
    try:
        document = await indexer.build_index(clear_existing=True)
        
        # Print results
        print("\n" + "=" * 70)
        print("📊 INDEXING COMPLETE - SUMMARY")
        print("=" * 70)
        
        print(f"\n📄 DOCUMENT: {document.title}")
        print(f"   Summary: {document.summary[:300]}..." if document.summary else "   No summary generated")
        if document.key_points:
            print(f"   Key Points: {len(document.key_points)}")
            for kp in document.key_points[:5]:
                print(f"   - {kp}")
        
        print("\n📚 CHAPTERS:")
        for ch in document.chapters:
            articles_with_summary = len([a for a in ch.articles if a.summary])
            print(f"\n   📁 {ch.name}: {ch.title}")
            print(f"      Summary: {ch.summary[:200]}..." if ch.summary else "      No summary")
            print(f"      Articles: {len(ch.articles)} ({articles_with_summary} with summaries)")
            if ch.key_topics:
                print(f"      Topics: {', '.join(ch.key_topics[:5])}")
        
        return document
        
    finally:
        indexer.close()


async def run_tests(config: dict):
    """Run test queries against the GraphRAG index"""
    print("\n" + "=" * 70)
    print("🧪 GRAPHRAG QUERY TESTING")
    print("=" * 70)
    
    engine = GraphRAGQueryEngine(
        neo4j_uri=config["neo4j_uri"],
        neo4j_user=config["neo4j_user"],
        neo4j_password=config["neo4j_password"],
        openrouter_api_key=config["openrouter_api_key"],
        model=config["model"]
    )
    
    # Test queries
    test_cases = [
        {
            "name": "LOCAL - Specific Article",
            "query": "Điều 5 quy định gì về học kỳ và năm học?",
            "expected_mode": QueryMode.LOCAL
        },
        {
            "name": "LOCAL - Specific Rule",
            "query": "Sinh viên bị cảnh cáo học vụ khi nào?",
            "expected_mode": QueryMode.LOCAL
        },
        {
            "name": "LOCAL - Specific Condition",
            "query": "Điều kiện để được đăng ký học cải thiện là gì?",
            "expected_mode": QueryMode.LOCAL
        },
        {
            "name": "GLOBAL - Summary Request",
            "query": "Tóm tắt các quy định về xét tốt nghiệp trong văn bản này",
            "expected_mode": QueryMode.GLOBAL
        },
        {
            "name": "GLOBAL - Cross-Chapter",
            "query": "Quyền và nghĩa vụ của sinh viên xuyên suốt quá trình đào tạo là gì?",
            "expected_mode": QueryMode.GLOBAL
        },
        {
            "name": "GLOBAL - Overview",
            "query": "Tổng quan về quy chế đào tạo tại UIT gồm những nội dung chính nào?",
            "expected_mode": QueryMode.GLOBAL
        },
    ]
    
    results = []
    
    try:
        for i, test in enumerate(test_cases, 1):
            print(f"\n{'='*60}")
            print(f"📝 Test {i}/{len(test_cases)}: {test['name']}")
            print(f"{'='*60}")
            print(f"❓ Query: {test['query']}")
            print(f"🎯 Expected Mode: {test['expected_mode'].value}")
            
            result = await engine.query(test['query'])
            
            mode_match = "✅" if result.mode == test['expected_mode'] else "⚠️"
            print(f"{mode_match} Actual Mode: {result.mode.value}")
            print(f"📊 Confidence: {result.confidence:.2f}")
            print(f"📚 Sources: {len(result.sources)}")
            print(f"\n💬 Answer:")
            print("-" * 40)
            print(result.answer[:800])
            if len(result.answer) > 800:
                print("...")
            print("-" * 40)
            
            results.append({
                "test": test['name'],
                "mode_correct": result.mode == test['expected_mode'],
                "sources": len(result.sources),
                "confidence": result.confidence
            })
            
            # Small delay between queries
            await asyncio.sleep(1)
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        correct = sum(1 for r in results if r['mode_correct'])
        print(f"Mode Detection: {correct}/{len(results)} correct")
        print(f"Average Confidence: {sum(r['confidence'] for r in results)/len(results):.2f}")
        print(f"Average Sources: {sum(r['sources'] for r in results)/len(results):.1f}")
        
    finally:
        engine.close()


async def main():
    parser = argparse.ArgumentParser(description="GraphRAG Pipeline Runner")
    parser.add_argument("--index-only", action="store_true", help="Only run indexing")
    parser.add_argument("--test-only", action="store_true", help="Only run tests")
    args = parser.parse_args()
    
    config = setup_environment()
    
    if args.test_only:
        await run_tests(config)
    elif args.index_only:
        await run_indexing(config)
    else:
        # Run both
        await run_indexing(config)
        await run_tests(config)
    
    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    asyncio.run(main())
