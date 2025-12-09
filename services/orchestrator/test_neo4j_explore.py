"""
Script để search xem Neo4j có Điều nào và test với dữ liệu thực tế.
"""

import os
import sys
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


async def explore_neo4j_data():
    """Khám phá xem Neo4j có dữ liệu gì"""
    
    print("\n" + "="*80)
    print("🔍 KHÁM PHÁ DỮ LIỆU TRONG NEO4J")
    print("="*80)
    
    from app.core.container import ServiceContainer
    
    container = ServiceContainer()
    adapter = container.get_graph_adapter()
    
    if adapter is None:
        print("\n❌ Graph Adapter is None!")
        return []
    
    print("\n✅ Graph Adapter initialized!")
    
    # 1. Get graph stats
    print("\n1️⃣ GETTING GRAPH STATISTICS...")
    try:
        stats = await adapter.get_graph_stats()
        
        print(f"\n   Graph Stats:")
        for key, value in stats.items():
            print(f"      - {key}: {value}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Get category distribution
    print("\n2️⃣ CHECKING CATEGORY DISTRIBUTION...")
    try:
        categories = await adapter.get_category_distribution()
        
        if categories:
            print(f"\n   Found {len(categories)} categories:")
            for cat, count in categories.items():
                print(f"      - {cat}: {count} nodes")
        else:
            print("   ❌ No categories found!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Search for Article nodes using search_articles_by_keyword
    print("\n3️⃣ SEARCHING FOR ARTICLES...")
    try:
        # Try searching with common keywords
        articles_result = await adapter.search_articles_by_keyword(
            keywords=["điều", "quy định", "học"],
            limit=50  # Get more to see all
        )
        
        if articles_result:
            print(f"\n   Found {len(articles_result)} articles:")
            article_ids = []
            for article in articles_result[:20]:  # Show first 20
                art_id = article.get('article_id')
                title = article.get('title', 'N/A')
                if art_id:
                    article_ids.append(art_id)
                    # Try to extract Điều number from title or id
                    title_str = str(title)[:70]
                    print(f"      - ID: {art_id} | {title_str}...")
            
            if article_ids:
                print(f"\n   📝 Found {len(article_ids)} article IDs in DB")
                print(f"   First 10 IDs: {article_ids[:10]}")
                return article_ids
            else:
                print("   ⚠️ Articles found but no article_id field!")
                return []
        else:
            print("   ❌ No articles found with keywords!")
            return []
            
    except Exception as e:
        print(f"   ❌ Error searching articles: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    # 4. Try getting nodes by category
    print("\n4️⃣ TRYING TO GET NODES BY CATEGORY...")
    try:
        # Try DIEU_KHOAN category
        from adapters.graph.enums import NodeCategory
        
        nodes = await adapter.get_nodes_by_category(
            category=NodeCategory.DIEU_KHOAN,
            limit=10
        )
        
        if nodes:
            print(f"\n   Found {len(nodes)} DIEU_KHOAN nodes:")
            article_numbers = []
            for node in nodes:
                props = node.get('properties', {})
                number = props.get('so_dieu') or props.get('article_number')
                title = props.get('tieu_de') or props.get('title', 'N/A')
                if number:
                    article_numbers.append(number)
                    print(f"      - Điều {number}: {title[:60]}...")
            
            if article_numbers:
                return sorted(set(article_numbers))
                
    except Exception as e:
        print(f"   ❌ Error getting nodes by category: {e}")
    
    return []


async def test_with_real_articles(article_ids):
    """Test với các Article thực sự có trong database"""
    
    if not article_ids:
        print("\n⚠️ Không có Article nào để test!")
        return
    
    print("\n" + "="*80)
    print("🧪 TEST VỚI DỮ LIỆU THỰC TẾ TRONG NEO4J")
    print("="*80)
    
    from app.core.container import ServiceContainer
    from app.core.domain import OrchestrationRequest
    
    container = ServiceContainer()
    orchestrator = container.get_multi_agent_orchestrator()
    
    # Tạo queries dựa trên article IDs thực tế
    test_queries = [
        "Điều 19 quy định gì?",
        "Điều 20 nói về vấn đề gì?",
        "Điều 21 quy định như thế nào?",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"📝 Query: {query}")
        print("-" * 80)
        
        try:
            request = OrchestrationRequest(
                user_query=query,
                session_id="test_session",
                use_rag=True,
                use_knowledge_graph=None  # Let Smart Planner decide
            )
            
            print("\n⏳ Processing...")
            response = await orchestrator.process_request(request)
            
            # Extract stats
            stats = response.processing_stats
            plan_result = response.agent_metadata.get('plan_result')
            
            # Show KG usage
            used_kg = stats.get('use_knowledge_graph', False)
            nodes_found = stats.get('graph_nodes_found', 0)
            
            print(f"\n📊 Stats:")
            print(f"   - Smart Planner use_kg: {plan_result.get('use_knowledge_graph') if plan_result else 'N/A'}")
            print(f"   - Actually used KG: {used_kg}")
            print(f"   - Nodes found: {nodes_found}")
            print(f"   - Docs retrieved: {stats.get('documents_retrieved', 0)}")
            print(f"   - Time: {stats.get('total_time', 0):.2f}s")
            
            # Show response
            print(f"\n💬 Response:")
            print("-" * 80)
            response_text = response.response
            if len(response_text) > 800:
                print(response_text[:800] + "\n... (truncated)")
            else:
                print(response_text)
            print("-" * 80)
            
            # Check if response is meaningful
            if "chưa tìm thấy" in response_text.lower() or "không có thông tin" in response_text.lower():
                print(f"\n⚠️ WARNING: Response indicates NO DATA FOUND!")
                print(f"   Graph Reasoning không tìm được dữ liệu phù hợp!")
            else:
                print(f"\n✅ Response looks good - contains actual information!")
                
                # Check if it mentions specific article content
                if "điều" in response_text.lower() and len(response_text) > 200:
                    print(f"   ✅✅ Great! Response contains detailed Điều content!")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Run exploration and tests"""
    print("\n" + "="*80)
    print("🔬 KHÁM PHÁ VÀ TEST DỮ LIỆU NEO4J")
    print("="*80)
    
    # Step 1: Explore what's in Neo4j
    article_numbers = await explore_neo4j_data()
    
    # Step 2: Test with real data
    if article_numbers:
        await test_with_real_articles(article_numbers)
    else:
        print("\n❌ Không tìm thấy Article nodes trong Neo4j!")
        print("   Database có thể rỗng hoặc schema khác!")
    
    print("\n" + "="*80)
    print("✅ HOÀN THÀNH")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
