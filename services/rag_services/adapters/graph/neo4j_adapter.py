"""
Neo4j Graph Adapter for Legal Knowledge Graph

This adapter implements the GraphRepository port for Neo4j database.
Provides concrete implementation of graph operations for Vietnamese Legal Documents.

Domain: Pháp luật Quốc gia (National Law)
Part of Clean Architecture - Infrastructure layer.
"""

import logging
import re
from typing import List, Optional, Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, ConstraintError

from core.ports.graph_repository import (
    GraphRepository,
    NodeNotFoundError,
    DuplicateNodeError,
    InvalidQueryError,
    ConnectionError as GraphConnectionError
)
from core.domain.graph_models import (
    GraphNode,
    GraphRelationship,
    GraphPath,
    SubGraph,
    GraphQuery,
    NodeType,
    EdgeType,
    LegalStatus
)

logger = logging.getLogger(__name__)


class Neo4jGraphAdapter(GraphRepository):
    """
    Neo4j adapter for Legal Knowledge Graph.
    
    Implements graph operations for Vietnamese legal documents including:
    - Document hierarchy (Luật -> Chương -> Điều -> Khoản -> Điểm)
    - Semantic nodes (Khái niệm, Hành vi cấm, Chế tài)
    - Legal relationships (THUOC_VE, DINH_NGHIA, BI_XU_LY, etc.)
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "uitchatbot",
        database: str = "neo4j"
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI
            username: Database username
            password: Database password
            database: Database name
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self._driver = None
        
        logger.info(f"Initializing Neo4j Legal Graph adapter: {uri}")
    
    def _get_driver(self):
        """Get or create Neo4j driver"""
        if self._driver is None:
            try:
                self._driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
                # Test connection
                self._driver.verify_connectivity()
                logger.info("✓ Neo4j connection established")
            except ServiceUnavailable as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise GraphConnectionError(f"Cannot connect to Neo4j at {self.uri}") from e
        
        return self._driver
    
    # =========================================================================
    # BASIC CRUD OPERATIONS
    # =========================================================================
    
    async def add_node(self, node: GraphNode) -> str:
        """
        Add a node to Neo4j.
        
        Example:
            node = create_article_node(1, "Phạm vi điều chỉnh", "...", doc_id)
            node_id = await adapter.add_node(node)
        """
        driver = self._get_driver()
        
        # Build Cypher query with Vietnamese label
        label = node.node_type.value
        props = node.properties.copy()
        
        # Add standard fields
        if node.id:
            props["id"] = node.id
        if node.name:
            props["name"] = node.name
        if node.content:
            props["content"] = node.content
        
        # Generate unique ID if not present
        if "id" not in props:
            import uuid
            props["id"] = str(uuid.uuid4())
        
        # Create parameterized query (escape Vietnamese labels)
        cypher = f"""
        CREATE (n:`{label}` $props)
        RETURN elementId(n) as id
        """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, props=props)
                record = result.single()
                node_id = record["id"]
                
                logger.info(f"✓ Created node: {label} with ID {node_id}")
                return node_id
                
        except ConstraintError as e:
            logger.error(f"Duplicate node constraint violation: {e}")
            raise DuplicateNodeError(f"Node already exists: {props}") from e
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            raise
    
    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by element ID or custom ID"""
        driver = self._get_driver()
        
        # Try by element ID first, then by custom id property
        cypher = """
        MATCH (n)
        WHERE elementId(n) = $node_id OR n.id = $node_id
        RETURN n, labels(n) as labels
        """
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, node_id=node_id)
            record = result.single()
            
            if not record:
                return None
            
            # Convert to GraphNode
            neo4j_node = record["n"]
            labels = record["labels"]
            
            # Get node type from label
            node_type_label = labels[0] if labels else None
            try:
                node_type = NodeType(node_type_label)
            except ValueError:
                logger.warning(f"Unknown node type: {node_type_label}")
                return None
            
            properties = dict(neo4j_node.items())
            
            return GraphNode(
                id=node_id,
                node_type=node_type,
                properties=properties,
                name=properties.get("name", ""),
                content=properties.get("content", "")
            )
    
    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """
        Add relationship between nodes.
        
        Example:
            rel = create_structural_relationship(article_id, chapter_id)
            await adapter.add_relationship(rel)
        """
        driver = self._get_driver()
        
        edge_type = relationship.edge_type.value
        props = relationship.properties.copy()
        
        # Add standard fields
        if relationship.description:
            props["description"] = relationship.description
        if relationship.weight != 1.0:
            props["weight"] = relationship.weight
        
        cypher = f"""
        MATCH (source), (target)
        WHERE (elementId(source) = $source_id OR source.id = $source_id)
          AND (elementId(target) = $target_id OR target.id = $target_id)
        CREATE (source)-[r:`{edge_type}` $props]->(target)
        RETURN r
        """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(
                    cypher,
                    source_id=relationship.source_id,
                    target_id=relationship.target_id,
                    props=props
                )
                
                if result.single():
                    logger.info(f"✓ Created relationship: {edge_type}")
                    return True
                else:
                    raise NodeNotFoundError("Source or target node not found")
                    
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            raise
    
    async def traverse(
        self,
        start_node_id: str,
        relationship_types: List[EdgeType],
        max_depth: int = 2,
        direction: str = "outgoing"
    ) -> SubGraph:
        """
        Traverse graph from starting node.
        
        Critical for legal queries like:
        - "Điều nào thuộc Chương II?"
        - "Hành vi cấm nào bị xử lý bởi chế tài X?"
        """
        driver = self._get_driver()
        
        # Build relationship pattern with Vietnamese edge types
        rel_types_str = "|".join(f"`{rt.value}`" for rt in relationship_types)
        
        if direction == "outgoing":
            pattern = f"-[r:{rel_types_str}*1..{max_depth}]->"
        elif direction == "incoming":
            pattern = f"<-[r:{rel_types_str}*1..{max_depth}]-"
        else:  # both
            pattern = f"-[r:{rel_types_str}*1..{max_depth}]-"
        
        cypher = f"""
        MATCH path = (start){pattern}(end)
        WHERE elementId(start) = $start_id OR start.id = $start_id
        RETURN path
        """
        
        nodes = []
        relationships = []
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, start_id=start_node_id)
            
            for record in result:
                path = record["path"]
                
                # Extract nodes
                for neo4j_node in path.nodes:
                    node_id = neo4j_node.element_id
                    labels = list(neo4j_node.labels)
                    
                    if labels:
                        try:
                            node_type = NodeType(labels[0])
                            properties = dict(neo4j_node.items())
                            
                            graph_node = GraphNode(
                                id=node_id,
                                node_type=node_type,
                                properties=properties,
                                name=properties.get("name", ""),
                                content=properties.get("content", "")
                            )
                            
                            # Avoid duplicates
                            if not any(n.id == node_id for n in nodes):
                                nodes.append(graph_node)
                        except ValueError:
                            continue
                
                # Extract relationships
                for neo4j_rel in path.relationships:
                    try:
                        edge_type = EdgeType(neo4j_rel.type)
                        
                        graph_rel = GraphRelationship(
                            source_id=neo4j_rel.start_node.element_id,
                            target_id=neo4j_rel.end_node.element_id,
                            edge_type=edge_type,
                            properties=dict(neo4j_rel.items())
                        )
                        
                        relationships.append(graph_rel)
                    except ValueError:
                        continue
        
        return SubGraph(
            nodes=nodes,
            relationships=relationships,
            center_node_id=start_node_id,
            metadata={
                "max_depth": max_depth,
                "direction": direction,
                "relationship_types": [rt.value for rt in relationship_types]
            }
        )
    
    async def get_nodes_by_type(
        self,
        node_type: NodeType,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[GraphNode]:
        """Get all nodes of a type (e.g., all Điều, all Khái niệm)"""
        driver = self._get_driver()
        
        label = node_type.value
        
        # Build WHERE clause for filters
        where_clauses = []
        params = {}
        
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cypher = f"""
        MATCH (n:`{label}`)
        {where_str}
        RETURN n, elementId(n) as id
        LIMIT {limit}
        """
        
        nodes = []
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, **params)
            
            for record in result:
                neo4j_node = record["n"]
                node_id = record["id"]
                properties = dict(neo4j_node.items())
                
                nodes.append(GraphNode(
                    id=node_id,
                    node_type=node_type,
                    properties=properties,
                    name=properties.get("name", ""),
                    content=properties.get("content", "")
                ))
        
        return nodes
    
    async def execute_cypher(
        self,
        cypher: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute raw Cypher query"""
        driver = self._get_driver()
        params = params or {}
        
        results = []
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, **params)
            
            for record in result:
                results.append(dict(record))
        
        return results

    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update node properties"""
        driver = self._get_driver()
        cypher = """
        MATCH (n)
        WHERE elementId(n) = $node_id OR n.id = $node_id
        SET n += $properties
        RETURN n
        """
        with driver.session(database=self.database) as session:
            result = session.run(cypher, node_id=node_id, properties=properties)
            return result.single() is not None

    async def delete_node(self, node_id: str, cascade: bool = False) -> bool:
        """Delete node"""
        driver = self._get_driver()
        op = "DETACH DELETE" if cascade else "DELETE"
        cypher = f"""
        MATCH (n)
        WHERE elementId(n) = $node_id OR n.id = $node_id
        {op} n
        """
        with driver.session(database=self.database) as session:
            session.run(cypher, node_id=node_id)
            return True

    async def get_relationships(self, node_id: str, edge_type: Optional[EdgeType] = None, direction: str = "both") -> List[GraphRelationship]:
        """Get relationships for a node"""
        driver = self._get_driver()
        rel_type = f":`{edge_type.value}`" if edge_type else ""
        if direction == "outgoing":
            pattern = f"(n)-[r{rel_type}]->(m)"
        elif direction == "incoming":
            pattern = f"(n)<-[r{rel_type}]-(m)"
        else:
            pattern = f"(n)-[r{rel_type}]-(m)"
        
        cypher = f"""
        MATCH {pattern}
        WHERE elementId(n) = $node_id OR n.id = $node_id
        RETURN r, elementId(startNode(r)) as source_id, elementId(endNode(r)) as target_id, type(r) as type
        """
        rels = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, node_id=node_id)
            for record in result:
                rels.append(GraphRelationship(
                    source_id=record["source_id"],
                    target_id=record["target_id"],
                    edge_type=EdgeType(record["type"]),
                    properties=dict(record["r"].items())
                ))
        return rels

    async def delete_relationship(self, source_id: str, target_id: str, edge_type: EdgeType) -> bool:
        """Delete relationship"""
        driver = self._get_driver()
        cypher = f"""
        MATCH (s)-[r:`{edge_type.value}`]->(t)
        WHERE (elementId(s) = $source_id OR s.id = $source_id)
          AND (elementId(t) = $target_id OR t.id = $target_id)
        DELETE r
        """
        with driver.session(database=self.database) as session:
            session.run(cypher, source_id=source_id, target_id=target_id)
            return True

    async def find_shortest_path(self, source_id: str, target_id: str, relationship_types: Optional[List[EdgeType]] = None, max_length: int = 5) -> Optional[GraphPath]:
        """Find shortest path between nodes"""
        # Minimal implementation
        return None

    async def find_all_paths(self, source_id: str, target_id: str, relationship_types: Optional[List[EdgeType]] = None, max_length: int = 3, limit: int = 10) -> List[GraphPath]:
        """Find all paths between nodes"""
        return []

    async def get_subgraph(self, center_node_id: str, expand_depth: int = 1, type_filter: Optional[List[NodeType]] = None) -> SubGraph:
        """Get subgraph around node"""
        return await self.traverse(center_node_id, relationship_types=[], max_depth=expand_depth)

    async def execute_query(self, query: GraphQuery) -> Any:
        """Execute graph query"""
        return []

    async def search_nodes(self, query: str, node_types: Optional[List[NodeType]] = None, limit: int = 10) -> List[GraphNode]:
        """Search nodes"""
        results = await self.search_legal_content(query, node_types, limit)
        nodes = []
        for r in results:
            nodes.append(GraphNode(
                id=r["id"],
                node_type=NodeType(r["type"]),
                properties=r["properties"],
                name=r["name"],
                content=r["content"]
            ))
        return nodes

    async def get_type_distribution(self) -> Dict[str, int]:
        """Get distribution of node types"""
        stats = await self.get_graph_stats()
        return stats.get("nodes_by_type", {})
    
    async def health_check(self) -> bool:
        """Check Neo4j connection health"""
        try:
            driver = self._get_driver()
            with driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as num")
                record = result.single()
                return record["num"] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics for legal documents"""
        driver = self._get_driver()
        
        stats = {}
        
        with driver.session(database=self.database) as session:
            # Count nodes by label
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
            node_counts = {}
            for record in result:
                labels = record["labels"]
                if labels:
                    node_counts[labels[0]] = record["count"]
            
            stats["nodes_by_type"] = node_counts
            stats["total_nodes"] = sum(node_counts.values())
            
            # Count relationships by type
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            rel_counts = {}
            for record in result:
                rel_counts[record["type"]] = record["count"]
            
            stats["relationships_by_type"] = rel_counts
            stats["total_relationships"] = sum(rel_counts.values())
        
        return stats
    
    async def clear_graph(self) -> bool:
        """Clear all data (USE WITH CAUTION)"""
        driver = self._get_driver()
        
        logger.warning("⚠️  Clearing entire graph database!")
        
        with driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        logger.info("✓ Graph cleared")
        return True
    
    # =========================================================================
    # LEGAL DOCUMENT SPECIFIC QUERIES
    # =========================================================================
    
    async def find_article_by_number(
        self, 
        article_number: int, 
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find article (Điều) by article number.
        
        Args:
            article_number: Article number (e.g., 3 for "Điều 3")
            document_id: Optional document ID to scope the search
            
        Returns:
            List of matching articles with their content
        """
        driver = self._get_driver()
        
        if document_id:
            cypher = """
            MATCH (a:Điều {article_number: $article_number})-[:THUOC_VE*]->(doc)
            WHERE doc.id = $document_id
            RETURN a, elementId(a) as id
            """
            params = {"article_number": article_number, "document_id": document_id}
        else:
            cypher = """
            MATCH (a:Điều {article_number: $article_number})
            RETURN a, elementId(a) as id
            """
            params = {"article_number": article_number}
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, **params)
            for record in result:
                props = dict(record["a"])
                props["_element_id"] = record["id"]
                results.append(props)
        
        return results
    
    async def find_concept_by_term(self, term: str) -> List[Dict[str, Any]]:
        """
        Find legal concept (Khái niệm) by term.
        
        Args:
            term: Search term (partial match supported)
            
        Returns:
            List of matching concepts with definitions
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (c:`Khái niệm`)
        WHERE toLower(c.term) CONTAINS toLower($term)
           OR toLower(c.name) CONTAINS toLower($term)
        OPTIONAL MATCH (a:Điều)-[:DINH_NGHIA]->(c)
        RETURN c, a.article_number as source_article, elementId(c) as id
        """
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, term=term)
            for record in result:
                props = dict(record["c"])
                props["source_article"] = record["source_article"]
                props["_element_id"] = record["id"]
                results.append(props)
        
        logger.info(f"Found {len(results)} concepts for term '{term}'")
        return results
    
    async def find_prohibited_acts(self, keyword: str = None) -> List[Dict[str, Any]]:
        """
        Find prohibited acts (Hành vi cấm).
        
        Args:
            keyword: Optional keyword filter
            
        Returns:
            List of prohibited acts with their source articles
        """
        driver = self._get_driver()
        
        if keyword:
            cypher = """
            MATCH (pa:`Hành vi cấm`)
            WHERE toLower(pa.prohibited_act) CONTAINS toLower($keyword)
               OR toLower(pa.content) CONTAINS toLower($keyword)
            OPTIONAL MATCH (a:Điều)-[:QUY_DINH]->(pa)
            OPTIONAL MATCH (pa)-[:BI_XU_LY]->(s:`Chế tài`)
            RETURN pa, a.article_number as source_article, 
                   collect(DISTINCT s.sanction_content) as related_sanctions,
                   elementId(pa) as id
            """
            params = {"keyword": keyword}
        else:
            cypher = """
            MATCH (pa:`Hành vi cấm`)
            OPTIONAL MATCH (a:Điều)-[:QUY_DINH]->(pa)
            OPTIONAL MATCH (pa)-[:BI_XU_LY]->(s:`Chế tài`)
            RETURN pa, a.article_number as source_article,
                   collect(DISTINCT s.sanction_content) as related_sanctions,
                   elementId(pa) as id
            LIMIT 50
            """
            params = {}
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, **params)
            for record in result:
                props = dict(record["pa"])
                props["source_article"] = record["source_article"]
                props["related_sanctions"] = record["related_sanctions"]
                props["_element_id"] = record["id"]
                results.append(props)
        
        logger.info(f"Found {len(results)} prohibited acts")
        return results
    
    async def find_sanctions_for_violation(
        self, 
        violation_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find sanctions (Chế tài) applicable to a prohibited act.
        
        Args:
            violation_id: ID of the prohibited act
            
        Returns:
            List of applicable sanctions
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (pa:`Hành vi cấm`)-[:BI_XU_LY]->(s:`Chế tài`)
        WHERE pa.id = $violation_id OR elementId(pa) = $violation_id
        OPTIONAL MATCH (a:Điều)-[:QUY_DINH]->(s)
        RETURN s, pa.prohibited_act as violation, 
               a.article_number as source_article,
               elementId(s) as id
        """
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, violation_id=violation_id)
            for record in result:
                props = dict(record["s"])
                props["violation"] = record["violation"]
                props["source_article"] = record["source_article"]
                props["_element_id"] = record["id"]
                results.append(props)
        
        return results
    
    async def find_amendments_for_document(
        self, 
        document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Find all amendments for a legal document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of amendment relationships with new document info
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (doc)
        WHERE doc.id = $document_id OR elementId(doc) = $document_id
        OPTIONAL MATCH (new_doc)-[r:`thay thế`|`sửa đổi`|`bổ sung`|`bãi bỏ`]->(doc)
        RETURN doc.title as original_title,
               doc.status as status,
               type(r) as amendment_type,
               new_doc.title as amending_document,
               new_doc.document_number as amending_doc_number,
               r.effective_date as effective_date,
               r.description as description
        """
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, document_id=document_id)
            for record in result:
                if record["amendment_type"]:
                    results.append({
                        "original_title": record["original_title"],
                        "status": record["status"],
                        "amendment_type": record["amendment_type"],
                        "amending_document": record["amending_document"],
                        "amending_doc_number": record["amending_doc_number"],
                        "effective_date": record["effective_date"],
                        "description": record["description"]
                    })
        
        logger.info(f"Found {len(results)} amendments for document {document_id}")
        return results
    
    async def get_article_structure(self, article_id: str) -> Dict[str, Any]:
        """
        Get full structure of an article including clauses, points, and semantic nodes.
        
        Args:
            article_id: ID of the article
            
        Returns:
            Dict with article info, clauses, points, concepts, prohibited acts, sanctions
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (a:Điều)
        WHERE a.id = $article_id OR elementId(a) = $article_id
        OPTIONAL MATCH (cl:Khoản)-[:THUOC_VE]->(a)
        OPTIONAL MATCH (p:Điểm)-[:THUOC_VE]->(cl)
        OPTIONAL MATCH (a)-[:DINH_NGHIA]->(c:`Khái niệm`)
        OPTIONAL MATCH (a)-[:QUY_DINH]->(pa:`Hành vi cấm`)
        OPTIONAL MATCH (a)-[:QUY_DINH]->(s:`Chế tài`)
        RETURN a,
               collect(DISTINCT {id: cl.id, number: cl.clause_number, content: cl.clause_content}) as clauses,
               collect(DISTINCT {id: p.id, label: p.point_label, content: p.point_content}) as points,
               collect(DISTINCT {term: c.term, definition: c.definition}) as concepts,
               collect(DISTINCT {act: pa.prohibited_act}) as prohibited_acts,
               collect(DISTINCT {type: s.sanction_type, content: s.sanction_content}) as sanctions
        """
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, article_id=article_id)
            record = result.single()
            
            if not record:
                return {}
            
            article_props = dict(record["a"])
            
            # Filter out None entries
            clauses = [c for c in record["clauses"] if c.get("id")]
            points = [p for p in record["points"] if p.get("id")]
            concepts = [c for c in record["concepts"] if c.get("term")]
            prohibited_acts = [pa for pa in record["prohibited_acts"] if pa.get("act")]
            sanctions = [s for s in record["sanctions"] if s.get("type")]
            
            return {
                "article": article_props,
                "clauses": clauses,
                "points": points,
                "concepts": concepts,
                "prohibited_acts": prohibited_acts,
                "sanctions": sanctions
            }
    
    async def search_articles_by_keyword(
        self, 
        keywords: List[str], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search articles (Điều) by keywords in title and content.
        
        Args:
            keywords: List of search keywords
            limit: Maximum number of results
            
        Returns:
            List of matching articles sorted by relevance
        """
        logger.info(f"🔍 search_articles_by_keyword: keywords={keywords}, limit={limit}")
        driver = self._get_driver()
        
        # Build search conditions
        conditions = []
        params = {"limit": limit}
        
        for i, kw in enumerate(keywords):
            param_name = f"kw{i}"
            conditions.append(
                f"(toLower(a.article_title) CONTAINS toLower(${param_name}) OR "
                f"toLower(a.article_content) CONTAINS toLower(${param_name}) OR "
                f"toLower(a.content) CONTAINS toLower(${param_name}))"
            )
            params[param_name] = kw
        
        where_clause = " OR ".join(conditions) if conditions else "true"
        
        # Build scoring for relevance
        score_parts = []
        for i in range(len(keywords)):
            param_name = f"kw{i}"
            score_parts.append(f"CASE WHEN toLower(a.article_title) CONTAINS toLower(${param_name}) THEN 3 ELSE 0 END")
            score_parts.append(f"CASE WHEN toLower(a.content) CONTAINS toLower(${param_name}) THEN 1 ELSE 0 END")
        
        score_expr = " + ".join(score_parts) if score_parts else "0"
        
        cypher = f"""
        MATCH (a:Điều)
        WHERE {where_clause}
        WITH a, ({score_expr}) as score
        RETURN a.id as id, 
               a.article_number as article_number,
               a.article_title as title, 
               a.content as content,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        
        results = []
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, **params)
                for record in result:
                    results.append({
                        "id": record["id"],
                        "article_number": record["article_number"],
                        "title": record["title"],
                        "content": record["content"][:500] if record["content"] else "",
                        "type": "Điều",
                        "score": record["score"]
                    })
            logger.info(f"✅ Found {len(results)} articles for keywords: {keywords}")
        except Exception as e:
            logger.error(f"❌ Error searching articles: {e}", exc_info=True)
        
        return results
    
    async def search_legal_content(
        self, 
        query: str, 
        node_types: List[NodeType] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across legal content.
        
        Args:
            query: Search query
            node_types: Filter by node types (default: Điều, Khái niệm, Hành vi cấm)
            limit: Maximum results
            
        Returns:
            List of matching nodes with relevance scores
        """
        driver = self._get_driver()
        
        if node_types is None:
            node_types = [NodeType.DIEU, NodeType.KHAI_NIEM, NodeType.HANH_VI_CAM]
        
        all_results = []
        
        for node_type in node_types:
            label = node_type.value
            
            # Determine which fields to search based on node type
            if node_type == NodeType.DIEU:
                search_fields = "n.article_title, n.article_content, n.content"
            elif node_type == NodeType.KHAI_NIEM:
                search_fields = "n.term, n.definition"
            elif node_type == NodeType.HANH_VI_CAM:
                search_fields = "n.prohibited_act, n.content"
            else:
                search_fields = "n.name, n.content"
            
            cypher = f"""
            MATCH (n:`{label}`)
            WHERE any(field IN [{search_fields}] WHERE toLower(toString(field)) CONTAINS toLower($query))
            RETURN elementId(n) as id, n, labels(n)[0] as type
            LIMIT $limit
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, query=query, limit=limit)
                    
                    for record in result:
                        props = dict(record["n"])
                        all_results.append({
                            "id": record["id"],
                            "type": record["type"],
                            "properties": props,
                            "name": props.get("name") or props.get("term") or props.get("article_title", ""),
                            "content": props.get("content") or props.get("definition") or props.get("prohibited_act", "")
                        })
            except Exception as e:
                logger.warning(f"Search failed for {label}: {e}")
                continue
        
        return all_results[:limit]
    
    async def get_document_hierarchy(self, document_id: str) -> Dict[str, Any]:
        """
        Get full document hierarchy: Document -> Chapters -> Sections -> Articles -> Clauses -> Points
        
        Args:
            document_id: ID of the legal document
            
        Returns:
            Hierarchical structure of the document
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (doc)
        WHERE doc.id = $document_id OR elementId(doc) = $document_id
        OPTIONAL MATCH (ch:Chương)-[:THUOC_VE]->(doc)
        OPTIONAL MATCH (sec:Mục)-[:THUOC_VE]->(ch)
        OPTIONAL MATCH (a:Điều)-[:THUOC_VE]->(ch)
        OPTIONAL MATCH (a2:Điều)-[:THUOC_VE]->(sec)
        OPTIONAL MATCH (cl:Khoản)-[:THUOC_VE]->(a)
        OPTIONAL MATCH (cl2:Khoản)-[:THUOC_VE]->(a2)
        RETURN doc,
               collect(DISTINCT {id: ch.id, number: ch.chapter_number, title: ch.chapter_title}) as chapters,
               collect(DISTINCT {id: sec.id, number: sec.section_number, title: sec.section_title, parent: ch.id}) as sections,
               collect(DISTINCT {id: a.id, number: a.article_number, title: a.article_title, parent: ch.id}) as articles1,
               collect(DISTINCT {id: a2.id, number: a2.article_number, title: a2.article_title, parent: sec.id}) as articles2,
               count(DISTINCT cl) + count(DISTINCT cl2) as clause_count
        """
        
        with driver.session(database=self.database) as session:
            result = session.run(cypher, document_id=document_id)
            record = result.single()
            
            if not record:
                return {}
            
            doc_props = dict(record["doc"])
            
            # Filter and combine
            chapters = [c for c in record["chapters"] if c.get("id")]
            sections = [s for s in record["sections"] if s.get("id")]
            articles = [a for a in record["articles1"] if a.get("id")]
            articles.extend([a for a in record["articles2"] if a.get("id")])
            
            return {
                "document": doc_props,
                "chapters": chapters,
                "sections": sections,
                "articles": articles,
                "clause_count": record["clause_count"]
            }
    
    async def get_related_articles(
        self, 
        article_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find articles related to a given article via shared concepts or references.
        
        Args:
            article_id: ID of the source article
            
        Returns:
            List of related articles with relationship info
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (a:Điều)
        WHERE a.id = $article_id OR elementId(a) = $article_id
        
        // Find articles sharing concepts
        OPTIONAL MATCH (a)-[:DINH_NGHIA]->(c:`Khái niệm`)<-[:DINH_NGHIA]-(related1:Điều)
        
        // Find articles in same chapter
        OPTIONAL MATCH (a)-[:THUOC_VE]->(ch:Chương)<-[:THUOC_VE]-(related2:Điều)
        
        // Find articles via references
        OPTIONAL MATCH (a)-[:`tham chiếu`]-(related3:Điều)
        
        WITH a, collect(DISTINCT related1) + collect(DISTINCT related2) + collect(DISTINCT related3) as all_related
        UNWIND all_related as related
        WHERE related <> a AND related IS NOT NULL
        
        RETURN DISTINCT related.id as id,
               related.article_number as article_number,
               related.article_title as title,
               related.content as content
        LIMIT $limit
        """
        
        results = []
        with driver.session(database=self.database) as session:
            result = session.run(cypher, article_id=article_id, limit=limit)
            for record in result:
                results.append({
                    "id": record["id"],
                    "article_number": record["article_number"],
                    "title": record["title"],
                    "content": record["content"][:300] if record["content"] else "",
                    "type": "Điều"
                })
        
        logger.info(f"Found {len(results)} related articles for {article_id}")
        return results
    
    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================
    
    async def add_nodes_batch(self, nodes: List[GraphNode]) -> List[str]:
        """
        Batch add nodes with MERGE to prevent duplicates.
        
        Args:
            nodes: List of GraphNodes to add
            
        Returns:
            List of assigned node IDs
        """
        if not nodes:
            return []
        
        driver = self._get_driver()
        
        # Group nodes by type for batch processing
        nodes_by_type = {}
        for node in nodes:
            type_label = node.node_type.value
            if type_label not in nodes_by_type:
                nodes_by_type[type_label] = []
            nodes_by_type[type_label].append(node)
        
        all_node_ids = []
        
        # Batch insert per type using MERGE
        for type_label, type_nodes in nodes_by_type.items():
            # Prepare data for UNWIND
            nodes_data = []
            for node in type_nodes:
                props = node.properties.copy()
                if node.id:
                    props["id"] = node.id
                if node.name:
                    props["name"] = node.name
                if node.content:
                    props["content"] = node.content
                
                # Ensure ID exists
                if "id" not in props:
                    import uuid
                    props["id"] = str(uuid.uuid4())
                
                nodes_data.append(props)
            
            # Use MERGE to prevent duplicates
            cypher = f"""
            UNWIND $nodes_data as node_props
            MERGE (n:`{type_label}` {{id: node_props.id}})
            SET n += node_props
            RETURN elementId(n) as id
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, nodes_data=nodes_data)
                    
                    for record in result:
                        all_node_ids.append(record["id"])
                
                logger.info(f"✓ Batch created/updated {len(type_nodes)} nodes of type {type_label}")
            except Exception as e:
                logger.error(f"Error in batch node creation: {e}")
                raise
        
        return all_node_ids
    
    async def add_relationships_batch(self, relationships: List[GraphRelationship]) -> int:
        """
        Batch add relationships.
        
        Args:
            relationships: List of GraphRelationships to add
            
        Returns:
            Number of relationships created
        """
        if not relationships:
            return 0
        
        driver = self._get_driver()
        
        # Group by relationship type
        rels_by_type = {}
        for rel in relationships:
            edge_type = rel.edge_type.value if hasattr(rel.edge_type, 'value') else rel.edge_type
            
            if edge_type not in rels_by_type:
                rels_by_type[edge_type] = []
            rels_by_type[edge_type].append(rel)
        
        total_created = 0
        
        # Batch insert per type
        for edge_type, type_rels in rels_by_type.items():
            # Prepare data for UNWIND
            rels_data = []
            for rel in type_rels:
                rels_data.append({
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "props": rel.properties
                })
            
            cypher = f"""
            UNWIND $rels_data as rel_data
            MATCH (source), (target)
            WHERE (source.id = rel_data.source_id OR elementId(source) = rel_data.source_id)
              AND (target.id = rel_data.target_id OR elementId(target) = rel_data.target_id)
            MERGE (source)-[r:`{edge_type}`]->(target)
            SET r += rel_data.props
            RETURN count(r) as created
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, rels_data=rels_data)
                    record = result.single()
                    created = record["created"] if record else 0
                    total_created += created
                
                logger.info(f"✓ Batch created {created} relationships of type {edge_type}")
            except Exception as e:
                logger.error(f"Error in batch relationship creation: {e}")
                raise
        
        return total_created
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def close(self):
        """Close Neo4j driver"""
        if self._driver:
            self._driver.close()
            logger.info("✓ Neo4j connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Factory function for easy instantiation
def create_neo4j_adapter(
    uri: str = "bolt://localhost:7687",
    username: str = "neo4j",
    password: str = "uitchatbot"
) -> Neo4jGraphAdapter:
    """
    Factory function to create Legal Graph adapter.
    
    Example:
        adapter = create_neo4j_adapter()
        await adapter.health_check()
    """
    return Neo4jGraphAdapter(uri=uri, username=username, password=password)
