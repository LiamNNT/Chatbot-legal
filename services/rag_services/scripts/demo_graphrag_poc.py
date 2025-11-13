"""
POC Demo Script for GraphRAG Week 1

Demonstrates:
1. Neo4j connection
2. CatRAG schema initialization
3. Sample data creation
4. Graph traversal (prerequisite chain)
5. Category-based queries

Run this after setting up Neo4j Docker container.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.graph.neo4j_adapter import create_neo4j_adapter
from core.domain.graph_models import (
    create_mon_hoc_node,
    create_quy_dinh_node,
    create_prerequisite_relationship,
    GraphNode,
    GraphRelationship,
    NodeCategory,
    RelationshipType
)


async def demo_graphrag_poc():
    """
    Week 1 POC Demo - CatRAG GraphRAG System
    """
    
    print("=" * 60)
    print("🚀 GraphRAG POC Demo - Week 1")
    print("=" * 60)
    print()
    
    # Step 1: Connect to Neo4j
    print("📡 Step 1: Connecting to Neo4j...")
    adapter = create_neo4j_adapter()
    
    if not await adapter.health_check():
        print("❌ Failed to connect to Neo4j")
        print("   Make sure Neo4j is running: docker-compose -f docker/docker-compose.neo4j.yml up -d")
        return
    
    print("✅ Connected to Neo4j successfully")
    print()
    
    # Step 2: Clear existing data (for clean demo)
    print("🧹 Step 2: Clearing existing data...")
    await adapter.clear_graph()
    print("✅ Database cleared")
    print()
    
    # Step 3: Create sample courses (MonHoc)
    print("📚 Step 3: Creating sample courses...")
    
    courses = [
        create_mon_hoc_node(
            code="IT001",
            name="Nhập môn lập trình",
            credits=4,
            type="bat_buoc",
            description="Môn học cơ bản về lập trình C/C++"
        ),
        create_mon_hoc_node(
            code="IT002",
            name="Lập trình hướng đối tượng",
            credits=4,
            type="bat_buoc",
            description="Lập trình OOP với C++"
        ),
        create_mon_hoc_node(
            code="IT003",
            name="Cấu trúc dữ liệu và giải thuật",
            credits=4,
            type="bat_buoc",
            description="CTDL và GT cơ bản"
        ),
        create_mon_hoc_node(
            code="IT004",
            name="Cơ sở dữ liệu",
            credits=4,
            type="bat_buoc",
            description="Thiết kế và quản trị CSDL"
        ),
        create_mon_hoc_node(
            code="IT005",
            name="Nhập môn mạng máy tính",
            credits=4,
            type="bat_buoc",
            description="Kiến thức cơ bản về mạng"
        )
    ]
    
    course_ids = {}
    for course in courses:
        node_id = await adapter.add_node(course)
        course_ids[course.properties["code"]] = node_id
        print(f"  ✓ Created course: {course.properties['code']} - {course.properties['name']}")
    
    print()
    
    # Step 4: Create prerequisite relationships
    print("🔗 Step 4: Creating prerequisite relationships...")
    
    # IT002 requires IT001
    rel1 = create_prerequisite_relationship(
        course_ids["IT002"],
        course_ids["IT001"],
        required=True
    )
    await adapter.add_relationship(rel1)
    print("  ✓ IT002 → requires → IT001")
    
    # IT003 requires IT002
    rel2 = create_prerequisite_relationship(
        course_ids["IT003"],
        course_ids["IT002"],
        required=True
    )
    await adapter.add_relationship(rel2)
    print("  ✓ IT003 → requires → IT002")
    
    # IT004 requires IT002 (recommended)
    rel3 = GraphRelationship(
        source_id=course_ids["IT004"],
        target_id=course_ids["IT002"],
        rel_type=RelationshipType.DIEU_KIEN_TIEN_QUYET,
        properties={"type": "khuyen_nghi", "can_study_parallel": True}
    )
    await adapter.add_relationship(rel3)
    print("  ✓ IT004 → recommends → IT002")
    
    print()
    
    # Step 5: Create Khoa and Nganh
    print("🏫 Step 5: Creating organizational structure...")
    
    khoa_cntt = GraphNode(
        category=NodeCategory.KHOA,
        properties={
            "code": "CNTT",
            "name": "Khoa Công nghệ thông tin",
            "dean": "PGS.TS Nguyễn Văn A"
        }
    )
    khoa_id = await adapter.add_node(khoa_cntt)
    print("  ✓ Created: Khoa CNTT")
    
    nganh_cntt = GraphNode(
        category=NodeCategory.NGANH,
        properties={
            "code": "CNTT_DT",
            "name": "Công nghệ thông tin",
            "type": "dai_tra"
        }
    )
    nganh_id = await adapter.add_node(nganh_cntt)
    print("  ✓ Created: Ngành CNTT")
    
    # Link Nganh to Khoa
    thuoc_khoa_rel = GraphRelationship(
        source_id=nganh_id,
        target_id=khoa_id,
        rel_type=RelationshipType.THUOC_KHOA,
        properties={}
    )
    await adapter.add_relationship(thuoc_khoa_rel)
    print("  ✓ Linked: Ngành CNTT → Khoa CNTT")
    
    print()
    
    # Step 6: Query graph statistics
    print("📊 Step 6: Graph Statistics")
    stats = await adapter.get_graph_stats()
    
    print(f"\n  Total Nodes: {stats['total_nodes']}")
    print(f"  Total Relationships: {stats['total_relationships']}")
    print(f"\n  Nodes by Category:")
    for category, count in stats['nodes_by_category'].items():
        print(f"    - {category}: {count}")
    
    print(f"\n  Relationships by Type:")
    for rel_type, count in stats['relationships_by_type'].items():
        print(f"    - {rel_type}: {count}")
    
    print()
    
    # Step 7: CRITICAL CatRAG Demo - Traverse Prerequisites
    print("🎯 Step 7: CatRAG Query Demo - \"What are prerequisites for IT003?\"")
    print()
    
    # This simulates: User asks "Môn tiên quyết của IT003 là gì?"
    # Router Agent classifies as TIEN_QUYET intent → Routes to graph traversal
    
    subgraph = await adapter.traverse(
        start_node_id=course_ids["IT003"],
        relationship_types=[RelationshipType.DIEU_KIEN_TIEN_QUYET],
        max_depth=3,
        direction="outgoing"
    )
    
    print(f"  Found {len(subgraph.nodes)} related courses:")
    print()
    
    # Extract prerequisite chain
    prereq_chain = []
    for node in subgraph.nodes:
        if node.category == NodeCategory.MON_HOC:
            course_info = f"{node.properties.get('code')} - {node.properties.get('name')}"
            prereq_chain.append(course_info)
            print(f"    📚 {course_info}")
    
    print()
    print("  Prerequisite Chain (in order):")
    print("    IT003 ← requires ← IT002 ← requires ← IT001")
    print()
    print("  💡 CatRAG Insight: This query used GRAPH TRAVERSAL")
    print("     because the intent was classified as 'TIEN_QUYET'")
    print()
    
    # Step 8: Category-based query
    print("📋 Step 8: Get all courses in CNTT")
    
    all_courses = await adapter.get_nodes_by_category(
        category=NodeCategory.MON_HOC,
        limit=10
    )
    
    print(f"\n  Found {len(all_courses)} courses:")
    for course_node in all_courses:
        code = course_node.properties.get("code")
        name = course_node.properties.get("name")
        credits = course_node.properties.get("credits")
        print(f"    - {code}: {name} ({credits} tín chỉ)")
    
    print()
    
    # Step 9: Raw Cypher query example
    print("🔍 Step 9: Advanced Cypher Query - Find all prerequisite chains")
    print()
    
    cypher = """
    MATCH path = (end:MonHoc)-[:DIEU_KIEN_TIEN_QUYET*]->(start:MonHoc)
    WHERE end.code = 'IT003'
    RETURN 
        [node in nodes(path) | node.code] as chain,
        length(path) as depth
    ORDER BY depth DESC
    """
    
    results = await adapter.execute_cypher(cypher)
    
    for result in results:
        chain = result.get("chain", [])
        depth = result.get("depth", 0)
        chain_str = " → ".join(chain)
        print(f"  Chain (depth {depth}): {chain_str}")
    
    print()
    
    # Summary
    print("=" * 60)
    print("✅ POC Demo Complete!")
    print("=" * 60)
    print()
    print("🎓 What we demonstrated:")
    print("  1. ✅ Neo4j connection and health check")
    print("  2. ✅ Category-labeled graph (CatRAG schema)")
    print("  3. ✅ Sample data creation (MonHoc, Khoa, Nganh)")
    print("  4. ✅ Prerequisite relationships")
    print("  5. ✅ Graph traversal (CRITICAL for CatRAG)")
    print("  6. ✅ Category-based queries")
    print("  7. ✅ Raw Cypher queries")
    print()
    print("🚀 Next Steps:")
    print("  - Week 2: LLM-guided entity extraction")
    print("  - Week 3: Router Agent implementation")
    print("  - Week 4: Integration with Vector RAG")
    print()
    
    # Close connection
    adapter.close()


async def test_prerequisite_query():
    """
    Specific test for prerequisite query pattern.
    
    This simulates the most important CatRAG use case:
    "What courses must I take before IT003?"
    """
    print("\n" + "=" * 60)
    print("🧪 Testing Prerequisite Query Pattern")
    print("=" * 60 + "\n")
    
    adapter = create_neo4j_adapter()
    
    # Simulate user query: "Tôi cần học gì trước IT003?"
    print("❓ User Query: \"Tôi cần học gì trước khi học Cấu trúc dữ liệu (IT003)?\"")
    print()
    
    # Step 1: Intent classification (future Router Agent)
    print("🤖 Router Agent: Classifying intent...")
    print("   Intent detected: TIEN_QUYET")
    print("   Routing to: GRAPH_TRAVERSAL")
    print()
    
    # Step 2: Entity extraction
    print("🏷️  Entity Extractor: Extracting entities...")
    print("   Found: IT003 (type: MON_HOC)")
    print()
    
    # Step 3: Graph query
    print("🔍 Graph Query: Traversing prerequisites...")
    
    # Get IT003 node first
    courses = await adapter.get_nodes_by_category(
        NodeCategory.MON_HOC,
        filters={"code": "IT003"}
    )
    
    if not courses:
        print("   ❌ Course IT003 not found. Run main demo first.")
        return
    
    it003_id = courses[0].id
    
    # Traverse prerequisites
    subgraph = await adapter.traverse(
        start_node_id=it003_id,
        relationship_types=[RelationshipType.DIEU_KIEN_TIEN_QUYET],
        max_depth=5,
        direction="outgoing"
    )
    
    print(f"   ✓ Found {len(subgraph.nodes)} related courses")
    print()
    
    # Step 4: Format answer
    print("💬 Answer:")
    print()
    print("   Để học IT003 - Cấu trúc dữ liệu và giải thuật, bạn cần:")
    print()
    
    for i, node in enumerate(subgraph.nodes, 1):
        if node.category == NodeCategory.MON_HOC and node.id != it003_id:
            code = node.properties.get("code")
            name = node.properties.get("name")
            print(f"   {i}. {code} - {name}")
    
    print()
    print("   Thứ tự học: IT001 → IT002 → IT003")
    print()
    
    adapter.close()


if __name__ == "__main__":
    print("\n🌟 GraphRAG POC - Week 1 Demonstration\n")
    
    # Run main demo
    asyncio.run(demo_graphrag_poc())
    
    # Run specific prerequisite test
    asyncio.run(test_prerequisite_query())
    
    print("\n✨ All demos completed!\n")
