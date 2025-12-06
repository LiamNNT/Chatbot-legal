#!/usr/bin/env python3
"""
Debug Smart Planner với câu hỏi về mối quan hệ
"""
import asyncio
import sys
import os
from pathlib import Path
import re

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except:
    pass

# Import after path is set
from app.core.container import get_container


async def test_planner():
    """Test Smart Planner decision"""
    
    query = "Điều 19 có liên quan gì đến Điều 20?"
    
    print("=" * 80)
    print("DEBUG SMART PLANNER - RELATIONSHIP QUERY")
    print("=" * 80)
    print(f"\nQuery: {query}")
    
    # Test regex manually
    print("\n" + "=" * 80)
    print("MANUAL REGEX TEST")
    print("=" * 80)
    query_lower = query.lower()
    print(f"Query lowercase: {query_lower}")
    
    article_pattern = r'điều\s+(\d+)'
    article_matches = re.findall(article_pattern, query_lower)
    print(f"\nPattern: {article_pattern}")
    print(f"Matches: {article_matches}")
    print(f"Unique articles: {set(article_matches)}")
    print(f"Count: {len(set(article_matches))}")
    
    # Check relationship patterns
    relationship_patterns = [
        "mối quan hệ", "quan hệ", "liên quan", "liên kết",
        "kết nối", "ảnh hưởng", "tác động", "phụ thuộc",
        "dẫn đến", "gây ra", "bắt nguồn từ"
    ]
    has_relationship = any(p in query_lower for p in relationship_patterns)
    print(f"\nHas relationship: {has_relationship}")
    for p in relationship_patterns:
        if p in query_lower:
            print(f"  ✅ Found: '{p}'")
    
    # Test with Smart Planner
    print("\n" + "=" * 80)
    print("SMART PLANNER TEST")
    print("=" * 80)
    
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        planner = orchestrator.smart_planner
        
        print("\n⏳ Calling Smart Planner...")
        plan_input = {"query": query, "context": {}, "user_profile": {}}
        plan_result = await planner.process(plan_input)
        
        print(f"\n📊 PLANNER DECISION:")
        print(f"   use_knowledge_graph: {plan_result.use_knowledge_graph}")
        print(f"   requires_rag: {plan_result.requires_rag}")
        print(f"   complexity: {plan_result.complexity}")
        print(f"   complexity_score: {plan_result.complexity_score}")
        print(f"   strategy: {plan_result.strategy}")
        print(f"   graph_query_type: {plan_result.graph_query_type}")
        print(f"   search_query: {plan_result.search_terms}")
        print(f"   analysis: {plan_result.reasoning}")
        
        if plan_result.use_knowledge_graph:
            print("\n✅ SMART PLANNER WILL USE KG!")
        else:
            print("\n❌ SMART PLANNER WON'T USE KG!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_planner())
