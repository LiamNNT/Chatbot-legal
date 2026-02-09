"""
Symbolic Reasoning Rules for Vietnamese Legal Knowledge Graph

This module defines the 8 core reasoning rules for legal inference:
- R001: Hierarchical Legal Structure (Luật → Điều → Khoản → Điểm)
- R002: Concept Regulation Mapping
- R003: Obligation Inference
- R004: Rights Protection
- R005: Transitive Legal Application
- R006: Prohibition Detection
- R007: Requirement Verification  
- R008: Context-Based Article Retrieval

Each rule defines:
- Pattern: Graph traversal pattern
- Logic: Inference logic
- Application: When and how to apply
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class RuleID(str, Enum):
    """Enumeration of reasoning rule IDs."""
    R001 = "R001"  # Hierarchical Structure
    R002 = "R002"  # Concept Regulation
    R003 = "R003"  # Obligation Inference
    R004 = "R004"  # Rights Protection
    R005 = "R005"  # Transitive Application
    R006 = "R006"  # Prohibition Detection
    R007 = "R007"  # Requirement Verification
    R008 = "R008"  # Context-Based Retrieval


@dataclass
class ReasoningRule:
    rule_id: RuleID
    name: str
    name_vi: str  # Vietnamese name
    pattern: str  # Graph pattern (e.g., "LAW CONTAINS_ARTICLE ARTICLE")
    logic: str  # Logic condition
    description: str
    description_vi: str
    
    # Applicability conditions
    applicable_intents: List[str] = field(default_factory=list)
    required_components: List[str] = field(default_factory=list)
    
    # Traversal configuration
    relationship_types: List[str] = field(default_factory=list)
    max_depth: int = 2
    direction: str = "outgoing"
    
    # Priority (higher = more specific)
    priority: int = 0
    
    def is_applicable(self, query_components) -> bool:
        # Handle both dict and QueryComponents object
        if hasattr(query_components, 'to_dict'):
            query_components = query_components.to_dict()
        
        intent = query_components.get("intent", "")
        
        # Check intent match
        if self.applicable_intents and intent not in self.applicable_intents:
            return False
        
        # Check required components
        for required in self.required_components:
            if required == "legal_refs" and not query_components.get("legal_refs"):
                return False
            if required == "concepts" and not query_components.get("concepts"):
                return False
            if required == "entity_type" and not query_components.get("entity_type"):
                return False
        
        return True
    
    def calculate_confidence(self, query_components) -> float:
        # Handle both dict and QueryComponents object
        if hasattr(query_components, 'to_dict'):
            query_components = query_components.to_dict()
            
        score = 0.5  # Base score
        
        # Boost for intent match
        intent = query_components.get("intent", "")
        if intent in self.applicable_intents:
            score += 0.3
        
        # Boost for component match
        for required in self.required_components:
            if query_components.get(required):
                score += 0.1
        
        # Priority boost
        score += self.priority * 0.05
        
        return min(score, 1.0)


# ============================================================================
# CORE REASONING RULES (R001 - R008)
# ============================================================================

RULE_R001_HIERARCHICAL = ReasoningRule(
    rule_id=RuleID.R001,
    name="Hierarchical Legal Structure",
    name_vi="Cấu trúc phân cấp văn bản pháp luật",
    pattern="LAW CONTAINS_ARTICLE ARTICLE CONTAINS_CLAUSE CLAUSE CONTAINS_POINT POINT",
    logic="IF entity_type=ARTICLE AND related_to=LAW THEN context=hierarchical_position",
    description="Establishes hierarchical relationship in legal documents (Law → Chapter → Article → Clause → Point)",
    description_vi="Xác định quan hệ phân cấp trong văn bản pháp luật (Luật → Chương → Điều → Khoản → Điểm)",
    applicable_intents=["definition", "regulation_query", "general_query"],
    required_components=["legal_refs"],
    relationship_types=["THUOC_VE", "CHUA", "CONTAINS_ARTICLE", "CONTAINS_CLAUSE", "CONTAINS_POINT"],
    max_depth=4,
    direction="both",
    priority=10
)

RULE_R002_CONCEPT_REGULATION = ReasoningRule(
    rule_id=RuleID.R002,
    name="Concept Regulation Mapping",
    name_vi="Ánh xạ khái niệm - quy định",
    pattern="CONCEPT REGULATED_BY LAW",
    logic="IF query_about=CONCEPT THEN retrieve=RELATED_LAWS",
    description="Maps legal concepts to their regulating laws",
    description_vi="Ánh xạ các khái niệm pháp lý với các luật quy định chúng",
    applicable_intents=["definition", "regulation_query", "general_query"],
    required_components=["concepts"],
    relationship_types=["DINH_NGHIA", "LIEN_QUAN", "QUY_DINH"],
    max_depth=2,
    direction="outgoing",
    priority=8
)

RULE_R003_OBLIGATION = ReasoningRule(
    rule_id=RuleID.R003,
    name="Obligation Inference",
    name_vi="Suy luận nghĩa vụ",
    pattern="ENTITY HAS_OBLIGATION OBLIGATION",
    logic="IF entity=ORGANIZATION OR entity=INDIVIDUAL THEN check=OBLIGATIONS",
    description="Identifies legal obligations for entities (organizations, individuals)",
    description_vi="Xác định nghĩa vụ pháp lý của các chủ thể (tổ chức, cá nhân)",
    applicable_intents=["obligation_query", "requirement_query"],
    required_components=["entity_type"],
    relationship_types=["CO_NGHIA_VU", "PHAI_THUC_HIEN", "TUAN_THU"],
    max_depth=2,
    direction="outgoing",
    priority=7
)

RULE_R004_RIGHTS = ReasoningRule(
    rule_id=RuleID.R004,
    name="Rights Protection",
    name_vi="Bảo vệ quyền lợi",
    pattern="RIGHT PROTECTED_BY LAW",
    logic="IF query_about=RIGHT THEN retrieve=PROTECTIVE_LAWS",
    description="Connects rights to their legal protections",
    description_vi="Kết nối quyền với các quy định bảo vệ tương ứng",
    applicable_intents=["rights_query", "protection_query"],
    required_components=["concepts"],
    relationship_types=["BAO_VE", "DAM_BAO", "CONG_NHAN"],
    max_depth=2,
    direction="outgoing",
    priority=7
)

RULE_R005_TRANSITIVE = ReasoningRule(
    rule_id=RuleID.R005,
    name="Transitive Legal Application",
    name_vi="Áp dụng bắc cầu",
    pattern="LAW_A RELATES_TO LAW_B RELATES_TO LAW_C",
    logic="IF LAW_A applicable THEN check=RELATED_LAWS transitively",
    description="Applies transitive relationships between laws",
    description_vi="Áp dụng quan hệ bắc cầu giữa các văn bản pháp luật",
    applicable_intents=["regulation_query", "relation_query"],
    required_components=[],
    relationship_types=["LIEN_QUAN", "THAM_CHIEU", "BO_SUNG", "THAY_THE"],
    max_depth=3,
    direction="both",
    priority=5
)

RULE_R006_PROHIBITION = ReasoningRule(
    rule_id=RuleID.R006,
    name="Prohibition Detection",
    name_vi="Phát hiện điều cấm",
    pattern="ACTION PROHIBITED_BY LAW",
    logic='IF query_contains="có được phép" OR "nghiêm cấm" THEN check=PROHIBITIONS',
    description="Identifies prohibited actions",
    description_vi="Xác định các hành vi bị nghiêm cấm",
    applicable_intents=["permission_check", "prohibition_query"],
    required_components=[],
    relationship_types=["CAM", "NGHIEM_CAM", "KHONG_DUOC_PHEP"],
    max_depth=2,
    direction="outgoing",
    priority=9
)

RULE_R007_REQUIREMENT = ReasoningRule(
    rule_id=RuleID.R007,
    name="Requirement Verification",
    name_vi="Xác minh yêu cầu",
    pattern="ENTITY MUST_COMPLY_WITH REQUIREMENT",
    logic="IF entity_type=ORGANIZATION THEN retrieve=COMPLIANCE_REQUIREMENTS",
    description="Verifies compliance requirements for entities",
    description_vi="Xác minh các yêu cầu tuân thủ cho chủ thể",
    applicable_intents=["obligation_query", "requirement_query", "compliance_query"],
    required_components=["entity_type"],
    relationship_types=["YEU_CAU", "DIEU_KIEN", "TIEU_CHUAN"],
    max_depth=2,
    direction="outgoing",
    priority=6
)

RULE_R008_CONTEXT_RETRIEVAL = ReasoningRule(
    rule_id=RuleID.R008,
    name="Context-Based Article Retrieval",
    name_vi="Truy xuất điều khoản theo ngữ cảnh",
    pattern="QUESTION REFERENCES ARTICLE IN LAW",
    logic="IF question_references=ARTICLE THEN retrieve=FULL_ARTICLE_CONTEXT",
    description="Retrieves full context when article is mentioned",
    description_vi="Truy xuất ngữ cảnh đầy đủ khi điều khoản được đề cập",
    applicable_intents=["definition", "regulation_query", "general_query"],
    required_components=["legal_refs"],
    relationship_types=["THUOC_VE", "CHUA", "LIEN_QUAN"],
    max_depth=3,
    direction="both",
    priority=9
)

# List of all rules
LEGAL_REASONING_RULES = [
    RULE_R001_HIERARCHICAL,
    RULE_R002_CONCEPT_REGULATION,
    RULE_R003_OBLIGATION,
    RULE_R004_RIGHTS,
    RULE_R005_TRANSITIVE,
    RULE_R006_PROHIBITION,
    RULE_R007_REQUIREMENT,
    RULE_R008_CONTEXT_RETRIEVAL,
]


class ReasoningRuleRegistry:
    def __init__(self, rules: Optional[List[ReasoningRule]] = None):
        self._rules: Dict[RuleID, ReasoningRule] = {}
        rules = rules or LEGAL_REASONING_RULES
        for rule in rules:
            self.register(rule)
        
        logger.info(f"ReasoningRuleRegistry initialized with {len(self._rules)} rules")
    
    def register(self, rule: ReasoningRule) -> None:
        self._rules[rule.rule_id] = rule
        logger.debug(f"Registered rule: {rule.rule_id.value} - {rule.name}")
    
    def get(self, rule_id: RuleID) -> Optional[ReasoningRule]:
        return self._rules.get(rule_id)
    
    def get_all(self) -> List[ReasoningRule]:
        return list(self._rules.values())
    
    def select_applicable_rules(
        self,
        query_components: Dict[str, Any],
        max_rules: int = 3
    ) -> List[Dict[str, Any]]:
        applicable = []
        
        for rule in self._rules.values():
            if rule.is_applicable(query_components):
                confidence = rule.calculate_confidence(query_components)
                applicable.append({
                    "rule": rule,
                    "confidence": confidence
                })
        
        # Sort by confidence (descending) then by priority (descending)
        applicable.sort(
            key=lambda x: (x["confidence"], x["rule"].priority),
            reverse=True
        )
        
        selected = applicable[:max_rules]
        
        if selected:
            logger.info(
                f"Selected {len(selected)} rules: " + 
                ", ".join(f"{r['rule'].rule_id.value}({r['confidence']:.2f})" for r in selected)
            )
        
        return selected
    
    def get_rules_for_intent(self, intent: str) -> List[ReasoningRule]:
        return [
            rule for rule in self._rules.values()
            if intent in rule.applicable_intents
        ]
