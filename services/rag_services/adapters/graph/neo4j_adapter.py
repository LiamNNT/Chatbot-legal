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
    
    # POC: Stub implementations for remaining methods
    
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """Update node properties"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def delete_node(self, node_id: str, cascade: bool = False) -> bool:
        """Delete node"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def get_relationships(
        self, node_id: str, rel_type: Optional[RelationshipType] = None, direction: str = "both"
    ) -> List[GraphRelationship]:
        """Get relationships"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def delete_relationship(
        self, source_id: str, target_id: str, rel_type: RelationshipType
    ) -> bool:
        """Delete relationship"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
    async def find_shortest_path(
        self, source_id: str, target_id: str, 
        relationship_types: Optional[List[RelationshipType]] = None, max_length: int = 5
    ) -> Optional[GraphPath]:
        """Find shortest path"""
        # TODO: Implement in full version
        raise NotImplementedError("POC: Not yet implemented")
    
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
        """Batch add nodes"""
        # TODO: Implement optimized batch version
        node_ids = []
        for node in nodes:
            node_id = await self.add_node(node)
            node_ids.append(node_id)
        return node_ids
    
    async def add_relationships_batch(self, relationships: List[GraphRelationship]) -> int:
        """Batch add relationships"""
        # TODO: Implement optimized batch version
        count = 0
        for rel in relationships:
            if await self.add_relationship(rel):
                count += 1
        return count
    
    async def search_nodes(
        self, query: str, categories: Optional[List[NodeCategory]] = None, limit: int = 10
    ) -> List[GraphNode]:
        """Search nodes"""
        # TODO: Implement full-text search
        raise NotImplementedError("POC: Not yet implemented")
    
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
