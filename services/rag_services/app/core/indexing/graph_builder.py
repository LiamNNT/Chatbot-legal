"""
Neo4j Graph Builder for Legal Document Knowledge Graph Pipeline.

This module builds a knowledge graph from Vietnamese legal documents
following the Legal Knowledge Graph schema.

Architecture:
1. Document Hierarchy: LegalDocument -> Chapter -> Section -> Article -> Clause -> Point
2. Semantic Nodes: Concept, ProhibitedAct, Sanction, Right, Obligation
3. Rich Relationships: THUOC_VE, DINH_NGHIA, BI_XU_LY, THAY_THE, etc.

Domain: Pháp luật Quốc gia (National Law)
Schema Source: knowledge_graph_schema.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import date

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class GraphStats:
    """Statistics from graph building process."""
    documents: int = 0
    chapters: int = 0
    sections: int = 0
    articles: int = 0
    clauses: int = 0
    points: int = 0
    concepts: int = 0
    prohibited_acts: int = 0
    sanctions: int = 0
    rights: int = 0
    obligations: int = 0
    subjects: int = 0
    structural_relations: int = 0
    semantic_relations: int = 0
    reference_relations: int = 0
    amendment_relations: int = 0
    total_nodes: int = 0
    total_edges: int = 0


class LegalGraphBuilder:
    """
    Build Legal Knowledge Graph in Neo4j from legal document data.
    
    Implements Legal Document Graph architecture:
    - Hierarchical structure: Document -> Chapter -> Section -> Article -> Clause -> Point
    - Semantic extraction: Concepts, ProhibitedActs, Sanctions linked to Articles
    - Legal references: Cross-references between articles and documents
    - Amendment tracking: THAY_THE, SUA_DOI, BO_SUNG, BAI_BO relationships
    
    Example:
        ```python
        builder = LegalGraphBuilder(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="password"
        )
        
        with open("legal_document_data.json") as f:
            data = json.load(f)
        
        stats = builder.build_graph(data)
        print(f"Created {stats.articles} articles, {stats.concepts} concepts")
        
        builder.close()
        ```
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j bolt URI
            user: Neo4j username
            password: Neo4j password
            database: Database name
        """
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("neo4j package required. Install: pip install neo4j")
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        
        # Verify connection
        try:
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # =========================================================================
    # CONSTRAINTS & INDEXES
    # =========================================================================
    
    def create_constraints(self):
        """
        Create constraints and indexes for legal document graph.
        
        Indexes on:
        - All node types by id (unique)
        - Article.article_number for quick lookup
        - Concept.term for semantic search
        - Full-text indexes for content search
        """
        constraints = [
            # Unique constraints for document structure nodes
            "CREATE CONSTRAINT luat_id IF NOT EXISTS FOR (n:Luật) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT nghi_dinh_id IF NOT EXISTS FOR (n:`Nghị định`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT thong_tu_id IF NOT EXISTS FOR (n:`Thông tư`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT quyet_dinh_id IF NOT EXISTS FOR (n:`Quyết định`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT chuong_id IF NOT EXISTS FOR (n:Chương) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT muc_id IF NOT EXISTS FOR (n:Mục) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT dieu_id IF NOT EXISTS FOR (n:Điều) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT khoan_id IF NOT EXISTS FOR (n:Khoản) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT diem_id IF NOT EXISTS FOR (n:Điểm) REQUIRE n.id IS UNIQUE",
            
            # Unique constraints for semantic nodes
            "CREATE CONSTRAINT khai_niem_id IF NOT EXISTS FOR (n:`Khái niệm`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT hanh_vi_cam_id IF NOT EXISTS FOR (n:`Hành vi cấm`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT che_tai_id IF NOT EXISTS FOR (n:`Chế tài`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT quyen_id IF NOT EXISTS FOR (n:Quyền) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT nghia_vu_id IF NOT EXISTS FOR (n:`Nghĩa vụ`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT chu_the_id IF NOT EXISTS FOR (n:`Chủ thể`) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT thu_tuc_id IF NOT EXISTS FOR (n:`Thủ tục`) REQUIRE n.id IS UNIQUE",
            
            # Indexes for search
            "CREATE INDEX dieu_number IF NOT EXISTS FOR (n:Điều) ON (n.article_number)",
            "CREATE INDEX doc_number IF NOT EXISTS FOR (n:Luật) ON (n.document_number)",
            "CREATE INDEX khai_niem_term IF NOT EXISTS FOR (n:`Khái niệm`) ON (n.term)",
            "CREATE INDEX status_idx IF NOT EXISTS FOR (n:Luật) ON (n.status)",
            
            # Full-text indexes for content search
            "CREATE FULLTEXT INDEX article_content_ft IF NOT EXISTS FOR (n:Điều) ON EACH [n.content, n.article_title]",
            "CREATE FULLTEXT INDEX concept_ft IF NOT EXISTS FOR (n:`Khái niệm`) ON EACH [n.term, n.definition]",
            "CREATE FULLTEXT INDEX prohibited_ft IF NOT EXISTS FOR (n:`Hành vi cấm`) ON EACH [n.prohibited_act, n.content]",
        ]
        
        with self.driver.session(database=self.database) as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.debug(f"Created: {constraint[:60]}...")
                except Exception as e:
                    # Constraint might already exist
                    if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                        logger.warning(f"Constraint warning: {e}")
        
        logger.info("Constraints and indexes created/verified")
    
    def clear_database(self):
        """
        Clear all nodes and relationships. USE WITH CAUTION!
        """
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.warning("Database cleared - all nodes and relationships deleted")
    
    # =========================================================================
    # MAIN BUILD METHOD
    # =========================================================================
    
    def build_graph(
        self,
        document_data: Dict[str, Any],
        clear_first: bool = False
    ) -> GraphStats:
        """
        Build complete legal knowledge graph from document data.
        
        Args:
            document_data: Extracted legal document data
            clear_first: Whether to clear database before building
            
        Returns:
            GraphStats with counts of created nodes/relations
        """
        stats = GraphStats()
        
        if clear_first:
            self.clear_database()
        
        # Ensure constraints exist
        self.create_constraints()
        
        with self.driver.session(database=self.database) as session:
            # 1. Create document hierarchy (LegalDocument -> Chapter -> Article -> Clause -> Point)
            hierarchy_stats = session.execute_write(
                self._create_document_hierarchy, document_data
            )
            stats.documents = hierarchy_stats["documents"]
            stats.chapters = hierarchy_stats["chapters"]
            stats.sections = hierarchy_stats["sections"]
            stats.articles = hierarchy_stats["articles"]
            stats.clauses = hierarchy_stats["clauses"]
            stats.points = hierarchy_stats["points"]
            stats.structural_relations = hierarchy_stats["relations"]
            
            # 2. Create semantic nodes (Concepts, ProhibitedActs, Sanctions, etc.)
            semantic_stats = session.execute_write(
                self._create_semantic_nodes, document_data
            )
            stats.concepts = semantic_stats["concepts"]
            stats.prohibited_acts = semantic_stats["prohibited_acts"]
            stats.sanctions = semantic_stats["sanctions"]
            stats.rights = semantic_stats["rights"]
            stats.obligations = semantic_stats["obligations"]
            stats.subjects = semantic_stats["subjects"]
            stats.semantic_relations = semantic_stats["relations"]
            
            # 3. Create reference relationships (cross-references between articles)
            stats.reference_relations = session.execute_write(
                self._create_reference_relations, document_data
            )
            
            # 4. Create amendment relationships (THAY_THE, SUA_DOI, etc.)
            amendments = document_data.get("amendments", [])
            if amendments:
                stats.amendment_relations = session.execute_write(
                    self._create_amendment_relations, amendments
                )
            
            # Calculate totals
            stats.total_nodes = (
                stats.documents + stats.chapters + stats.sections + 
                stats.articles + stats.clauses + stats.points +
                stats.concepts + stats.prohibited_acts + stats.sanctions +
                stats.rights + stats.obligations + stats.subjects
            )
            stats.total_edges = (
                stats.structural_relations + stats.semantic_relations +
                stats.reference_relations + stats.amendment_relations
            )
        
        logger.info(
            f"Graph built: {stats.documents} docs, {stats.articles} articles, "
            f"{stats.clauses} clauses, {stats.concepts} concepts, "
            f"{stats.prohibited_acts} prohibited acts, {stats.sanctions} sanctions"
        )
        
        return stats
    
    # =========================================================================
    # DOCUMENT HIERARCHY
    # =========================================================================
    
    @staticmethod
    def _create_document_hierarchy(
        tx, 
        document_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Create document structure hierarchy.
        
        Structure: LegalDocument -> Chapter -> Section -> Article -> Clause -> Point
        
        Also creates:
        - [:THUOC_VE] from child to parent (belongs to)
        - [:KE_TIEP] between sequential articles (follows)
        """
        stats = {"documents": 0, "chapters": 0, "sections": 0, 
                 "articles": 0, "clauses": 0, "points": 0, "relations": 0}
        
        # --- Create Legal Document node ---
        doc_info = document_data.get("document", {})
        if doc_info:
            doc_type = doc_info.get("document_type", "Luật")
            label = doc_type  # Use Vietnamese label directly
            
            query = f"""
            MERGE (d:`{label}` {{id: $id}})
            SET d.document_number = $document_number,
                d.title = $title,
                d.content = $content,
                d.issuing_authority = $issuing_authority,
                d.issuing_date = $issuing_date,
                d.effective_date = $effective_date,
                d.status = $status,
                d.scope = $scope,
                d.name = $name,
                d.updated_at = datetime()
            RETURN d
            """
            tx.run(query,
                id=doc_info.get("id", ""),
                document_number=doc_info.get("document_number", ""),
                title=doc_info.get("title", ""),
                content=doc_info.get("content", ""),
                issuing_authority=doc_info.get("issuing_authority", ""),
                issuing_date=doc_info.get("issuing_date", ""),
                effective_date=doc_info.get("effective_date", ""),
                status=doc_info.get("status", "Còn hiệu lực"),
                scope=doc_info.get("scope", ""),
                name=doc_info.get("name", doc_info.get("title", ""))
            )
            stats["documents"] = 1
            logger.debug(f"Created Document: {doc_info.get('id')}")
        
        # --- Create Chapter nodes ---
        for chapter in document_data.get("chapters", []):
            query = """
            MERGE (ch:Chương {id: $id})
            SET ch.chapter_number = $chapter_number,
                ch.chapter_title = $chapter_title,
                ch.content = $content,
                ch.name = $name,
                ch.order_index = $order_index,
                ch.updated_at = datetime()
            
            WITH ch
            OPTIONAL MATCH (doc) WHERE doc.id = $parent_document_id
            FOREACH (_ IN CASE WHEN doc IS NOT NULL THEN [1] ELSE [] END |
                MERGE (ch)-[:THUOC_VE]->(doc)
            )
            
            RETURN ch
            """
            tx.run(query,
                id=chapter.get("id", ""),
                chapter_number=chapter.get("chapter_number", ""),
                chapter_title=chapter.get("chapter_title", ""),
                content=chapter.get("content", ""),
                name=chapter.get("name", f"Chương {chapter.get('chapter_number', '')}"),
                order_index=chapter.get("order_index", 0),
                parent_document_id=chapter.get("parent_document_id", "")
            )
            stats["chapters"] += 1
            stats["relations"] += 1
        
        # --- Create Section nodes (Mục) ---
        for section in document_data.get("sections", []):
            query = """
            MERGE (sec:Mục {id: $id})
            SET sec.section_number = $section_number,
                sec.section_title = $section_title,
                sec.content = $content,
                sec.name = $name,
                sec.order_index = $order_index,
                sec.updated_at = datetime()
            
            WITH sec
            OPTIONAL MATCH (ch:Chương) WHERE ch.id = $parent_chapter_id
            FOREACH (_ IN CASE WHEN ch IS NOT NULL THEN [1] ELSE [] END |
                MERGE (sec)-[:THUOC_VE]->(ch)
            )
            
            RETURN sec
            """
            tx.run(query,
                id=section.get("id", ""),
                section_number=section.get("section_number", ""),
                section_title=section.get("section_title", ""),
                content=section.get("content", ""),
                name=section.get("name", f"Mục {section.get('section_number', '')}"),
                order_index=section.get("order_index", 0),
                parent_chapter_id=section.get("parent_chapter_id", "")
            )
            stats["sections"] += 1
            stats["relations"] += 1
        
        # --- Create Article nodes (Điều) ---
        prev_article_id = None
        for article in document_data.get("articles", []):
            query = """
            MERGE (a:Điều {id: $id})
            SET a.article_number = $article_number,
                a.article_title = $article_title,
                a.article_content = $article_content,
                a.content = $content,
                a.name = $name,
                a.article_category = $article_category,
                a.is_definition_article = $is_definition_article,
                a.order_index = $order_index,
                a.updated_at = datetime()
            
            WITH a
            
            // Link to parent (Chapter or Section)
            OPTIONAL MATCH (parent) 
            WHERE parent.id IN [$parent_chapter_id, $parent_section_id]
            FOREACH (_ IN CASE WHEN parent IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:THUOC_VE]->(parent)
            )
            
            // Link to document directly if no chapter
            WITH a
            OPTIONAL MATCH (doc) WHERE doc.id = $parent_document_id
            FOREACH (_ IN CASE WHEN doc IS NOT NULL 
                              AND $parent_chapter_id = '' 
                              AND $parent_section_id = '' THEN [1] ELSE [] END |
                MERGE (a)-[:THUOC_VE]->(doc)
            )
            
            RETURN a
            """
            tx.run(query,
                id=article.get("id", ""),
                article_number=article.get("article_number", 0),
                article_title=article.get("article_title", ""),
                article_content=article.get("article_content", ""),
                content=article.get("content", article.get("article_content", "")),
                name=article.get("name", f"Điều {article.get('article_number', '')}"),
                article_category=article.get("article_category", ""),
                is_definition_article=article.get("is_definition_article", False),
                order_index=article.get("order_index", 0),
                parent_document_id=article.get("parent_document_id", ""),
                parent_chapter_id=article.get("parent_chapter_id", ""),
                parent_section_id=article.get("parent_section_id", "")
            )
            stats["articles"] += 1
            stats["relations"] += 1
            
            # Create KE_TIEP (follows) relationship with previous article
            if prev_article_id:
                follow_query = """
                MATCH (prev:Điều {id: $prev_id})
                MATCH (curr:Điều {id: $curr_id})
                MERGE (prev)-[:KE_TIEP]->(curr)
                """
                tx.run(follow_query, prev_id=prev_article_id, curr_id=article.get("id", ""))
                stats["relations"] += 1
            
            prev_article_id = article.get("id", "")
            logger.debug(f"Created Article: {article.get('id')}")
        
        # --- Create Clause nodes (Khoản) ---
        for clause in document_data.get("clauses", []):
            query = """
            MERGE (cl:Khoản {id: $id})
            SET cl.clause_number = $clause_number,
                cl.clause_content = $clause_content,
                cl.content = $content,
                cl.name = $name,
                cl.order_index = $order_index,
                cl.updated_at = datetime()
            
            WITH cl
            OPTIONAL MATCH (a:Điều) WHERE a.id = $parent_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (cl)-[:THUOC_VE]->(a)
            )
            
            RETURN cl
            """
            tx.run(query,
                id=clause.get("id", ""),
                clause_number=clause.get("clause_number", 0),
                clause_content=clause.get("clause_content", ""),
                content=clause.get("content", clause.get("clause_content", "")),
                name=clause.get("name", f"Khoản {clause.get('clause_number', '')}"),
                order_index=clause.get("order_index", 0),
                parent_article_id=clause.get("parent_article_id", "")
            )
            stats["clauses"] += 1
            stats["relations"] += 1
            logger.debug(f"Created Clause: {clause.get('id')}")
        
        # --- Create Point nodes (Điểm) ---
        for point in document_data.get("points", []):
            query = """
            MERGE (p:Điểm {id: $id})
            SET p.point_label = $point_label,
                p.point_content = $point_content,
                p.content = $content,
                p.name = $name,
                p.order_index = $order_index,
                p.updated_at = datetime()
            
            WITH p
            OPTIONAL MATCH (cl:Khoản) WHERE cl.id = $parent_clause_id
            FOREACH (_ IN CASE WHEN cl IS NOT NULL THEN [1] ELSE [] END |
                MERGE (p)-[:THUOC_VE]->(cl)
            )
            
            RETURN p
            """
            tx.run(query,
                id=point.get("id", ""),
                point_label=point.get("point_label", ""),
                point_content=point.get("point_content", ""),
                content=point.get("content", point.get("point_content", "")),
                name=point.get("name", f"Điểm {point.get('point_label', '')}"),
                order_index=point.get("order_index", 0),
                parent_clause_id=point.get("parent_clause_id", "")
            )
            stats["points"] += 1
            stats["relations"] += 1
        
        logger.info(
            f"Hierarchy created: {stats['documents']} docs, {stats['chapters']} chapters, "
            f"{stats['sections']} sections, {stats['articles']} articles, "
            f"{stats['clauses']} clauses, {stats['points']} points"
        )
        
        return stats
    
    # =========================================================================
    # SEMANTIC NODES
    # =========================================================================
    
    @staticmethod
    def _create_semantic_nodes(
        tx,
        document_data: Dict[str, Any]
    ) -> Dict[str, int]:
        """
        Create semantic nodes extracted from articles.
        
        - Concepts (Khái niệm): Definitions from "Giải thích từ ngữ" articles
        - ProhibitedActs (Hành vi cấm): Prohibited behaviors from articles
        - Sanctions (Chế tài): Penalties and sanctions
        - Rights (Quyền): Rights of subjects
        - Obligations (Nghĩa vụ): Obligations of subjects
        - Subjects (Chủ thể): Legal entities/subjects
        """
        stats = {"concepts": 0, "prohibited_acts": 0, "sanctions": 0, 
                 "rights": 0, "obligations": 0, "subjects": 0, "relations": 0}
        
        # --- Create Concept nodes ---
        for concept in document_data.get("concepts", []):
            query = """
            MERGE (c:`Khái niệm` {id: $id})
            SET c.term = $term,
                c.definition = $definition,
                c.content = $definition,
                c.name = $term,
                c.related_terms = $related_terms,
                c.synonyms = $synonyms,
                c.keywords = $keywords,
                c.updated_at = datetime()
            
            WITH c
            
            // Link to source article
            OPTIONAL MATCH (a:Điều) WHERE a.id = $source_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:DINH_NGHIA]->(c)
            )
            
            // Link to source document
            WITH c
            OPTIONAL MATCH (doc) WHERE doc.id = $source_document_id
            FOREACH (_ IN CASE WHEN doc IS NOT NULL THEN [1] ELSE [] END |
                MERGE (c)-[:THUOC_VE]->(doc)
            )
            
            RETURN c
            """
            tx.run(query,
                id=concept.get("id", ""),
                term=concept.get("term", ""),
                definition=concept.get("definition", ""),
                related_terms=concept.get("related_terms", []),
                synonyms=concept.get("synonyms", []),
                keywords=concept.get("keywords", []),
                source_article_id=concept.get("source_article_id", ""),
                source_document_id=concept.get("source_document_id", "")
            )
            stats["concepts"] += 1
            stats["relations"] += 2  # DINH_NGHIA + THUOC_VE
        
        # --- Create ProhibitedAct nodes ---
        for act in document_data.get("prohibited_acts", []):
            query = """
            MERGE (pa:`Hành vi cấm` {id: $id})
            SET pa.prohibited_act = $prohibited_act,
                pa.content = $prohibited_act,
                pa.name = $name,
                pa.keywords = $keywords,
                pa.updated_at = datetime()
            
            WITH pa
            
            // Link to source article with QUY_DINH relationship
            OPTIONAL MATCH (a:Điều) WHERE a.id = $source_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:QUY_DINH]->(pa)
            )
            
            RETURN pa
            """
            tx.run(query,
                id=act.get("id", ""),
                prohibited_act=act.get("prohibited_act", ""),
                name=act.get("name", act.get("prohibited_act", "")[:100]),
                keywords=act.get("keywords", []),
                source_article_id=act.get("source_article_id", "")
            )
            stats["prohibited_acts"] += 1
            stats["relations"] += 1
        
        # --- Create Sanction nodes ---
        for sanction in document_data.get("sanctions", []):
            query = """
            MERGE (s:`Chế tài` {id: $id})
            SET s.sanction_type = $sanction_type,
                s.sanction_content = $sanction_content,
                s.content = $sanction_content,
                s.name = $name,
                s.keywords = $keywords,
                s.updated_at = datetime()
            
            WITH s
            
            // Link to source article
            OPTIONAL MATCH (a:Điều) WHERE a.id = $source_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:QUY_DINH]->(s)
            )
            
            RETURN s
            """
            tx.run(query,
                id=sanction.get("id", ""),
                sanction_type=sanction.get("sanction_type", ""),
                sanction_content=sanction.get("sanction_content", ""),
                name=sanction.get("name", sanction.get("sanction_type", "")),
                keywords=sanction.get("keywords", []),
                source_article_id=sanction.get("source_article_id", "")
            )
            stats["sanctions"] += 1
            stats["relations"] += 1
        
        # --- Link ProhibitedActs to Sanctions ---
        for act in document_data.get("prohibited_acts", []):
            for sanction_id in act.get("related_sanctions", []):
                query = """
                MATCH (pa:`Hành vi cấm` {id: $act_id})
                MATCH (s:`Chế tài` {id: $sanction_id})
                MERGE (pa)-[:BI_XU_LY]->(s)
                RETURN pa, s
                """
                result = tx.run(query, act_id=act.get("id", ""), sanction_id=sanction_id)
                if list(result):
                    stats["relations"] += 1
        
        # --- Create Right nodes ---
        for right in document_data.get("rights", []):
            query = """
            MERGE (r:Quyền {id: $id})
            SET r.right_content = $right_content,
                r.content = $right_content,
                r.name = $name,
                r.conditions = $conditions,
                r.keywords = $keywords,
                r.updated_at = datetime()
            
            WITH r
            
            OPTIONAL MATCH (a:Điều) WHERE a.id = $source_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:QUY_DINH]->(r)
            )
            
            RETURN r
            """
            tx.run(query,
                id=right.get("id", ""),
                right_content=right.get("right_content", ""),
                name=right.get("name", right.get("right_content", "")[:100]),
                conditions=right.get("conditions", []),
                keywords=right.get("keywords", []),
                source_article_id=right.get("source_article_id", "")
            )
            stats["rights"] += 1
            stats["relations"] += 1
        
        # --- Create Obligation nodes ---
        for obligation in document_data.get("obligations", []):
            query = """
            MERGE (o:`Nghĩa vụ` {id: $id})
            SET o.obligation_content = $obligation_content,
                o.content = $obligation_content,
                o.name = $name,
                o.deadline = $deadline,
                o.keywords = $keywords,
                o.updated_at = datetime()
            
            WITH o
            
            OPTIONAL MATCH (a:Điều) WHERE a.id = $source_article_id
            FOREACH (_ IN CASE WHEN a IS NOT NULL THEN [1] ELSE [] END |
                MERGE (a)-[:QUY_DINH]->(o)
            )
            
            RETURN o
            """
            tx.run(query,
                id=obligation.get("id", ""),
                obligation_content=obligation.get("obligation_content", ""),
                name=obligation.get("name", obligation.get("obligation_content", "")[:100]),
                deadline=obligation.get("deadline", ""),
                keywords=obligation.get("keywords", []),
                source_article_id=obligation.get("source_article_id", "")
            )
            stats["obligations"] += 1
            stats["relations"] += 1
        
        # --- Create Subject nodes ---
        for subject in document_data.get("subjects", []):
            query = """
            MERGE (s:`Chủ thể` {id: $id})
            SET s.subject_type = $subject_type,
                s.full_name = $full_name,
                s.abbreviation = $abbreviation,
                s.description = $description,
                s.name = $name,
                s.updated_at = datetime()
            
            RETURN s
            """
            tx.run(query,
                id=subject.get("id", ""),
                subject_type=subject.get("subject_type", ""),
                full_name=subject.get("full_name", ""),
                abbreviation=subject.get("abbreviation", ""),
                description=subject.get("description", ""),
                name=subject.get("name", subject.get("full_name", ""))
            )
            stats["subjects"] += 1
        
        # --- Link Subjects to Rights/Obligations ---
        for right in document_data.get("rights", []):
            for subject_id in right.get("subject_ids", []):
                query = """
                MATCH (s:`Chủ thể` {id: $subject_id})
                MATCH (r:Quyền {id: $right_id})
                MERGE (s)-[:CO_QUYEN]->(r)
                """
                tx.run(query, subject_id=subject_id, right_id=right.get("id", ""))
                stats["relations"] += 1
        
        for obligation in document_data.get("obligations", []):
            for subject_id in obligation.get("subject_ids", []):
                query = """
                MATCH (s:`Chủ thể` {id: $subject_id})
                MATCH (o:`Nghĩa vụ` {id: $obligation_id})
                MERGE (s)-[:CO_NGHIA_VU]->(o)
                """
                tx.run(query, subject_id=subject_id, obligation_id=obligation.get("id", ""))
                stats["relations"] += 1
        
        logger.info(
            f"Semantic nodes: {stats['concepts']} concepts, {stats['prohibited_acts']} prohibited acts, "
            f"{stats['sanctions']} sanctions, {stats['rights']} rights, {stats['obligations']} obligations"
        )
        
        return stats
    
    # =========================================================================
    # REFERENCE RELATIONS
    # =========================================================================
    
    @staticmethod
    def _create_reference_relations(
        tx,
        document_data: Dict[str, Any]
    ) -> int:
        """
        Create reference relationships between articles and documents.
        
        Types:
        - THAM_CHIEU: Internal reference between articles
        - DAN_CHIEU: External reference to another document
        - VIEN_DAN: Citing legal basis
        """
        count = 0
        
        for ref in document_data.get("references", []):
            ref_type = ref.get("type", "THAM_CHIEU")
            source_id = ref.get("source_id", "")
            target_id = ref.get("target_id", "")
            reference_text = ref.get("reference_text", "")
            
            if not source_id or not target_id:
                continue
            
            query = f"""
            MATCH (source) WHERE source.id = $source_id
            MATCH (target) WHERE target.id = $target_id
            MERGE (source)-[r:`{ref_type}`]->(target)
            ON CREATE SET 
                r.reference_text = $reference_text,
                r.created_at = datetime()
            RETURN r
            """
            
            result = tx.run(query,
                source_id=source_id,
                target_id=target_id,
                reference_text=reference_text
            )
            
            if list(result):
                count += 1
        
        logger.info(f"Reference relations created: {count}")
        return count
    
    # =========================================================================
    # AMENDMENT RELATIONS
    # =========================================================================
    
    @staticmethod
    def _create_amendment_relations(
        tx,
        amendments: List[Dict[str, Any]]
    ) -> int:
        """
        Create amendment relationships between documents.
        
        Types:
        - THAY_THE: New document replaces old document
        - SUA_DOI: New document amends old document
        - BO_SUNG: New document supplements old document
        - BAI_BO: New document repeals old document
        """
        count = 0
        
        # Mapping of action to target status
        action_to_status = {
            "thay thế": "Hết hiệu lực",
            "sửa đổi": "Bị sửa đổi",
            "bổ sung": "Bị sửa đổi",
            "bãi bỏ": "Bị bãi bỏ"
        }
        
        for amendment in amendments:
            amendment_type = amendment.get("type", "sửa đổi")
            source_id = amendment.get("source_id", "")  # New document
            target_id = amendment.get("target_id", "")  # Old document
            effective_date = amendment.get("effective_date", "")
            description = amendment.get("description", "")
            
            if not source_id or not target_id:
                continue
            
            new_status = action_to_status.get(amendment_type, "Bị sửa đổi")
            
            # Map Vietnamese edge type
            edge_type_map = {
                "thay thế": "thay thế",
                "sửa đổi": "sửa đổi",
                "bổ sung": "bổ sung",
                "bãi bỏ": "bãi bỏ"
            }
            edge_type = edge_type_map.get(amendment_type, "sửa đổi")
            
            query = f"""
            MATCH (source) WHERE source.id = $source_id
            MATCH (target) WHERE target.id = $target_id
            MERGE (source)-[r:`{edge_type}`]->(target)
            ON CREATE SET 
                r.description = $description,
                r.effective_date = $effective_date,
                r.created_at = datetime()
            
            SET target.status = $new_status
            
            RETURN r
            """
            
            result = tx.run(query,
                source_id=source_id,
                target_id=target_id,
                description=description,
                effective_date=effective_date,
                new_status=new_status
            )
            
            if list(result):
                count += 1
                logger.info(f"Amendment created: {source_id} -{amendment_type}-> {target_id}")
        
        logger.info(f"Amendment relations created: {count}")
        return count
    
    # =========================================================================
    # QUERY HELPERS
    # =========================================================================
    
    def find_article_by_number(self, article_number: int, document_id: str = None) -> List[Dict]:
        """
        Find article by article number.
        """
        with self.driver.session(database=self.database) as session:
            if document_id:
                query = """
                MATCH (a:Điều {article_number: $article_number})-[:THUOC_VE*]->(doc)
                WHERE doc.id = $document_id
                RETURN a
                """
                result = session.run(query, article_number=article_number, document_id=document_id)
            else:
                query = """
                MATCH (a:Điều {article_number: $article_number})
                RETURN a
                """
                result = session.run(query, article_number=article_number)
            
            return [dict(record["a"]) for record in result]
    
    def find_concepts_by_term(self, term: str) -> List[Dict]:
        """
        Find concepts by term (partial match).
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (c:`Khái niệm`)
            WHERE toLower(c.term) CONTAINS toLower($term)
            RETURN c
            """
            result = session.run(query, term=term)
            return [dict(record["c"]) for record in result]
    
    def find_prohibited_acts(self, keyword: str = None) -> List[Dict]:
        """
        Find prohibited acts, optionally filtered by keyword.
        """
        with self.driver.session(database=self.database) as session:
            if keyword:
                query = """
                MATCH (pa:`Hành vi cấm`)
                WHERE toLower(pa.prohibited_act) CONTAINS toLower($keyword)
                   OR toLower(pa.content) CONTAINS toLower($keyword)
                RETURN pa
                """
                result = session.run(query, keyword=keyword)
            else:
                query = """
                MATCH (pa:`Hành vi cấm`)
                RETURN pa
                LIMIT 50
                """
                result = session.run(query)
            
            return [dict(record["pa"]) for record in result]
    
    def find_sanctions_for_violation(self, violation_id: str) -> List[Dict]:
        """
        Find sanctions associated with a prohibited act.
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (pa:`Hành vi cấm` {id: $violation_id})-[:BI_XU_LY]->(s:`Chế tài`)
            RETURN s, pa.prohibited_act AS violation
            """
            result = session.run(query, violation_id=violation_id)
            return [{"sanction": dict(record["s"]), "violation": record["violation"]} for record in result]
    
    def find_legal_basis(self, document_id: str) -> List[Dict]:
        """
        Find legal basis (documents cited by this document).
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (doc)-[r:VIEN_DAN|DAN_CHIEU]->(basis)
            WHERE doc.id = $document_id
            RETURN basis, type(r) AS relation_type
            """
            result = session.run(query, document_id=document_id)
            return [{"document": dict(record["basis"]), "relation": record["relation_type"]} for record in result]
    
    def find_latest_version(self, document_id: str) -> Dict:
        """
        Find the latest version of a document (following amendment chain).
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH path = (new)-[:`thay thế`|`sửa đổi`*0..]->(old)
            WHERE old.id = $document_id
            WITH new, length(path) AS depth
            ORDER BY depth DESC
            LIMIT 1
            RETURN new
            """
            result = session.run(query, document_id=document_id)
            record = result.single()
            return dict(record["new"]) if record else {}
    
    def get_article_structure(self, article_id: str) -> Dict:
        """
        Get full structure of an article including clauses, points, and semantic nodes.
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (a:Điều {id: $article_id})
            OPTIONAL MATCH (a)<-[:THUOC_VE]-(cl:Khoản)
            OPTIONAL MATCH (cl)<-[:THUOC_VE]-(p:Điểm)
            OPTIONAL MATCH (a)-[:DINH_NGHIA]->(c:`Khái niệm`)
            OPTIONAL MATCH (a)-[:QUY_DINH]->(pa:`Hành vi cấm`)
            OPTIONAL MATCH (a)-[:QUY_DINH]->(s:`Chế tài`)
            RETURN a, 
                   collect(DISTINCT cl) AS clauses,
                   collect(DISTINCT p) AS points,
                   collect(DISTINCT c) AS concepts,
                   collect(DISTINCT pa) AS prohibited_acts,
                   collect(DISTINCT s) AS sanctions
            """
            result = session.run(query, article_id=article_id)
            record = result.single()
            
            if not record:
                return {}
            
            return {
                "article": dict(record["a"]),
                "clauses": [dict(cl) for cl in record["clauses"]],
                "points": [dict(p) for p in record["points"]],
                "concepts": [dict(c) for c in record["concepts"]],
                "prohibited_acts": [dict(pa) for pa in record["prohibited_acts"]],
                "sanctions": [dict(s) for s in record["sanctions"]]
            }
    
    def get_graph_stats(self) -> Dict[str, int]:
        """
        Get current graph statistics.
        """
        with self.driver.session(database=self.database) as session:
            query = """
            MATCH (n:Luật) WITH count(n) AS laws
            MATCH (n:Điều) WITH laws, count(n) AS articles
            MATCH (n:Khoản) WITH laws, articles, count(n) AS clauses
            MATCH (n:`Khái niệm`) WITH laws, articles, clauses, count(n) AS concepts
            MATCH (n:`Hành vi cấm`) WITH laws, articles, clauses, concepts, count(n) AS prohibited_acts
            MATCH (n:`Chế tài`) WITH laws, articles, clauses, concepts, prohibited_acts, count(n) AS sanctions
            MATCH ()-[r]->() WITH laws, articles, clauses, concepts, prohibited_acts, sanctions, count(r) AS total_relations
            RETURN laws, articles, clauses, concepts, prohibited_acts, sanctions, total_relations
            """
            result = session.run(query)
            record = result.single()
            return dict(record) if record else {}


# =============================================================================
# CLI / Main
# =============================================================================

def main():
    """
    CLI to build legal graph from extraction JSON file.
    """
    import argparse
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Build Neo4j Legal Knowledge Graph from JSON")
    parser.add_argument("json_file", help="Path to legal document JSON file")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "password"))
    parser.add_argument("--clear", action="store_true", help="Clear database before building")
    
    args = parser.parse_args()
    
    # Load JSON
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"ERROR: File not found: {json_path}")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n{'='*60}")
    print("LEGAL KNOWLEDGE GRAPH BUILDER")
    print(f"{'='*60}")
    print(f"Source: {json_path.name}")
    print(f"Neo4j: {args.uri}")
    
    # Build graph
    try:
        with LegalGraphBuilder(
            uri=args.uri,
            user=args.user,
            password=args.password
        ) as builder:
            stats = builder.build_graph(
                document_data=data,
                clear_first=args.clear
            )
            
            print(f"\n{'='*60}")
            print("BUILD COMPLETE")
            print(f"{'='*60}")
            print(f"  Documents:       {stats.documents}")
            print(f"  Chapters:        {stats.chapters}")
            print(f"  Sections:        {stats.sections}")
            print(f"  Articles:        {stats.articles}")
            print(f"  Clauses:         {stats.clauses}")
            print(f"  Points:          {stats.points}")
            print(f"  Concepts:        {stats.concepts}")
            print(f"  Prohibited Acts: {stats.prohibited_acts}")
            print(f"  Sanctions:       {stats.sanctions}")
            print(f"  Rights:          {stats.rights}")
            print(f"  Obligations:     {stats.obligations}")
            print(f"  Total Nodes:     {stats.total_nodes}")
            print(f"  Total Edges:     {stats.total_edges}")
            
            # Show graph stats
            print(f"\nGraph Statistics:")
            graph_stats = builder.get_graph_stats()
            for key, value in graph_stats.items():
                print(f"  {key}: {value}")
                
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


# Alias for backward compatibility
Neo4jGraphBuilder = LegalGraphBuilder


if __name__ == "__main__":
    main()
