import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SymbolicGraphExtension:
    def __init__(self, neo4j_adapter):
        self.adapter = neo4j_adapter
        logger.info("SymbolicGraphExtension initialized")
    
    # =========================================================================
    # R001: HIERARCHICAL STRUCTURE QUERIES
    # =========================================================================
    
    async def get_article_hierarchy(self, article_number: int, law_name: Optional[str] = None) -> Dict[str, Any]:
        driver = self.adapter._get_driver()
        
        law_filter = ""
        params = {"article_number": article_number}
        
        if law_name:
            law_filter = "AND toLower(law.name) CONTAINS toLower($law_name)"
            params["law_name"] = law_name
        
        cypher = f"""
        MATCH (a:Điều {{article_number: $article_number}})
        OPTIONAL MATCH (a)-[:THUOC_VE]->(ch:Chương)-[:THUOC_VE]->(law)
        {law_filter}
        OPTIONAL MATCH (cl:Khoản)-[:THUOC_VE]->(a)
        OPTIONAL MATCH (p:Điểm)-[:THUOC_VE]->(cl)
        RETURN a as article,
               ch as chapter,
               law,
               collect(DISTINCT {{
                   number: cl.clause_number,
                   content: cl.clause_content,
                   points: collect(DISTINCT {{label: p.point_label, content: p.point_content}})
               }}) as clauses
        """
        
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, **params)
            record = result.single()
            
            if not record:
                return {}
            
            return {
                "law": dict(record["law"]) if record["law"] else {},
                "chapter": dict(record["chapter"]) if record["chapter"] else {},
                "article": dict(record["article"]) if record["article"] else {},
                "clauses": record["clauses"]
            }
    
    async def traverse_document_hierarchy(self, start_node_id: str, direction: str = "both", max_depth: int = 3) -> Dict[str, Any]:
        driver = self.adapter._get_driver()
        results = {"ancestors": [], "descendants": [], "center": None}
        
        # Get center node
        cypher = """
        MATCH (n)
        WHERE n.id = $node_id OR elementId(n) = $node_id
        RETURN n, labels(n) as labels
        """
        
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, node_id=start_node_id)
            record = result.single()
            
            if not record:
                return results
            
            results["center"] = {
                "properties": dict(record["n"]),
                "type": record["labels"][0] if record["labels"] else "Unknown"
            }
        
        # Get ancestors (up)
        if direction in ("up", "both"):
            cypher = f"""
            MATCH path = (start)-[:THUOC_VE*1..{max_depth}]->(ancestor)
            WHERE start.id = $node_id OR elementId(start) = $node_id
            RETURN ancestor, labels(ancestor) as labels, length(path) as distance
            ORDER BY distance
            """
            
            with driver.session(database=self.adapter.database) as session:
                result = session.run(cypher, node_id=start_node_id)
                for record in result:
                    results["ancestors"].append({
                        "properties": dict(record["ancestor"]),
                        "type": record["labels"][0] if record["labels"] else "Unknown",
                        "distance": record["distance"]
                    })
        
        # Get descendants (down)
        if direction in ("down", "both"):
            cypher = f"""
            MATCH path = (start)<-[:THUOC_VE*1..{max_depth}]-(descendant)
            WHERE start.id = $node_id OR elementId(start) = $node_id
            RETURN descendant, labels(descendant) as labels, length(path) as distance
            ORDER BY distance
            """
            
            with driver.session(database=self.adapter.database) as session:
                result = session.run(cypher, node_id=start_node_id)
                for record in result:
                    results["descendants"].append({
                        "properties": dict(record["descendant"]),
                        "type": record["labels"][0] if record["labels"] else "Unknown",
                        "distance": record["distance"]
                    })
        
        return results
    
    # =========================================================================
    # R002: CONCEPT REGULATION MAPPING
    # =========================================================================
    
    async def get_laws_for_concept(self, concept: str, limit: int = 10) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        cypher = """
        MATCH (c:`Khái niệm`)
        WHERE toLower(c.term) CONTAINS toLower($concept)
           OR toLower(c.name) CONTAINS toLower($concept)
        MATCH (c)<-[:DINH_NGHIA]-(a:Điều)
        OPTIONAL MATCH (a)-[:THUOC_VE*]->(law)
        WHERE law:Luật OR law:VanBan OR labels(law)[0] = 'Luật'
        RETURN DISTINCT c.term as concept,
               c.definition as definition,
               a.article_number as article_number,
               a.article_title as article_title,
               law.name as law_name,
               law.title as law_title
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, concept=concept, limit=limit)
            for record in result:
                results.append({
                    "concept": record["concept"],
                    "definition": record["definition"],
                    "article_number": record["article_number"],
                    "article_title": record["article_title"],
                    "law_name": record["law_name"] or record["law_title"]
                })
        
        logger.info(f"Found {len(results)} laws for concept '{concept}'")
        return results
    
    async def get_concepts_in_law(self, law_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        cypher = """
        MATCH (law)
        WHERE toLower(law.name) CONTAINS toLower($law_name)
           OR toLower(law.title) CONTAINS toLower($law_name)
        MATCH (c:`Khái niệm`)<-[:DINH_NGHIA]-(a:Điều)-[:THUOC_VE*]->(law)
        RETURN DISTINCT c.term as term,
               c.definition as definition,
               a.article_number as defined_in_article
        ORDER BY a.article_number
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, law_name=law_name, limit=limit)
            for record in result:
                results.append({
                    "term": record["term"],
                    "definition": record["definition"],
                    "defined_in_article": record["defined_in_article"]
                })
        
        return results
    
    # =========================================================================
    # R003: OBLIGATION INFERENCE
    # =========================================================================
    
    async def get_obligations_for_entity(self, entity_type: str, law_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        law_filter = ""
        params = {"entity_type": entity_type, "limit": limit}
        
        if law_name:
            law_filter = "AND toLower(law.name) CONTAINS toLower($law_name)"
            params["law_name"] = law_name
        
        # Search in article content for obligation keywords
        cypher = f"""
        MATCH (a:Điều)
        WHERE (toLower(a.content) CONTAINS 'trách nhiệm'
               OR toLower(a.content) CONTAINS 'nghĩa vụ'
               OR toLower(a.content) CONTAINS 'phải')
          AND toLower(a.content) CONTAINS toLower($entity_type)
        OPTIONAL MATCH (a)-[:THUOC_VE*]->(law)
        {law_filter}
        RETURN a.article_number as article_number,
               a.article_title as title,
               a.content as content,
               law.name as law_name
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, **params)
            for record in result:
                results.append({
                    "article_number": record["article_number"],
                    "title": record["title"],
                    "content": record["content"][:500] if record["content"] else "",
                    "law_name": record["law_name"],
                    "type": "obligation"
                })
        
        logger.info(f"Found {len(results)} obligations for entity type '{entity_type}'")
        return results
    
    # =========================================================================
    # R004: RIGHTS PROTECTION
    # =========================================================================
    
    async def get_rights_protection(self, right_keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        cypher = """
        MATCH (a:Điều)
        WHERE (toLower(a.content) CONTAINS 'bảo vệ'
               OR toLower(a.content) CONTAINS 'đảm bảo'
               OR toLower(a.content) CONTAINS 'quyền')
          AND toLower(a.content) CONTAINS toLower($right_keyword)
        OPTIONAL MATCH (a)-[:THUOC_VE*]->(law)
        RETURN a.article_number as article_number,
               a.article_title as title,
               a.content as content,
               law.name as law_name
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, right_keyword=right_keyword, limit=limit)
            for record in result:
                results.append({
                    "article_number": record["article_number"],
                    "title": record["title"],
                    "content": record["content"][:500] if record["content"] else "",
                    "law_name": record["law_name"],
                    "type": "right_protection"
                })
        
        return results
    
    # =========================================================================
    # R005: TRANSITIVE LAW RELATIONSHIPS
    # =========================================================================
    
    async def get_related_laws(self, law_name: str, max_depth: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        cypher = f"""
        MATCH (law)
        WHERE toLower(law.name) CONTAINS toLower($law_name)
           OR toLower(law.title) CONTAINS toLower($law_name)
        MATCH path = (law)-[r:LIEN_QUAN|THAM_CHIEU|BO_SUNG|THAY_THE*1..{max_depth}]-(related)
        WHERE related <> law
        RETURN DISTINCT related.name as name,
               related.title as title,
               [rel in relationships(path) | type(rel)] as relationship_types,
               length(path) as distance
        ORDER BY distance
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, law_name=law_name, limit=limit)
            for record in result:
                results.append({
                    "name": record["name"] or record["title"],
                    "relationship_types": record["relationship_types"],
                    "distance": record["distance"]
                })
        
        return results
    
    # =========================================================================
    # R006: PROHIBITION DETECTION
    # =========================================================================
    
    async def find_prohibitions(self, action_keyword: Optional[str] = None, law_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        driver = self.adapter._get_driver()
        
        # First try dedicated Hành vi cấm nodes
        cypher1 = """
        MATCH (pa:`Hành vi cấm`)
        WHERE $action_keyword IS NULL 
           OR toLower(pa.prohibited_act) CONTAINS toLower($action_keyword)
           OR toLower(pa.content) CONTAINS toLower($action_keyword)
        OPTIONAL MATCH (a:Điều)-[:QUY_DINH]->(pa)
        OPTIONAL MATCH (pa)-[:BI_XU_LY]->(s:`Chế tài`)
        RETURN pa.prohibited_act as prohibition,
               pa.content as detail,
               a.article_number as article_number,
               collect(DISTINCT s.sanction_content) as penalties
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher1, action_keyword=action_keyword, limit=limit)
            for record in result:
                results.append({
                    "prohibition": record["prohibition"],
                    "detail": record["detail"],
                    "article_number": record["article_number"],
                    "penalties": record["penalties"],
                    "type": "prohibition"
                })
        
        # If no results from dedicated nodes, search in article content
        if not results:
            cypher2 = """
            MATCH (a:Điều)
            WHERE (toLower(a.content) CONTAINS 'nghiêm cấm'
                   OR toLower(a.content) CONTAINS 'cấm'
                   OR toLower(a.content) CONTAINS 'không được')
            RETURN a.article_number as article_number,
                   a.article_title as title,
                   a.content as content
            LIMIT $limit
            """
            
            if action_keyword:
                cypher2 = """
                MATCH (a:Điều)
                WHERE (toLower(a.content) CONTAINS 'nghiêm cấm'
                       OR toLower(a.content) CONTAINS 'cấm'
                       OR toLower(a.content) CONTAINS 'không được')
                  AND toLower(a.content) CONTAINS toLower($action_keyword)
                RETURN a.article_number as article_number,
                       a.article_title as title,
                       a.content as content
                LIMIT $limit
                """
            
            with driver.session(database=self.adapter.database) as session:
                result = session.run(cypher2, action_keyword=action_keyword, limit=limit)
                for record in result:
                    results.append({
                        "article_number": record["article_number"],
                        "title": record["title"],
                        "content": record["content"][:500] if record["content"] else "",
                        "type": "prohibition_article"
                    })
        
        logger.info(f"Found {len(results)} prohibitions")
        return results
    
    # =========================================================================
    # R008: CONTEXT-BASED ARTICLE RETRIEVAL
    # =========================================================================
    
    async def get_full_article_context(self, article_number: int, clause_number: Optional[int] = None, point_label: Optional[str] = None, law_name: Optional[str] = None) -> Dict[str, Any]:
        driver = self.adapter._get_driver()
        
        law_filter = ""
        params = {"article_number": article_number}
        
        if law_name:
            law_filter = "AND toLower(law.name) CONTAINS toLower($law_name)"
            params["law_name"] = law_name
        
        cypher = f"""
        MATCH (a:Điều {{article_number: $article_number}})
        OPTIONAL MATCH (a)-[:THUOC_VE*]->(law)
        {law_filter}
        OPTIONAL MATCH (cl:Khoản)-[:THUOC_VE]->(a)
        OPTIONAL MATCH (p:Điểm)-[:THUOC_VE]->(cl)
        OPTIONAL MATCH (a)-[:DINH_NGHIA]->(concept:`Khái niệm`)
        OPTIONAL MATCH (a)-[:QUY_DINH]->(prohibition:`Hành vi cấm`)
        RETURN a as article,
               law.name as law_name,
               collect(DISTINCT {{
                   number: cl.clause_number,
                   content: cl.clause_content
               }}) as clauses,
               collect(DISTINCT {{
                   label: p.point_label,
                   content: p.point_content,
                   clause: cl.clause_number
               }}) as points,
               collect(DISTINCT concept.term) as concepts,
               collect(DISTINCT prohibition.prohibited_act) as prohibitions
        """
        
        with driver.session(database=self.adapter.database) as session:
            result = session.run(cypher, **params)
            record = result.single()
            
            if not record:
                return {}
            
            article_data = dict(record["article"]) if record["article"] else {}
            
            # Filter clauses and points
            clauses = [c for c in record["clauses"] if c.get("number")]
            points = [p for p in record["points"] if p.get("label")]
            
            # Filter to specific clause/point if requested
            if clause_number:
                clauses = [c for c in clauses if c.get("number") == clause_number]
                points = [p for p in points if p.get("clause") == clause_number]
            
            if point_label:
                points = [p for p in points if p.get("label") == point_label]
            
            return {
                "law_name": record["law_name"],
                "article": article_data,
                "clauses": clauses,
                "points": points,
                "concepts": [c for c in record["concepts"] if c],
                "prohibitions": [p for p in record["prohibitions"] if p],
                "full_content": article_data.get("content", "")
            }
    
    # =========================================================================
    # KEYWORD SEARCH (For SymbolicReasoningEngine)
    # =========================================================================
    
    async def keyword_search(self, keyword: str, node_types: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        # Delegate to adapter's search method
        if hasattr(self.adapter, 'search_articles_by_keyword'):
            results = await self.adapter.search_articles_by_keyword([keyword], limit)
            
            # Convert to standard format
            return [
                {
                    "id": r.get("id"),
                    "name": r.get("title") or r.get("article_title"),
                    "type": r.get("type", "Điều"),
                    "content": r.get("content", ""),
                    "article_number": r.get("article_number")
                }
                for r in results
            ]
        
        # Fallback to legal content search
        if hasattr(self.adapter, 'search_legal_content'):
            return await self.adapter.search_legal_content(keyword, limit=limit)
        
        return []
    
    async def search_articles(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        # Delegate to adapter
        if hasattr(self.adapter, 'search_articles_by_keyword'):
            keywords = search_term.split()
            return await self.adapter.search_articles_by_keyword(keywords, limit)
        
        return await self.keyword_search(search_term, limit=limit)
