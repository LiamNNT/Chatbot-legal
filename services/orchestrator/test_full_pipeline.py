"""
Test full pipeline: Gọi orchestrator để xem có truy xuất KG và trả lời đúng không.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Set UTF-8 encoding for console
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# Check environment
if not os.getenv("OPENROUTER_API_KEY"):
    print("ERROR: OPENROUTER_API_KEY not set!")
    sys.exit(1)


async def test_full_pipeline_with_kg():
    """Test toàn bộ pipeline từ query đến response"""
    
    print("\n" + "="*80)
    print("🔬 TEST FULL PIPELINE: ORCHESTRATOR + KG + LLM")
    print("="*80)
    
    # Import sau khi đã set path
    from app.core.container import ServiceContainer
    from app.core.domain import OrchestrationRequest
    
    # Get orchestrator instance
    print("\n1. Initializing orchestrator...")
    container = ServiceContainer()
    orchestrator = container.get_multi_agent_orchestrator()
    
    # Check if graph reasoning is enabled
    has_graph = orchestrator.graph_reasoning_agent is not None
    print(f"   - Graph Reasoning Agent: {'✅ ENABLED' if has_graph else '❌ DISABLED'}")
    print(f"   - Smart Planner: {'✅' if orchestrator.smart_planner else '❌'}")
    print(f"   - Answer Agent: {'✅' if orchestrator.answer_agent else '❌'}")
    
    if not has_graph:
        print("\n⚠️ WARNING: Graph Reasoning Agent not initialized!")
        print("   This means KG will NOT be used even if LLM requests it.")
        print("   Check if Neo4j connection is configured properly.")
    
    # Test queries about courses
    test_queries = [
        {
            "query": "Môn IT001 có những môn tiên quyết nào?",
            "should_use_kg": True,
            "expected_terms": ["IT001", "tiên quyết", "môn học"]
        },
        {
            "query": "Nhập môn lập trình thuộc khoa nào?",
            "should_use_kg": True,
            "expected_terms": ["Nhập môn lập trình", "khoa"]
        },
        {
            "query": "Điều 14 quy định gì?",
            "should_use_kg": True,
            "expected_terms": ["Điều 14", "quy định"]
        }
    ]
    
    for idx, test in enumerate(test_queries, 1):
        query = test["query"]
        should_use_kg = test["should_use_kg"]
        
        print(f"\n{'='*80}")
        print(f"TEST {idx}/{len(test_queries)}: {query}")
        print(f"Expected to use KG: {should_use_kg}")
        print("-" * 80)
        
        try:
            # Create request
            request = OrchestrationRequest(
                user_query=query,
                session_id="test_session",
                use_rag=True,
                # Don't force KG - let Smart Planner decide
                use_knowledge_graph=None
            )
            
            print("\n2. Processing request through orchestrator...")
            response = await orchestrator.process_request(request)
            
            # Extract stats
            stats = response.processing_stats
            
            print("\n3. Processing Stats:")
            print(f"   - Pipeline: {stats.get('pipeline', 'unknown')}")
            print(f"   - LLM calls: {stats.get('llm_calls', 0)}")
            print(f"   - Total time: {stats.get('total_time', 0):.2f}s")
            
            # Check if Smart Planner detected need for KG
            plan_result = response.agent_metadata.get('plan_result')
            if plan_result:
                print(f"\n4. Smart Planner Analysis:")
                print(f"   - Intent: {plan_result.get('intent')}")
                print(f"   - Complexity: {plan_result.get('complexity')} (score: {plan_result.get('complexity_score')})")
                print(f"   - Strategy: {plan_result.get('strategy')}")
                print(f"   - use_knowledge_graph: {plan_result.get('use_knowledge_graph')}")
                print(f"   - graph_query_type: {plan_result.get('graph_query_type')}")
            
            # Check if KG was actually used
            used_kg = stats.get('use_knowledge_graph', False)
            graph_time = stats.get('graph_reasoning_time', 0)
            nodes_found = stats.get('graph_nodes_found', 0)
            paths_found = stats.get('graph_paths_found', 0)
            
            print(f"\n5. Knowledge Graph Usage:")
            print(f"   - KG Used: {'✅ YES' if used_kg else '❌ NO'}")
            if used_kg:
                print(f"   - Query Type: {stats.get('graph_query_type', 'unknown')}")
                print(f"   - Graph Time: {graph_time:.2f}s")
                print(f"   - Nodes Found: {nodes_found}")
                print(f"   - Paths Found: {paths_found}")
            
            # Check vector search
            docs_retrieved = stats.get('documents_retrieved', 0)
            print(f"\n6. Vector Search:")
            print(f"   - Documents Retrieved: {docs_retrieved}")
            
            # Show response
            print(f"\n7. LLM Response:")
            print("-" * 80)
            print(response.response[:500] + "..." if len(response.response) > 500 else response.response)
            print("-" * 80)
            
            # Verify expectations
            print(f"\n8. Verification:")
            if should_use_kg and used_kg:
                print(f"   ✅ PASS - KG was used as expected!")
            elif should_use_kg and not used_kg:
                print(f"   ❌ FAIL - KG should be used but wasn't!")
                print(f"   🔍 Debugging info:")
                print(f"      - Smart Planner said use_kg: {plan_result.get('use_knowledge_graph') if plan_result else 'N/A'}")
                print(f"      - Graph agent exists: {has_graph}")
                print(f"      - Possible issues:")
                print(f"        1. Graph Reasoning Agent not initialized")
                print(f"        2. Neo4j connection failed")
                print(f"        3. Orchestrator logic not checking plan_result.use_knowledge_graph")
            elif not should_use_kg and not used_kg:
                print(f"   ✅ PASS - KG not used as expected!")
            else:
                print(f"   ⚠️ WARNING - KG used when not expected")
            
        except Exception as e:
            print(f"\n   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✅ TEST COMPLETED")
    print("="*80)


async def test_neo4j_connection():
    """Test xem Neo4j có kết nối được không"""
    
    print("\n" + "="*80)
    print("🔌 TEST NEO4J CONNECTION")
    print("="*80)
    
    try:
        # Try to get graph adapter from container
        from app.core.container import ServiceContainer
        
        container = ServiceContainer()
        adapter = container.get_graph_adapter()
        
        if adapter is None:
            print(f"\n❌ Graph Adapter is None!")
            print(f"   Possible reasons:")
            print(f"   1. ENABLE_GRAPH_REASONING=false in environment")
            print(f"   2. Neo4j connection failed")
            print(f"   3. Import error for Neo4jGraphAdapter")
            return False
        
        print(f"\n✅ Graph Adapter initialized!")
        
        # Test query (execute_query is async)
        result = await adapter.execute_query("MATCH (n) RETURN count(n) as total LIMIT 1")
        
        if result:
            total = result[0].get('total', 0)
            print(f"✅ Connected! Total nodes: {total}")
            
            if total == 0:
                print(f"\n❌ WARNING: Database is EMPTY!")
                print(f"   No nodes found in Neo4j.")
                print(f"   This is why KG cannot be used!")
                return False
            
            # Check for Course nodes
            courses = await adapter.execute_query("""
                MATCH (c:Course)
                RETURN c.course_code as code, c.course_name as name
                LIMIT 5
            """)
            
            if courses:
                print(f"\n✅ Found {len(courses)} Course nodes:")
                for course in courses:
                    print(f"   - {course.get('code')}: {course.get('name')}")
            else:
                print(f"\n❌ WARNING: No Course nodes found!")
                print(f"   Cannot answer questions about courses!")
                return False
            
            return True
            
        else:
            print(f"\n❌ Connection failed - no results")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 FULL PIPELINE TEST WITH KNOWLEDGE GRAPH")
    print("="*80)
    
    # Test 1: Check Neo4j connection
    neo4j_ok = await test_neo4j_connection()
    
    if not neo4j_ok:
        print("\n⚠️ Neo4j is not ready. KG tests will likely fail.")
        print("Continue anyway? (tests will show debugging info)")
    
    # Test 2: Full pipeline
    await test_full_pipeline_with_kg()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
