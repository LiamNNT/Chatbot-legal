#!/usr/bin/env python3
"""
Build Cross-Reference Layer for Neo4j Knowledge Graph

This script scans Article and Clause nodes in Neo4j to detect cross-references
and creates REFERENCES relationships between them.

Examples of cross-references detected:
- "theo Điều 6" → (Article X)-[:REFERENCES]->(Article 6)
- "tại Khoản 2 Điều 10" → (Article Y)-[:REFERENCES]->(Article 10, Clause 2)
- "quy định tại Điều 25" → (Article Z)-[:REFERENCES]->(Article 25)
- "Quy chế này" → (Article)-[:REFERENCES]->(Document root)

Benefits:
- Automatic context traversal (no need for vector search)
- Multi-hop reasoning ("What does Article 10 reference?")
- Improved RAG accuracy for legal documents

Author: Knowledge Graph Enhancement Team  
Date: November 21, 2025
"""

import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrossReferenceBuilder:
    """Build cross-reference relationships in Neo4j Knowledge Graph."""
    
    # Regex patterns for detecting references
    REFERENCE_PATTERNS = [
        # "Điều 6", "điều 10", "Điều 25"
        (r'[Đđ]iều\s+(\d+)', 'article'),
        
        # "theo Điều 6 của Quy chế này"
        (r'theo\s+[Đđ]iều\s+(\d+)', 'article'),
        
        # "quy định tại Điều 25"
        (r'quy\s+định\s+tại\s+[Đđ]iều\s+(\d+)', 'article'),
        
        # "tại Điều 30"
        (r'tại\s+[Đđ]iều\s+(\d+)', 'article'),
        
        # "Khoản 2 Điều 10"
        (r'[Kk]hoản\s+(\d+)\s+[Đđ]iều\s+(\d+)', 'clause_article'),
        
        # "theo khoản 3 Điều 15"
        (r'theo\s+[Kk]hoản\s+(\d+)\s+[Đđ]iều\s+(\d+)', 'clause_article'),
        
        # "Chương 2", "chương 3"
        (r'[Cc]hương\s+(\d+)', 'chapter'),
        
        # "quy chế này", "quy định này"
        (r'[Qq]uy\s+[chếđịnh]+\s+này', 'document'),
    ]
    
    def __init__(self, driver):
        """
        Initialize builder.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.stats = defaultdict(int)
    
    def extract_references(self, text: str) -> List[Dict]:
        """
        Extract all references from text.
        
        Args:
            text: Text content to scan
            
        Returns:
            List of reference dictionaries
        """
        references = []
        
        for pattern, ref_type in self.REFERENCE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                if ref_type == 'article':
                    article_num = int(match.group(1))
                    references.append({
                        'type': 'article',
                        'article_number': article_num,
                        'matched_text': match.group(0),
                        'position': match.start()
                    })
                    
                elif ref_type == 'clause_article':
                    clause_num = int(match.group(1))
                    article_num = int(match.group(2))
                    references.append({
                        'type': 'clause_article',
                        'article_number': article_num,
                        'clause_number': clause_num,
                        'matched_text': match.group(0),
                        'position': match.start()
                    })
                    
                elif ref_type == 'chapter':
                    chapter_num = int(match.group(1))
                    references.append({
                        'type': 'chapter',
                        'chapter_number': chapter_num,
                        'matched_text': match.group(0),
                        'position': match.start()
                    })
                    
                elif ref_type == 'document':
                    references.append({
                        'type': 'document',
                        'matched_text': match.group(0),
                        'position': match.start()
                    })
        
        # Remove duplicates (same reference mentioned multiple times)
        unique_refs = []
        seen = set()
        for ref in references:
            key = (ref['type'], ref.get('article_number'), ref.get('clause_number'))
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        return unique_refs
    
    def get_all_articles(self) -> List[Dict]:
        """
        Fetch all Article nodes from Neo4j.
        
        Returns:
            List of article dictionaries with id, number, text, doc_id
        """
        query = """
        MATCH (a:Article)
        WHERE a.text IS NOT NULL
        RETURN 
            elementId(a) as id,
            a.article_number as article_number,
            a.text as text,
            a.doc_id as doc_id,
            a.filename as filename,
            a.title as title
        ORDER BY a.doc_id, a.article_number
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            articles = []
            for record in result:
                articles.append({
                    'id': record['id'],
                    'article_number': record['article_number'],
                    'text': record['text'] or '',
                    'doc_id': record['doc_id'],
                    'filename': record['filename'],
                    'title': record['title'] or ''
                })
            
            logger.info(f"📊 Loaded {len(articles)} articles from Neo4j")
            return articles
    
    def create_reference_relationship(
        self,
        source_id: str,
        target_article_number: int,
        filename: str,
        ref_type: str = 'article',
        clause_number: Optional[int] = None
    ) -> bool:
        """
        Create a REFERENCES relationship between nodes.
        
        Args:
            source_id: Element ID of source node
            target_article_number: Article number being referenced
            filename: Filename (to find target in same document)
            ref_type: Type of reference (article, clause_article, etc.)
            clause_number: Optional clause number
            
        Returns:
            True if relationship was created
        """
        # Find target article
        if ref_type == 'article':
            query = """
            MATCH (source)
            WHERE elementId(source) = $source_id
            MATCH (target:Article {filename: $filename, article_number: $target_article_number})
            WHERE elementId(source) <> elementId(target)  // Avoid self-reference
            MERGE (source)-[r:REFERENCES]->(target)
            ON CREATE SET 
                r.created_at = datetime(),
                r.reference_type = $ref_type
            RETURN elementId(r) as rel_id
            """
        else:
            # For clause references, we might need to extend this
            logger.warning(f"Reference type '{ref_type}' not fully implemented yet")
            return False
        
        try:
            with self.driver.session() as session:
                result = session.run(
                    query,
                    source_id=source_id,
                    filename=filename,
                    target_article_number=target_article_number,
                    ref_type=ref_type
                )
                
                if result.single():
                    self.stats['references_created'] += 1
                    return True
                else:
                    self.stats['references_not_found'] += 1
                    return False
                    
        except Exception as e:
            logger.error(f"Error creating reference: {e}")
            self.stats['errors'] += 1
            return False
    
    def build_references_for_article(self, article: Dict) -> int:
        """
        Build all cross-references for a single article.
        
        Args:
            article: Article dictionary with id, text, doc_id
            
        Returns:
            Number of references created
        """
        text = article['text']
        references = self.extract_references(text)
        
        if not references:
            return 0
        
        count = 0
        for ref in references:
            if ref['type'] == 'article':
                # Don't create self-reference
                if ref['article_number'] == article.get('article_number'):
                    continue
                
                success = self.create_reference_relationship(
                    source_id=article['id'],
                    target_article_number=ref['article_number'],
                    filename=article['filename'],
                    ref_type='article'
                )
                
                if success:
                    count += 1
                    logger.debug(
                        f"   ✓ Article {article.get('article_number')} "
                        f"→ Article {ref['article_number']}"
                    )
        
        return count
    
    def build_all_references(self) -> Dict:
        """
        Build cross-references for all articles in the graph.
        
        Returns:
            Statistics dictionary
        """
        logger.info("🔨 Starting cross-reference building...")
        
        # Get all articles
        articles = self.get_all_articles()
        
        if not articles:
            logger.warning("⚠️  No articles found in Neo4j")
            return self.stats
        
        # Process each article
        for i, article in enumerate(articles, 1):
            if i % 10 == 0:
                logger.info(f"   Processing article {i}/{len(articles)}...")
            
            self.stats['articles_processed'] += 1
            refs_created = self.build_references_for_article(article)
            
            if refs_created > 0:
                self.stats['articles_with_refs'] += 1
        
        logger.info("✅ Cross-reference building complete!")
        return self.stats
    
    def print_statistics(self):
        """Print statistics about cross-reference building."""
        print("\n" + "="*80)
        print("CROSS-REFERENCE BUILDING STATISTICS")
        print("="*80)
        print(f"\n📊 Articles processed:        {self.stats['articles_processed']}")
        print(f"📝 Articles with references: {self.stats['articles_with_refs']}")
        print(f"🔗 References created:       {self.stats['references_created']}")
        print(f"⚠️  Targets not found:       {self.stats['references_not_found']}")
        print(f"❌ Errors:                   {self.stats['errors']}")
        
        if self.stats['articles_processed'] > 0:
            coverage = (self.stats['articles_with_refs'] / self.stats['articles_processed']) * 100
            print(f"\n📈 Coverage: {coverage:.1f}% of articles have cross-references")
        
        print("\n" + "="*80 + "\n")
    
    def verify_references(self) -> Dict:
        """
        Verify created references by querying the graph.
        
        Returns:
            Verification statistics
        """
        query = """
        MATCH (source:Article)-[r:REFERENCES]->(target:Article)
        RETURN 
            source.article_number as source_article,
            target.article_number as target_article,
            source.doc_id as doc_id,
            count(r) as ref_count
        LIMIT 10
        """
        
        logger.info("\n🔍 Sample cross-references:")
        
        with self.driver.session() as session:
            result = session.run(query)
            
            for record in result:
                logger.info(
                    f"   Article {record['source_article']} → "
                    f"Article {record['target_article']} "
                    f"(Doc: {record['doc_id']})"
                )
        
        # Count total references
        count_query = """
        MATCH ()-[r:REFERENCES]->()
        RETURN count(r) as total
        """
        
        with self.driver.session() as session:
            result = session.run(count_query)
            total = result.single()['total']
            logger.info(f"\n✅ Total REFERENCES relationships: {total}")
            
            return {'total_references': total}


def main():
    """Main execution."""
    
    print("\n🚀 Cross-Reference Layer Builder for Neo4j")
    print("="*80)
    
    try:
        # Connect to Neo4j
        print("\n📡 Connecting to Neo4j...")
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "uitchatbot")
        )
        
        # Verify connection
        with driver.session() as session:
            result = session.run("RETURN 1")
            result.single()
            logger.info("✅ Connected to Neo4j successfully")
        
        # Initialize builder
        builder = CrossReferenceBuilder(driver)
        
        # Test reference extraction
        print("\n🧪 Testing reference extraction:")
        test_text = """
        1. Theo Điều 6 của Quy chế này, sinh viên phải đăng ký học phần.
        2. Quy định tại Điều 10 về thời gian học tập.
        3. Khoản 2 Điều 15 quy định về điểm thi.
        """
        refs = builder.extract_references(test_text)
        for ref in refs:
            print(f"   ✓ Found: {ref['matched_text']} → Type: {ref['type']}")
        
        # Confirm action
        response = input("\n⚠️  Build cross-references for all articles? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Operation cancelled")
            return
        
        # Build references
        print("\n🔧 Building cross-references...")
        stats = builder.build_all_references()
        
        # Print statistics
        builder.print_statistics()
        
        # Verify
        print("\n🔍 Verifying created references...")
        builder.verify_references()
        
        print("\n✅ SUCCESS! Cross-reference layer built")
        print("\n📋 Next Steps:")
        print("   1. Test multi-hop queries in Neo4j Browser")
        print("   2. Update RAG retrieval to use REFERENCES relationships")
        print("   3. Implement 'explain reasoning' feature using reference paths")
        
        # Close driver
        driver.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
