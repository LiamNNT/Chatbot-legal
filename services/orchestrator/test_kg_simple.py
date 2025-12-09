"""
Simple test để kiểm tra Smart Planner có phát hiện câu hỏi về môn học cần dùng KG không.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_planner_simple():
    """Test Smart Planner với câu hỏi về môn học"""
    
    from app.core.agent_factory import ConfigurableAgentFactory
    from app.adapters.openrouter_adapter import OpenRouterAdapter
    from app.core.config import settings
    
    print("\n" + "="*80)
    print("TEST: SMART PLANNER KG DETECTION")
    print("="*80)
    
    # Initialize LLM adapter
    llm_adapter = OpenRouterAdapter(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL
    )
    
    # Create agent factory
    agent_factory = ConfigurableAgentFactory()
    
    # Create Smart Planner
    smart_planner = agent_factory.create_agent("smart_planner", llm_adapter)
    
    # Test queries về môn học
    test_queries = [
        "Môn IT001 có những môn tiên quyết nào?",
        "Nhập môn lập trình học những gì?",
        "Cấu trúc dữ liệu cần học gì trước?",
        "Điều 14 quy định gì?",
        "Học phí năm 2024 là bao nhiêu?"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 80)
        
        try:
            result = await smart_planner.plan(query)
            
            print(f"   ✅ Intent: {result.intent}")
            print(f"   ✅ Complexity: {result.complexity} (score: {result.complexity_score})")
            print(f"   ✅ Requires RAG: {result.requires_rag}")
            
            # Check use_knowledge_graph attribute
            use_kg = getattr(result, 'use_knowledge_graph', None)
            print(f"   🔍 use_knowledge_graph: {use_kg}")
            
            if hasattr(result, 'graph_query_type'):
                print(f"   🔍 graph_query_type: {result.graph_query_type}")
            else:
                print(f"   ⚠️ graph_query_type: NOT SET")
            
            print(f"   📊 Strategy: {result.strategy}")
            
            if use_kg:
                print(f"   ✅✅✅ KG WILL BE USED! ✅✅✅")
            else:
                print(f"   ❌❌❌ KG NOT USED - THIS IS THE PROBLEM! ❌❌❌")
            
            # Show rewritten queries
            if result.rewritten_queries:
                print(f"   📝 Rewritten queries:")
                for rq in result.rewritten_queries:
                    print(f"      - {rq}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


async def test_neo4j_connection():
    """Test kết nối Neo4j"""
    
    print("\n" + "="*80)
    print("TEST: NEO4J CONNECTION")
    print("="*80)
    
    try:
        from app.adapters.neo4j_adapter import Neo4jAdapter
        from app.core.config import settings
        
        print(f"\n🔌 Connecting to Neo4j...")
        print(f"   URI: {settings.NEO4J_URI}")
        print(f"   Database: {settings.NEO4J_DATABASE}")
        
        graph_adapter = Neo4jAdapter(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE
        )
        
        # Test connection
        print(f"\n✅ Testing connection...")
        
        query = "MATCH (n) RETURN count(n) as total_nodes LIMIT 1"
        result = graph_adapter.execute_query(query)
        
        if result:
            print(f"   ✅ Connected! Total nodes: {result[0].get('total_nodes', 0)}")
        else:
            print(f"   ⚠️ Connected but no results")
        
        # Check for Course nodes
        print(f"\n🔍 Checking for Course nodes...")
        course_query = """
        MATCH (c:Course)
        RETURN c.course_code as code, c.course_name as name
        LIMIT 5
        """
        courses = graph_adapter.execute_query(course_query)
        
        if courses:
            print(f"   ✅ Found {len(courses)} courses (showing first 5):")
            for course in courses:
                print(f"      - {course.get('code')}: {course.get('name')}")
        else:
            print(f"   ❌❌❌ NO COURSES FOUND IN NEO4J! ❌❌❌")
            print(f"   ⚠️ Đây có thể là nguyên nhân!")
        
        # Check for Article nodes
        print(f"\n🔍 Checking for Article nodes (Điều)...")
        article_query = """
        MATCH (a:Article)
        RETURN a.article_number as number, a.title as title
        LIMIT 5
        """
        articles = graph_adapter.execute_query(article_query)
        
        if articles:
            print(f"   ✅ Found {len(articles)} articles:")
            for article in articles:
                print(f"      - Điều {article.get('number')}: {article.get('title')}")
        else:
            print(f"   ❌ No Article nodes found")
        
        graph_adapter.close()
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🔍 KNOWLEDGE GRAPH DEBUG - SIMPLE VERSION")
    print("="*80)
    
    # Test 1: Smart Planner
    await test_planner_simple()
    
    # Test 2: Neo4j
    await test_neo4j_connection()
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
