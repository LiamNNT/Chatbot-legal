"""
GraphRAG Query Engine with Local/Global Routing

This module implements the two-mode query system:
1. LOCAL MODE (Specific queries): "Điều 5 khoản 2 là gì?"
   → Vector Search + Graph Traversal to find specific articles
   
2. GLOBAL MODE (General queries): "Tóm tắt các quy định về xét tốt nghiệp"
   → Use pre-computed summaries at Chapter/Document level

Reference: Microsoft GraphRAG Paper - Query Modes
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from neo4j import GraphDatabase
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryMode(Enum):
    """Query routing modes"""
    LOCAL = "local"      # Specific, detailed questions
    GLOBAL = "global"    # General, summary questions
    HYBRID = "hybrid"    # Both modes combined


@dataclass
class QueryResult:
    """Result from GraphRAG query"""
    mode: QueryMode
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    reasoning: str


class QueryRouter:
    """
    Routes queries to appropriate search mode (Local vs Global).
    
    LOCAL indicators:
    - Specific article references: "Điều X", "Khoản Y"
    - Specific questions: "là gì", "như thế nào", "khi nào"
    - Entity-specific: tên cụ thể, số liệu cụ thể
    
    GLOBAL indicators:
    - Summary requests: "tóm tắt", "tổng quan", "liệt kê"
    - Cross-chapter questions: "toàn bộ", "tất cả", "xuyên suốt"
    - Comparative questions: "so sánh", "khác biệt"
    """
    
    # Patterns indicating LOCAL mode
    LOCAL_PATTERNS = [
        r'điều\s*\d+',           # Điều X
        r'khoản\s*\d+',          # Khoản Y  
        r'mục\s*\d+',            # Mục Z
        r'là\s+gì\??',           # là gì?
        r'như\s+thế\s+nào',      # như thế nào
        r'khi\s+nào',            # khi nào
        r'bao\s+nhiêu',          # bao nhiêu
        r'được\s+không',         # được không
        r'có\s+được',            # có được
        r'điều\s+kiện',          # điều kiện (specific)
        r'quy\s+định\s+về\s+\w+', # quy định về X cụ thể
    ]
    
    # Patterns indicating GLOBAL mode
    GLOBAL_PATTERNS = [
        r'tóm\s*tắt',            # tóm tắt
        r'tổng\s*quan',          # tổng quan
        r'liệt\s*kê',            # liệt kê
        r'tất\s*cả',             # tất cả
        r'toàn\s*bộ',            # toàn bộ
        r'xuyên\s*suốt',         # xuyên suốt
        r'các\s+quy\s+định',     # các quy định (general)
        r'những\s+điểm',         # những điểm
        r'so\s*sánh',            # so sánh
        r'khác\s*biệt',          # khác biệt
        r'quyền\s+và\s+nghĩa\s+vụ',  # quyền và nghĩa vụ
        r'trong\s+văn\s+bản',    # trong văn bản này
        r'chương\s+nào',         # chương nào
    ]
    
    def route(self, query: str) -> Tuple[QueryMode, float, str]:
        """
        Determine the best query mode for the given query.
        
        Returns:
            Tuple of (mode, confidence, reasoning)
        """
        query_lower = query.lower()
        
        local_score = 0
        global_score = 0
        local_matches = []
        global_matches = []
        
        # Check LOCAL patterns
        for pattern in self.LOCAL_PATTERNS:
            if re.search(pattern, query_lower):
                local_score += 1
                local_matches.append(pattern)
        
        # Check GLOBAL patterns
        for pattern in self.GLOBAL_PATTERNS:
            if re.search(pattern, query_lower):
                global_score += 1
                global_matches.append(pattern)
        
        # Specific article reference is strong LOCAL indicator
        if re.search(r'điều\s*\d+', query_lower):
            local_score += 2
        
        # "Tóm tắt" or "tổng quan" is strong GLOBAL indicator
        if re.search(r'tóm\s*tắt|tổng\s*quan', query_lower):
            global_score += 2
        
        # Determine mode
        total = local_score + global_score
        if total == 0:
            # Default to LOCAL for simple questions
            return (QueryMode.LOCAL, 0.5, "Default to local mode")
        
        if local_score > global_score:
            confidence = local_score / total
            reasoning = f"LOCAL patterns matched: {local_matches}"
            return (QueryMode.LOCAL, confidence, reasoning)
        elif global_score > local_score:
            confidence = global_score / total
            reasoning = f"GLOBAL patterns matched: {global_matches}"
            return (QueryMode.GLOBAL, confidence, reasoning)
        else:
            return (QueryMode.HYBRID, 0.5, "Equal LOCAL and GLOBAL signals")


class GraphRAGQueryEngine:
    """
    GraphRAG Query Engine supporting both Local and Global search modes.
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 openrouter_api_key: str, model: str = "openai/gpt-4o-mini"):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.api_key = openrouter_api_key
        self.model = model
        self.router = QueryRouter()
        
    async def query(self, query: str, mode: Optional[QueryMode] = None) -> QueryResult:
        """
        Execute a query using GraphRAG.
        
        Args:
            query: The user's question
            mode: Optional forced mode, otherwise auto-detected
        """
        # Auto-detect mode if not specified
        if mode is None:
            detected_mode, confidence, reasoning = self.router.route(query)
            logger.info(f"Query routing: {detected_mode.value} (confidence: {confidence:.2f})")
            logger.info(f"   Reasoning: {reasoning}")
        else:
            detected_mode = mode
            confidence = 1.0
            reasoning = "Mode specified by user"
        
        # Execute appropriate search
        if detected_mode == QueryMode.LOCAL:
            return await self._local_search(query)
        elif detected_mode == QueryMode.GLOBAL:
            return await self._global_search(query)
        else:
            return await self._hybrid_search(query)
    
    async def _local_search(self, query: str) -> QueryResult:
        """
        Local search: Vector search + Graph traversal for specific answers.
        """
        logger.info("🔍 Executing LOCAL search...")
        
        # Extract article reference if present
        article_match = re.search(r'điều\s*(\d+)', query.lower())
        target_article = int(article_match.group(1)) if article_match else None
        
        with self.driver.session() as session:
            if target_article:
                # Direct article lookup
                result = session.run("""
                    MATCH (a:Article)
                    WHERE a.article_number = $num OR a.id = $id
                    OPTIONAL MATCH (a)-[:MENTIONS]->(e:Entity)
                    OPTIONAL MATCH (c:Chapter)-[:HAS_ARTICLE]->(a)
                    RETURN a.id as id, a.title as title, a.text as text, 
                           a.summary as summary, a.key_rules as key_rules,
                           c.name as chapter_name, c.title as chapter_title,
                           collect(DISTINCT {name: e.name, type: e.type}) as entities
                """, num=target_article, id=f"Điều {target_article}")
                
            else:
                # Keyword-based search in articles
                keywords = self._extract_keywords(query)
                result = session.run("""
                    MATCH (a:Article)
                    WHERE any(kw IN $keywords WHERE 
                        toLower(a.text) CONTAINS toLower(kw) OR
                        toLower(a.title) CONTAINS toLower(kw) OR
                        toLower(a.summary) CONTAINS toLower(kw)
                    )
                    OPTIONAL MATCH (a)-[:MENTIONS]->(e:Entity)
                    OPTIONAL MATCH (c:Chapter)-[:HAS_ARTICLE]->(a)
                    RETURN a.id as id, a.title as title, a.text as text,
                           a.summary as summary, a.key_rules as key_rules,
                           c.name as chapter_name, c.title as chapter_title,
                           collect(DISTINCT {name: e.name, type: e.type}) as entities
                    LIMIT 5
                """, keywords=keywords)
            
            articles = list(result)
        
        if not articles:
            return QueryResult(
                mode=QueryMode.LOCAL,
                answer="Không tìm thấy thông tin phù hợp với câu hỏi.",
                sources=[],
                confidence=0.0,
                reasoning="No matching articles found"
            )
        
        # Build context and generate answer
        context = self._build_local_context(articles)
        answer = await self._generate_answer(query, context, "local")
        
        sources = [{
            "id": a['id'],
            "title": a['title'],
            "chapter": f"{a['chapter_name']}: {a['chapter_title']}" if a['chapter_name'] else "Unknown",
            "summary": a['summary'][:200] if a['summary'] else None
        } for a in articles]
        
        return QueryResult(
            mode=QueryMode.LOCAL,
            answer=answer,
            sources=sources,
            confidence=0.85,
            reasoning=f"Found {len(articles)} relevant articles"
        )
    
    async def _global_search(self, query: str) -> QueryResult:
        """
        Global search: Use Community Reports + Chapter/Document summaries.
        
        This follows Microsoft GraphRAG standard:
        1. Search Community summaries (cross-chapter insights)
        2. Fall back to Chapter/Document summaries
        3. Synthesize comprehensive answer
        """
        logger.info("🌐 Executing GLOBAL search...")
        
        with self.driver.session() as session:
            # Step 1: Get relevant Community Reports (PRIMARY for global queries)
            # Match communities whose label or full_summary contains query keywords
            keywords = self._extract_keywords(query)
            
            communities_result = session.run("""
                MATCH (c:Community)
                WHERE c.full_summary IS NOT NULL AND c.full_summary <> ''
                WITH c, 
                     [kw IN $keywords WHERE 
                        toLower(c.full_summary) CONTAINS toLower(kw) OR
                        toLower(c.label) CONTAINS toLower(kw)
                     ] as matches
                WHERE size(matches) > 0
                OPTIONAL MATCH (a:Article)-[:BELONGS_TO]->(c)
                RETURN c.id as id, c.label as label, c.full_summary as full_summary,
                       c.size as size, c.key_entities as key_entities,
                       collect(DISTINCT a.id) as article_ids,
                       size(matches) as relevance
                ORDER BY relevance DESC, c.size DESC
            """, keywords=keywords)
            communities = list(communities_result)
            
            # If no keyword match, get all communities
            if not communities:
                communities_result = session.run("""
                    MATCH (c:Community)
                    WHERE c.full_summary IS NOT NULL AND c.full_summary <> ''
                    OPTIONAL MATCH (a:Article)-[:BELONGS_TO]->(c)
                    RETURN c.id as id, c.label as label, c.full_summary as full_summary,
                           c.size as size, c.key_entities as key_entities,
                           collect(DISTINCT a.id) as article_ids,
                           0 as relevance
                    ORDER BY c.size DESC
                """)
                communities = list(communities_result)
            
            # Step 2: Get document summary (TOP level context)
            doc_result = session.run("""
                MATCH (d:Document)
                RETURN d.title as title, d.summary as summary, d.key_points as key_points
                LIMIT 1
            """)
            doc = doc_result.single()
            
            # Step 3: Get chapter summaries (MIDDLE level context)
            chapters_result = session.run("""
                MATCH (c:Chapter)
                WHERE c.summary IS NOT NULL AND c.summary <> ''
                RETURN c.name as name, c.title as title, c.summary as summary,
                       c.key_topics as key_topics
                ORDER BY c.name
            """)
            chapters = list(chapters_result)
        
        # Build global context prioritizing Community Reports
        context = self._build_global_context_with_communities(doc, chapters, communities, query)
        answer = await self._generate_answer(query, context, "global")
        
        # Build sources from communities and chapters
        sources = []
        
        # Add community sources first (most relevant for global queries)
        for comm in communities[:3]:
            sources.append({
                "type": "community",
                "id": comm['id'],
                "label": comm['label'],
                "size": comm['size'],
                "articles": comm['article_ids'][:5],
                "summary_preview": comm['full_summary'][:200] if comm['full_summary'] else None
            })
        
        # Add chapter sources
        for ch in chapters[:3]:
            sources.append({
                "type": "chapter",
                "name": ch['name'],
                "title": ch['title'],
                "summary": ch['summary'][:200] if ch['summary'] else None
            })
        
        return QueryResult(
            mode=QueryMode.GLOBAL,
            answer=answer,
            sources=sources,
            confidence=0.9,
            reasoning=f"Used {len(communities)} community reports, document summary, and {len(chapters)} chapter summaries"
        )
    
    async def _hybrid_search(self, query: str) -> QueryResult:
        """
        Hybrid search: Combine both Local and Global results.
        """
        logger.info("🔄 Executing HYBRID search...")
        
        # Run both searches
        local_result = await self._local_search(query)
        global_result = await self._global_search(query)
        
        # Combine contexts
        combined_context = f"""
=== THÔNG TIN CHI TIẾT (Local) ===
{local_result.answer}

=== THÔNG TIN TỔNG QUAN (Global) ===
{global_result.answer}
"""
        
        # Generate final answer
        final_prompt = f"""Dựa trên thông tin chi tiết và tổng quan sau, hãy trả lời câu hỏi:

Câu hỏi: {query}

{combined_context}

Hãy tổng hợp thông tin và trả lời đầy đủ, kết hợp cả chi tiết cụ thể và bối cảnh tổng quan."""

        answer = await self._call_llm(final_prompt)
        
        return QueryResult(
            mode=QueryMode.HYBRID,
            answer=answer,
            sources=local_result.sources + global_result.sources,
            confidence=0.85,
            reasoning="Combined local and global search"
        )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove common words
        stopwords = {'là', 'gì', 'như', 'thế', 'nào', 'có', 'được', 'không', 
                     'và', 'của', 'cho', 'khi', 'trong', 'về', 'để', 'với'}
        
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Add important phrases
        phrases = re.findall(r'(sinh viên|học phí|tín chỉ|điểm|tốt nghiệp|học kỳ|đăng ký|cảnh cáo)', 
                           query.lower())
        keywords.extend(phrases)
        
        return list(set(keywords))
    
    def _build_local_context(self, articles: List[Dict]) -> str:
        """Build context from local search results"""
        context_parts = []
        
        for art in articles:
            part = f"""
### {art['id']}: {art['title']}
**Chương:** {art['chapter_name']} - {art['chapter_title']}
**Tóm tắt:** {art['summary'] or 'Chưa có'}
**Nội dung:**
{art['text'][:2000]}...

**Quy tắc chính:** {', '.join(art['key_rules']) if art['key_rules'] else 'Chưa trích xuất'}
"""
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def _build_global_context(self, doc: Dict, chapters: List[Dict], query: str) -> str:
        """Build context from global summaries"""
        context = f"""
## VĂN BẢN: {doc['title'] if doc else 'Quy chế đào tạo'}

**Tóm tắt văn bản:**
{doc['summary'] if doc and doc['summary'] else 'Chưa có tóm tắt'}

**Điểm chính:**
{', '.join(doc['key_points']) if doc and doc['key_points'] else 'Chưa trích xuất'}

---
## CÁC CHƯƠNG:
"""
        
        for ch in chapters:
            if ch['summary']:
                context += f"""
### {ch['name']}: {ch['title']}
**Tóm tắt:** {ch['summary']}
**Chủ đề chính:** {', '.join(ch['key_topics']) if ch['key_topics'] else 'N/A'}
"""
        
        return context
    
    def _build_global_context_with_communities(self, doc: Dict, chapters: List[Dict], 
                                                communities: List[Dict], query: str) -> str:
        """
        Build context prioritizing Community Reports for global queries.
        
        Structure:
        1. Community Reports (cross-chapter insights) - PRIMARY
        2. Document summary (top-level overview)
        3. Chapter summaries (structural context)
        """
        context_parts = []
        
        # Part 1: Community Reports (MOST IMPORTANT for global queries)
        if communities:
            context_parts.append("## 🏘️ BÁO CÁO THEO CHỦ ĐỀ (Community Reports)")
            context_parts.append("Các nhóm điều khoản liên quan được phát hiện qua phân tích đồ thị:\n")
            
            for comm in communities[:4]:  # Top 4 most relevant
                context_parts.append(f"""
### {comm['label']}
**Số điều khoản:** {comm['size']}
**Các điều:** {', '.join(comm['article_ids'][:10])}

**Báo cáo tổng hợp:**
{comm['full_summary']}
""")
        
        # Part 2: Document Overview
        context_parts.append("\n---\n## 📄 TỔNG QUAN VĂN BẢN")
        if doc:
            context_parts.append(f"""
**Tên văn bản:** {doc['title']}
**Tóm tắt:** {doc['summary'] if doc['summary'] else 'Chưa có'}
**Điểm chính:** {', '.join(doc['key_points']) if doc['key_points'] else 'N/A'}
""")
        
        # Part 3: Chapter Structure (brief)
        if chapters:
            context_parts.append("\n---\n## 📚 CẤU TRÚC CHƯƠNG")
            for ch in chapters:
                if ch['summary']:
                    context_parts.append(f"""
**{ch['name']}: {ch['title']}**
{ch['summary'][:300]}...
""")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(self, query: str, context: str, mode: str) -> str:
        """Generate answer using LLM"""
        if mode == "local":
            system_prompt = """Bạn là trợ lý pháp lý chuyên về quy chế đào tạo đại học.
Trả lời câu hỏi dựa trên thông tin cụ thể được cung cấp.
Trích dẫn điều khoản và số liệu chính xác."""
        else:
            system_prompt = """Bạn là trợ lý pháp lý chuyên về quy chế đào tạo đại học.
Trả lời câu hỏi bằng cách tổng hợp thông tin từ nhiều chương/điều.
Cung cấp cái nhìn tổng quan và toàn diện."""
        
        prompt = f"""Dựa trên ngữ cảnh sau, trả lời câu hỏi:

{context}

---
Câu hỏi: {query}

Trả lời (bằng tiếng Việt, rõ ràng và chi tiết):"""

        return await self._call_llm(prompt, system_prompt)
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"LLM API error: {response.status_code}")
                    return "Lỗi khi tạo câu trả lời."
                    
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "Lỗi khi tạo câu trả lời."
    
    def close(self):
        """Close Neo4j driver"""
        self.driver.close()


# Test function
async def test_query_engine():
    """Test the query engine with sample queries"""
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    engine = GraphRAGQueryEngine(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "uitchatbot"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/gpt-4o-mini"
    )
    
    test_queries = [
        # LOCAL queries
        ("Điều 5 quy định về học kỳ như thế nào?", QueryMode.LOCAL),
        ("Sinh viên bị cảnh cáo học vụ khi nào?", QueryMode.LOCAL),
        
        # GLOBAL queries
        ("Tóm tắt các quy định về xét tốt nghiệp trong văn bản này", QueryMode.GLOBAL),
        ("Quyền và nghĩa vụ của sinh viên xuyên suốt quá trình đào tạo là gì?", QueryMode.GLOBAL),
    ]
    
    print("=" * 80)
    print("🧪 TESTING GRAPHRAG QUERY ENGINE")
    print("=" * 80)
    
    for query, expected_mode in test_queries:
        print(f"\n📝 Query: {query}")
        print(f"   Expected mode: {expected_mode.value}")
        
        result = await engine.query(query)
        
        print(f"   Actual mode: {result.mode.value}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Sources: {len(result.sources)}")
        print(f"   Answer preview: {result.answer[:200]}...")
        print("-" * 40)
    
    engine.close()


if __name__ == "__main__":
    asyncio.run(test_query_engine())
