#!/usr/bin/env python3
"""
Extract entities and relations from sample data and build graph in Neo4j

This script:
1. Takes sample Vietnamese academic text
2. Extracts entities using CategoryGuidedEntityExtractor
3. Extracts relations using LLM (OpenRouter)
4. Builds graph in Neo4j
5. Shows visualization instructions
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample data về quy định học tập UIT
SAMPLE_TEXTS = [
    """
    Chương 2: QUY ĐỊNH VỀ HỌC TẬP VÀ KIỂM TRA
    
    Điều 5. Điều kiện đăng ký học phần
    
    1. Môn học IT003 (Cấu trúc dữ liệu và giải thuật) yêu cầu:
       - Hoàn thành môn IT002 (Lập trình hướng đối tượng) với điểm C trở lên
       - Hoàn thành môn IT001 (Nhập môn lập trình) với điểm C trở lên
    
    2. Môn học IT007 (Hệ điều hành) yêu cầu:
       - Hoàn thành môn IT003 (Cấu trúc dữ liệu và giải thuật)
       - Hoàn thành môn IT006 (Kiến trúc máy tính)
    
    3. Môn học IT012 (Mạng máy tính) yêu cầu:
       - Hoàn thành môn IT007 (Hệ điều hành)
    
    Sinh viên thuộc Khoa Công nghệ Thông tin phải đăng ký tối thiểu 12 tín chỉ mỗi học kỳ.
    """,
    
    """
    Điều 8. Quy định về điểm số và học lại
    
    1. Môn học IT008 (Cơ sở dữ liệu) là môn bắt buộc của Ngành Khoa học máy tính.
       Sinh viên phải đạt điểm D trở lên mới được xem là hoàn thành.
       
    2. Môn học IT004 (Đồ án 1) yêu cầu:
       - Hoàn thành ít nhất 60 tín chỉ
       - Hoàn thành môn IT003 (Cấu trúc dữ liệu và giải thuật)
    
    3. Chương trình Đào tạo Tiên tiến CNTT gồm các môn:
       - IT001, IT002, IT003, IT004
       - IT006, IT007, IT008
       - Tổng cộng 140 tín chỉ
    """,
    
    """
    Điều 12. Quy định về khoa và ngành
    
    1. Khoa Công nghệ Thông tin quản lý các ngành:
       - Ngành Khoa học máy tính (mã ngành: CS)
       - Ngành Kỹ thuật phần mềm (mã ngành: SE)
       - Ngành Hệ thống thông tin (mã ngành: IS)
    
    2. Khoa Khoa học và Kỹ thuật Máy tính quản lý:
       - Ngành Kỹ thuật máy tính (mã ngành: CE)
    
    3. Mỗi ngành có Chương trình Đào tạo riêng với các môn học bắt buộc và tự chọn.
    """
]


async def main():
    print("\n" + "="*80)
    print("EXTRACT & BUILD KNOWLEDGE GRAPH - NEO4J")
    print("="*80)
    
    # Step 0: Check Neo4j
    print("\n📊 Step 0: Check Neo4j Connection")
    try:
        from adapters.graph.neo4j_adapter import create_neo4j_adapter
        
        graph_repo = create_neo4j_adapter()
        is_healthy = await graph_repo.health_check()
        
        if not is_healthy:
            print("   ❌ Neo4j is not healthy!")
            print("\n   Start Neo4j:")
            print("   docker-compose -f docker/docker-compose.neo4j.yml up -d")
            return
        
        print("   ✅ Neo4j is healthy and connected")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Step 1: Check LLM configuration
    print("\n🤖 Step 1: Check LLM Configuration")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", "google/gemini-flash-1.5")
    provider = os.getenv("LLM_PROVIDER", "openrouter")
    
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")
    print(f"   API Key: {'✅ Set' if api_key else '❌ Not set'}")
    
    if not api_key:
        print("\n   ⚠️  No API key set - will skip LLM relation extraction")
        print("   Only rule-based entity extraction will be performed")
        use_llm = False
    else:
        use_llm = True
        print("   ✅ LLM extraction enabled")
    
    # Step 2: Import required modules
    print("\n📦 Step 2: Loading modules...")
    try:
        from indexing.category_guided_entity_extractor import CategoryGuidedEntityExtractor
        from core.domain.graph_models import GraphNode, GraphRelationship, NodeCategory, RelationshipType
        
        if use_llm:
            from adapters.llm import create_llm_client_from_env
            from indexing.llm_relation_extractor import LLMRelationExtractor
        
        print("   ✅ All modules loaded")
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return
    
    # Step 3: Extract entities from all texts
    print("\n🔍 Step 3: Extracting Entities...")
    entity_extractor = CategoryGuidedEntityExtractor()
    
    # Mapping từ entity type sang NodeCategory
    ENTITY_TO_NODE_CATEGORY = {
        'MON_HOC': NodeCategory.MON_HOC,
        'QUY_DINH': NodeCategory.QUY_DINH,
        'DIEU_KIEN': NodeCategory.DIEU_KIEN,
        'KHOA': NodeCategory.KHOA,
        'NGANH': NodeCategory.NGANH,
        'CHUONG_TRINH_DAO_TAO': NodeCategory.CHUONG_TRINH_DAO_TAO,
        'SINH_VIEN': NodeCategory.SINH_VIEN,
        'KY_HOC': NodeCategory.KY_HOC,
        'GIANG_VIEN': NodeCategory.GIANG_VIEN,
        'HOC_PHI': NodeCategory.HOC_PHI,
    }
    
    all_entities = []
    all_nodes = []
    node_ids = set()
    
    for i, text in enumerate(SAMPLE_TEXTS, 1):
        print(f"\n   Processing text {i}/{len(SAMPLE_TEXTS)}...")
        entities_dict = entity_extractor.extract(text)
        
        for category, entities in entities_dict.items():
            print(f"     {category}: {len(entities)} entities")
            all_entities.extend(entities)
            
            # Get NodeCategory
            node_category = ENTITY_TO_NODE_CATEGORY.get(category)
            if not node_category:
                print(f"     ⚠️  Unknown category: {category}, skipping...")
                continue
            
            # Create graph nodes
            for entity in entities:
                node_id = f"{category}_{entity.text}".replace(" ", "_").replace("(", "").replace(")", "")
                
                if node_id in node_ids:
                    continue
                node_ids.add(node_id)
                
                # Build properties based on category
                props = {
                    'name': entity.text,
                    'confidence': entity.confidence,
                    'extracted_from': f'text_{i}',
                    'source': 'sample_extraction',
                }
                
                # Add category-specific required properties
                if node_category == NodeCategory.MON_HOC:
                    props.update({
                        'code': node_id,
                        'credits': 4,  # Default
                    })
                elif node_category == NodeCategory.QUY_DINH:
                    props.update({
                        'id': node_id,
                        'title': entity.text,
                        'year': 2024,
                    })
                elif node_category == NodeCategory.DIEU_KIEN:
                    props.update({
                        'id': node_id,
                        'type': 'prerequisite',
                        'description': entity.text,
                    })
                elif node_category in [NodeCategory.KHOA, NodeCategory.NGANH]:
                    props.update({
                        'code': node_id,
                    })
                elif node_category == NodeCategory.CHUONG_TRINH_DAO_TAO:
                    props.update({
                        'id': node_id,
                        'year': 2024,
                    })
                elif node_category == NodeCategory.SINH_VIEN:
                    props.update({
                        'cohort': 2024,
                    })
                elif node_category == NodeCategory.KY_HOC:
                    props.update({
                        'code': node_id,
                        'year': 2024,
                    })
                else:
                    # Generic - add id
                    props['id'] = node_id
                
                node = GraphNode(
                    category=node_category,
                    properties=props
                )
                all_nodes.append(node)
    
    print(f"\n   ✅ Total entities extracted: {len(all_entities)}")
    print(f"   ✅ Unique nodes created: {len(all_nodes)}")
    
    # Step 4: Extract relations using LLM (if enabled)
    all_relations = []
    total_tokens = 0
    total_cost = 0.0
    
    if use_llm:
        print("\n🔗 Step 4: Extracting Relations with LLM...")
        
        try:
            llm_client = create_llm_client_from_env()
            relation_extractor = LLMRelationExtractor(llm_client)
            
            for i, text in enumerate(SAMPLE_TEXTS, 1):
                print(f"\n   Processing text {i}/{len(SAMPLE_TEXTS)} with LLM...")
                
                # Get entities for this text
                text_entities_dict = entity_extractor.extract(text)
                text_entities = [e for ents in text_entities_dict.values() for e in ents]
                
                if not text_entities:
                    print(f"     No entities found, skipping LLM")
                    continue
                
                # Extract relations
                result = await relation_extractor.extract_relations(
                    text=text,
                    entities=text_entities,
                    use_few_shot=True
                )
                
                print(f"     Relations: {len(result.relations)}")
                print(f"     Tokens: {result.tokens_used}")
                print(f"     Cost: ${result.cost_usd:.4f}")
                
                total_tokens += result.tokens_used
                total_cost += result.cost_usd
                
                all_relations.extend(result.relations)
            
            print(f"\n   ✅ Total relations extracted: {len(all_relations)}")
            print(f"   📊 Total tokens used: {total_tokens}")
            print(f"   💰 Total cost: ${total_cost:.4f}")
            
        except Exception as e:
            print(f"   ⚠️  LLM extraction failed: {e}")
            print("   Continuing with nodes only...")
    
    else:
        print("\n⚠️  Step 4: Skipped (no LLM API key)")
    
    # Step 5: Prepare graph relationships (but we need node IDs first)
    graph_relationships = []
    
    # Step 6: Build graph in Neo4j
    print("\n📊 Step 6: Building Graph in Neo4j...")
    
    try:
        # Note: Skipping clear since execute_query not implemented in POC
        # await graph_repo.execute_query("MATCH (n) DETACH DELETE n")
        
        # Create nodes
        print(f"   Creating {len(all_nodes)} nodes...")
        created_node_ids = await graph_repo.add_nodes_batch(all_nodes)
        print(f"   ✅ Created {len(created_node_ids)} nodes")
        
        # Now create relationships with real node IDs
        if all_relations:
            print(f"   Creating {len(all_relations)} relationships...")
            
            # Create mapping from node text IDs to Neo4j element IDs
            node_id_map = {}
            for node, neo4j_id in zip(all_nodes, created_node_ids):
                text_id = f"{node.category.name}_{node.properties.get('name', node.properties.get('title', 'unknown'))}"
                text_id = text_id.replace(" ", "_").replace("(", "").replace(")", "")
                node_id_map[text_id] = neo4j_id
            
            print(f"   📍 Mapped {len(node_id_map)} nodes to Neo4j IDs")
            
            for rel in all_relations:
                try:
                    source_text_id = f"{rel.source.type}_{rel.source.text}".replace(" ", "_").replace("(", "").replace(")", "")
                    target_text_id = f"{rel.target.type}_{rel.target.text}".replace(" ", "_").replace("(", "").replace(")", "")
                    
                    # Look up Neo4j element IDs
                    source_neo4j_id = node_id_map.get(source_text_id)
                    target_neo4j_id = node_id_map.get(target_text_id)
                    
                    if not source_neo4j_id or not target_neo4j_id:
                        # Debug: print available keys on first failure
                        if not graph_relationships:
                            print(f"     🔍 Available node IDs: {list(node_id_map.keys())[:5]}...")
                        print(f"     ⚠️  Skipping relation: node not found (source: {source_text_id}, target: {target_text_id})")
                        continue
                    
                    graph_rel = GraphRelationship(
                        source_id=source_neo4j_id,
                        target_id=target_neo4j_id,
                        rel_type=rel.rel_type,
                        properties={
                            'confidence': rel.confidence,
                            'evidence': rel.metadata.get('evidence', ''),
                            'extracted_by': 'llm_openrouter',
                        }
                    )
                    graph_relationships.append(graph_rel)
                    
                except Exception as e:
                    print(f"     ⚠️  Failed to create relationship: {e}")
            
            print(f"   ✅ Prepared {len(graph_relationships)} graph relationships")
        
        # Create relationships in Neo4j
        if graph_relationships:
            created_rel_count = await graph_repo.add_relationships_batch(graph_relationships)
            print(f"   ✅ Created {created_rel_count} relationships in Neo4j")
        
    except Exception as e:
        print(f"   ❌ Error building graph: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 7: Graph Statistics
    print("\n📊 Step 7: Graph Statistics...")
    
    print(f"""
   Nodes created: {len(created_node_ids)}
   Relationships created: {len(graph_relationships) if graph_relationships else 0}
""")
    
    # Note: execute_query not implemented in POC, skipping stats queries
    # try:
    #     result = await graph_repo.execute_query(...)
    # except Exception as e:
    #     print(f"   ⚠️  Error querying stats: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("✅ EXTRACTION COMPLETED!")
    print("="*80)
    
    print(f"""
📊 Summary:
   • Texts processed: {len(SAMPLE_TEXTS)}
   • Entities extracted: {len(all_entities)}
   • Nodes created: {len(created_node_ids)}
   • Relations extracted: {len(all_relations) if use_llm else 0}
   • Relationships created: {len(graph_relationships) if graph_relationships else 0}
""")
    
    if use_llm:
        print(f"""💰 LLM Usage:
   • Total tokens: {total_tokens:,}
   • Total cost: ${total_cost:.4f}
   • Model: {model}
""")
    
    print(f"""🔍 View Graph in Neo4j Browser:
   1. Open: http://localhost:7474
   2. Login: neo4j / uitchatbot
   3. Run queries:
   
   # View all nodes
   MATCH (n) RETURN n LIMIT 50
   
   # View relationships
   MATCH p=()-[r]->() RETURN p LIMIT 25
   
   # View specific category
   MATCH (n:MON_HOC) RETURN n.name, n.id
   
   # View prerequisite chain
   MATCH path = (a:MON_HOC)-[:TIEN_QUYET*1..3]->(b:MON_HOC)
   WHERE a.name CONTAINS 'IT003'
   RETURN path
   LIMIT 10
""")
    
    print("="*80)
    
    # Close connection
    await graph_repo.close()


if __name__ == "__main__":
    asyncio.run(main())
