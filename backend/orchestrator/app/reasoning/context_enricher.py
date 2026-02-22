import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EnrichedContext:
    primary_content: str
    legal_citations: List[Dict[str, str]] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    related_questions: List[str] = field(default_factory=list)
    graph_entities: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_llm_context(self) -> str:
        parts = []
        
        # Primary content
        if self.primary_content:
            parts.append("=== NỘI DUNG CHÍNH ===")
            parts.append(self.primary_content)
            parts.append("")
        
        # Reasoning steps
        if self.reasoning_steps:
            parts.append("=== QUÁ TRÌNH SUY LUẬN ===")
            for i, step in enumerate(self.reasoning_steps, 1):
                parts.append(f"{i}. {step}")
            parts.append("")
        
        # Graph entities
        if self.graph_entities:
            parts.append("=== THỰC THỂ LIÊN QUAN ===")
            for entity in self.graph_entities[:10]:
                name = entity.get("name") or entity.get("title", "Unknown")
                etype = entity.get("type", "Node")
                content = entity.get("content", "")
                
                if content:
                    parts.append(f"• [{etype}] {name}")
                    # Truncate long content
                    if len(content) > 500:
                        content = content[:500] + "..."
                    parts.append(f"  {content}")
                else:
                    parts.append(f"• [{etype}] {name}")
            parts.append("")
        
        # Supporting evidence
        if self.supporting_evidence:
            parts.append("=== BẰNG CHỨNG HỖ TRỢ ===")
            for evidence in self.supporting_evidence[:5]:
                parts.append(f"• {evidence}")
            parts.append("")
        
        # Legal citations
        if self.legal_citations:
            parts.append("=== CƠ SỞ PHÁP LÝ ===")
            for citation in self.legal_citations:
                citation_str = citation.get("law", "")
                if citation.get("article"):
                    citation_str += f", Điều {citation['article']}"
                if citation.get("clause"):
                    citation_str += f", Khoản {citation['clause']}"
                if citation.get("point"):
                    citation_str += f", Điểm {citation['point']}"
                parts.append(f"• {citation_str}")
            parts.append("")
        
        # Related concepts
        if self.related_concepts:
            parts.append("=== KHÁI NIỆM LIÊN QUAN ===")
            parts.append(", ".join(self.related_concepts[:10]))
            parts.append("")
        
        return "\n".join(parts) if parts else "Không tìm thấy ngữ cảnh."
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_content": self.primary_content,
            "legal_citations": self.legal_citations,
            "supporting_evidence": self.supporting_evidence,
            "related_concepts": self.related_concepts,
            "related_questions": self.related_questions,
            "graph_entities": self.graph_entities,
            "reasoning_steps": self.reasoning_steps,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class ContextEnricher:
    def __init__(self, qa_data: Optional[Any] = None):
        self.qa_data = qa_data
        logger.info("ContextEnricher initialized")
    
    def enrich(
        self,
        query_components: Dict[str, Any],
        graph_results: Dict[str, Any],
        reasoning_chain: Optional[List[str]] = None,
        inferred_knowledge: Optional[Dict[str, Any]] = None
    ) -> EnrichedContext:
        # Extract primary content from graph results
        primary_content = self._extract_primary_content(graph_results)
        
        # Extract legal citations
        citations = self._extract_citations(graph_results)
        
        # Get supporting evidence
        evidence = self._get_supporting_evidence(
            query_components,
            graph_results
        )
        
        # Find related concepts
        related_concepts = self._find_related_concepts(
            query_components.get("concepts", []),
            graph_results
        )
        
        # Match with Q&A data if available
        related_questions = []
        if self.qa_data is not None:
            related_questions = self._find_related_questions(query_components)
        
        # Extract graph entities
        graph_entities = self._format_graph_entities(
            graph_results.get("nodes", [])
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            graph_results,
            citations,
            evidence
        )
        
        context = EnrichedContext(
            primary_content=primary_content,
            legal_citations=citations,
            supporting_evidence=evidence,
            related_concepts=related_concepts,
            related_questions=related_questions,
            graph_entities=graph_entities,
            reasoning_steps=reasoning_chain or [],
            confidence=confidence,
            metadata={
                "query": query_components.get("original_query", ""),
                "intent": query_components.get("intent", ""),
                "num_nodes": len(graph_results.get("nodes", [])),
                "num_relationships": len(graph_results.get("relationships", []))
            }
        )
        
        logger.info(
            f"Context enriched: {len(graph_entities)} entities, "
            f"{len(citations)} citations, confidence={confidence:.2f}"
        )
        
        return context
    
    def _extract_primary_content(self, graph_results: Dict[str, Any]) -> str:
        """Extract main content from graph results."""
        contents = []
        
        nodes = graph_results.get("nodes", [])
        
        for node in nodes:
            # Check various content fields
            content = (
                node.get("content") or
                node.get("full_text") or
                node.get("noi_dung") or
                node.get("text") or
                ""
            )
            
            if content:
                name = node.get("name") or node.get("title", "")
                if name:
                    contents.append(f"**{name}**\n{content}")
                else:
                    contents.append(content)
        
        return "\n\n".join(contents[:5])  # Limit to top 5
    
    def _extract_citations(
        self,
        graph_results: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Extract legal citations from graph results."""
        citations = []
        seen = set()
        
        nodes = graph_results.get("nodes", [])
        
        for node in nodes:
            node_type = node.get("type", "")
            
            # Extract from article nodes
            if "ARTICLE" in node_type.upper() or "DIEU" in node_type.upper():
                citation = {
                    "law": node.get("law_name", "") or node.get("ten_van_ban", ""),
                    "article": node.get("article_number", "") or node.get("so_dieu", ""),
                    "clause": node.get("clause_number", "") or node.get("so_khoan", ""),
                    "point": node.get("point_letter", "") or node.get("so_diem", "")
                }
                
                # Create unique key
                key = f"{citation['law']}-{citation['article']}-{citation['clause']}"
                if key not in seen and citation['article']:
                    seen.add(key)
                    citations.append(citation)
            
            # Extract from properties
            elif node.get("ten_van_ban") or node.get("law_name"):
                citation = {
                    "law": node.get("ten_van_ban", "") or node.get("law_name", ""),
                    "article": str(node.get("so_dieu", "") or node.get("article_number", "")),
                    "clause": str(node.get("so_khoan", "") or node.get("clause_number", "")),
                    "point": str(node.get("so_diem", "") or node.get("point_letter", ""))
                }
                
                key = f"{citation['law']}-{citation['article']}-{citation['clause']}"
                if key not in seen and (citation['law'] or citation['article']):
                    seen.add(key)
                    citations.append(citation)
        
        return citations
    
    def _get_supporting_evidence(
        self,
        query_components: Dict[str, Any],
        graph_results: Dict[str, Any]
    ) -> List[str]:
        """Get supporting evidence for the answer."""
        evidence = []
        
        # Extract from paths
        paths = graph_results.get("paths", [])
        for path in paths:
            path_desc = path.get("description", "")
            if path_desc:
                evidence.append(path_desc)
            
            # Or construct from node names
            node_names = path.get("node_names", [])
            if node_names:
                evidence.append(" → ".join(node_names))
        
        # Extract from relationships
        relationships = graph_results.get("relationships", [])
        for rel in relationships[:5]:  # Limit
            source = rel.get("source_name", "")
            target = rel.get("target_name", "")
            rel_type = rel.get("type", "")
            
            if source and target and rel_type:
                evidence.append(f"{source} [{rel_type}] {target}")
        
        return evidence[:10]  # Limit to 10
    
    def _find_related_concepts(
        self,
        query_concepts: List[str],
        graph_results: Dict[str, Any]
    ) -> List[str]:
        """Find concepts related to the query."""
        related = set(query_concepts)
        
        nodes = graph_results.get("nodes", [])
        
        for node in nodes:
            node_type = node.get("type", "").upper()
            
            # Concept nodes
            if "CONCEPT" in node_type or "KHAI_NIEM" in node_type:
                name = node.get("name", "")
                if name:
                    related.add(name)
            
            # Extract from properties
            concepts = node.get("concepts", [])
            if isinstance(concepts, list):
                related.update(concepts)
        
        return list(related)[:15]  # Limit to 15
    
    def _find_related_questions(
        self,
        query_components: Dict[str, Any]
    ) -> List[str]:
        """Find related questions from Q&A data."""
        if self.qa_data is None:
            return []
        
        related = []
        keywords = query_components.get("keywords", [])
        concepts = query_components.get("concepts", [])
        
        search_terms = keywords + concepts
        
        try:
            # Pandas DataFrame
            if hasattr(self.qa_data, 'iterrows'):
                for idx, row in self.qa_data.iterrows():
                    question = str(row.get("question", "")).lower()
                    
                    # Score based on keyword matches
                    score = sum(1 for term in search_terms if term.lower() in question)
                    
                    if score > 0:
                        related.append({
                            "question": row.get("question"),
                            "score": score
                        })
            
            # List of dicts
            elif isinstance(self.qa_data, list):
                for item in self.qa_data:
                    question = str(item.get("question", "")).lower()
                    score = sum(1 for term in search_terms if term.lower() in question)
                    
                    if score > 0:
                        related.append({
                            "question": item.get("question"),
                            "score": score
                        })
            
            # Sort by score and return top questions
            related.sort(key=lambda x: x["score"], reverse=True)
            return [r["question"] for r in related[:5] if r["question"]]
            
        except Exception as e:
            logger.warning(f"Error finding related questions: {e}")
            return []
    
    def _format_graph_entities(
        self,
        nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format graph nodes for display."""
        formatted = []
        
        for node in nodes:
            entity = {
                "name": (
                    node.get("name") or
                    node.get("title") or
                    node.get("ten_mon") or
                    node.get("ma_mon") or
                    node.get("article_id") or
                    "Unknown"
                ),
                "type": node.get("type") or node.get("node_type", "Node"),
                "content": (
                    node.get("content") or
                    node.get("full_text") or
                    node.get("noi_dung") or
                    node.get("text") or
                    ""
                )
            }
            
            # Add additional properties
            for key in ["so_dieu", "so_khoan", "ten_van_ban", "article_number"]:
                if node.get(key):
                    entity[key] = node[key]
            
            formatted.append(entity)
        
        return formatted
    
    def _calculate_confidence(
        self,
        graph_results: Dict[str, Any],
        citations: List[Dict[str, str]],
        evidence: List[str]
    ) -> float:
        """Calculate confidence score for the enriched context."""
        score = 0.5  # Base score
        
        # Boost for having nodes
        num_nodes = len(graph_results.get("nodes", []))
        if num_nodes > 0:
            score += min(0.2, num_nodes * 0.02)
        
        # Boost for citations
        if citations:
            score += min(0.2, len(citations) * 0.05)
        
        # Boost for evidence
        if evidence:
            score += min(0.1, len(evidence) * 0.02)
        
        return min(score, 1.0)
