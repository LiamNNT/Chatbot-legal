"""
Test script don gian de kiem tra tai sao LLM khong truy xuat KG.
Script nay se:
1. Kiem tra xem Smart Planner co dung cach phan tich cau hoi ve mon hoc khong
2. Kiem tra xem Neo4j co du lieu khong
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for console
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables if not already set
if not os.getenv("OPENROUTER_API_KEY"):
    print("WARNING: OPENROUTER_API_KEY not set! Please set it first.")
    sys.exit(1)

import asyncio
from app.core.agent_factory import ConfigurableAgentFactory
from app.adapters.openrouter_adapter import OpenRouterAdapter

async def test_smart_planner():
    """Test Smart Planner với câu hỏi về môn học"""
    
    print("\n" + "="*80)
    print("TEST 1: SMART PLANNER - Phát hiện câu hỏi cần dùng KG")
    print("="*80)
    
    # Initialize LLM adapter
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    
    llm_adapter = OpenRouterAdapter(
        api_key=api_key,
        base_url=base_url
    )
    
    # Create agent factory
    agent_factory = ConfigurableAgentFactory()
    
    # Create Smart Planner
    print("\n📦 Creating Smart Planner...")
    smart_planner = agent_factory.create_agent("smart_planner", llm_adapter)
    print(f"✅ Smart Planner created with model: {smart_planner.config.model}")
    
    # Test queries về môn học
    test_queries = [
        {
            "query": "Môn IT001 có những môn tiên quyết nào?",
            "expected_kg": True,
            "reason": "Câu hỏi về môn tiên quyết - PHẢI dùng KG"
        },
        {
            "query": "Nhập môn lập trình học những gì?",
            "expected_kg": True,
            "reason": "Câu hỏi về môn học - NÊN dùng KG"
        },
        {
            "query": "Điều 14 quy định gì?",
            "expected_kg": True,
            "reason": "Câu hỏi về Điều cụ thể - PHẢI dùng KG"
        },
        {
            "query": "Học phí năm 2024 là bao nhiêu?",
            "expected_kg": False,
            "reason": "Câu hỏi về số liệu - không cần KG"
        }
    ]
    
    results = []
    
    for test in test_queries:
        query = test["query"]
        expected = test["expected_kg"]
        reason = test["reason"]
        
        print(f"\n{'='*80}")
        print(f"📝 Query: {query}")
        print(f"🎯 Expected use_knowledge_graph: {expected}")
        print(f"💡 Lý do: {reason}")
        print("-" * 80)
        
        try:
            result = await smart_planner.plan(query)
            
            print(f"   Intent: {result.intent}")
            print(f"   Complexity: {result.complexity} (score: {result.complexity_score})")
            print(f"   Requires RAG: {result.requires_rag}")
            
            # Check use_knowledge_graph attribute
            use_kg = getattr(result, 'use_knowledge_graph', False)
            graph_query_type = getattr(result, 'graph_query_type', None)
            
            print(f"\n   🔍 use_knowledge_graph: {use_kg}")
            print(f"   🔍 graph_query_type: {graph_query_type}")
            
            # Determine if test passed
            if use_kg == expected:
                print(f"\n   ✅ PASS - Đúng như expected!")
                status = "PASS"
            else:
                print(f"\n   ❌ FAIL - Sai! Expected {expected} nhưng nhận {use_kg}")
                status = "FAIL"
            
            results.append({
                "query": query,
                "expected": expected,
                "actual": use_kg,
                "status": status,
                "graph_query_type": graph_query_type
            })
            
            # Show rewritten queries
            if result.rewritten_queries:
                print(f"\n   📝 Rewritten queries:")
                for rq in result.rewritten_queries[:2]:  # Show only first 2
                    print(f"      - {rq}")
                
        except Exception as e:
            print(f"\n   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": query,
                "expected": expected,
                "actual": None,
                "status": "ERROR",
                "error": str(e)
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"✅ Passed: {passed}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"⚠️ Errors: {errors}/{len(results)}")
    
    if failed > 0:
        print(f"\n⚠️⚠️⚠️ CÓ {failed} TEST FAIL! ⚠️⚠️⚠️")
        print("\nCác test FAIL:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  - {r['query']}")
                print(f"    Expected: {r['expected']}, Actual: {r['actual']}")
    
    return results


async def test_neo4j():
    """Test kết nối Neo4j và kiểm tra dữ liệu"""
    
    print("\n" + "="*80)
    print("TEST 2: NEO4J - Kiểm tra dữ liệu môn học")
    print("="*80)
    
    try:
        from app.adapters.neo4j_adapter import Neo4jAdapter
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        print(f"\n🔌 Connecting to Neo4j...")
        print(f"   URI: {neo4j_uri}")
        print(f"   Database: {neo4j_database}")
        
        graph_adapter = Neo4jAdapter(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )
        
        # Test connection
        print(f"\n✅ Testing connection...")
        query = "MATCH (n) RETURN count(n) as total_nodes LIMIT 1"
        result = graph_adapter.execute_query(query)
        
        if result:
            total = result[0].get('total_nodes', 0)
            print(f"   ✅ Connected! Total nodes: {total}")
            
            if total == 0:
                print(f"   ❌❌❌ DATABASE RỖNG! ❌❌❌")
                print(f"   ⚠️ Đây là nguyên nhân chính tại sao LLM không thể truy xuất KG!")
                print(f"   💡 Cần import dữ liệu vào Neo4j trước!")
                return False
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
            print(f"   ✅ Found {len(courses)} courses:")
            for course in courses:
                print(f"      - {course.get('code')}: {course.get('name')}")
        else:
            print(f"   ❌❌❌ KHÔNG CÓ COURSE NODES! ❌❌❌")
            print(f"   ⚠️ Đây là nguyên nhân tại sao không thể truy vấn môn học!")
            print(f"   💡 Cần import dữ liệu môn học vào Neo4j!")
        
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
            print(f"   ⚠️ Không có Article nodes")
        
        graph_adapter.close()
        return True
        
    except Exception as e:
        print(f"\n   ❌ ERROR khi kết nối Neo4j: {e}")
        print(f"   ⚠️ Không thể kết nối với Neo4j - đây là nguyên nhân chính!")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🔍 KIỂM TRA TẠI SAO LLM KHÔNG TRUY XUẤT KNOWLEDGE GRAPH")
    print("="*80)
    
    # Test 1: Smart Planner
    planner_results = await test_smart_planner()
    
    # Test 2: Neo4j
    neo4j_ok = await test_neo4j()
    
    # Final diagnosis
    print("\n" + "="*80)
    print("🔬 CHẨN ĐOÁN CUỐI CÙNG")
    print("="*80)
    
    planner_failed = sum(1 for r in planner_results if r["status"] == "FAIL")
    
    if not neo4j_ok:
        print("\n❌ NGUYÊN NHÂN CHÍNH: Neo4j không có dữ liệu hoặc không kết nối được!")
        print("💡 GIẢI PHÁP: Import dữ liệu môn học vào Neo4j")
    elif planner_failed > 0:
        print("\n⚠️ NGUYÊN NHÂN: Smart Planner không đánh dấu use_knowledge_graph=true")
        print("💡 GIẢI PHÁP: Cập nhật system prompt của Smart Planner")
    else:
        print("\n✅ Cả Smart Planner và Neo4j đều OK!")
        print("⚠️ Vấn đề có thể ở orchestrator logic hoặc graph reasoning agent")
    
    print("\n" + "="*80)
    print("✅ HOÀN THÀNH KIỂM TRA")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
