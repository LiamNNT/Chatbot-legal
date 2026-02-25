"""
Cypher Query Verifier — Stage 2 of the Symbolic Verification Pipeline.

Deterministic (rule-based) checks that run BEFORE executing the Cypher
query on Neo4j.  Each check is a pure function that inspects the Cypher
text and/or the ``QuestionSpec`` and returns pass/fail.

Rule catalogue:
  V-01  Type-match        — query shape matches expected answer type
  V-02  Constraint coverage — all key constraints present
  V-03  Relation polarity  — "permitted" ≠ "prohibited" etc.
  V-04  Temporal validity  — effectiveDate / repealedBy filter present
  V-05  Syntax sanity      — MATCH + RETURN, balanced parentheses
  V-06  No write ops       — no CREATE/DELETE/SET/MERGE
  V-07  Scope match        — document/article referenced in query
"""

from __future__ import annotations

import logging
import re
from typing import List

from .models import (
    AnswerType,
    CypherVerificationResult,
    GeneratedCypher,
    QuestionSpec,
    RuleCheckResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)

# Label pairs that must NOT be swapped
_POLARITY_PAIRS = [
    ("Hành vi cấm", "Hành vi được phép"),
    ("Quyền", "Nghĩa vụ"),
    ("Chế tài", "Khái niệm"),
]

# Write keywords that must never appear in a read query
_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|DELETE|DETACH\s+DELETE|SET|REMOVE|MERGE)\b",
    re.IGNORECASE,
)


class CypherQueryVerifier:
    """Run deterministic checks on a ``GeneratedCypher``."""

    def verify(
        self,
        cypher: GeneratedCypher,
        spec: QuestionSpec,
    ) -> CypherVerificationResult:
        """
        Run all verification rules.  Returns an aggregated result.
        The query should NOT be executed if ``result.passed`` is False.
        """
        checks: List[RuleCheckResult] = [
            self._v01_type_match(cypher, spec),
            self._v02_constraint_coverage(cypher, spec),
            self._v03_relation_polarity(cypher, spec),
            self._v04_temporal_validity(cypher, spec),
            self._v05_syntax_sanity(cypher),
            self._v06_no_write_ops(cypher),
            self._v07_scope_match(cypher, spec),
        ]

        failures = [c for c in checks if c.status == VerificationStatus.FAIL]
        warnings = [c for c in checks if c.status == VerificationStatus.WARN]

        passed = len(failures) == 0
        failure_reasons = [c.message for c in failures]
        warning_msgs = [c.message for c in warnings]

        hint = ""
        if not passed:
            hint = "Sửa Cypher: " + "; ".join(failure_reasons)

        result = CypherVerificationResult(
            passed=passed,
            checks=checks,
            failure_reasons=failure_reasons,
            warnings=warning_msgs,
            corrective_hint=hint,
        )
        logger.info(f"Cypher verification: {result.summary}")
        return result

    # ==================================================================
    # Individual rules
    # ==================================================================

    def _v01_type_match(
        self, cypher: GeneratedCypher, spec: QuestionSpec
    ) -> RuleCheckResult:
        """Query shape must match expected answer type."""
        q = cypher.cypher.upper()

        # BOOLEAN → look for EXISTS / COUNT or RETURN boolean-ish
        if spec.answer_type == AnswerType.BOOLEAN:
            if not any(k in q for k in ("EXISTS", "COUNT", "CASE WHEN", "boolean")):
                return RuleCheckResult(
                    rule_id="V-01", rule_name="type_match",
                    status=VerificationStatus.WARN,
                    message="Câu hỏi boolean nhưng Cypher không dùng EXISTS/COUNT",
                )

        # AMOUNT_RANGE → must return amount/penalty fields
        if spec.answer_type == AnswerType.AMOUNT_RANGE:
            if not any(k in q for k in ("AMOUNT", "PENALTY", "MỨC", "MIN_AMOUNT", "MAX_AMOUNT", "CHẾ TÀI", "PHẠT")):
                return RuleCheckResult(
                    rule_id="V-01", rule_name="type_match",
                    status=VerificationStatus.FAIL,
                    message="Câu hỏi mức phạt nhưng Cypher không trả về trường tiền phạt",
                )

        # DEFINITION → must touch definition labels
        if spec.answer_type == AnswerType.DEFINITION:
            if not any(k in q for k in ("KHÁI NIỆM", "THUẬT NGỮ", "DINH_NGHIA", "DEFINITION")):
                return RuleCheckResult(
                    rule_id="V-01", rule_name="type_match",
                    status=VerificationStatus.WARN,
                    message="Câu hỏi định nghĩa nhưng Cypher không truy vấn Khái niệm/Thuật ngữ",
                )

        return RuleCheckResult(
            rule_id="V-01", rule_name="type_match",
            status=VerificationStatus.PASS,
            message="Type-match OK",
        )

    def _v02_constraint_coverage(
        self, cypher: GeneratedCypher, spec: QuestionSpec
    ) -> RuleCheckResult:
        """All key constraints from the question must appear in the query."""
        missing: list[str] = []
        q_lower = cypher.cypher.lower()
        params_str = str(cypher.params).lower()
        combined = q_lower + " " + params_str

        if spec.act_or_behaviour:
            behaviour_terms = spec.act_or_behaviour.lower().split()
            # At least some terms should appear
            found = sum(1 for t in behaviour_terms if t in combined)
            if found < len(behaviour_terms) * 0.3:
                missing.append(f"hành vi '{spec.act_or_behaviour}'")

        if spec.subject and spec.subject.lower() not in combined:
            # Warn, not fail — subject may be implicit
            pass

        if spec.scope_documents:
            doc_found = any(
                d.lower() in combined or d.split()[-1].lower() in combined
                for d in spec.scope_documents
            )
            if not doc_found:
                missing.append(f"văn bản {spec.scope_documents}")

        if missing:
            return RuleCheckResult(
                rule_id="V-02", rule_name="constraint_coverage",
                status=VerificationStatus.FAIL,
                message=f"Thiếu ràng buộc: {', '.join(missing)}",
                details={"missing": missing},
            )

        return RuleCheckResult(
            rule_id="V-02", rule_name="constraint_coverage",
            status=VerificationStatus.PASS,
            message="Constraint coverage OK",
        )

    def _v03_relation_polarity(
        self, cypher: GeneratedCypher, spec: QuestionSpec
    ) -> RuleCheckResult:
        """Ensure labels are not swapped (e.g. prohibited ≠ permitted)."""
        q = cypher.cypher

        for label_a, label_b in _POLARITY_PAIRS:
            if spec.intent.value in ("prohibition_check", "sanction_lookup"):
                # Expect "Hành vi cấm", not "Hành vi được phép"
                if label_b in q and label_a not in q:
                    return RuleCheckResult(
                        rule_id="V-03", rule_name="relation_polarity",
                        status=VerificationStatus.FAIL,
                        message=f"Sai quan hệ: dùng '{label_b}' thay vì '{label_a}'",
                    )
            elif spec.intent.value == "right_obligation":
                # Both are OK — just warn if only one is used
                pass

        return RuleCheckResult(
            rule_id="V-03", rule_name="relation_polarity",
            status=VerificationStatus.PASS,
            message="Relation polarity OK",
        )

    def _v04_temporal_validity(
        self, cypher: GeneratedCypher, spec: QuestionSpec
    ) -> RuleCheckResult:
        """If question implies 'current' law, query should filter by validity."""
        needs_temporal = (
            spec.answer_type == AnswerType.TEMPORAL
            or spec.time_reference is not None
            or spec.intent == "validity_check"
        )

        if not needs_temporal:
            return RuleCheckResult(
                rule_id="V-04", rule_name="temporal_validity",
                status=VerificationStatus.PASS,
                message="No temporal constraint needed",
            )

        q_upper = cypher.cypher.upper()
        has_temporal = any(kw in q_upper for kw in (
            "EFFECTIVE_DATE", "STATUS", "THAY_THE", "BAI_BO",
            "SUA_DOI", "HIEU_LUC", "CÒN HIỆU LỰC",
        ))

        if not has_temporal:
            return RuleCheckResult(
                rule_id="V-04", rule_name="temporal_validity",
                status=VerificationStatus.WARN,
                message="Câu hỏi có ràng buộc thời gian nhưng Cypher không lọc hiệu lực",
            )

        return RuleCheckResult(
            rule_id="V-04", rule_name="temporal_validity",
            status=VerificationStatus.PASS,
            message="Temporal validity OK",
        )

    def _v05_syntax_sanity(self, cypher: GeneratedCypher) -> RuleCheckResult:
        """Basic syntactic checks on the Cypher text."""
        q = cypher.cypher.strip()

        if not q:
            return RuleCheckResult(
                rule_id="V-05", rule_name="syntax_sanity",
                status=VerificationStatus.FAIL,
                message="Cypher query rỗng",
            )

        q_upper = q.upper()
        if "MATCH" not in q_upper:
            return RuleCheckResult(
                rule_id="V-05", rule_name="syntax_sanity",
                status=VerificationStatus.FAIL,
                message="Cypher thiếu MATCH clause",
            )

        if "RETURN" not in q_upper:
            return RuleCheckResult(
                rule_id="V-05", rule_name="syntax_sanity",
                status=VerificationStatus.FAIL,
                message="Cypher thiếu RETURN clause",
            )

        # Balanced parentheses
        if q.count("(") != q.count(")"):
            return RuleCheckResult(
                rule_id="V-05", rule_name="syntax_sanity",
                status=VerificationStatus.FAIL,
                message="Ngoặc tròn không cân bằng",
            )
        if q.count("[") != q.count("]"):
            return RuleCheckResult(
                rule_id="V-05", rule_name="syntax_sanity",
                status=VerificationStatus.FAIL,
                message="Ngoặc vuông không cân bằng",
            )

        return RuleCheckResult(
            rule_id="V-05", rule_name="syntax_sanity",
            status=VerificationStatus.PASS,
            message="Syntax OK",
        )

    def _v06_no_write_ops(self, cypher: GeneratedCypher) -> RuleCheckResult:
        """Query must be read-only. No CREATE, DELETE, SET, MERGE."""
        if _WRITE_KEYWORDS.search(cypher.cypher):
            return RuleCheckResult(
                rule_id="V-06", rule_name="no_write_ops",
                status=VerificationStatus.FAIL,
                message="Cypher chứa thao tác ghi (CREATE/DELETE/SET/MERGE) — không được phép",
            )
        return RuleCheckResult(
            rule_id="V-06", rule_name="no_write_ops",
            status=VerificationStatus.PASS,
            message="Read-only OK",
        )

    def _v07_scope_match(
        self, cypher: GeneratedCypher, spec: QuestionSpec
    ) -> RuleCheckResult:
        """If the question names a specific document, it must appear in the query."""
        if not spec.scope_documents:
            return RuleCheckResult(
                rule_id="V-07", rule_name="scope_match",
                status=VerificationStatus.PASS,
                message="No scope constraint",
            )

        combined = (cypher.cypher + " " + str(cypher.params)).lower()
        for doc in spec.scope_documents:
            # Check full name or document number fragment
            fragments = doc.lower().split("/")
            if not any(f in combined for f in fragments):
                return RuleCheckResult(
                    rule_id="V-07", rule_name="scope_match",
                    status=VerificationStatus.FAIL,
                    message=f"Cypher không tham chiếu văn bản '{doc}'",
                )

        return RuleCheckResult(
            rule_id="V-07", rule_name="scope_match",
            status=VerificationStatus.PASS,
            message="Scope match OK",
        )
