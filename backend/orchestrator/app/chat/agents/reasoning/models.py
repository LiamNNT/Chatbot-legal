"""
Data models for the Symbolic Verification Pipeline.

Reference: Rademaker et al. (2024) — "Deductive Verification of LLM generated
SPARQL queries" adapted to Cypher/Neo4j for Vietnamese legal KG.

Pipeline stages:
  1. QuestionSpec — structured representation of user question
  2. CypherQuery — LLM-generated Cypher + entity mappings
  3. VerificationResult — deterministic check before execution
  4. KGResult — raw data from Neo4j
  5. StructuredAnswer — LLM answer with evidence traceability
  6. AnswerVerdict — final pass/reject decision
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import date, datetime


# ====================================================================
# Stage A — Question Spec
# ====================================================================

class AnswerType(str, Enum):
    """Expected answer type derived from the question."""
    BOOLEAN = "boolean"                 # Có/không, đúng/sai
    AMOUNT_RANGE = "amount_range"       # Mức phạt, số tiền
    ARTICLE_REF = "article_ref"         # Điều/khoản/điểm
    LIST = "list"                       # Danh sách hành vi, quyền…
    DEFINITION = "definition"           # Khái niệm, thuật ngữ
    PROCEDURE = "procedure"             # Thủ tục, trình tự
    COMPARISON = "comparison"           # So sánh giữa 2+ mục
    TEMPORAL = "temporal"               # Thời điểm hiệu lực


class QuestionIntent(str, Enum):
    """High-level intent of the legal question."""
    SANCTION_LOOKUP = "sanction_lookup"       # Hỏi mức phạt
    ARTICLE_LOOKUP = "article_lookup"         # Hỏi nội dung điều khoản
    DEFINITION_LOOKUP = "definition_lookup"   # Hỏi định nghĩa
    PROHIBITION_CHECK = "prohibition_check"   # Hỏi hành vi bị cấm
    RIGHT_OBLIGATION = "right_obligation"     # Hỏi quyền/nghĩa vụ
    PROCEDURE_LOOKUP = "procedure_lookup"     # Hỏi thủ tục
    VALIDITY_CHECK = "validity_check"         # Hỏi hiệu lực
    COMPARISON = "comparison"                 # So sánh quy định
    GENERAL = "general"                       # Câu hỏi chung


@dataclass
class QuestionSpec:
    """
    Machine-readable structured representation of a user question.
    Extracted by LLM in the first step.
    """
    original_question: str
    answer_type: AnswerType
    intent: QuestionIntent

    # Scope — which documents/articles the question targets
    scope_documents: List[str] = field(default_factory=list)     # e.g. ["Nghị định 100/2019/NĐ-CP"]
    scope_articles: List[str] = field(default_factory=list)      # e.g. ["Điều 5", "Khoản 2"]

    # Constraints
    subject: Optional[str] = None           # "cá nhân", "tổ chức"
    act_or_behaviour: Optional[str] = None  # "không đội mũ bảo hiểm"
    context: Optional[str] = None           # "khi tham gia giao thông"
    vehicle_or_object: Optional[str] = None # "xe máy", "ô tô"

    # Temporal
    time_reference: Optional[str] = None    # "hiện nay", "năm 2024"
    effective_date: Optional[date] = None   # resolved date for validity check

    # Required fields in the answer (for verification)
    required_fields: List[str] = field(default_factory=list)
    # e.g. ["penalty_amount", "article_ref", "currency"]


# ====================================================================
# Stage 1 — Cypher Query
# ====================================================================

@dataclass
class EntityMapping:
    """An entity in the question mapped to a KG node/label."""
    mention: str          # text span in question
    node_type: str        # NodeType value, e.g. "Nghị định"
    kg_identifier: str    # resolved KG id / name
    confidence: float = 1.0


@dataclass
class GeneratedCypher:
    """LLM-generated Cypher query with metadata."""
    cypher: str
    params: Dict[str, Any] = field(default_factory=dict)
    entity_mappings: List[EntityMapping] = field(default_factory=list)
    explanation: str = ""                # LLM's explanation of what query does
    expected_return_fields: List[str] = field(default_factory=list)


# ====================================================================
# Stage 2 — Verification Result
# ====================================================================

class VerificationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class RuleCheckResult:
    """Result of a single deterministic verification rule."""
    rule_id: str
    rule_name: str
    status: VerificationStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CypherVerificationResult:
    """Aggregated verification result for a Cypher query."""
    passed: bool
    checks: List[RuleCheckResult] = field(default_factory=list)
    failure_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    corrective_hint: str = ""  # hint for LLM to fix query

    @property
    def summary(self) -> str:
        if self.passed:
            warns = f" ({len(self.warnings)} warnings)" if self.warnings else ""
            return f"PASS{warns}"
        return f"FAIL: {'; '.join(self.failure_reasons)}"


# ====================================================================
# Stage 3 — KG Result
# ====================================================================

@dataclass
class KGRecord:
    """A single record from Cypher execution on Neo4j."""
    data: Dict[str, Any]
    node_labels: List[str] = field(default_factory=list)
    relationship_types: List[str] = field(default_factory=list)


@dataclass
class KGResult:
    """Result set from a verified Cypher execution."""
    records: List[KGRecord] = field(default_factory=list)
    query_used: str = ""
    execution_time_ms: float = 0.0
    is_empty: bool = False
    raw_records: List[Dict[str, Any]] = field(default_factory=list)


# ====================================================================
# Stage 4/5 — Structured Answer + Verdict
# ====================================================================

@dataclass
class ArticleRef:
    """Reference to a specific legal provision."""
    document: str = ""     # e.g. "Nghị định 100/2019/NĐ-CP"
    article: str = ""      # e.g. "Điều 5"
    clause: str = ""       # e.g. "Khoản 2"
    point: str = ""        # e.g. "Điểm a"


@dataclass
class AmountRange:
    """Penalty amount / range."""
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: str = "VND"
    unit: str = ""  # "triệu đồng", etc.


@dataclass
class StructuredAnswer:
    """
    Machine-checkable structured answer that LLM must produce
    alongside the natural-language answer.
    """
    answer_type: AnswerType
    article_refs: List[ArticleRef] = field(default_factory=list)
    amount_range: Optional[AmountRange] = None
    evidence_ids: List[str] = field(default_factory=list)   # map to KGRecord indices
    boolean_answer: Optional[bool] = None
    list_items: List[str] = field(default_factory=list)
    definition_text: str = ""
    assumptions: List[str] = field(default_factory=list)    # if KG lacks data
    natural_language: str = ""                               # prose answer
    citations: List[str] = field(default_factory=list)       # formatted citations


class AnswerVerdictStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REGEN = "needs_regen"


@dataclass
class AnswerVerdict:
    """Final deterministic verdict on the LLM answer."""
    status: AnswerVerdictStatus
    checks: List[RuleCheckResult] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    confidence: float = 0.0


# ====================================================================
# Pipeline — overall result
# ====================================================================

@dataclass
class VerificationPipelineResult:
    """End-to-end result of the Symbolic Verification Pipeline."""
    question_spec: Optional[QuestionSpec] = None
    generated_cypher: Optional[GeneratedCypher] = None
    cypher_verification: Optional[CypherVerificationResult] = None
    kg_result: Optional[KGResult] = None
    structured_answer: Optional[StructuredAnswer] = None
    answer_verdict: Optional[AnswerVerdict] = None

    # Final output
    final_answer: str = ""
    is_verified: bool = False
    fallback_reason: str = ""

    # Stats
    total_time_s: float = 0.0
    llm_calls: int = 0
    cypher_retries: int = 0
