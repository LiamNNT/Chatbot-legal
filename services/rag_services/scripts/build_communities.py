#!/usr/bin/env python3
"""
Leiden Community Detection for GraphRAG with LLM-based Community Reports

This script detects communities across the knowledge graph using the Leiden algorithm
and generates comprehensive Community Reports using LLM (following Microsoft GraphRAG standard).

Features:
1. Leiden algorithm for cross-chapter community detection
2. LLM-generated Community Reports (not just keyword labels)
3. Full summaries stored in Neo4j for query routing

Requirements:
    pip install leidenalg igraph httpx
"""

import os
import sys
import asyncio
from pathlib import Path
from collections import defaultdict
import json
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from neo4j import GraphDatabase
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Leiden - if not available, use fallback
try:
    import igraph as ig
    import leidenalg
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False
    print("⚠️ leidenalg/igraph not installed. Using Entity co-occurrence fallback.")
    print("   Install with: pip install leidenalg igraph")


def setup_environment():
    """Load environment variables"""
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path, override=True)
    
    # Support both OPENROUTER_API_KEY and OPENAI_API_KEY (legacy)
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    return {
        "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
        "neo4j_password": os.getenv("NEO4J_PASSWORD"),
        "openrouter_api_key": api_key,
        "model": os.getenv("GRAPHRAG_MODEL", "openai/gpt-4o-mini")
    }


class LLMClient:
    """LLM client for generating community reports"""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
    
    async def generate_community_report(self, community_data: dict) -> str:
        """
        Generate a comprehensive Community Report using LLM.
        
        This follows Microsoft GraphRAG standard: not just keywords,
        but a coherent narrative describing the community's content.
        """
        # Build context from article summaries
        article_context = []
        for art in community_data.get('articles', []):
            summary = art.get('summary', '')
            if summary:
                article_context.append(f"- {art['id']} ({art.get('title', '')}): {summary}")
        
        # Build entity context
        entity_context = []
        for ent in community_data.get('key_entities', []):
            entity_context.append(f"- {ent['name']} ({ent['type']}): xuất hiện trong {ent['count']} điều")
        
        prompt = f"""Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam.

Dưới đây là nhóm các điều khoản pháp quy có liên quan chặt chẽ với nhau (được phát hiện bởi thuật toán phân cụm):

**CÁC ĐIỀU KHOẢN TRONG NHÓM:**
{chr(10).join(article_context) if article_context else "Không có tóm tắt"}

**CÁC THỰC THỂ CHÍNH:**
{chr(10).join(entity_context) if entity_context else "Không có thực thể"}

**YÊU CẦU:**
Viết một BÁO CÁO TỔNG HỢP (Community Report) cho nhóm điều khoản này, bao gồm:

1. **Chủ đề chính**: Nhóm này quy định về vấn đề gì?
2. **Nội dung cốt lõi**: Tóm tắt các quy định chính trong 2-3 câu
3. **Mối liên hệ**: Các điều khoản liên kết với nhau như thế nào?
4. **Đối tượng áp dụng**: Ai chịu ảnh hưởng bởi các quy định này?
5. **Điểm quan trọng**: 2-3 điểm cần lưu ý khi áp dụng

Viết thành một đoạn văn mạch lạc (150-250 từ), không dùng bullet points.
Sử dụng ngôn ngữ chuyên nghiệp, dễ hiểu."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Bạn là chuyên gia phân tích văn bản pháp luật giáo dục Việt Nam."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 800
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"LLM API error {response.status_code}: {response.text[:200]}")
                    return ""
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return ""


class CommunityDetector:
    """Detect cross-chapter communities using Leiden algorithm or Entity co-occurrence"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
    def close(self):
        self.driver.close()
    
    def build_article_graph(self) -> dict:
        """
        Build a graph where Articles are connected if they share Entities.
        
        Returns:
            Dict with 'nodes' (Article IDs) and 'edges' (pairs of connected Articles)
        """
        with self.driver.session() as session:
            # Get all Articles
            articles = session.run("""
                MATCH (a:Article)
                RETURN a.id as id, a.article_number as num
                ORDER BY a.article_number
            """)
            nodes = {r['id']: r['num'] for r in articles}
            
            # Find Articles that share Entities (co-mention)
            edges = session.run("""
                MATCH (a1:Article)-[:MENTIONS]->(e:Entity)<-[:MENTIONS]-(a2:Article)
                WHERE a1.id < a2.id
                RETURN a1.id as source, a2.id as target, count(e) as weight
            """)
            edge_list = [(r['source'], r['target'], r['weight']) for r in edges]
            
            print(f"   📊 Graph: {len(nodes)} nodes, {len(edge_list)} edges")
            
            return {'nodes': nodes, 'edges': edge_list}
    
    def detect_communities_leiden(self, graph_data: dict) -> dict:
        """
        Detect communities using Leiden algorithm.
        
        Returns:
            Dict mapping community_id -> list of Article IDs
        """
        if not LEIDEN_AVAILABLE:
            return self.detect_communities_fallback(graph_data)
        
        nodes = list(graph_data['nodes'].keys())
        node_to_idx = {n: i for i, n in enumerate(nodes)}
        
        # Build igraph
        g = ig.Graph()
        g.add_vertices(len(nodes))
        
        edges = []
        weights = []
        for src, tgt, w in graph_data['edges']:
            if src in node_to_idx and tgt in node_to_idx:
                edges.append((node_to_idx[src], node_to_idx[tgt]))
                weights.append(w)
        
        g.add_edges(edges)
        g.es['weight'] = weights
        
        # Run Leiden
        partition = leidenalg.find_partition(
            g, 
            leidenalg.ModularityVertexPartition,
            weights='weight'
        )
        
        # Convert to communities
        communities = defaultdict(list)
        for node_idx, community_id in enumerate(partition.membership):
            article_id = nodes[node_idx]
            communities[community_id].append(article_id)
        
        return dict(communities)
    
    def detect_communities_fallback(self, graph_data: dict) -> dict:
        """
        Fallback community detection using connected components and Entity clustering.
        Groups Articles that share similar Entity types.
        """
        with self.driver.session() as session:
            # Group Articles by dominant Entity type
            result = session.run("""
                MATCH (a:Article)-[:MENTIONS]->(e:Entity)
                WITH a, e.type as entity_type, count(*) as cnt
                ORDER BY cnt DESC
                WITH a, collect(entity_type)[0] as dominant_type
                RETURN dominant_type, collect(a.id) as articles
            """)
            
            communities = {}
            for i, r in enumerate(result):
                if r['dominant_type']:
                    communities[i] = r['articles']
            
            return communities
    
    def label_communities(self, communities: dict) -> dict:
        """
        Generate human-readable labels for each community based on shared Entities.
        Also fetches article summaries for LLM report generation.
        
        Returns:
            Dict mapping community_id -> {articles, label, key_entities, article_summaries}
        """
        labeled = {}
        
        with self.driver.session() as session:
            for comm_id, articles in communities.items():
                if len(articles) < 2:
                    continue  # Skip single-article communities
                
                # Find common entities in this community
                result = session.run("""
                    MATCH (a:Article)-[:MENTIONS]->(e:Entity)
                    WHERE a.id IN $articles
                    WITH e.name as entity, e.type as type, count(DISTINCT a) as article_count
                    WHERE article_count >= 2
                    RETURN entity, type, article_count
                    ORDER BY article_count DESC
                    LIMIT 5
                """, articles=articles)
                
                key_entities = [
                    {"name": r['entity'], "type": r['type'], "count": r['article_count']}
                    for r in result
                ]
                
                # Generate label from top entities
                if key_entities:
                    top_entities = [e['name'] for e in key_entities[:3]]
                    label = f"Cộng đồng: {', '.join(top_entities)}"
                else:
                    label = f"Cộng đồng {comm_id}"
                
                # Get Article titles AND summaries for LLM report
                art_result = session.run("""
                    MATCH (a:Article)
                    WHERE a.id IN $articles
                    RETURN a.id, a.title, a.article_number, a.summary
                    ORDER BY a.article_number
                """, articles=articles)
                
                article_info = [
                    {
                        "id": r['a.id'], 
                        "title": r['a.title'], 
                        "number": r['a.article_number'],
                        "summary": r['a.summary'] or ""
                    }
                    for r in art_result
                ]
                
                labeled[comm_id] = {
                    "label": label,
                    "articles": article_info,
                    "key_entities": key_entities,
                    "size": len(articles),
                    "full_summary": ""  # Will be filled by LLM
                }
        
        return labeled
    
    async def generate_community_reports(self, labeled_communities: dict, llm_client: LLMClient) -> dict:
        """
        Generate LLM-based Community Reports for each community.
        This follows Microsoft GraphRAG standard.
        """
        print("\n5️⃣ Generating Community Reports with LLM...")
        
        for comm_id, data in labeled_communities.items():
            print(f"   📝 Generating report for: {data['label'][:50]}...")
            
            report = await llm_client.generate_community_report(data)
            
            if report:
                data['full_summary'] = report
                print(f"      ✅ Generated ({len(report)} chars)")
            else:
                # Fallback to basic summary
                data['full_summary'] = f"Nhóm gồm {data['size']} điều khoản liên quan đến: {data['label'].replace('Cộng đồng: ', '')}."
                print(f"      ⚠️ Using fallback summary")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        return labeled_communities
    
    def store_communities(self, labeled_communities: dict):
        """Store communities in Neo4j as :Community nodes with full_summary"""
        with self.driver.session() as session:
            # Clear existing communities
            session.run("MATCH (c:Community) DETACH DELETE c")
            
            for comm_id, data in labeled_communities.items():
                # Create Community node with full_summary
                session.run("""
                    CREATE (c:Community {
                        id: $id,
                        label: $label,
                        size: $size,
                        key_entities: $key_entities,
                        full_summary: $full_summary
                    })
                """, 
                    id=f"community_{comm_id}",
                    label=data['label'],
                    size=data['size'],
                    key_entities=json.dumps(data['key_entities'], ensure_ascii=False),
                    full_summary=data.get('full_summary', '')
                )
                
                # Link Articles to Community
                article_ids = [a['id'] for a in data['articles']]
                session.run("""
                    MATCH (c:Community {id: $comm_id})
                    MATCH (a:Article)
                    WHERE a.id IN $article_ids
                    MERGE (a)-[:BELONGS_TO]->(c)
                """, comm_id=f"community_{comm_id}", article_ids=article_ids)
            
            print(f"   ✅ Stored {len(labeled_communities)} communities with reports in Neo4j")
    
    async def run(self, llm_client: LLMClient = None, min_community_size: int = 2):
        """Run the complete community detection pipeline with LLM reports"""
        print("\n" + "=" * 60)
        print("🔍 LEIDEN COMMUNITY DETECTION WITH LLM REPORTS")
        print("=" * 60)
        
        # Step 1: Build graph
        print("\n1️⃣ Building Article co-mention graph...")
        graph_data = self.build_article_graph()
        
        # Step 2: Detect communities
        print("\n2️⃣ Detecting communities...")
        method = "Leiden" if LEIDEN_AVAILABLE else "Entity clustering (fallback)"
        print(f"   Method: {method}")
        communities = self.detect_communities_leiden(graph_data)
        print(f"   Found {len(communities)} raw communities")
        
        # Step 3: Filter and label
        print("\n3️⃣ Labeling communities...")
        labeled = self.label_communities(communities)
        
        # Filter by size
        filtered = {k: v for k, v in labeled.items() if v['size'] >= min_community_size}
        print(f"   Communities with size >= {min_community_size}: {len(filtered)}")
        
        # Step 4: Generate LLM reports (NEW!)
        if llm_client:
            filtered = await self.generate_community_reports(filtered, llm_client)
        else:
            print("\n4️⃣ Skipping LLM reports (no API key provided)")
        
        # Step 5: Store in Neo4j
        print("\n6️⃣ Storing in Neo4j...")
        self.store_communities(filtered)
        
        # Step 6: Report
        print("\n" + "=" * 60)
        print("📊 COMMUNITY REPORTS")
        print("=" * 60)
        
        for comm_id, data in sorted(filtered.items(), key=lambda x: -x[1]['size']):
            print(f"\n{'='*60}")
            print(f"🏘️ {data['label']}")
            print(f"   Size: {data['size']} articles")
            print(f"   Articles: {[a['id'] for a in data['articles']]}")
            
            if data.get('full_summary'):
                print(f"\n   📄 COMMUNITY REPORT:")
                print(f"   {'-'*50}")
                # Print report with wrapping
                report = data['full_summary']
                for line in report.split('\n'):
                    if line.strip():
                        print(f"   {line.strip()}")
                print(f"   {'-'*50}")
        
        return filtered


async def main():
    config = setup_environment()
    
    # Initialize LLM client if API key available
    llm_client = None
    if config.get("openrouter_api_key"):
        llm_client = LLMClient(
            api_key=config["openrouter_api_key"],
            model=config["model"]
        )
        print(f"✅ LLM Client initialized (model: {config['model']})")
    else:
        print("⚠️ No API key found. Community reports will use basic labels.")
    
    detector = CommunityDetector(
        neo4j_uri=config["neo4j_uri"],
        neo4j_user=config["neo4j_user"],
        neo4j_password=config["neo4j_password"]
    )
    
    try:
        communities = await detector.run(llm_client=llm_client, min_community_size=2)
        print(f"\n✅ Community detection complete! Found {len(communities)} communities with reports.")
    finally:
        detector.close()


if __name__ == "__main__":
    asyncio.run(main())
