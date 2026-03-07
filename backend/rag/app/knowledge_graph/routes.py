"""
API Routes for Knowledge Graph queries and visualization.

Provides endpoints for:
- Get graph data for visualization
- Get graph statistics
- Search in knowledge graph
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter(prefix="/kg", tags=["Knowledge Graph"])


def get_neo4j_connection():
    """Get Neo4j connection parameters from environment."""
    return {
        "uri": os.getenv("NEO4J_URI", ""),
        "user": os.getenv("NEO4J_USERNAME", ""),
        "password": os.getenv("NEO4J_PASSWORD", "")
    }


@router.get("/stats")
async def get_kg_stats():
    """
    Get Knowledge Graph statistics.
    
    Returns counts of nodes and relationships in the graph.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            stats = builder.get_graph_stats()
        
        return {
            "status": "connected",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to get KG stats: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/graph")
async def get_knowledge_graph(
    document_number: Optional[str] = Query(None, description="Filter by document number (e.g., 24-2018-QH14)"),
    doc_kind: Optional[str] = Query(None, description="Filter by document type (LAW, DECREE, CIRCULAR)"),
    limit: int = Query(1000, description="Maximum number of nodes to return")
):
    """
    Get Knowledge Graph data for visualization.
    
    Returns nodes and relationships in a format suitable for graph visualization.
    Supports filtering by document number and document type.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            # Build query based on filters
            if document_number:
                # Get specific document's graph
                graph_data = _query_document_graph(builder, document_number, limit)
            elif doc_kind:
                # Get documents by type
                graph_data = _query_graphs_by_type(builder, doc_kind, limit)
            else:
                # Get overview of all documents
                graph_data = _query_all_graphs(builder, limit)
        
        return graph_data
    except Exception as e:
        logger.error(f"Failed to get KG graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _query_document_graph(builder, document_number: str, limit: int) -> Dict[str, Any]:
    """Query graph for a specific document with all relationships."""
    with builder.driver.session(database=builder.database) as session:
        # Get all nodes related to this document
        nodes_query = """
        MATCH (doc)
        WHERE (doc:Luật OR doc:`Nghị định` OR doc:`Thông tư`)
          AND doc.document_number = $doc_num
        WITH doc
        
        // Get chapters
        OPTIONAL MATCH (chapter:Chương)-[:THUOC_VE]->(doc)
        
        // Get articles (can be under chapter directly or via section)
        OPTIONAL MATCH (article:Điều)-[:THUOC_VE]->(chapter)
        
        // Get clauses
        OPTIONAL MATCH (clause:Khoản)-[:THUOC_VE]->(article)
        
        // Get points
        OPTIONAL MATCH (point:Điểm)-[:THUOC_VE]->(clause)
        
        WITH doc, 
             collect(DISTINCT chapter) as chapters,
             collect(DISTINCT article) as articles,
             collect(DISTINCT clause) as clauses,
             collect(DISTINCT point) as points
        RETURN doc, chapters, articles, clauses, points
        """
        
        result = session.run(nodes_query, doc_num=document_number)
        record = result.single()
        
        if not record:
            return {"nodes": [], "relationships": [], "total_nodes": 0, "total_relationships": 0}
        
        nodes = []
        relationships = []
        node_ids = set()
        
        # Add document node
        doc_node = _format_node(record["doc"])
        if doc_node:
            nodes.append(doc_node)
            node_ids.add(doc_node["id"])
        
        # Add chapters with relationships to document
        chapter_map = {}  # Map chapter_number to node
        for chapter in record["chapters"]:
            if chapter:
                chapter_node = _format_node(chapter)
                if chapter_node["id"] not in node_ids:
                    nodes.append(chapter_node)
                    node_ids.add(chapter_node["id"])
                    chapter_props = dict(chapter)
                    chapter_map[chapter_props.get("chapter_number")] = chapter_node
                    # Add relationship to document
                    relationships.append({
                        "source": chapter_node["id"],
                        "target": doc_node["id"],
                        "type": "THUOC_VE",
                        "label": "thuộc về"
                    })
        
        # Add articles with relationships to chapters
        article_map = {}  # Map article_id to node
        for article in record["articles"]:
            if article:
                article_node = _format_node(article)
                if article_node["id"] not in node_ids:
                    nodes.append(article_node)
                    node_ids.add(article_node["id"])
                    article_map[article_node["id"]] = article_node
                    
                    # Find parent chapter from article's id
                    article_id = article_node.get("properties", {}).get("id", "")
                    # Extract chapter number from id like "LAW=86_2015_QH13_CHUONG=VII_DIEU=51"
                    if "_CHUONG=" in article_id:
                        parts = article_id.split("_CHUONG=")
                        if len(parts) > 1:
                            chapter_part = parts[1].split("_")[0]
                            if chapter_part in chapter_map:
                                relationships.append({
                                    "source": article_node["id"],
                                    "target": chapter_map[chapter_part]["id"],
                                    "type": "THUOC_VE",
                                    "label": "thuộc về"
                                })
        
        # Add clauses with relationships to articles
        clause_map = {}
        for clause in record["clauses"][:100]:  # Limit for performance
            if clause:
                clause_node = _format_node(clause)
                if clause_node["id"] not in node_ids:
                    nodes.append(clause_node)
                    node_ids.add(clause_node["id"])
                    clause_map[clause_node["id"]] = clause_node
                    
                    # Find parent article from clause's id
                    clause_id = clause_node.get("properties", {}).get("id", "")
                    # Extract article part from id like "LAW=86_2015_QH13_CHUONG=VII_DIEU=51_KHOAN=1"
                    if "_DIEU=" in clause_id and "_KHOAN=" in clause_id:
                        # Get the article id (everything before _KHOAN=)
                        article_id = clause_id.rsplit("_KHOAN=", 1)[0]
                        # Find matching article
                        for art_id, art_node in article_map.items():
                            art_props_id = art_node.get("properties", {}).get("id", "")
                            if art_props_id == article_id:
                                relationships.append({
                                    "source": clause_node["id"],
                                    "target": art_node["id"],
                                    "type": "THUOC_VE",
                                    "label": "thuộc về"
                                })
                                break
        
        # Add points with relationships to clauses
        for point in record["points"][:50]:  # Limit for performance
            if point:
                point_node = _format_node(point)
                if point_node["id"] not in node_ids:
                    nodes.append(point_node)
                    node_ids.add(point_node["id"])
                    
                    # Find parent clause from point's id
                    point_id = point_node.get("properties", {}).get("id", "")
                    if "_KHOAN=" in point_id and "_DIEM=" in point_id:
                        clause_id = point_id.rsplit("_DIEM=", 1)[0]
                        for cl_id, cl_node in clause_map.items():
                            cl_props_id = cl_node.get("properties", {}).get("id", "")
                            if cl_props_id == clause_id:
                                relationships.append({
                                    "source": point_node["id"],
                                    "target": cl_node["id"],
                                    "type": "THUOC_VE",
                                    "label": "thuộc về"
                                })
                                break
        
        return {
            "nodes": nodes[:limit],
            "relationships": relationships,
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
            "document_number": document_number
        }


def _query_graphs_by_type(builder, doc_kind: str, limit: int) -> Dict[str, Any]:
    """Query graphs filtered by document type."""
    # Map doc_kind to Vietnamese label
    label_map = {
        "LAW": "Luật",
        "DECREE": "Nghị định", 
        "CIRCULAR": "Thông tư"
    }
    label = label_map.get(doc_kind.upper(), "Luật")
    
    with builder.driver.session(database=builder.database) as session:
        query = f"""
        MATCH (doc:`{label}`)
        OPTIONAL MATCH (doc)-[r1:THUOC_VE]-(chapter:Chương)
        OPTIONAL MATCH (chapter)-[r2:THUOC_VE]-(article:Điều)
        WITH doc, 
             collect(distinct chapter) as chapters,
             collect(distinct article) as articles,
             collect(distinct r1) as rels1,
             collect(distinct r2) as rels2
        RETURN doc, chapters, articles, rels1, rels2
        LIMIT $limit
        """
        
        result = session.run(query, limit=limit)
        
        all_nodes = []
        all_rels = []
        
        for record in result:
            doc_node = _format_node(record["doc"])
            all_nodes.append(doc_node)
            
            for chapter in record["chapters"]:
                if chapter:
                    all_nodes.append(_format_node(chapter))
            
            for article in record["articles"]:
                if article:
                    all_nodes.append(_format_node(article))
            
            for rel in record["rels1"]:
                if rel:
                    all_rels.append(_format_relationship(rel))
            
            for rel in record["rels2"]:
                if rel:
                    all_rels.append(_format_relationship(rel))
        
        # Remove duplicates
        unique_nodes = {n["id"]: n for n in all_nodes}
        unique_rels = {(r["source"], r["target"], r["type"]): r for r in all_rels}
        
        return {
            "nodes": list(unique_nodes.values())[:limit],
            "relationships": list(unique_rels.values()),
            "total_nodes": len(unique_nodes),
            "total_relationships": len(unique_rels),
            "doc_kind": doc_kind
        }


def _query_all_graphs(builder, limit: int) -> Dict[str, Any]:
    """Query overview of all documents in the graph."""
    with builder.driver.session(database=builder.database) as session:
        # Get all document nodes with their chapters
        query = """
        MATCH (doc)
        WHERE doc:Luật OR doc:`Nghị định` OR doc:`Thông tư`
        OPTIONAL MATCH (doc)<-[:THUOC_VE]-(chapter:Chương)
        OPTIONAL MATCH (chapter)<-[:THUOC_VE]-(article:Điều)
        WITH doc, 
             collect(distinct chapter)[0..5] as chapters,
             count(distinct article) as article_count
        RETURN doc, chapters, article_count
        ORDER BY doc.effective_date DESC
        LIMIT $limit
        """
        
        result = session.run(query, limit=limit)
        
        nodes = []
        relationships = []
        
        for record in result:
            doc_node = _format_node(record["doc"])
            doc_node["article_count"] = record["article_count"]
            nodes.append(doc_node)
            
            for chapter in record["chapters"]:
                if chapter:
                    chapter_node = _format_node(chapter)
                    nodes.append(chapter_node)
                    relationships.append({
                        "source": chapter_node["id"],
                        "target": doc_node["id"],
                        "type": "THUOC_VE",
                        "label": "thuộc về"
                    })
        
        # Remove duplicate nodes
        unique_nodes = {n["id"]: n for n in nodes}
        
        return {
            "nodes": list(unique_nodes.values()),
            "relationships": relationships,
            "total_nodes": len(unique_nodes),
            "total_relationships": len(relationships)
        }


def _format_nodes(nodes) -> List[Dict[str, Any]]:
    """Format Neo4j nodes for JSON response."""
    return [_format_node(n) for n in nodes if n]


def _format_node(node) -> Dict[str, Any]:
    """Format a single Neo4j node."""
    if not node:
        return None
    
    props = dict(node)
    labels = list(node.labels) if hasattr(node, 'labels') else []
    
    # Determine node type from labels
    node_type = "unknown"
    type_priority = ["Luật", "Nghị định", "Thông tư", "Chương", "Mục", "Điều", "Khoản", "Điểm", 
                     "Khái niệm", "Hành vi cấm", "Chế tài", "Quyền", "Nghĩa vụ", "Chủ thể"]
    
    for t in type_priority:
        if t in labels:
            node_type = t
            break
    
    return {
        "id": str(node.element_id) if hasattr(node, 'element_id') else props.get("id", str(id(node))),
        "type": node_type,
        "labels": labels,
        "properties": props,
        "name": props.get("name") or props.get("title") or props.get("content", "")[:100],
        "document_number": props.get("document_number"),
        "number": props.get("number") or props.get("article_number") or props.get("chapter_number")
    }


def _format_relationships(relationships) -> List[Dict[str, Any]]:
    """Format Neo4j relationships for JSON response."""
    return [_format_relationship(r) for r in relationships if r]


def _format_relationship(rel) -> Dict[str, Any]:
    """Format a single Neo4j relationship."""
    if not rel:
        return None
    
    return {
        "source": str(rel.start_node.element_id) if hasattr(rel, 'start_node') else None,
        "target": str(rel.end_node.element_id) if hasattr(rel, 'end_node') else None,
        "type": rel.type if hasattr(rel, 'type') else "RELATED",
        "label": rel.type.lower().replace("_", " ") if hasattr(rel, 'type') else "related",
        "properties": dict(rel) if rel else {}
    }


@router.get("/search")
async def search_knowledge_graph(
    query: str = Query(..., description="Search query"),
    doc_kind: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(20, description="Maximum results to return")
):
    """
    Search in Knowledge Graph.
    
    Searches across articles, clauses, and concepts for matching content.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            with builder.driver.session(database=builder.database) as session:
                # Full-text search across relevant nodes
                search_query = """
                CALL db.index.fulltext.queryNodes('legal_content_index', $query)
                YIELD node, score
                WHERE score > 0.5
                RETURN node, score
                ORDER BY score DESC
                LIMIT $limit
                """
                
                # Fallback to CONTAINS search if fulltext index doesn't exist
                fallback_query = """
                MATCH (n)
                WHERE (n:Điều OR n:Khoản OR n:`Khái niệm` OR n:`Hành vi cấm`)
                  AND (toLower(n.content) CONTAINS toLower($query) 
                       OR toLower(n.name) CONTAINS toLower($query)
                       OR toLower(n.title) CONTAINS toLower($query))
                RETURN n as node, 1.0 as score
                LIMIT $limit
                """
                
                try:
                    result = session.run(search_query, query=query, limit=limit)
                    records = list(result)
                except Exception:
                    # Fallback if fulltext index doesn't exist
                    result = session.run(fallback_query, query=query, limit=limit)
                    records = list(result)
                
                results = []
                for record in records:
                    node = record["node"]
                    results.append({
                        "node": _format_node(node),
                        "score": record["score"]
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "total": len(results)
                }
                
    except Exception as e:
        logger.error(f"Failed to search KG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents():
    """
    List all documents in the Knowledge Graph.
    
    Returns a list of all legal documents with basic metadata.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            with builder.driver.session(database=builder.database) as session:
                query = """
                MATCH (doc)
                WHERE doc:Luật OR doc:`Nghị định` OR doc:`Thông tư`
                OPTIONAL MATCH (doc)<-[:THUOC_VE]-(chapter:Chương)
                OPTIONAL MATCH (chapter)<-[:THUOC_VE]-(article:Điều)
                WITH doc, count(distinct chapter) as chapter_count, count(distinct article) as article_count
                RETURN doc, chapter_count, article_count
                ORDER BY doc.effective_date DESC
                """
                
                result = session.run(query)
                
                documents = []
                for record in result:
                    doc = record["doc"]
                    props = dict(doc)
                    labels = list(doc.labels)
                    
                    # Determine doc_kind from labels
                    doc_kind = "UNKNOWN"
                    if "Luật" in labels:
                        doc_kind = "LAW"
                    elif "Nghị định" in labels:
                        doc_kind = "DECREE"
                    elif "Thông tư" in labels:
                        doc_kind = "CIRCULAR"
                    
                    documents.append({
                        "document_number": props.get("document_number"),
                        "name": props.get("name") or props.get("title"),
                        "doc_kind": doc_kind,
                        "issuer": props.get("issuer"),
                        "effective_date": props.get("effective_date"),
                        "chapter_count": record["chapter_count"],
                        "article_count": record["article_count"]
                    })
                
                return {
                    "documents": documents,
                    "total": len(documents)
                }
                
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/structure")
async def get_document_structure(document_number: str = Query(..., description="Document number")):
    """
    Get full hierarchical structure of a document with content.
    
    Returns document with all chapters, articles, clauses, and their content.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            with builder.driver.session(database=builder.database) as session:
                # Get document with full hierarchy
                query = """
                MATCH (doc)
                WHERE (doc:Luật OR doc:`Nghị định` OR doc:`Thông tư`)
                  AND doc.document_number = $doc_num
                WITH doc
                OPTIONAL MATCH (chapter:Chương)-[:THUOC_VE]->(doc)
                OPTIONAL MATCH (article:Điều)-[:THUOC_VE]->(chapter)
                OPTIONAL MATCH (clause:Khoản)-[:THUOC_VE]->(article)
                OPTIONAL MATCH (point:Điểm)-[:THUOC_VE]->(clause)
                WITH doc, chapter, article, clause, collect(distinct point) as points
                WITH doc, chapter, article, collect({clause: clause, points: points}) as clauses_data
                WITH doc, chapter, collect({article: article, clauses: clauses_data}) as articles_data
                WITH doc, collect({chapter: chapter, articles: articles_data}) as chapters_data
                RETURN doc, chapters_data
                LIMIT 1
                """
                
                result = session.run(query, doc_num=document_number)
                record = result.single()
                
                if not record:
                    raise HTTPException(status_code=404, detail=f"Document {document_number} not found")
                
                doc = record["doc"]
                doc_props = dict(doc)
                
                # Build tree structure
                tree = {
                    "id": doc_props.get("id", f"DOC={document_number}"),
                    "type": list(doc.labels)[0] if doc.labels else "Document",
                    "document_number": document_number,
                    "name": doc_props.get("name") or doc_props.get("title"),
                    "content": doc_props.get("content", ""),
                    "properties": doc_props,
                    "children": []
                }
                
                # Process chapters
                seen_chapters = set()
                for chapter_data in record["chapters_data"]:
                    chapter = chapter_data.get("chapter")
                    if not chapter:
                        continue
                    
                    ch_props = dict(chapter)
                    ch_id = ch_props.get("id") or ch_props.get("chapter_number")
                    
                    if ch_id in seen_chapters:
                        continue
                    seen_chapters.add(ch_id)
                    
                    chapter_node = {
                        "id": ch_id,
                        "type": "Chương",
                        "name": ch_props.get("name") or f"Chương {ch_props.get('chapter_number', '')}",
                        "number": ch_props.get("chapter_number"),
                        "title": ch_props.get("title") or ch_props.get("chapter_title", ""),
                        "content": ch_props.get("content", ""),
                        "properties": ch_props,
                        "children": []
                    }
                    
                    # Process articles in this chapter
                    seen_articles = set()
                    for article_data in chapter_data.get("articles", []):
                        article = article_data.get("article")
                        if not article:
                            continue
                        
                        art_props = dict(article)
                        art_id = art_props.get("id") or art_props.get("article_number")
                        
                        if art_id in seen_articles:
                            continue
                        seen_articles.add(art_id)
                        
                        article_node = {
                            "id": art_id,
                            "type": "Điều",
                            "name": f"Điều {art_props.get('article_number', '')}",
                            "number": art_props.get("article_number"),
                            "title": art_props.get("title") or art_props.get("article_title", ""),
                            "content": art_props.get("content", ""),
                            "properties": art_props,
                            "children": []
                        }
                        
                        # Process clauses
                        for clause_data in article_data.get("clauses", []):
                            clause = clause_data.get("clause")
                            if not clause:
                                continue
                            
                            cl_props = dict(clause)
                            clause_node = {
                                "id": cl_props.get("id") or cl_props.get("clause_number"),
                                "type": "Khoản",
                                "name": f"Khoản {cl_props.get('clause_number', '')}",
                                "number": cl_props.get("clause_number"),
                                "content": cl_props.get("content", ""),
                                "properties": cl_props,
                                "children": []
                            }
                            
                            # Process points
                            for point in clause_data.get("points", []):
                                if not point:
                                    continue
                                pt_props = dict(point)
                                point_node = {
                                    "id": pt_props.get("id") or pt_props.get("point_label"),
                                    "type": "Điểm",
                                    "name": f"Điểm {pt_props.get('point_label', '')}",
                                    "label": pt_props.get("point_label"),
                                    "content": pt_props.get("content", ""),
                                    "properties": pt_props,
                                    "children": []
                                }
                                clause_node["children"].append(point_node)
                            
                            article_node["children"].append(clause_node)
                        
                        chapter_node["children"].append(article_node)
                    
                    # Sort articles by number
                    chapter_node["children"].sort(key=lambda x: _parse_number(x.get("number")))
                    tree["children"].append(chapter_node)
                
                # Sort chapters by Roman numeral
                tree["children"].sort(key=lambda x: _roman_to_int(x.get("number", "")))
                
                # Count statistics
                stats = _count_tree_stats(tree)
                
                return {
                    "tree": tree,
                    "stats": stats,
                    "document_number": document_number
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_number(num_str):
    """Parse a number string, handling None and non-numeric values."""
    if not num_str:
        return 0
    try:
        return int(num_str)
    except (ValueError, TypeError):
        return 0


def _roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    if not roman:
        return 0
    roman = str(roman).upper()
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    result = 0
    for i, char in enumerate(roman):
        if char not in roman_map:
            continue
        curr = roman_map[char]
        next_val = roman_map.get(roman[i + 1], 0) if i + 1 < len(roman) else 0
        if curr < next_val:
            result -= curr
        else:
            result += curr
    return result


def _count_tree_stats(tree: Dict) -> Dict:
    """Count statistics from tree structure."""
    stats = {"chapters": 0, "articles": 0, "clauses": 0, "points": 0}
    
    def count_node(node, node_type):
        if node_type == "Chương":
            stats["chapters"] += 1
        elif node_type == "Điều":
            stats["articles"] += 1
        elif node_type == "Khoản":
            stats["clauses"] += 1
        elif node_type == "Điểm":
            stats["points"] += 1
        
        for child in node.get("children", []):
            count_node(child, child.get("type"))
    
    for child in tree.get("children", []):
        count_node(child, child.get("type"))
    
    return stats


@router.get("/node/{node_id}")
async def get_node_detail(node_id: str):
    """
    Get detailed information about a specific node.
    
    Returns all properties and related nodes.
    """
    try:
        from app.ingest.indexing.graph_builder import Neo4jGraphBuilder
        
        conn = get_neo4j_connection()
        
        with Neo4jGraphBuilder(uri=conn["uri"], user=conn["user"], password=conn["password"]) as builder:
            with builder.driver.session(database=builder.database) as session:
                # Find node by id property
                query = """
                MATCH (n)
                WHERE n.id = $node_id OR elementId(n) = $node_id
                OPTIONAL MATCH (n)-[r]-(related)
                RETURN n, labels(n) as labels, 
                       collect({rel_type: type(r), direction: CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END, node: related}) as relationships
                LIMIT 1
                """
                
                result = session.run(query, node_id=node_id)
                record = result.single()
                
                if not record:
                    raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
                
                node = record["n"]
                props = dict(node)
                labels = record["labels"]
                
                # Process relationships
                related_nodes = []
                for rel in record["relationships"]:
                    if rel["node"]:
                        rel_node = rel["node"]
                        related_nodes.append({
                            "relationship": rel["rel_type"],
                            "direction": rel["direction"],
                            "node": {
                                "id": dict(rel_node).get("id", str(rel_node.element_id)),
                                "type": list(rel_node.labels)[0] if rel_node.labels else "Unknown",
                                "name": dict(rel_node).get("name") or dict(rel_node).get("title") or dict(rel_node).get("content", "")[:50],
                                "properties": dict(rel_node)
                            }
                        })
                
                return {
                    "id": props.get("id", node_id),
                    "type": labels[0] if labels else "Unknown",
                    "labels": labels,
                    "name": props.get("name") or props.get("title"),
                    "content": props.get("content"),
                    "properties": props,
                    "related_nodes": related_nodes
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document")
async def delete_document(document_number: str = Query(..., description="Document number to delete")):
    """
    Delete a document and all its related nodes from the Knowledge Graph.
    
    This will delete:
    - The document node (Luật/Nghị định/Thông tư)
    - All related chapters (Chương)
    - All related sections (Mục)
    - All related articles (Điều)
    - All related clauses (Khoản)
    - All related points (Điểm)
    - All relationships between these nodes
    
    Args:
        document_number: The document number (e.g., "24-2018-QH14" or "67/2006/QH11")
    
    Returns:
        Status and count of deleted nodes
    """
    try:
        from neo4j import GraphDatabase
        
        conn = get_neo4j_connection()
        
        driver = GraphDatabase.driver(
            conn["uri"],
            auth=(conn["user"], conn["password"])
        )
        
        deleted_counts = {
            "total": 0
        }
        
        document_found_in_kg = False
        
        with driver.session() as session:
            # Check if document exists in KG
            check_query = """
            MATCH (doc)
            WHERE doc.document_number = $doc_num
            RETURN count(doc) as count
            """
            result = session.run(check_query, doc_num=document_number)
            record = result.single()
            
            if record and record["count"] > 0:
                document_found_in_kg = True
            else:
                # Try by ID prefix
                check_query2 = """
                MATCH (n)
                WHERE n.id STARTS WITH $prefix
                RETURN count(n) as count
                """
                for prefix in [f"DOC={document_number}", f"LAW={document_number}", 
                               f"DECREE={document_number}", f"CIRCULAR={document_number}"]:
                    result = session.run(check_query2, prefix=prefix)
                    record = result.single()
                    if record and record["count"] > 0:
                        document_found_in_kg = True
                        break
            
            # Delete from KG if found
            total_deleted = 0
            if document_found_in_kg:
                delete_by_prefix = """
                MATCH (n)
                WHERE n.id STARTS WITH $prefix
                WITH n LIMIT 500
                DETACH DELETE n
                RETURN count(*) as deleted
                """
                
                id_prefixes = [
                    f"DOC={document_number}",
                    f"LAW={document_number}",
                    f"DECREE={document_number}",
                    f"CIRCULAR={document_number}"
                ]
                
                for prefix in id_prefixes:
                    # Delete in batches until nothing left
                    while True:
                        result = session.run(delete_by_prefix, prefix=prefix)
                        record = result.single()
                        deleted = record["deleted"] if record else 0
                        total_deleted += deleted
                        if deleted < 500:
                            break
                
                # Also delete by document_number property
                delete_by_doc_num = """
                MATCH (n)
                WHERE n.document_number = $doc_num
                WITH n LIMIT 500
                DETACH DELETE n
                RETURN count(*) as deleted
                """
                
                while True:
                    result = session.run(delete_by_doc_num, doc_num=document_number)
                    record = result.single()
                    deleted = record["deleted"] if record else 0
                    total_deleted += deleted
                    if deleted < 500:
                        break
            
            deleted_counts["total"] = total_deleted
        
        driver.close()
        
        # Also delete from job store
        jobs_deleted = 0
        try:
            from app.ingest.services.job_store import get_job_store
            job_store = get_job_store()
            
            # Get all jobs and find matching ones
            all_jobs, _ = await job_store.list_jobs(limit=1000)
            for job in all_jobs:
                job_law_id = getattr(job, 'law_id', None)
                job_doc_num = getattr(job, 'document_number', None)
                if job_law_id == document_number or job_doc_num == document_number:
                    # Delete directly from internal store
                    if hasattr(job_store, '_jobs'):
                        job_store._jobs.pop(job.job_id, None)
                        if hasattr(job_store, '_chunks'):
                            job_store._chunks.pop(job.job_id, None)
                        if hasattr(job_store, '_job_order') and job.job_id in job_store._job_order:
                            job_store._job_order.remove(job.job_id)
                    jobs_deleted += 1
                    logger.info(f"Deleted job {job.job_id} for document {document_number}")
        except Exception as e:
            logger.warning(f"Could not delete jobs: {e}")
        
        # Delete from Qdrant vector store
        qdrant_deleted = 0
        try:
            import os
            from app.shared.config.settings import settings
            from app.ingest.store.vector.qdrant_store import (
                get_qdrant_client, 
                delete_documents_by_law_id
            )
            
            qdrant_url = os.getenv("QDRANT_URL", settings.qdrant_url)
            qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
            
            client = get_qdrant_client(url=qdrant_url, api_key=qdrant_api_key if qdrant_api_key else None)
            qdrant_deleted = delete_documents_by_law_id(client, document_number)
            
            logger.info(f"Deleted {qdrant_deleted} chunks from Qdrant for {document_number}")
        except Exception as e:
            logger.warning(f"Could not delete from Qdrant: {e}")
        
        # Delete from OpenSearch
        opensearch_deleted = 0
        try:
            from app.search.adapters.opensearch_keyword_adapter import OpenSearchKeywordAdapter
            
            opensearch_adapter = OpenSearchKeywordAdapter()
            
            # Try to delete by various doc_id formats
            doc_id_formats = [
                document_number,
                document_number.replace("/", "_"),
                document_number.replace("/", "-"),
                f"DOC={document_number}",
                f"LAW={document_number}",
            ]
            
            for doc_id in doc_id_formats:
                try:
                    success = await opensearch_adapter.delete_document_index(doc_id)
                    if success:
                        opensearch_deleted += 1
                        logger.info(f"Deleted OpenSearch index for doc_id: {doc_id}")
                except Exception as e:
                    logger.debug(f"Could not delete OpenSearch index for {doc_id}: {e}")
            
            logger.info(f"Deleted {opensearch_deleted} indices from OpenSearch for {document_number}")
        except Exception as e:
            logger.warning(f"Could not delete from OpenSearch: {e}")
        
        logger.info(f"Deleted document {document_number}: Neo4j={total_deleted} nodes, Jobs={jobs_deleted}, Qdrant={qdrant_deleted}, OpenSearch={opensearch_deleted}")
        
        return {
            "status": "success",
            "message": f"Document {document_number} deleted successfully",
            "deleted": deleted_counts,
            "total_deleted": total_deleted,
            "jobs_deleted": jobs_deleted,
            "qdrant_deleted": qdrant_deleted,
            "opensearch_deleted": opensearch_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

