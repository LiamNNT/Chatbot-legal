"""
Enhanced Symbolic Reasoning Agent

This agent extends GraphReasoningAgent with symbolic reasoning capabilities:
- Rule-based inference (R001-R008)
- Query analysis and intent detection
- Context enrichment for better LLM responses
- Hybrid reasoning: Rules + ReAct

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                  SymbolicReasoningAgent                     │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  QueryAnalyzer   │  │  RuleRegistry    │                │
│  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                           │
│           ▼                     ▼                           │
│  ┌──────────────────────────────────────┐                  │
│  │      SymbolicReasoningEngine         │                  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐ │                  │
│  │  │ R001   │  │ R002   │  │ R00N   │ │                  │
│  │  └────────┘  └────────┘  └────────┘ │                  │
│  └──────────────────────────────────────┘                  │
│                      │                                      │
│                      ▼                                      │
│  ┌──────────────────────────────────────┐                  │
│  │      ContextEnricher                 │                  │
│  │  (Merge rules + graph + Q&A)         │                  │
│  └──────────────────────────────────────┘                  │
│                      │                                      │
│                      ▼                                      │
│  ┌──────────────────────────────────────┐                  │
│  │   GraphReasoningAgent (ReAct)        │                  │
│  │   (For complex multi-hop queries)    │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .graph_reasoning_agent import (
    GraphReasoningAgent,
    GraphReasoningResult,
    GraphQueryType
)

logger = logging.getLogger(__name__)


class SymbolicQueryType(str, Enum):
    # Basic types (from GraphQueryType)
    LOCAL = "local"
    GLOBAL = "global"
    MULTI_HOP = "multi_hop"
    
    # Symbolic reasoning types
    HIERARCHICAL = "hierarchical"      # R001: Law structure queries
    CONCEPT = "concept"                # R002: Concept-law mapping
    OBLIGATION = "obligation"          # R003: Obligation inference
    RIGHTS = "rights"                  # R004: Rights protection
    TRANSITIVE = "transitive"          # R005: Related laws
    PROHIBITION = "prohibition"        # R006: Prohibited actions
    REQUIREMENT = "requirement"        # R007: Requirements
    CONTEXT = "context"                # R008: Full context retrieval


@dataclass
class SymbolicReasoningResult:
    query: str
    query_type: SymbolicQueryType
    
    # Rule-based results
    rules_applied: List[str] = field(default_factory=list)
    inference_chain: List[str] = field(default_factory=list)
    
    # Graph results
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    paths: List[Dict[str, Any]] = field(default_factory=list)
    
    # Enriched context
    legal_citations: List[Dict[str, str]] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    
    # Final output
    synthesized_context: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_context_string(self) -> str:
        """Convert to context string for AnswerAgent."""
        if self.synthesized_context:
            return self.synthesized_context
        
        parts = []
        
        # Add inference chain
        if self.inference_chain:
            parts.append("=== Quá trình suy luận ===")
            for i, step in enumerate(self.inference_chain, 1):
                parts.append(f"{i}. {step}")
            parts.append("")
        
        # Add rules applied
        if self.rules_applied:
            parts.append(f"=== Quy tắc áp dụng: {', '.join(self.rules_applied)} ===")
            parts.append("")
        
        # Add nodes with content
        if self.nodes:
            parts.append("=== Thông tin liên quan ===")
            for node in self.nodes[:10]:
                name = (
                    node.get("name") or 
                    node.get("title") or
                    node.get("article_title") or
                    "Unknown"
                )
                node_type = node.get("type", "Node")
                content = (
                    node.get("content") or
                    node.get("full_text") or
                    node.get("article_content") or
                    ""
                )
                
                parts.append(f"• [{node_type}] {name}")
                if content:
                    # Truncate long content
                    if len(content) > 500:
                        content = content[:500] + "..."
                    parts.append(f"  {content}")
                parts.append("")
        
        # Add legal citations
        if self.legal_citations:
            parts.append("=== Cơ sở pháp lý ===")
            for citation in self.legal_citations[:5]:
                citation_str = citation.get("law", "")
                if citation.get("article"):
                    citation_str += f", Điều {citation['article']}"
                if citation.get("clause"):
                    citation_str += f", Khoản {citation['clause']}"
                parts.append(f"• {citation_str}")
            parts.append("")
        
        # Add related concepts
        if self.related_concepts:
            parts.append("=== Khái niệm liên quan ===")
            parts.append(", ".join(self.related_concepts[:10]))
            parts.append("")
        
        return "\n".join(parts) if parts else "Không tìm thấy ngữ cảnh."


class SymbolicReasoningAgent:
    def __init__(
        self,
        graph_adapter,
        symbolic_engine=None,
        llm_port=None,
        react_model: Optional[str] = None
    ):
        self.graph_adapter = graph_adapter
        self.llm_port = llm_port
        self.react_model = react_model
        
        # Initialize symbolic reasoning engine
        self.symbolic_engine = symbolic_engine
        if not self.symbolic_engine:
            self._init_symbolic_engine()
        
        # Initialize base GraphReasoningAgent for ReAct
        self.graph_agent = GraphReasoningAgent(
            graph_adapter=graph_adapter,
            llm_port=llm_port,
            react_model=react_model
        )
        
        logger.info("SymbolicReasoningAgent initialized with hybrid capabilities")
    
    def _init_symbolic_engine(self):
        """Initialize symbolic reasoning engine."""
        try:
            from ..reasoning.symbolic_engine import (
                SymbolicReasoningEngine,
                ReasoningMode
            )
            from ..reasoning.symbolic_graph_extension import SymbolicGraphExtension
            
            # Wrap adapter with symbolic extension
            symbolic_ext = SymbolicGraphExtension(self.graph_adapter)
            
            self.symbolic_engine = SymbolicReasoningEngine(
                graph_adapter=symbolic_ext,
                mode=ReasoningMode.HYBRID,
                llm_port=self.llm_port
            )
            
            logger.info("Symbolic engine initialized in HYBRID mode")
            
        except ImportError as e:
            logger.warning(f"Could not import symbolic engine: {e}")
            self.symbolic_engine = None
    
    async def reason(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        force_mode: Optional[str] = None
    ) -> SymbolicReasoningResult:
        logger.info(f"SymbolicReasoningAgent processing: {query[:100]}...")
        
        # Determine query type and mode
        query_type = self._classify_query(query)
        
        if force_mode == "rule" or (self.symbolic_engine and query_type in [
            SymbolicQueryType.HIERARCHICAL,
            SymbolicQueryType.CONCEPT,
            SymbolicQueryType.CONTEXT
        ]):
            # Use rule-based symbolic reasoning
            return await self._rule_based_reasoning(query, query_type)
        
        elif force_mode == "graph" or query_type in [
            SymbolicQueryType.MULTI_HOP,
            SymbolicQueryType.GLOBAL
        ]:
            # Use graph ReAct reasoning
            return await self._graph_reasoning(query, context)
        
        else:
            # Use hybrid: rules first, then graph if needed
            return await self._hybrid_reasoning(query, query_type, context)
    
    def _classify_query(self, query: str) -> SymbolicQueryType:
        query_lower = query.lower()
        
        # Check for prohibition queries (R006)
        if any(kw in query_lower for kw in [
            "có được", "có thể", "nghiêm cấm", "cấm",
            "vi phạm", "không được"
        ]):
            return SymbolicQueryType.PROHIBITION
        
        # Check for obligation queries (R003)
        if any(kw in query_lower for kw in [
            "trách nhiệm", "nghĩa vụ", "phải", "bắt buộc"
        ]):
            return SymbolicQueryType.OBLIGATION
        
        # Check for rights queries (R004)
        if any(kw in query_lower for kw in [
            "quyền", "được bảo vệ", "đảm bảo"
        ]):
            return SymbolicQueryType.RIGHTS
        
        # Check for specific article references (R001, R008)
        import re
        if re.search(r'[Đđ]iều\s+\d+', query) or re.search(r'[Kk]hoản\s+\d+', query):
            return SymbolicQueryType.CONTEXT
        
        # Check for concept definitions (R002)
        if any(kw in query_lower for kw in [
            "là gì", "nghĩa là", "định nghĩa", "khái niệm"
        ]):
            return SymbolicQueryType.CONCEPT
        
        # Check for relationship queries (R005)
        if any(kw in query_lower for kw in [
            "liên quan", "quan hệ", "so với", "so sánh"
        ]):
            return SymbolicQueryType.TRANSITIVE
        
        # Check for requirement queries (R007)
        if any(kw in query_lower for kw in [
            "điều kiện", "yêu cầu", "cần có", "tiêu chuẩn"
        ]):
            return SymbolicQueryType.REQUIREMENT
        
        # Default to local for simple queries
        return SymbolicQueryType.LOCAL
    
    async def _rule_based_reasoning(
        self,
        query: str,
        query_type: SymbolicQueryType
    ) -> SymbolicReasoningResult:
        """Execute rule-based symbolic reasoning."""
        result = SymbolicReasoningResult(
            query=query,
            query_type=query_type
        )
        
        if not self.symbolic_engine:
            logger.warning("Symbolic engine not available, falling back to graph")
            return await self._graph_reasoning(query)
        
        try:
            # Execute symbolic reasoning
            symbolic_result = await self.symbolic_engine.reason(query)
            
            # Convert to our result format
            result.rules_applied = [r["rule_id"] for r in symbolic_result.rules_applied]
            result.inference_chain = symbolic_result.inference_chain
            result.nodes = symbolic_result.graph_data.get("nodes", [])
            result.relationships = symbolic_result.graph_data.get("relationships", [])
            result.paths = symbolic_result.graph_data.get("paths", [])
            
            # Extract from enriched context
            ctx = symbolic_result.context
            result.legal_citations = ctx.legal_citations
            result.related_concepts = ctx.related_concepts
            result.confidence = ctx.confidence
            
            # Build synthesized context
            result.synthesized_context = ctx.to_llm_context()
            
            logger.info(
                f"Rule-based reasoning complete: "
                f"rules={result.rules_applied}, "
                f"nodes={len(result.nodes)}"
            )
            
        except Exception as e:
            logger.error(f"Rule-based reasoning failed: {e}")
            result.inference_chain.append(f"Error: {str(e)}")
            result.confidence = 0.3
        
        return result
    
    async def _graph_reasoning(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SymbolicReasoningResult:
        """Execute graph-based ReAct reasoning."""
        result = SymbolicReasoningResult(
            query=query,
            query_type=SymbolicQueryType.MULTI_HOP
        )
        
        try:
            # Use GraphReasoningAgent
            graph_result = await self.graph_agent.reason(query, context or {})
            
            # Convert GraphReasoningResult to SymbolicReasoningResult
            result.nodes = graph_result.nodes
            result.relationships = graph_result.relationships
            result.paths = graph_result.paths
            result.inference_chain = graph_result.reasoning_steps
            result.confidence = graph_result.confidence
            result.synthesized_context = graph_result.to_context_string()
            
            # Extract citations from nodes
            result.legal_citations = self._extract_citations_from_nodes(result.nodes)
            
            logger.info(
                f"Graph reasoning complete: "
                f"nodes={len(result.nodes)}, "
                f"confidence={result.confidence:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Graph reasoning failed: {e}")
            result.inference_chain.append(f"Error: {str(e)}")
            result.confidence = 0.3
        
        return result
    
    async def _hybrid_reasoning(
        self,
        query: str,
        query_type: SymbolicQueryType,
        context: Optional[Dict[str, Any]] = None
    ) -> SymbolicReasoningResult:
        """
        Execute hybrid reasoning: rules first, then graph if needed.
        
        Strategy:
        1. Apply rule-based reasoning
        2. If results insufficient, augment with graph reasoning
        3. Merge and enrich results
        """
        # Step 1: Try rule-based first
        rule_result = await self._rule_based_reasoning(query, query_type)
        
        # Check if we have sufficient results
        if rule_result.confidence >= 0.7 and len(rule_result.nodes) >= 3:
            logger.info("Rule-based result sufficient, skipping graph reasoning")
            return rule_result
        
        # Step 2: Augment with graph reasoning
        logger.info("Augmenting with graph reasoning")
        graph_result = await self._graph_reasoning(query, context)
        
        # Step 3: Merge results
        merged = self._merge_results(rule_result, graph_result)
        
        return merged
    
    def _merge_results(
        self,
        rule_result: SymbolicReasoningResult,
        graph_result: SymbolicReasoningResult
    ) -> SymbolicReasoningResult:
        """Merge rule-based and graph results."""
        merged = SymbolicReasoningResult(
            query=rule_result.query,
            query_type=rule_result.query_type
        )
        
        # Combine inference chains
        merged.inference_chain = rule_result.inference_chain.copy()
        merged.inference_chain.append("--- Graph augmentation ---")
        merged.inference_chain.extend(graph_result.inference_chain)
        
        # Merge nodes (deduplicate by ID)
        seen_ids = set()
        for node in rule_result.nodes + graph_result.nodes:
            node_id = node.get("id") or node.get("name")
            if node_id and node_id not in seen_ids:
                seen_ids.add(node_id)
                merged.nodes.append(node)
        
        # Merge relationships
        merged.relationships = rule_result.relationships + graph_result.relationships
        
        # Merge paths
        merged.paths = rule_result.paths + graph_result.paths
        
        # Merge citations (deduplicate)
        seen_citations = set()
        for citation in rule_result.legal_citations + graph_result.legal_citations:
            key = f"{citation.get('law')}-{citation.get('article')}"
            if key not in seen_citations:
                seen_citations.add(key)
                merged.legal_citations.append(citation)
        
        # Merge concepts
        merged.related_concepts = list(set(
            rule_result.related_concepts + graph_result.related_concepts
        ))
        
        # Rules from rule-based
        merged.rules_applied = rule_result.rules_applied
        
        # Average confidence
        merged.confidence = (rule_result.confidence + graph_result.confidence) / 2
        
        # Build merged context
        merged.synthesized_context = merged.to_context_string()
        
        return merged
    
    def _extract_citations_from_nodes(
        self,
        nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Extract legal citations from node data."""
        citations = []
        seen = set()
        
        for node in nodes:
            citation = {}
            
            # Try different field names
            law = (
                node.get("law_name") or
                node.get("ten_van_ban") or
                node.get("law") or
                ""
            )
            article = (
                node.get("article_number") or
                node.get("so_dieu") or
                ""
            )
            clause = (
                node.get("clause_number") or
                node.get("so_khoan") or
                ""
            )
            
            if law or article:
                citation = {
                    "law": str(law),
                    "article": str(article),
                    "clause": str(clause)
                }
                
                key = f"{law}-{article}"
                if key not in seen:
                    seen.add(key)
                    citations.append(citation)
        
        return citations
