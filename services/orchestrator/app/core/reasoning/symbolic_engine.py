"""
Symbolic Reasoning Engine for Legal Knowledge Graph

Main engine that orchestrates:
1. Query Analysis → Extract components from user query
2. Rule Selection → Select applicable reasoning rules
3. Graph Traversal → Execute graph queries based on rules
4. Inference → Apply symbolic reasoning
5. Context Enrichment → Combine results for LLM

This is the core module implementing the symbolic reasoning pipeline.

Architecture:
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query Analyzer │  ← Natural Language Processing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Rule Matcher   │  ← Match query to reasoning rules
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Graph Traversal │  ← Navigate knowledge graph
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Fusion  │  ← Combine multiple sources
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Answer Synthesis │  ← Generate final response
└─────────────────┘
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

from .query_analyzer import QueryAnalyzer, QueryComponents
from .reasoning_rules import (
    ReasoningRule,
    ReasoningRuleRegistry,
    RuleID,
    LEGAL_REASONING_RULES
)
from .context_enricher import ContextEnricher, EnrichedContext

logger = logging.getLogger(__name__)


class ReasoningMode(str, Enum):
    RULE_BASED = "rule_based"       # Pure rule-based inference
    HYBRID = "hybrid"               # Rules + LLM reasoning
    REACT = "react"                 # Full ReAct with LLM


@dataclass
class ReasoningResult:
    query: str
    mode: ReasoningMode
    context: EnrichedContext
    rules_applied: List[Dict[str, Any]] = field(default_factory=list)
    inference_chain: List[str] = field(default_factory=list)
    graph_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_context_string(self) -> str:
        """Get formatted context string for LLM."""
        return self.context.to_llm_context()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "mode": self.mode.value,
            "context": self.context.to_dict(),
            "rules_applied": self.rules_applied,
            "inference_chain": self.inference_chain,
            "graph_data": self.graph_data
        }


class SymbolicReasoningEngine:
    def __init__(
        self,
        graph_adapter,
        mode: ReasoningMode = ReasoningMode.HYBRID,
        custom_rules: Optional[List[ReasoningRule]] = None,
        llm_port = None
    ):
        self.graph_adapter = graph_adapter
        self.mode = mode
        self.llm_port = llm_port
        
        # Initialize components
        self.query_analyzer = QueryAnalyzer()
        self.rule_registry = ReasoningRuleRegistry(custom_rules)
        self.context_enricher = ContextEnricher()
        
        logger.info(
            f"SymbolicReasoningEngine initialized: "
            f"mode={mode.value}, rules={len(self.rule_registry.get_all())}"
        )
    
    async def reason(
        self,
        query: str,
        additional_context: Optional[Dict[str, Any]] = None,
        max_rules: int = 3
    ) -> ReasoningResult:
        logger.info(f"Starting symbolic reasoning for: {query[:100]}...")
        
        # Step 1: Analyze query
        query_components = self.query_analyzer.analyze(query)
        
        # Step 2: Select applicable rules
        applicable_rules = self.rule_registry.select_applicable_rules(
            query_components.to_dict(),
            max_rules=max_rules
        )
        
        # Step 3: Execute graph traversal based on rules
        graph_results = await self._execute_graph_queries(
            query_components,
            applicable_rules
        )
        
        # Step 4: Apply inference
        inference_chain = self._apply_inference(
            query_components,
            applicable_rules,
            graph_results
        )
        
        # Step 5: Enrich context
        enriched_context = self.context_enricher.enrich(
            query_components.to_dict(),
            graph_results,
            inference_chain
        )
        
        # Build result
        result = ReasoningResult(
            query=query,
            mode=self.mode,
            context=enriched_context,
            rules_applied=[
                {
                    "rule_id": r["rule"].rule_id.value,
                    "name": r["rule"].name,
                    "confidence": r["confidence"]
                }
                for r in applicable_rules
            ],
            inference_chain=inference_chain,
            graph_data=graph_results
        )
        
        logger.info(
            f"Reasoning complete: {len(applicable_rules)} rules applied, "
            f"{len(graph_results.get('nodes', []))} nodes found"
        )
        
        return result
    
    async def _execute_graph_queries(
        self,
        query_components: QueryComponents,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        all_nodes = []
        all_relationships = []
        all_paths = []
        
        for rule_info in rules:
            rule: ReasoningRule = rule_info["rule"]
            
            try:
                # Execute rule-specific query
                results = await self._execute_rule_query(rule, query_components)
                
                # Merge results
                all_nodes.extend(results.get("nodes", []))
                all_relationships.extend(results.get("relationships", []))
                all_paths.extend(results.get("paths", []))
                
            except Exception as e:
                logger.warning(f"Error executing rule {rule.rule_id}: {e}")
                continue
        
        # Deduplicate nodes by ID
        seen_ids = set()
        unique_nodes = []
        for node in all_nodes:
            node_id = node.get("id") or node.get("name")
            if node_id and node_id not in seen_ids:
                seen_ids.add(node_id)
                unique_nodes.append(node)
        
        return {
            "nodes": unique_nodes,
            "relationships": all_relationships,
            "paths": all_paths
        }
    
    async def _execute_rule_query(
        self,
        rule: ReasoningRule,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        results = {"nodes": [], "relationships": [], "paths": []}
        
        if not self.graph_adapter:
            logger.warning("No graph adapter available")
            return results
        
        # Dispatch based on rule type
        if rule.rule_id == RuleID.R001:
            # Hierarchical Structure - search by legal refs
            results = await self._query_hierarchical(query_components)
            
        elif rule.rule_id == RuleID.R002:
            # Concept Regulation - search concepts
            results = await self._query_concepts(query_components)
            
        elif rule.rule_id == RuleID.R003:
            # Obligation Inference
            results = await self._query_obligations(query_components)
            
        elif rule.rule_id == RuleID.R004:
            # Rights Protection
            results = await self._query_rights(query_components)
            
        elif rule.rule_id == RuleID.R005:
            # Transitive Application
            results = await self._query_transitive(query_components)
            
        elif rule.rule_id == RuleID.R006:
            # Prohibition Detection
            results = await self._query_prohibitions(query_components)
            
        elif rule.rule_id == RuleID.R007:
            # Requirement Verification
            results = await self._query_requirements(query_components)
            
        elif rule.rule_id == RuleID.R008:
            # Context-Based Retrieval
            results = await self._query_article_context(query_components)
        
        return results
    
    async def _query_hierarchical(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        results = {"nodes": [], "relationships": [], "paths": []}
        
        legal_refs = query_components.legal_refs
        
        for ref in legal_refs:
            ref_type = ref.get("type")
            ref_value = ref.get("value")
            
            if ref_type == "ARTICLE":
                # Search for specific article
                nodes = await self._search_articles(f"Điều {ref_value}")
                results["nodes"].extend(nodes)
                
            elif ref_type == "LAW":
                # Search for law
                nodes = await self._search_by_keyword(ref_value)
                results["nodes"].extend(nodes)
        
        return results
    
    async def _query_concepts(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query concepts and their regulations."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        for concept in query_components.concepts:
            nodes = await self._search_by_keyword(concept)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_obligations(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query obligations for entities."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        keywords = ["nghĩa vụ", "trách nhiệm", "phải"]
        
        for keyword in keywords:
            nodes = await self._search_by_keyword(keyword)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_rights(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query rights and protections."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        keywords = ["quyền", "bảo vệ", "được phép"]
        
        for keyword in keywords:
            nodes = await self._search_by_keyword(keyword)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_transitive(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query transitive relationships."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        # Search for related laws
        for concept in query_components.concepts:
            nodes = await self._search_by_keyword(concept)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_prohibitions(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query prohibitions."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        keywords = ["cấm", "nghiêm cấm", "không được", "vi phạm"]
        
        for keyword in keywords:
            nodes = await self._search_by_keyword(keyword)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_requirements(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query requirements."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        keywords = ["điều kiện", "yêu cầu", "tiêu chuẩn"]
        
        for keyword in keywords:
            nodes = await self._search_by_keyword(keyword)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _query_article_context(
        self,
        query_components: QueryComponents
    ) -> Dict[str, Any]:
        """Query full article context."""
        results = {"nodes": [], "relationships": [], "paths": []}
        
        # First try legal refs
        for ref in query_components.legal_refs:
            if ref.get("type") == "ARTICLE":
                nodes = await self._search_articles(f"Điều {ref.get('value')}")
                results["nodes"].extend(nodes)
        
        # Then try concepts
        for concept in query_components.concepts[:3]:  # Limit
            nodes = await self._search_by_keyword(concept)
            results["nodes"].extend(nodes)
        
        return results
    
    async def _search_articles(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for articles by term."""
        try:
            if hasattr(self.graph_adapter, 'search_articles'):
                return await self.graph_adapter.search_articles(search_term)
            elif hasattr(self.graph_adapter, 'keyword_search'):
                return await self.graph_adapter.keyword_search(search_term)
            return []
        except Exception as e:
            logger.warning(f"Error searching articles: {e}")
            return []
    
    async def _search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Search nodes by keyword."""
        try:
            if hasattr(self.graph_adapter, 'keyword_search'):
                return await self.graph_adapter.keyword_search(keyword)
            elif hasattr(self.graph_adapter, 'search_articles'):
                return await self.graph_adapter.search_articles(keyword)
            return []
        except Exception as e:
            logger.warning(f"Error searching by keyword: {e}")
            return []
    
    def _apply_inference(
        self,
        query_components: QueryComponents,
        rules: List[Dict[str, Any]],
        graph_results: Dict[str, Any]
    ) -> List[str]:
        """
        Apply inference rules to generate reasoning chain.
        
        Args:
            query_components: Query components
            rules: Applied rules
            graph_results: Graph query results
            
        Returns:
            List of inference steps
        """
        chain = []
        
        # Add query analysis step
        chain.append(
            f"Phân tích câu hỏi: Intent={query_components.intent}, "
            f"Concepts={query_components.concepts}"
        )
        
        # Add rule application steps
        for rule_info in rules:
            rule = rule_info["rule"]
            confidence = rule_info["confidence"]
            
            chain.append(
                f"Áp dụng quy tắc {rule.rule_id.value} ({rule.name_vi}): "
                f"Độ tin cậy {confidence:.0%}"
            )
        
        # Add result summary
        num_nodes = len(graph_results.get("nodes", []))
        if num_nodes > 0:
            chain.append(f"Tìm thấy {num_nodes} thực thể liên quan trong Knowledge Graph")
        else:
            chain.append("Không tìm thấy thực thể trực tiếp trong Knowledge Graph")
        
        return chain
    
    def set_mode(self, mode: ReasoningMode) -> None:
        """Change reasoning mode."""
        self.mode = mode
        logger.info(f"Reasoning mode changed to: {mode.value}")
    
    def add_rule(self, rule: ReasoningRule) -> None:
        """Add a custom reasoning rule."""
        self.rule_registry.register(rule)
        logger.info(f"Added custom rule: {rule.rule_id.value}")
