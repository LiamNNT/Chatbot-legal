"""
Neo4j Graph Adapter - POC Implementation

This adapter implements the GraphRepository port for Neo4j database.
Provides concrete implementation of graph operations using neo4j-driver.

Part of Clean Architecture - Infrastructure layer.
"""

import logging
from typing import List, Optional, Dict, Any
from neo4j import GraphDatabase, AsyncGraphDatabase
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
    NodeCategory,
    RelationshipType
)

logger = logging.getLogger(__name__)


class Neo4jGraphAdapter(GraphRepository):
    """
    Neo4j adapter implementing GraphRepository port.
    
    POC Version - Basic functionality for Week 1 demo.
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
        
        logger.info(f"Initializing Neo4j adapter: {uri}")
    
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
    
    async def add_node(self, node: GraphNode) -> str:
        """
        Add a node to Neo4j.
        
        Example:
            node = create_mon_hoc_node("IT001", "Nhập môn lập trình", 4)
            node_id = await adapter.add_node(node)
        """
        driver = self._get_driver()
        
        # Build Cypher query
        label = node.category.value
        props = node.properties.copy()
        
        # Generate unique ID if not present
        if "id" not in props and "code" not in props:
            import uuid
            props["_generated_id"] = str(uuid.uuid4())
        
        # Create parameterized query
        cypher = f"""
        CREATE (n:{label} $props)
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
        """Get node by ID"""
        driver = self._get_driver()
        
        cypher = """
        MATCH (n)
        WHERE elementId(n) = $node_id
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
            
            # Get category from label
            category_label = labels[0]  # Primary label
            try:
                category = NodeCategory(category_label)
            except ValueError:
                logger.warning(f"Unknown category: {category_label}")
                return None
            
            properties = dict(neo4j_node.items())
            
            return GraphNode(
                id=node_id,
                category=category,
                properties=properties
            )
    
    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """
        Add relationship between nodes.
        
        Example:
            rel = create_prerequisite_relationship(it002_id, it001_id, required=True)
            await adapter.add_relationship(rel)
        """
        driver = self._get_driver()
        
        rel_type = relationship.rel_type.value
        props = relationship.properties
        
        cypher = f"""
        MATCH (source), (target)
        WHERE elementId(source) = $source_id AND elementId(target) = $target_id
        CREATE (source)-[r:{rel_type} $props]->(target)
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
                    logger.info(f"✓ Created relationship: {rel_type}")
                    return True
                else:
                    raise NodeNotFoundError("Source or target node not found")
                    
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            raise
    
    async def traverse(
        self,
        start_node_id: str,
        relationship_types: List[RelationshipType],
        max_depth: int = 2,
        direction: str = "outgoing"
    ) -> SubGraph:
        """
        Traverse graph from starting node.
        
        CRITICAL for CatRAG queries like "What are prerequisites for IT003?"
        """
        driver = self._get_driver()
        
        # Build relationship pattern
        rel_types_str = "|".join(rt.value for rt in relationship_types)
        
        if direction == "outgoing":
            pattern = f"-[r:{rel_types_str}*1..{max_depth}]->"
        elif direction == "incoming":
            pattern = f"<-[r:{rel_types_str}*1..{max_depth}]-"
        else:  # both
            pattern = f"-[r:{rel_types_str}*1..{max_depth}]-"
        
        cypher = f"""
        MATCH path = (start){pattern}(end)
        WHERE elementId(start) = $start_id
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
                            category = NodeCategory(labels[0])
                            properties = dict(neo4j_node.items())
                            
                            graph_node = GraphNode(
                                id=node_id,
                                category=category,
                                properties=properties
                            )
                            
                            # Avoid duplicates
                            if not any(n.id == node_id for n in nodes):
                                nodes.append(graph_node)
                        except ValueError:
                            continue
                
                # Extract relationships
                for neo4j_rel in path.relationships:
                    try:
                        rel_type = RelationshipType(neo4j_rel.type)
                        
                        graph_rel = GraphRelationship(
                            source_id=neo4j_rel.start_node.element_id,
                            target_id=neo4j_rel.end_node.element_id,
                            rel_type=rel_type,
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
    
    async def get_nodes_by_category(
        self,
        category: NodeCategory,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[GraphNode]:
        """Get all nodes of a category"""
        driver = self._get_driver()
        
        label = category.value
        
        # Build WHERE clause for filters
        where_clauses = []
        params = {}
        
        if filters:
            for key, value in filters.items():
                where_clauses.append(f"n.{key} = ${key}")
                params[key] = value
        
        where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        cypher = f"""
        MATCH (n:{label})
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
                    category=category,
                    properties=properties
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
        """Get graph statistics"""
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
            
            stats["nodes_by_category"] = node_counts
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
    
    # ========== Full Implementation - Week 1 Task A4 ==========
    
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update node properties.
        
        Args:
            node_id: Neo4j element ID
            properties: Dictionary of properties to update
            
        Returns:
            True if updated successfully
            
        Example:
            await adapter.update_node(node_id, {"so_tin_chi": 5, "updated_at": datetime.now()})
        """
        driver = self._get_driver()
        
        # Build SET clause
        set_clauses = []
        params = {"node_id": node_id}
        
        for key, value in properties.items():
            set_clauses.append(f"n.{key} = ${key}")
            params[key] = value
        
        set_str = ", ".join(set_clauses)
        
        cypher = f"""
        MATCH (n)
        WHERE elementId(n) = $node_id
        SET {set_str}
        RETURN n
        """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, **params)
                record = result.single()
                
                if record:
                    logger.info(f"✓ Updated node: {node_id}")
                    return True
                else:
                    logger.warning(f"Node not found: {node_id}")
                    return False
        except Exception as e:
            logger.error(f"Error updating node: {e}")
            raise
    
    async def delete_node(self, node_id: str, cascade: bool = False) -> bool:
        """
        Delete node (soft delete with timestamp or hard delete).
        
        Args:
            node_id: Neo4j element ID
            cascade: If True, delete relationships; if False, fail if relationships exist
            
        Returns:
            True if deleted successfully
            
        Example:
            # Soft delete (mark as deleted)
            await adapter.delete_node(node_id, cascade=True)
        """
        driver = self._get_driver()
        
        if cascade:
            # Hard delete with relationships
            cypher = """
            MATCH (n)
            WHERE elementId(n) = $node_id
            DETACH DELETE n
            RETURN count(n) as deleted
            """
        else:
            # Soft delete - set deleted_at timestamp
            cypher = """
            MATCH (n)
            WHERE elementId(n) = $node_id
            SET n.deleted_at = datetime()
            RETURN n
            """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, node_id=node_id)
                record = result.single()
                
                if record:
                    logger.info(f"✓ Deleted node: {node_id} (cascade={cascade})")
                    return True
                else:
                    logger.warning(f"Node not found: {node_id}")
                    return False
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            raise
    
    async def get_relationships(
        self, node_id: str, rel_type: Optional[RelationshipType] = None, direction: str = "both"
    ) -> List[GraphRelationship]:
        """
        Get relationships for a node.
        
        Args:
            node_id: Neo4j element ID
            rel_type: Filter by relationship type (optional)
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of GraphRelationships
            
        Example:
            rels = await adapter.get_relationships(course_id, RelationshipType.DIEU_KIEN_TIEN_QUYET, "outgoing")
        """
        driver = self._get_driver()
        
        # Build cypher based on direction
        if direction == "outgoing":
            pattern = "(n)-[r]->(m)"
        elif direction == "incoming":
            pattern = "(n)<-[r]-(m)"
        else:  # both
            pattern = "(n)-[r]-(m)"
        
        # Add type filter if specified
        if rel_type:
            type_filter = f":{rel_type.value}"
        else:
            type_filter = ""
        
        cypher = f"""
        MATCH {pattern.replace('[r]', f'[r{type_filter}]')}
        WHERE elementId(n) = $node_id
        RETURN elementId(startNode(r)) as source_id, 
               elementId(endNode(r)) as target_id,
               type(r) as rel_type,
               properties(r) as props
        """
        
        relationships = []
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, node_id=node_id)
                
                for record in result:
                    try:
                        rel_type_value = RelationshipType(record["rel_type"])
                        
                        relationships.append(GraphRelationship(
                            source_id=record["source_id"],
                            target_id=record["target_id"],
                            rel_type=rel_type_value,
                            properties=dict(record["props"])
                        ))
                    except ValueError:
                        logger.warning(f"Unknown relationship type: {record['rel_type']}")
                        continue
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            raise
        
        return relationships
    
    async def delete_relationship(
        self, source_id: str, target_id: str, rel_type: RelationshipType
    ) -> bool:
        """
        Delete relationship between two nodes.
        
        Args:
            source_id: Source node element ID
            target_id: Target node element ID
            rel_type: Relationship type to delete
            
        Returns:
            True if deleted successfully
            
        Example:
            await adapter.delete_relationship(it003_id, it002_id, RelationshipType.DIEU_KIEN_TIEN_QUYET)
        """
        driver = self._get_driver()
        
        cypher = f"""
        MATCH (source)-[r:{rel_type.value}]->(target)
        WHERE elementId(source) = $source_id AND elementId(target) = $target_id
        DELETE r
        RETURN count(r) as deleted
        """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, source_id=source_id, target_id=target_id)
                record = result.single()
                
                if record and record["deleted"] > 0:
                    logger.info(f"✓ Deleted relationship: {rel_type.value}")
                    return True
                else:
                    logger.warning(f"Relationship not found")
                    return False
        except Exception as e:
            logger.error(f"Error deleting relationship: {e}")
            raise
    
    async def find_shortest_path(
        self, source_id: str, target_id: str, 
        relationship_types: Optional[List[RelationshipType]] = None, max_length: int = 5
    ) -> Optional[GraphPath]:
        """
        Find shortest path between two nodes (Dijkstra/BFS).
        
        Critical for CatRAG: Finding prerequisite chains for courses.
        
        Args:
            source_id: Source node element ID
            target_id: Target node element ID
            relationship_types: List of relationship types to follow (None = all)
            max_length: Maximum path length
            
        Returns:
            GraphPath if found, None otherwise
            
        Example:
            # Find prerequisite chain from SE363 to IT001
            path = await adapter.find_shortest_path(se363_id, it001_id, [RelationshipType.DIEU_KIEN_TIEN_QUYET])
        """
        driver = self._get_driver()
        
        # Build relationship type filter
        if relationship_types:
            rel_types_str = "|".join([rt.value for rt in relationship_types])
            rel_filter = f":{rel_types_str}"
        else:
            rel_filter = ""
        
        cypher = f"""
        MATCH path = shortestPath((source)-[{rel_filter}*1..{max_length}]->(target))
        WHERE elementId(source) = $source_id AND elementId(target) = $target_id
        RETURN path,
               [node IN nodes(path) | {{id: elementId(node), labels: labels(node), properties: properties(node)}}] as nodes,
               [rel IN relationships(path) | {{type: type(rel), properties: properties(rel)}}] as rels,
               length(path) as path_length
        """
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, source_id=source_id, target_id=target_id)
                record = result.single()
                
                if not record:
                    logger.info(f"No path found between {source_id} and {target_id}")
                    return None
                
                # Convert to GraphPath
                nodes_data = record["nodes"]
                rels_data = record["rels"]
                
                # Build GraphNode objects
                graph_nodes = []
                for node_data in nodes_data:
                    try:
                        category = NodeCategory(node_data["labels"][0])
                        graph_nodes.append(GraphNode(
                            id=node_data["id"],
                            category=category,
                            properties=node_data["properties"]
                        ))
                    except (ValueError, IndexError):
                        logger.warning(f"Invalid node in path")
                        continue
                
                # Build GraphRelationship objects
                graph_rels = []
                for i, rel_data in enumerate(rels_data):
                    try:
                        rel_type = RelationshipType(rel_data["type"])
                        graph_rels.append(GraphRelationship(
                            source_id=nodes_data[i]["id"],
                            target_id=nodes_data[i+1]["id"],
                            rel_type=rel_type,
                            properties=rel_data["properties"]
                        ))
                    except (ValueError, IndexError):
                        logger.warning(f"Invalid relationship in path")
                        continue
                
                return GraphPath(
                    nodes=graph_nodes,
                    relationships=graph_rels
                    # length is auto-calculated
                )
                
        except Exception as e:
            logger.error(f"Error finding shortest path: {e}")
            raise
    
    async def find_all_paths(
        self, source_id: str, target_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        max_length: int = 3, limit: int = 10
    ) -> List[GraphPath]:
        """Find all paths"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def get_subgraph(
        self, center_node_id: str, expand_depth: int = 1,
        category_filter: Optional[List[NodeCategory]] = None
    ) -> SubGraph:
        """Get subgraph"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def execute_query(self, query: GraphQuery) -> SubGraph:
        """Execute graph query"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def add_nodes_batch(self, nodes: List[GraphNode]) -> List[str]:
        """
        Batch add nodes with optimized MERGE query (Deduplication enabled).
        
        Uses MERGE instead of CREATE to prevent duplicate nodes.
        Merges based on the standard ID key for each label (ma_mon, ma_khoa, etc).
        
        Args:
            nodes: List of GraphNodes to add
            
        Returns:
            List of assigned node IDs (elementId from Neo4j)
            
        Example:
            nodes = [create_mon_hoc_node(...), create_mon_hoc_node(...)]
            node_ids = await adapter.add_nodes_batch(nodes)
        """
        if not nodes:
            return []
        
        from core.domain.schema_mapper import SchemaMapper
        
        driver = self._get_driver()
        
        # Group nodes by category for batch processing
        nodes_by_category = {}
        for node in nodes:
            category = node.category.value
            if category not in nodes_by_category:
                nodes_by_category[category] = []
            nodes_by_category[category].append(node)
        
        all_node_ids = []
        
        # Batch insert per category using MERGE
        for category, category_nodes in nodes_by_category.items():
            # Get the standard ID key for this category
            id_key = SchemaMapper.PROPERTY_MAPPING.get(category, {}).get("id_key", "id")
            
            # Prepare data for UNWIND
            nodes_data = []
            for node in category_nodes:
                props = node.properties.copy()
                
                # Ensure ID key exists
                if id_key not in props:
                    # Try to extract from common keys
                    id_value = props.get("code") or props.get("id") or props.get("name")
                    if id_value:
                        # Clean the ID
                        id_value = SchemaMapper.extract_clean_id(str(id_value), category)
                        props[id_key] = id_value
                    else:
                        # Generate fallback ID
                        import uuid
                        props[id_key] = f"auto_{str(uuid.uuid4())[:8]}"
                
                nodes_data.append(props)
            
            # Use MERGE to prevent duplicates
            cypher = f"""
            UNWIND $nodes_data as node_props
            MERGE (n:{category} {{{id_key}: node_props.{id_key}}})
            SET n += node_props
            RETURN elementId(n) as id
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, nodes_data=nodes_data)
                    
                    for record in result:
                        all_node_ids.append(record["id"])
                
                logger.info(f"✓ Batch created/updated {len(category_nodes)} nodes of type {category}")
            except Exception as e:
                logger.error(f"Error in batch node creation: {e}")
                raise
        
        return all_node_ids
    
    async def add_relationships_batch(self, relationships: List[GraphRelationship]) -> int:
        """
        Batch add relationships with optimized UNWIND query.
        
        Args:
            relationships: List of GraphRelationships to add
            
        Returns:
            Number of relationships created
            
        Example:
            rels = [create_prerequisite_relationship(...), ...]
            count = await adapter.add_relationships_batch(rels)
        """
        if not relationships:
            return 0
        
        driver = self._get_driver()
        
        # Group by relationship type
        rels_by_type = {}
        for rel in relationships:
            # Handle both string and enum types
            # Check if it has .value attribute (enum) instead of isinstance
            if hasattr(rel.rel_type, 'value'):
                rel_type = rel.rel_type.value
            else:
                rel_type = rel.rel_type
            
            if rel_type not in rels_by_type:
                rels_by_type[rel_type] = []
            rels_by_type[rel_type].append(rel)
        
        total_created = 0
        
        # Batch insert per type
        for rel_type, type_rels in rels_by_type.items():
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
            WHERE elementId(source) = rel_data.source_id AND elementId(target) = rel_data.target_id
            CREATE (source)-[r:{rel_type}]->(target)
            SET r = rel_data.props
            RETURN count(r) as created
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, rels_data=rels_data)
                    record = result.single()
                    created = record["created"] if record else 0
                    total_created += created
                
                logger.info(f"✓ Batch created {created} relationships of type {rel_type}")
            except Exception as e:
                logger.error(f"Error in batch relationship creation: {e}")
                raise
        
        return total_created
    
    async def search_nodes(
        self, query: str, categories: Optional[List[NodeCategory]] = None, limit: int = 10
    ) -> List[GraphNode]:
        """
        Full-text search on nodes using Neo4j's full-text indexes.
        
        Uses the full-text indexes created in 02_create_indexes.cypher.
        
        Args:
            query: Search query string (Vietnamese or English)
            categories: Filter by node categories (optional)
            limit: Maximum results
            
        Returns:
            List of matching GraphNodes sorted by relevance score
            
        Example:
            # Search for courses about "cấu trúc dữ liệu"
            results = await adapter.search_nodes("cấu trúc dữ liệu", [NodeCategory.MON_HOC], limit=5)
        """
        driver = self._get_driver()
        
        # Map categories to index names
        index_names = {
            NodeCategory.MON_HOC: "mon_hoc_fulltext",
            NodeCategory.KHOA: "khoa_fulltext",
            NodeCategory.CHUONG_TRINH_DAO_TAO: "chuong_trinh_fulltext",
            NodeCategory.QUY_DINH: "quy_dinh_fulltext",
            NodeCategory.GIANG_VIEN: "giang_vien_fulltext"
        }
        
        all_results = []
        
        # Search in specified categories or all
        search_categories = categories if categories else list(index_names.keys())
        
        for category in search_categories:
            index_name = index_names.get(category)
            if not index_name:
                continue
            
            cypher = f"""
            CALL db.index.fulltext.queryNodes($index_name, $query)
            YIELD node, score
            RETURN elementId(node) as id, node, score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            try:
                with driver.session(database=self.database) as session:
                    result = session.run(cypher, index_name=index_name, query=query, limit=limit)
                    
                    for record in result:
                        neo4j_node = record["node"]
                        node_id = record["id"]
                        score = record["score"]
                        
                        properties = dict(neo4j_node.items())
                        properties["_search_score"] = score  # Add relevance score
                        
                        graph_node = GraphNode(
                            id=node_id,
                            category=category,
                            properties=properties
                        )
                        
                        all_results.append((score, graph_node))
            except Exception as e:
                logger.warning(f"Full-text search failed for {category}: {e}")
                continue
        
        # Sort by score and return nodes
        all_results.sort(key=lambda x: x[0], reverse=True)
        return [node for score, node in all_results[:limit]]
    
    # ========== CatRAG-Specific Methods ==========
    
    async def find_prerequisites_chain(
        self, 
        course_code: str,
        max_depth: int = 10
    ) -> List[GraphPath]:
        """
        Find all prerequisite chains for a course (CatRAG-specific).
        
        This is a critical query for the Router Agent to handle prerequisite questions.
        Returns all paths from the course to foundational courses.
        
        Args:
            course_code: Course code (e.g., "SE363", "IT004")
            max_depth: Maximum prerequisite chain depth
            
        Returns:
            List of GraphPaths representing prerequisite chains
            
        Example:
            # Find all prerequisites for SE363 (AI course)
            chains = await adapter.find_prerequisites_chain("SE363")
            # Returns: SE363 -> IT003 -> IT002 -> IT001
        """
        driver = self._get_driver()
        
        cypher = f"""
        MATCH (target:MON_HOC {{ma_mon: $course_code}})
        MATCH path = (target)-[:DIEU_KIEN_TIEN_QUYET*1..{max_depth}]->(prereq:MON_HOC)
        WITH path, length(path) as depth
        ORDER BY depth DESC
        RETURN path,
               [node IN nodes(path) | {{
                   id: elementId(node),
                   code: node.ma_mon,
                   name: node.ten_mon,
                   credits: node.so_tin_chi
               }}] as nodes,
               [rel IN relationships(path) | {{
                   type: type(rel),
                   required: rel.loai = 'bat_buoc',
                   min_grade: rel.diem_toi_thieu
               }}] as rels,
               depth
        """
        
        paths = []
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(cypher, course_code=course_code)
                
                for record in result:
                    nodes_data = record["nodes"]
                    rels_data = record["rels"]
                    depth = record["depth"]
                    
                    # Build GraphNode objects
                    graph_nodes = []
                    for node_data in nodes_data:
                        graph_nodes.append(GraphNode(
                            id=node_data["id"],
                            category=NodeCategory.MON_HOC,
                            properties={
                                "code": node_data["code"],  # Required by validation
                                "ma_mon": node_data["code"],
                                "name": node_data["name"],  # Required
                                "ten_mon": node_data["name"],
                                "credits": node_data["credits"],  # Required
                                "so_tin_chi": node_data["credits"]
                            }
                        ))
                    
                    # Build GraphRelationship objects
                    graph_rels = []
                    for i, rel_data in enumerate(rels_data):
                        graph_rels.append(GraphRelationship(
                            source_id=nodes_data[i]["id"],
                            target_id=nodes_data[i+1]["id"],
                            rel_type=RelationshipType.DIEU_KIEN_TIEN_QUYET,
                            properties={
                                "loai": "bat_buoc" if rel_data["required"] else "khuyen_nghi",
                                "diem_toi_thieu": rel_data["min_grade"]
                            }
                        ))
                    
                    paths.append(GraphPath(
                        nodes=graph_nodes,
                        relationships=graph_rels
                        # length is auto-calculated in __post_init__
                    ))
            
            logger.info(f"Found {len(paths)} prerequisite paths for {course_code}")
            return paths
            
        except Exception as e:
            logger.error(f"Error finding prerequisite chain: {e}")
            raise
    
    async def find_related_courses(
        self,
        course_code: str,
        similarity_threshold: float = 0.7,
        limit: int = 5
    ) -> List[GraphNode]:
        """
        Find semantically related courses (CatRAG-specific).
        
        Uses LIEN_QUAN relationships with similarity scores.
        
        Args:
            course_code: Course code
            similarity_threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum results
            
        Returns:
            List of related course GraphNodes
        """
        driver = self._get_driver()
        
        cypher = """
        MATCH (source:MON_HOC {ma_mon: $course_code})-[r:LIEN_QUAN]-(related:MON_HOC)
        WHERE r.do_tuong_tu >= $threshold
        RETURN elementId(related) as id, related, r.do_tuong_tu as similarity
        ORDER BY similarity DESC
        LIMIT $limit
        """
        
        related_courses = []
        
        try:
            with driver.session(database=self.database) as session:
                result = session.run(
                    cypher,
                    course_code=course_code,
                    threshold=similarity_threshold,
                    limit=limit
                )
                
                for record in result:
                    neo4j_node = record["related"]
                    node_id = record["id"]
                    similarity = record["similarity"]
                    
                    properties = dict(neo4j_node.items())
                    properties["_similarity_score"] = similarity
                    
                    related_courses.append(GraphNode(
                        id=node_id,
                        category=NodeCategory.MON_HOC,
                        properties=properties
                    ))
            
            logger.info(f"Found {len(related_courses)} related courses for {course_code}")
            return related_courses
            
        except Exception as e:
            logger.error(f"Error finding related courses: {e}")
            raise
    
    async def get_category_distribution(self) -> Dict[str, int]:
        """Get category distribution"""
        stats = await self.get_graph_stats()
        return stats.get("nodes_by_category", {})
    
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
    Factory function to create Neo4j adapter.
    
    Example:
        adapter = create_neo4j_adapter()
        await adapter.health_check()
    """
    return Neo4jGraphAdapter(uri=uri, username=username, password=password)
