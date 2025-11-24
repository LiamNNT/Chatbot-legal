"""
Cross-Reference Detector and Linker
====================================

Automatically detects and creates relationships between legal document nodes
when cross-references are mentioned.

Patterns detected:
- "theo Điều X" → Link to Article X
- "Khoản Y Điều Z" → Link from current clause to Article Z, Clause Y  
- "quy định tại Điều X" → Link to Article X
- "theo quy định tại Khoản X" → Link to Clause X
- "Điều X của Quy chế này" → Link to Article X

Example:
    ```python
    from indexing.cross_reference_detector import CrossReferenceDetector
    
    detector = CrossReferenceDetector(neo4j_adapter)
    
    # Detect and create links
    links_created = detector.process_document("QD_790_2022")
    print(f"Created {links_created} cross-reference relationships")
    ```
"""

import logging
import re
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class CrossReference:
    """Represents a detected cross-reference"""
    source_node_id: str
    source_type: str  # "Article" or "Clause"
    target_article_no: Optional[int] = None
    target_clause_no: Optional[str] = None
    reference_text: str = ""
    reference_type: str = ""  # "article", "clause", "article_clause"
    
    def __repr__(self):
        target = f"Article {self.target_article_no}"
        if self.target_clause_no:
            target += f", Clause {self.target_clause_no}"
        return f"<XRef: {self.source_node_id} → {target}>"


class CrossReferenceDetector:
    """
    Detect cross-references in legal documents and create graph relationships
    
    This class:
    1. Scans all Article and Clause nodes for reference patterns
    2. Extracts article/clause numbers from patterns
    3. Creates REFERENCES relationships in Neo4j
    """
    
    # Regex patterns for cross-reference detection
    PATTERNS = [
        # Pattern 1: "theo Điều X"
        (
            r'theo\s+Điều\s+(\d+)',
            'article',
            'theo_dieu'
        ),
        
        # Pattern 2: "Điều X của Quy chế"
        (
            r'Điều\s+(\d+)\s+của\s+Quy\s+chế',
            'article',
            'dieu_cua_quy_che'
        ),
        
        # Pattern 3: "quy định tại Điều X"
        (
            r'quy\s+định\s+tại\s+Điều\s+(\d+)',
            'article',
            'quy_dinh_tai_dieu'
        ),
        
        # Pattern 4: "Khoản X Điều Y"
        (
            r'Khoản\s+(\d+[a-z]?)\s+Điều\s+(\d+)',
            'article_clause',
            'khoan_dieu'
        ),
        
        # Pattern 5: "theo quy định tại Khoản X"
        (
            r'theo\s+quy\s+định\s+tại\s+Khoản\s+(\d+[a-z]?)',
            'clause',
            'theo_khoan'
        ),
        
        # Pattern 6: "theo Khoản X"
        (
            r'theo\s+Khoản\s+(\d+[a-z]?)',
            'clause',
            'theo_khoan_simple'
        ),
        
        # Pattern 7: "tại Điều X"
        (
            r'tại\s+Điều\s+(\d+)',
            'article',
            'tai_dieu'
        ),
        
        # Pattern 8: "căn cứ Điều X"
        (
            r'căn\s+cứ\s+Điều\s+(\d+)',
            'article',
            'can_cu_dieu'
        ),
    ]
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", 
                 password: str = "uitchatbot"):
        """
        Initialize detector with Neo4j connection
        
        Args:
            uri: Neo4j bolt URI
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def detect_in_text(self, text: str, source_article_no: Optional[int] = None) -> List[CrossReference]:
        """
        Detect all cross-references in text
        
        Args:
            text: Text to scan
            source_article_no: Article number context for resolving relative references
            
        Returns:
            List of detected cross-references
        """
        references = []
        
        for pattern, ref_type, pattern_name in self.PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                ref = self._create_reference(match, ref_type, pattern_name, source_article_no)
                if ref:
                    references.append(ref)
        
        return references
    
    def _create_reference(self, match: re.Match, ref_type: str, 
                          pattern_name: str, context_article_no: Optional[int]) -> Optional[CrossReference]:
        """Create CrossReference from regex match"""
        ref = CrossReference(
            source_node_id="",  # Will be set later
            source_type="",
            reference_text=match.group(0),
            reference_type=ref_type
        )
        
        if ref_type == 'article':
            # Article reference: match.group(1) is article number
            ref.target_article_no = int(match.group(1))
        
        elif ref_type == 'clause':
            # Clause reference in same article
            ref.target_clause_no = match.group(1)
            ref.target_article_no = context_article_no
        
        elif ref_type == 'article_clause':
            # Both clause and article: group(1)=clause, group(2)=article
            ref.target_clause_no = match.group(1)
            ref.target_article_no = int(match.group(2))
        
        return ref
    
    def process_document(self, doc_id: str = "QD_790_2022", dry_run: bool = False) -> Dict[str, int]:
        """
        Process all nodes in document and create cross-reference relationships
        
        Args:
            doc_id: Document ID to process
            dry_run: If True, detect but don't create relationships
            
        Returns:
            Statistics dict with counts
        """
        stats = {
            "articles_scanned": 0,
            "clauses_scanned": 0,
            "references_detected": 0,
            "relationships_created": 0,
            "relationships_failed": 0
        }
        
        with self.driver.session() as session:
            # Process Articles
            logger.info("Scanning Articles for cross-references...")
            articles = session.run("""
                MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                      -[:HAS_ARTICLE]->(a:Article)
                RETURN elementId(a) as node_id, a.article_id as article_id,
                       a.article_no as article_no, a.raw_text as text
            """, {"doc_id": doc_id}).data()
            
            for article in articles:
                stats["articles_scanned"] += 1
                refs = self.detect_in_text(
                    article['text'], 
                    source_article_no=article['article_no']
                )
                
                for ref in refs:
                    ref.source_node_id = article['node_id']
                    ref.source_type = "Article"
                    stats["references_detected"] += 1
                    
                    if not dry_run:
                        if self._create_relationship(session, ref, doc_id):
                            stats["relationships_created"] += 1
                        else:
                            stats["relationships_failed"] += 1
            
            # Process Clauses
            logger.info("Scanning Clauses for cross-references...")
            clauses = session.run("""
                MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                      -[:HAS_ARTICLE]->(a:Article)-[:HAS_CLAUSE]->(cl:Clause)
                RETURN elementId(cl) as node_id, cl.clause_id as clause_id,
                       a.article_no as article_no, cl.raw_text as text
            """, {"doc_id": doc_id}).data()
            
            for clause in clauses:
                stats["clauses_scanned"] += 1
                refs = self.detect_in_text(
                    clause['text'],
                    source_article_no=clause['article_no']
                )
                
                for ref in refs:
                    ref.source_node_id = clause['node_id']
                    ref.source_type = "Clause"
                    stats["references_detected"] += 1
                    
                    if not dry_run:
                        if self._create_relationship(session, ref, doc_id):
                            stats["relationships_created"] += 1
                        else:
                            stats["relationships_failed"] += 1
        
        logger.info(f"Cross-reference processing complete: {stats}")
        return stats
    
    def _create_relationship(self, session, ref: CrossReference, doc_id: str) -> bool:
        """
        Create REFERENCES relationship in Neo4j
        
        Returns True if successful, False otherwise
        """
        try:
            # Build target node query based on reference type
            if ref.reference_type in ['article', 'article_clause']:
                # Find target article
                if ref.target_clause_no:
                    # Find specific clause in article
                    query = """
                    MATCH (source)
                    WHERE elementId(source) = $source_id
                    
                    MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                          -[:HAS_ARTICLE]->(target:Article {article_no: $article_no})
                          -[:HAS_CLAUSE]->(cl:Clause {clause_no: $clause_no})
                    
                    MERGE (source)-[r:REFERENCES {
                        reference_text: $ref_text,
                        reference_type: $ref_type
                    }]->(cl)
                    
                    RETURN count(r) as created
                    """
                    params = {
                        "source_id": ref.source_node_id,
                        "doc_id": doc_id,
                        "article_no": ref.target_article_no,
                        "clause_no": ref.target_clause_no,
                        "ref_text": ref.reference_text,
                        "ref_type": ref.reference_type
                    }
                else:
                    # Reference to entire article
                    query = """
                    MATCH (source)
                    WHERE elementId(source) = $source_id
                    
                    MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                          -[:HAS_ARTICLE]->(target:Article {article_no: $article_no})
                    
                    MERGE (source)-[r:REFERENCES {
                        reference_text: $ref_text,
                        reference_type: $ref_type
                    }]->(target)
                    
                    RETURN count(r) as created
                    """
                    params = {
                        "source_id": ref.source_node_id,
                        "doc_id": doc_id,
                        "article_no": ref.target_article_no,
                        "ref_text": ref.reference_text,
                        "ref_type": ref.reference_type
                    }
            
            elif ref.reference_type == 'clause':
                # Reference to clause in same article
                if not ref.target_article_no:
                    logger.warning(f"Clause reference without article context: {ref}")
                    return False
                
                query = """
                MATCH (source)
                WHERE elementId(source) = $source_id
                
                MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                      -[:HAS_ARTICLE]->(a:Article {article_no: $article_no})
                      -[:HAS_CLAUSE]->(target:Clause {clause_no: $clause_no})
                
                MERGE (source)-[r:REFERENCES {
                    reference_text: $ref_text,
                    reference_type: $ref_type
                }]->(target)
                
                RETURN count(r) as created
                """
                params = {
                    "source_id": ref.source_node_id,
                    "doc_id": doc_id,
                    "article_no": ref.target_article_no,
                    "clause_no": ref.target_clause_no,
                    "ref_text": ref.reference_text,
                    "ref_type": ref.reference_type
                }
            else:
                logger.warning(f"Unknown reference type: {ref.reference_type}")
                return False
            
            result = session.run(query, params).single()
            
            if result and result['created'] > 0:
                logger.debug(f"Created reference: {ref}")
                return True
            else:
                logger.warning(f"Failed to create reference (target not found): {ref}")
                return False
        
        except Exception as e:
            logger.error(f"Error creating relationship for {ref}: {e}")
            return False
    
    def get_cross_reference_stats(self, doc_id: str = "QD_790_2022") -> Dict[str, Any]:
        """Get statistics about cross-references in document"""
        with self.driver.session() as session:
            query = """
            MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                  -[:HAS_ARTICLE]->(a:Article)
            OPTIONAL MATCH (a)-[r:REFERENCES]->()
            WITH a, count(r) as ref_count
            RETURN 
                count(a) as total_articles,
                sum(ref_count) as total_references_from_articles,
                avg(ref_count) as avg_references_per_article
            """
            article_stats = session.run(query, {"doc_id": doc_id}).single()
            
            query = """
            MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                  -[:HAS_ARTICLE]->(:Article)-[:HAS_CLAUSE]->(cl:Clause)
            OPTIONAL MATCH (cl)-[r:REFERENCES]->()
            WITH cl, count(r) as ref_count
            RETURN 
                count(cl) as total_clauses,
                sum(ref_count) as total_references_from_clauses,
                avg(ref_count) as avg_references_per_clause
            """
            clause_stats = session.run(query, {"doc_id": doc_id}).single()
            
            return {
                "articles": dict(article_stats) if article_stats else {},
                "clauses": dict(clause_stats) if clause_stats else {},
            }
    
    def find_most_referenced_articles(self, doc_id: str = "QD_790_2022", limit: int = 10) -> List[Dict]:
        """Find articles that are referenced most often"""
        with self.driver.session() as session:
            query = """
            MATCH (d:Document {doc_id: $doc_id})-[:HAS_CHAPTER]->(:Chapter)
                  -[:HAS_ARTICLE]->(a:Article)
            OPTIONAL MATCH (a)<-[r:REFERENCES]-()
            WITH a, count(r) as reference_count
            WHERE reference_count > 0
            RETURN a.article_no as article_no, 
                   a.title_vi as title,
                   reference_count
            ORDER BY reference_count DESC
            LIMIT $limit
            """
            results = session.run(query, {"doc_id": doc_id, "limit": limit}).data()
            return results


# ============================================================================
# Command-line interface
# ============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    detector = CrossReferenceDetector()
    
    try:
        print("=" * 80)
        print("CROSS-REFERENCE DETECTION AND LINKING")
        print("=" * 80)
        
        # Dry run first
        print("\n🔍 DRY RUN: Detecting cross-references...")
        dry_stats = detector.process_document(dry_run=True)
        
        print(f"\n📊 Detection Results:")
        print(f"   Articles scanned: {dry_stats['articles_scanned']}")
        print(f"   Clauses scanned: {dry_stats['clauses_scanned']}")
        print(f"   Cross-references found: {dry_stats['references_detected']}")
        
        if dry_stats['references_detected'] == 0:
            print("\n⚠️  No cross-references detected. Exiting.")
            sys.exit(0)
        
        # Ask for confirmation
        response = input(f"\n❓ Create {dry_stats['references_detected']} REFERENCES relationships? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            print("\n🔨 Creating relationships...")
            stats = detector.process_document(dry_run=False)
            
            print(f"\n✅ COMPLETE!")
            print(f"   Relationships created: {stats['relationships_created']}")
            print(f"   Failed: {stats['relationships_failed']}")
            
            # Show stats
            print("\n📊 Cross-Reference Statistics:")
            detailed_stats = detector.get_cross_reference_stats()
            print(f"   Articles: {detailed_stats['articles']}")
            print(f"   Clauses: {detailed_stats['clauses']}")
            
            # Most referenced
            print("\n🔗 Most Referenced Articles:")
            top = detector.find_most_referenced_articles(limit=5)
            for item in top:
                print(f"   Article {item['article_no']}: {item['title']} ({item['reference_count']} refs)")
        else:
            print("\n❌ Cancelled.")
    
    finally:
        detector.close()
