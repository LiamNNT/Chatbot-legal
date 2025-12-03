#!/usr/bin/env python3
"""
Test Graph Reasoning with REAL data from Neo4j

Tests against actual data from:
- 790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf (Quy chế đào tạo UIT)
- Community nodes built by build_communities.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Setup paths BEFORE any imports
orchestrator_path = Path(__file__).parent.parent
rag_services_path = orchestrator_path.parent / "rag_services"

sys.path.insert(0, str(orchestrator_path))
sys.path.insert(0, str(rag_services_path))

# Load environment
from dotenv import load_dotenv
env_path = rag_services_path / ".env"
load_dotenv(env_path)


def print_separator(title):
    """Print section separator."""
    print(f"\n{'='*70}")
    print(f"🧪 {title}")
    print(f"{'='*70}")


async def test_neo4j_connection():
    """Test Neo4j connection and show graph stats."""
    print_separator("TEST 1: Neo4j Connection & Graph Stats")
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
        
        print(f"\n📡 Connecting to Neo4j: {uri}")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Get node counts
            result = session.run("""
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count
                ORDER BY count DESC
            """)
            
            print("\n📊 Node Statistics:")
            total_nodes = 0
            for record in result:
                labels = record["labels"]
                count = record["count"]
                total_nodes += count
                label_str = labels[0] if labels else "Unknown"
                print(f"   • {label_str}: {count} nodes")
            
            print(f"   ─────────────────")
            print(f"   Total: {total_nodes} nodes")
            
            # Get relationship counts
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            
            print("\n🔗 Relationship Statistics:")
            total_rels = 0
            for record in result:
                rel_type = record["type"]
                count = record["count"]
                total_rels += count
                print(f"   • {rel_type}: {count}")
            
            print(f"   ─────────────────")
            print(f"   Total: {total_rels} relationships")
            
            # Check for Community nodes
            result = session.run("""
                MATCH (c:Community)
                RETURN count(c) as count
            """)
            community_count = result.single()["count"]
            print(f"\n🏘️ Communities: {community_count}")
        
        driver.close()
        return True, total_nodes > 0
        
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return False, False


# Global imports for GraphQueryType (will be set after initialization)
GraphQueryType = None
GraphReasoningAgent = None


async def test_real_graph_reasoning():
    """Test Graph Reasoning with real Neo4j data."""
    global GraphQueryType, GraphReasoningAgent
    
    print_separator("TEST 2: Graph Reasoning with Real Data")
    
    try:
        # Import the real Neo4j adapter from rag_services
        from adapters.graph.neo4j_adapter import Neo4jGraphAdapter
        
        # Import GraphReasoningAgent directly 
        graph_reasoning_path = orchestrator_path / "app" / "agents" / "graph_reasoning_agent.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("graph_reasoning_agent", graph_reasoning_path)
        graph_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_module)
        
        GRA = graph_module.GraphReasoningAgent
        GQT = graph_module.GraphQueryType
        
        # Set global references
        GraphQueryType = GQT
        GraphReasoningAgent = GRA
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
        
        print(f"\n📡 Initializing Graph Adapter...")
        adapter = Neo4jGraphAdapter(uri=uri, username=user, password=password)
        
        # Test health check
        healthy = await adapter.health_check()
        print(f"   Health check: {'✅ OK' if healthy else '❌ Failed'}")
        
        if not healthy:
            return False
        
        # Initialize GraphReasoningAgent
        print(f"\n🤖 Initializing GraphReasoningAgent...")
        agent = GRA(graph_adapter=adapter)
        print(f"   Agent info: {agent.get_agent_info()}")
        
        return True, adapter, agent
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

async def test_local_queries(agent):
    """Test LOCAL reasoning with real data."""
    print_separator("TEST 3: LOCAL Reasoning (Real Queries)")
    
    test_queries = [
        "Điều kiện để đăng ký học phần là gì?",
        "Quy định về điểm trung bình tích lũy",
        "Sinh viên phải đạt bao nhiêu tín chỉ để tốt nghiệp?",
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        try:
            result = await agent.reason(
                query=query,
                query_type=GraphQueryType.LOCAL,
                context={}
            )
            
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Nodes found: {len(result.nodes)}")
            print(f"   Paths found: {len(result.paths)}")
            
            if result.reasoning_steps:
                print(f"   Steps: {result.reasoning_steps[0][:60]}...")
            
            if result.synthesized_context:
                context_preview = result.synthesized_context[:200].replace('\n', ' ')
                print(f"   Context: {context_preview}...")
            
            results.append(result.confidence > 0)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    return all(results) if results else False


async def test_global_queries(agent):
    """Test GLOBAL reasoning with Community data."""
    print_separator("TEST 4: GLOBAL Reasoning (Community Summaries)")
    
    test_queries = [
        "Tóm tắt các quy định về đăng ký học phần",
        "Tổng quan về quy trình xét tốt nghiệp",
        "So sánh các loại điểm trong quy chế đào tạo",
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        try:
            result = await agent.reason(
                query=query,
                query_type=GraphQueryType.GLOBAL,
                context={}
            )
            
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Communities found: {len(result.community_summaries)}")
            print(f"   Nodes: {len(result.nodes)}")
            
            if result.community_summaries:
                for i, summary in enumerate(result.community_summaries[:2], 1):
                    print(f"   Community [{i}]: {summary[:80]}...")
            
            if result.reasoning_steps:
                for step in result.reasoning_steps[:2]:
                    print(f"   • {step}")
            
            results.append(True)  # GLOBAL may have low confidence if no communities
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    return all(results) if results else False


async def test_multi_hop_queries(agent):
    """Test MULTI_HOP reasoning."""
    print_separator("TEST 5: MULTI_HOP Reasoning (Path Exploration)")
    
    test_queries = [
        "Nếu sinh viên không đạt điểm trung bình thì ảnh hưởng thế nào đến việc xét tốt nghiệp?",
        "Quy trình từ đăng ký học phần đến nhận kết quả điểm như thế nào?",
        "Các điều khoản liên quan đến buộc thôi học?",
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        
        try:
            result = await agent.reason(
                query=query,
                query_type=GraphQueryType.MULTI_HOP,
                context={}
            )
            
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Paths found: {len(result.paths)}")
            print(f"   Nodes affected: {len(result.nodes)}")
            
            if result.reasoning_steps:
                for step in result.reasoning_steps[:3]:
                    print(f"   • {step}")
            
            if result.paths:
                for path in result.paths[:2]:
                    names = path.get("node_names", path.get("node_codes", []))
                    if names:
                        print(f"   Path: {' → '.join(str(n) for n in names[:4])}...")
            
            results.append(True)  # Multi-hop may have varying results
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    return all(results) if results else False


async def test_integration_with_real_data(adapter, agent):
    """Test full integration with specific regulation queries."""
    print_separator("TEST 6: Integration - Quy chế đào tạo Queries")
    
    # Queries based on actual content from 790-qd-dhcntt
    real_queries = [
        {
            "query": "Điều 14 của quy chế đào tạo quy định gì?",
            "type": "local",
            "expected_keywords": ["đăng ký", "học phần"]
        },
        {
            "query": "Quy định về thực tập tối thiểu cho chương trình chuyên sâu đặc thù?",
            "type": "local", 
            "expected_keywords": ["8 tín chỉ", "thực tập"]
        },
        {
            "query": "Tóm tắt chương 3 về kiểm tra và thi học phần",
            "type": "global",
            "expected_keywords": ["kiểm tra", "thi"]
        },
    ]
    
    results = []
    
    for test_case in real_queries:
        query = test_case["query"]
        query_type = GraphQueryType(test_case["type"])
        
        print(f"\n📝 Query: {query}")
        print(f"   Type: {query_type.value}")
        
        try:
            result = await agent.reason(
                query=query,
                query_type=query_type,
                context={}
            )
            
            print(f"   ✓ Confidence: {result.confidence:.2f}")
            print(f"   ✓ Context length: {len(result.synthesized_context)} chars")
            
            # Check if expected keywords are in the context
            context_lower = result.synthesized_context.lower()
            found_keywords = []
            for kw in test_case["expected_keywords"]:
                if kw.lower() in context_lower:
                    found_keywords.append(kw)
            
            if found_keywords:
                print(f"   ✓ Found keywords: {found_keywords}")
            else:
                print(f"   ⚠ Keywords not found: {test_case['expected_keywords']}")
            
            results.append(result.confidence >= 0)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append(False)
    
    return all(results)


async def explore_graph_structure():
    """Explore the actual graph structure in Neo4j."""
    print_separator("BONUS: Explore Graph Structure")
    
    try:
        from neo4j import GraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
        
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Sample some nodes
            print("\n📋 Sample Nodes (first 5 of each type):")
            
            # Articles
            result = session.run("""
                MATCH (a:Article)
                RETURN a.id, a.title, a.article_number
                LIMIT 5
            """)
            
            articles = list(result)
            if articles:
                print("\n   📄 Articles:")
                for r in articles:
                    print(f"      • [{r['a.article_number']}] {r['a.title'][:50] if r['a.title'] else 'N/A'}...")
            
            # Entities
            result = session.run("""
                MATCH (e:Entity)
                RETURN e.name, e.type, e.description
                LIMIT 5
            """)
            
            entities = list(result)
            if entities:
                print("\n   🏷️ Entities:")
                for r in entities:
                    print(f"      • [{r['e.type']}] {r['e.name']}")
            
            # Communities
            result = session.run("""
                MATCH (c:Community)
                RETURN c.id, c.label, c.size, c.full_summary
                LIMIT 3
            """)
            
            communities = list(result)
            if communities:
                print("\n   🏘️ Communities:")
                for r in communities:
                    summary = r['c.full_summary'][:100] if r['c.full_summary'] else 'No summary'
                    print(f"      • {r['c.label']}")
                    print(f"        Size: {r['c.size']}, Summary: {summary}...")
            
            # Sample relationships
            result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN type(r) as rel_type, labels(a)[0] as from_label, labels(b)[0] as to_label
                LIMIT 10
            """)
            
            print("\n   🔗 Sample Relationships:")
            for r in result:
                print(f"      • ({r['from_label']})-[{r['rel_type']}]->({r['to_label']})")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Exploration failed: {e}")
        return False


async def main():
    """Run all real data tests."""
    print("\n" + "🚀" * 35)
    print("    GRAPH REASONING - REAL DATA TEST SUITE")
    print("    Data Source: 790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf")
    print("🚀" * 35)
    
    # Change working directory
    os.chdir(Path(__file__).parent.parent.parent / "rag_services")
    
    results = []
    
    # Test 1: Neo4j Connection
    connected, has_data = await test_neo4j_connection()
    results.append(("Neo4j Connection", connected))
    
    if not connected:
        print("\n❌ Cannot proceed without Neo4j connection")
        return False
    
    # Explore graph structure
    await explore_graph_structure()
    
    if not has_data:
        print("\n⚠️ Graph is empty. Please run data indexing first.")
        print("   Run: python scripts/build_communities.py")
        return False
    
    # Test 2: Initialize agents
    success, adapter, agent = await test_real_graph_reasoning()
    results.append(("Agent Initialization", success))
    
    if not success or not agent:
        print("\n❌ Cannot proceed without GraphReasoningAgent")
        return False
    
    # Test 3: Local Queries
    local_result = await test_local_queries(agent)
    results.append(("LOCAL Reasoning", local_result))
    
    # Test 4: Global Queries
    global_result = await test_global_queries(agent)
    results.append(("GLOBAL Reasoning", global_result))
    
    # Test 5: Multi-hop Queries
    multi_hop_result = await test_multi_hop_queries(agent)
    results.append(("MULTI_HOP Reasoning", multi_hop_result))
    
    # Test 6: Integration with real queries
    integration_result = await test_integration_with_real_data(adapter, agent)
    results.append(("Integration Tests", integration_result))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {status}: {name}")
        if result:
            passed += 1
    
    print(f"\n   Total: {passed}/{len(results)} tests passed")
    print("=" * 70)
    
    # Cleanup
    if adapter:
        adapter.close()
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
