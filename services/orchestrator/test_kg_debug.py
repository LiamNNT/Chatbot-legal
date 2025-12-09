"""
Test script để debug tại sao LLM không truy xuất Knowledge Graph.

Script này kiểm tra:
1. Smart Planner có đánh dấu use_knowledge_graph=True cho câu hỏi về môn học không?
2. Graph Reasoning Agent có được khởi tạo không?
3. Neo4j có dữ liệu môn học không?
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_smart_planner_kg_detection():
    """Test 1: Smart Planner có phát hiện câu hỏi cần dùng KG không?"""
    print("\n" + "="*80)
    print("TEST 1: SMART PLANNER KG DETECTION")
    print("="*80)
    
    from app.core.agent_factory import YAMLAgentFactory
    from app.adapters.openrouter_adapter import OpenRouterAdapter
    from app.core.config import settings
    
    # Initialize LLM adapter
    llm_adapter = OpenRouterAdapter(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL
    )
    
    # Create agent factory
    config_path = Path(__file__).parent / "config" / "agents_config_optimized.yaml"
    agent_factory = YAMLAgentFactory(str(config_path))
    
    # Create Smart Planner
    smart_planner = agent_factory.create_agent("smart_planner", llm_adapter)
    
    # Test queries về môn học
    test_queries = [
        "Môn IT001 có những môn tiên quyết nào?",
        "Nhập môn lập trình học những gì?",
        "Cấu trúc dữ liệu cần học gì trước?",
        "Môn học IT003 thuộc khoa nào?",
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
            print(f"   🔍 use_knowledge_graph: {result.use_knowledge_graph}")
            
            if hasattr(result, 'graph_query_type'):
                print(f"   🔍 graph_query_type: {result.graph_query_type}")
            
            print(f"   📊 Strategy: {result.strategy}")
            
            if result.use_knowledge_graph:
                print(f"   ✅ KG WILL BE USED! ✅")
            else:
                print(f"   ❌ KG NOT USED - WHY?")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


async def test_graph_adapter_connection():
    """Test 2: Graph Adapter có kết nối được với Neo4j không?"""
    print("\n" + "="*80)
    print("TEST 2: GRAPH ADAPTER CONNECTION")
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
        print(f"\n✅ Testing connection with simple query...")
        
        query = "MATCH (n) RETURN count(n) as total_nodes LIMIT 1"
        result = graph_adapter.execute_query(query)
        
        if result:
            print(f"   ✅ Connected! Total nodes in DB: {result[0].get('total_nodes', 0)}")
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
            print(f"   ❌ NO COURSES FOUND IN NEO4J!")
            print(f"   ⚠️ This is likely the root cause!")
        
        graph_adapter.close()
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def test_graph_reasoning_agent():
    """Test 3: Graph Reasoning Agent có hoạt động không?"""
    print("\n" + "="*80)
    print("TEST 3: GRAPH REASONING AGENT")
    print("="*80)
    
    try:
        from app.agents.graph_reasoning_agent import GraphReasoningAgent, GraphQueryType
        from app.adapters.neo4j_adapter import Neo4jAdapter
        from app.adapters.openrouter_adapter import OpenRouterAdapter
        from app.core.config import settings
        
        # Initialize adapters
        graph_adapter = Neo4jAdapter(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE
        )
        
        llm_adapter = OpenRouterAdapter(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL
        )
        
        # Create Graph Reasoning Agent
        graph_agent = GraphReasoningAgent(
            graph_adapter=graph_adapter,
            llm_port=llm_adapter
        )
        
        # Test query
        test_query = "Môn IT001 có những môn tiên quyết nào?"
        
        print(f"\n📝 Query: {test_query}")
        print("-" * 80)
        
        result = await graph_agent.reason(
            query=test_query,
            query_type=GraphQueryType.MULTI_HOP,
            context={}
        )
        
        print(f"\n📊 Results:")
        print(f"   Nodes found: {len(result.nodes)}")
        print(f"   Paths found: {len(result.paths)}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Context length: {len(result.synthesized_context)} chars")
        
        if result.nodes:
            print(f"\n   Nodes:")
            for node in result.nodes[:3]:
                print(f"      - {node}")
        
        if result.paths:
            print(f"\n   Paths:")
            for path in result.paths[:3]:
                print(f"      - {path}")
        
        if result.synthesized_context:
            print(f"\n   📝 Synthesized Context (first 500 chars):")
            print(f"      {result.synthesized_context[:500]}...")
        
        graph_adapter.close()
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def test_full_orchestration():
    """Test 4: Full orchestration với câu hỏi về môn học"""
    print("\n" + "="*80)
    print("TEST 4: FULL ORCHESTRATION WITH KG")
    print("="*80)
    
    try:
        from app.main import app
        from app.core.domain import OrchestrationRequest
        
        # Get orchestrator from app state
        orchestrator = app.state.orchestrator
        
        test_query = "Môn IT001 có những môn tiên quyết nào?"
        
        print(f"\n📝 Query: {test_query}")
        print("-" * 80)
        
        request = OrchestrationRequest(
            user_query=test_query,
            session_id="test_session",
            use_rag=True,
            use_knowledge_graph=True  # Force enable KG
        )
        
        print(f"\n🚀 Processing request...")
        response = await orchestrator.process_request(request)
        
        print(f"\n📊 Response:")
        print(f"   {response.response}")
        
        print(f"\n📈 Stats:")
        if response.processing_stats:
            for key, value in response.processing_stats.items():
                print(f"   - {key}: {value}")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🔍 KNOWLEDGE GRAPH DEBUG TEST SUITE")
    print("="*80)
    
    # Test 1: Smart Planner
    await test_smart_planner_kg_detection()
    
    # Test 2: Graph Adapter
    await test_graph_adapter_connection()
    
    # Test 3: Graph Reasoning Agent
    await test_graph_reasoning_agent()
    
    # Test 4: Full Orchestration
    # await test_full_orchestration()  # Uncomment if server is running
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
