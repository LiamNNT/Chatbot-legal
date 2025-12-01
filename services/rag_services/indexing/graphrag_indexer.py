"""
GraphRAG Indexer - Bottom-Up Summarization Pipeline

This module implements the GraphRAG indexing strategy with:
1. Granular Chunking: Document → Chapter → Article (not fixed-size)
2. Bottom-Up Summarization: Article summaries → Chapter summaries → Document summary
3. Entity Extraction at each level
4. Community-based organization using Chapter structure

Reference: Microsoft GraphRAG Paper
"""

import asyncio
import json
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime

from neo4j import GraphDatabase
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Represents a legal article (Điều)"""
    id: str
    number: int
    title: str
    text: str
    chapter: str
    summary: str = ""
    entities: List[Dict[str, str]] = field(default_factory=list)
    key_rules: List[str] = field(default_factory=list)


@dataclass
class Chapter:
    """Represents a chapter (Chương)"""
    id: str
    number: int
    name: str
    title: str
    articles: List[Article] = field(default_factory=list)
    summary: str = ""
    key_topics: List[str] = field(default_factory=list)


@dataclass 
class Document:
    """Represents a legal document (Văn bản)"""
    id: str
    filename: str
    title: str
    chapters: List[Chapter] = field(default_factory=list)
    summary: str = ""
    key_points: List[str] = field(default_factory=list)


class LLMSummarizer:
    """LLM-based summarizer using OpenRouter API"""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def summarize_article(self, article: Article) -> Tuple[str, List[Dict], List[str]]:
        """
        Summarize an article and extract entities and key rules.
        
        Returns:
            Tuple of (summary, entities, key_rules)
        """
        prompt = f"""Phân tích điều khoản pháp quy sau và trả về JSON:

**{article.id}: {article.title}**
{article.text}

Trả về JSON với format:
{{
    "summary": "Tóm tắt ngắn gọn (2-3 câu) nội dung chính của điều này",
    "entities": [
        {{"name": "tên thực thể", "type": "loại (Person/Course/Certificate/Duration/Score/Penalty/...)"}}
    ],
    "key_rules": ["Quy tắc/điều kiện quan trọng 1", "Quy tắc 2", ...]
}}

Chỉ trả về JSON, không có text khác."""

        response = await self._call_llm(prompt)
        try:
            data = json.loads(response)
            return (
                data.get("summary", ""),
                data.get("entities", []),
                data.get("key_rules", [])
            )
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON for {article.id}, using fallback")
            return (response[:500], [], [])
    
    async def summarize_chapter(self, chapter: Chapter, article_summaries: List[str]) -> Tuple[str, List[str]]:
        """
        Summarize a chapter based on its article summaries.
        
        Returns:
            Tuple of (summary, key_topics)
        """
        articles_text = "\n".join([
            f"- {art.id}: {art.summary}" 
            for art in chapter.articles if art.summary
        ])
        
        prompt = f"""Tóm tắt chương sau dựa trên các điều khoản:

**{chapter.name}: {chapter.title}**

Các điều trong chương:
{articles_text}

Trả về JSON:
{{
    "summary": "Tóm tắt tổng quan chương (3-5 câu), nêu rõ mục đích và nội dung chính",
    "key_topics": ["Chủ đề chính 1", "Chủ đề 2", ...]
}}

Chỉ trả về JSON."""

        response = await self._call_llm(prompt)
        try:
            data = json.loads(response)
            return (data.get("summary", ""), data.get("key_topics", []))
        except json.JSONDecodeError:
            return (response[:500], [])
    
    async def summarize_document(self, document: Document, chapter_summaries: List[str]) -> Tuple[str, List[str]]:
        """
        Summarize a document based on its chapter summaries.
        
        Returns:
            Tuple of (summary, key_points)
        """
        chapters_text = "\n".join([
            f"- {ch.name} ({ch.title}): {ch.summary}"
            for ch in document.chapters if ch.summary
        ])
        
        prompt = f"""Tóm tắt văn bản pháp quy sau dựa trên các chương:

**{document.title}**
File: {document.filename}

Các chương:
{chapters_text}

Trả về JSON:
{{
    "summary": "Tóm tắt tổng quan văn bản (5-7 câu), nêu rõ phạm vi áp dụng, đối tượng và các quy định chính",
    "key_points": ["Điểm quan trọng 1", "Điểm 2", ...]
}}

Chỉ trả về JSON."""

        response = await self._call_llm(prompt)
        try:
            data = json.loads(response)
            return (data.get("summary", ""), data.get("key_points", []))
        except json.JSONDecodeError:
            return (response[:500], [])
    
    async def _call_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Call LLM API with retry logic"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam. Luôn trả về JSON hợp lệ."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        for attempt in range(max_retries):
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
                        logger.warning(f"API error {response.status_code}: {response.text}")
                        
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)
        
        return ""


class PDFStructureParser:
    """Parse PDF into hierarchical structure (Document → Chapter → Article)"""
    
    # Chapter patterns for Vietnamese legal documents
    CHAPTER_PATTERN = re.compile(
        r'(?:CHƯƠNG|Chương)\s*(\d+|[IVX]+)[.:]\s*(.+?)(?=\n|$)',
        re.IGNORECASE | re.MULTILINE
    )
    
    # Article patterns
    ARTICLE_PATTERN = re.compile(
        r'(?:Điều|ĐIỀU)\s*(\d+)[.:]?\s*(.+?)(?=\n|$)',
        re.IGNORECASE | re.MULTILINE
    )
    
    def __init__(self):
        self.chapter_titles = {
            1: "QUY ĐỊNH CHUNG",
            2: "TỔ CHỨC ĐÀO TẠO",
            3: "KIỂM TRA VÀ THI HỌC PHẦN",
            4: "ỨNG DỤNG CÔNG NGHỆ THÔNG TIN TRONG TỔ CHỨC - QUẢN LÝ ĐÀO TẠO",
            5: "THỰC TẬP, KHÓA LUẬN TỐT NGHIỆP VÀ CÔNG NHẬN TỐT NGHIỆP",
            6: "ĐIỀU KHOẢN THI HÀNH"
        }
        
        # Article to chapter mapping for UIT regulation
        self.article_chapter_map = {
            # Chương 1: Điều 1-9
            **{i: 1 for i in range(1, 10)},
            # Chương 2: Điều 10-19  
            **{i: 2 for i in range(10, 20)},
            # Chương 3: Điều 20-27
            **{i: 3 for i in range(20, 28)},
            # Chương 4: Điều 28-30
            **{i: 4 for i in range(28, 31)},
            # Chương 5: Điều 31-34
            **{i: 5 for i in range(31, 35)},
            # Chương 6: Điều 35+
            **{i: 6 for i in range(35, 40)},
        }
    
    def parse_from_neo4j(self, driver) -> Document:
        """Parse existing Neo4j data into Document structure"""
        document = Document(
            id="790-qd-dhcntt",
            filename="790-qd-dhcntt_28-9-22_quy_che_dao_tao.pdf",
            title="Quy chế đào tạo trình độ đại học - Trường ĐH Công nghệ Thông tin"
        )
        
        # Create chapters
        chapters_dict = {}
        for ch_num, ch_title in self.chapter_titles.items():
            chapter = Chapter(
                id=f"chapter_{ch_num}",
                number=ch_num,
                name=f"Chương {ch_num}",
                title=ch_title
            )
            chapters_dict[ch_num] = chapter
        
        # Load articles from Neo4j
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Article)
                RETURN a.id as id, a.article_number as number, a.title as title, 
                       a.text as text, a.chapter as chapter
                ORDER BY a.article_number
            """)
            
            for record in result:
                art_num = record['number'] or 0
                ch_num = self.article_chapter_map.get(art_num, 1)
                
                article = Article(
                    id=record['id'] or f"Điều {art_num}",
                    number=art_num,
                    title=record['title'] or "",
                    text=record['text'] or "",
                    chapter=f"Chương {ch_num}"
                )
                
                if ch_num in chapters_dict:
                    chapters_dict[ch_num].articles.append(article)
        
        # Add chapters to document
        document.chapters = [chapters_dict[i] for i in sorted(chapters_dict.keys())]
        
        return document


class GraphRAGIndexer:
    """
    Main GraphRAG Indexer implementing Bottom-Up Summarization.
    
    Pipeline:
    1. Parse PDF into hierarchical structure
    2. Generate Article summaries (Level 3) - Bottom
    3. Generate Chapter summaries (Level 2) - Middle
    4. Generate Document summary (Level 1) - Top
    5. Store everything in Neo4j with proper relationships
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, 
                 openrouter_api_key: str, model: str = "openai/gpt-4o-mini"):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.summarizer = LLMSummarizer(openrouter_api_key, model)
        self.parser = PDFStructureParser()
        
    async def build_index(self, clear_existing: bool = True) -> Document:
        """
        Build the complete GraphRAG index.
        
        Args:
            clear_existing: Whether to clear existing summaries
        """
        logger.info("=" * 60)
        logger.info("🚀 Starting GraphRAG Indexing Pipeline")
        logger.info("=" * 60)
        
        # Step 1: Parse existing data into structure
        logger.info("\n📄 Step 1: Parsing document structure from Neo4j...")
        document = self.parser.parse_from_neo4j(self.driver)
        logger.info(f"   Found {len(document.chapters)} chapters")
        for ch in document.chapters:
            logger.info(f"   - {ch.name}: {len(ch.articles)} articles")
        
        # Step 2: Clear existing summaries if requested
        if clear_existing:
            logger.info("\n🧹 Clearing existing summaries...")
            self._clear_summaries()
        
        # Step 3: Generate Article summaries (Bottom level)
        logger.info("\n📝 Step 2: Generating Article summaries (Level 3)...")
        await self._generate_article_summaries(document)
        
        # Step 4: Generate Chapter summaries (Middle level)
        logger.info("\n📚 Step 3: Generating Chapter summaries (Level 2)...")
        await self._generate_chapter_summaries(document)
        
        # Step 5: Generate Document summary (Top level)
        logger.info("\n📖 Step 4: Generating Document summary (Level 1)...")
        await self._generate_document_summary(document)
        
        # Step 6: Store in Neo4j
        logger.info("\n💾 Step 5: Storing in Neo4j...")
        await self._store_in_neo4j(document)
        
        logger.info("\n✅ GraphRAG Indexing Complete!")
        return document
    
    def _clear_summaries(self):
        """Clear existing summary properties"""
        with self.driver.session() as session:
            session.run("MATCH (a:Article) REMOVE a.summary, a.entities_json, a.key_rules")
            session.run("MATCH (c:Chapter) REMOVE c.summary, c.key_topics")
            session.run("MATCH (d:Document) DETACH DELETE d")
    
    async def _generate_article_summaries(self, document: Document):
        """Generate summaries for all articles"""
        total_articles = sum(len(ch.articles) for ch in document.chapters)
        processed = 0
        
        for chapter in document.chapters:
            for article in chapter.articles:
                if not article.text:
                    continue
                    
                processed += 1
                logger.info(f"   [{processed}/{total_articles}] Processing {article.id}...")
                
                try:
                    summary, entities, key_rules = await self.summarizer.summarize_article(article)
                    article.summary = summary
                    article.entities = entities
                    article.key_rules = key_rules
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"   Error processing {article.id}: {e}")
    
    async def _generate_chapter_summaries(self, document: Document):
        """Generate summaries for all chapters"""
        for i, chapter in enumerate(document.chapters):
            if not chapter.articles:
                continue
                
            logger.info(f"   [{i+1}/{len(document.chapters)}] Processing {chapter.name}...")
            
            try:
                article_summaries = [a.summary for a in chapter.articles if a.summary]
                summary, key_topics = await self.summarizer.summarize_chapter(chapter, article_summaries)
                chapter.summary = summary
                chapter.key_topics = key_topics
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   Error processing {chapter.name}: {e}")
    
    async def _generate_document_summary(self, document: Document):
        """Generate summary for the document"""
        try:
            chapter_summaries = [ch.summary for ch in document.chapters if ch.summary]
            summary, key_points = await self.summarizer.summarize_document(document, chapter_summaries)
            document.summary = summary
            document.key_points = key_points
            
        except Exception as e:
            logger.error(f"   Error processing document summary: {e}")
    
    async def _store_in_neo4j(self, document: Document):
        """Store the indexed document in Neo4j"""
        with self.driver.session() as session:
            # Create Document node
            session.run("""
                MERGE (d:Document {id: $id})
                SET d.filename = $filename,
                    d.title = $title,
                    d.summary = $summary,
                    d.key_points = $key_points,
                    d.indexed_at = datetime()
            """, 
                id=document.id,
                filename=document.filename,
                title=document.title,
                summary=document.summary,
                key_points=document.key_points
            )
            
            # Update Chapters
            for chapter in document.chapters:
                session.run("""
                    MATCH (c:Chapter {name: $name})
                    SET c.summary = $summary,
                        c.key_topics = $key_topics
                """,
                    name=chapter.name,
                    summary=chapter.summary,
                    key_topics=chapter.key_topics
                )
                
                # Create Document-Chapter relationship
                session.run("""
                    MATCH (d:Document {id: $doc_id})
                    MATCH (c:Chapter {name: $chapter_name})
                    MERGE (d)-[:HAS_CHAPTER]->(c)
                """,
                    doc_id=document.id,
                    chapter_name=chapter.name
                )
            
            # Update Articles
            for chapter in document.chapters:
                for article in chapter.articles:
                    session.run("""
                        MATCH (a:Article {id: $id})
                        SET a.summary = $summary,
                            a.entities_json = $entities_json,
                            a.key_rules = $key_rules
                    """,
                        id=article.id,
                        summary=article.summary,
                        entities_json=json.dumps(article.entities, ensure_ascii=False),
                        key_rules=article.key_rules
                    )
                    
                    # Create Entity nodes and relationships
                    for entity in article.entities:
                        session.run("""
                            MERGE (e:Entity {name: $name, type: $type})
                            WITH e
                            MATCH (a:Article {id: $article_id})
                            MERGE (a)-[:MENTIONS]->(e)
                        """,
                            name=entity.get('name', ''),
                            type=entity.get('type', 'Unknown'),
                            article_id=article.id
                        )
            
            logger.info("   ✅ All data stored in Neo4j")
    
    def close(self):
        """Close the Neo4j driver"""
        self.driver.close()


async def main():
    """Main entry point for building GraphRAG index"""
    from dotenv import load_dotenv
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    # Get configuration
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "uitchatbot")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if not openrouter_key:
        logger.error("OPENROUTER_API_KEY not found in environment")
        return
    
    # Create indexer and build index
    indexer = GraphRAGIndexer(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        openrouter_api_key=openrouter_key,
        model="openai/gpt-4o-mini"
    )
    
    try:
        document = await indexer.build_index(clear_existing=True)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 INDEXING RESULTS")
        print("=" * 60)
        print(f"\n📄 Document: {document.title}")
        print(f"   Summary: {document.summary[:200]}..." if document.summary else "   No summary")
        
        for chapter in document.chapters:
            print(f"\n📁 {chapter.name}: {chapter.title}")
            print(f"   Summary: {chapter.summary[:150]}..." if chapter.summary else "   No summary")
            print(f"   Articles: {len(chapter.articles)}")
            
    finally:
        indexer.close()


if __name__ == "__main__":
    asyncio.run(main())
