"""
Answer Verifier — Stage 5 / C of the Symbolic Verification Pipeline.

Deterministic (rule-based) checks that run AFTER LLM produces the
``StructuredAnswer``.  They compare the answer against the ``QuestionSpec``
and the raw ``KGResult`` to catch hallucinations.

Rule catalogue:
  A-01  Type match        — answer_type matches spec.answer_type
  A-02  Constraint coverage — required_fields present
  A-03  Scope consistency  — article_refs cite correct documents
  A-04  Temporal validity  — evidence still in force
  A-05  No new facts      — every claim has evidence_id in KGResult
  A-06  Amount sanity     — if amount_range, must have numbers
"""

from __future__ import annotations

import logging
from typing import List

from .models import (
    AnswerType,
    AnswerVerdict,
    AnswerVerdictStatus,
    KGResult,
    QuestionSpec,
    RuleCheckResult,
    StructuredAnswer,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class AnswerVerifier:
    """Run deterministic checks on a ``StructuredAnswer``."""

    def verify(
        self,
        answer: StructuredAnswer,
        spec: QuestionSpec,
        kg_result: KGResult,
    ) -> AnswerVerdict:
        """
        Validate *answer* against *spec* and *kg_result*.

        Returns an ``AnswerVerdict`` indicating whether the answer
        is accepted, rejected, or needs regeneration.
        """
        checks: List[RuleCheckResult] = [
            self._a01_type_match(answer, spec),
            self._a02_constraint_coverage(answer, spec),
            self._a03_scope_consistency(answer, spec),
            self._a04_temporal_validity(answer, spec, kg_result),
            self._a05_no_new_facts(answer, kg_result),
            self._a06_amount_sanity(answer, spec),
        ]

        failures = [c for c in checks if c.status == VerificationStatus.FAIL]
        warnings = [c for c in checks if c.status == VerificationStatus.WARN]

        if failures:
            status = AnswerVerdictStatus.REJECTED
            if len(failures) <= 2 and all(
                f.rule_id in ("A-02", "A-04") for f in failures
            ):
                # Soft failures → allow regen instead of hard reject
                status = AnswerVerdictStatus.NEEDS_REGEN
        else:
            status = AnswerVerdictStatus.ACCEPTED

        # Confidence heuristic
        total = len(checks)
        passed = sum(1 for c in checks if c.status == VerificationStatus.PASS)
        confidence = passed / total if total else 0.0

        verdict = AnswerVerdict(
            status=status,
            checks=checks,
            rejection_reasons=[c.message for c in failures],
            confidence=confidence,
        )
        logger.info(f"Answer verdict: {status.value} (confidence={confidence:.2f})")
        return verdict

    # ==================================================================
    # Individual rules
    # ==================================================================

    def _a01_type_match(
        self, answer: StructuredAnswer, spec: QuestionSpec
    ) -> RuleCheckResult:
        """Answer type must match what the question expects."""
        if answer.answer_type != spec.answer_type:
            return RuleCheckResult(
                rule_id="A-01", rule_name="type_match",
                status=VerificationStatus.WARN,
                message=(
                    f"Câu hỏi yêu cầu {spec.answer_type.value} "
                    f"nhưng câu trả lời là {answer.answer_type.value}"
                ),
            )
        return RuleCheckResult(
            rule_id="A-01", rule_name="type_match",
            status=VerificationStatus.PASS,
            message="Type match OK",
        )

    def _a02_constraint_coverage(
        self, answer: StructuredAnswer, spec: QuestionSpec
    ) -> RuleCheckResult:
        """Required fields from spec must appear in the answer."""
        missing: list[str] = []

        for field_name in spec.required_fields:
            if field_name == "penalty_amount":
                if answer.amount_range is None:
                    missing.append("penalty_amount (amount_range)")
            elif field_name == "currency":
                if answer.amount_range is None or not answer.amount_range.currency:
                    missing.append("currency")
            elif field_name == "article_ref":
                if not answer.article_refs:
                    missing.append("article_ref")
            elif field_name == "boolean_answer":
                if answer.boolean_answer is None:
                    missing.append("boolean_answer")
            elif field_name == "definition_text":
                if not answer.definition_text:
                    missing.append("definition_text")
            elif field_name == "list_items":
                if not answer.list_items:
                    missing.append("list_items")
            elif field_name == "effective_date":
                # Check citations or natural_language for date info
                has_date = any(
                    "hiệu lực" in c.lower() or "ngày" in c.lower()
                    for c in answer.citations
                )
                if not has_date and "hiệu lực" not in answer.natural_language.lower():
                    missing.append("effective_date")

        if missing:
            return RuleCheckResult(
                rule_id="A-02", rule_name="constraint_coverage",
                status=VerificationStatus.FAIL,
                message=f"Thiếu trường bắt buộc: {', '.join(missing)}",
                details={"missing_fields": missing},
            )
        return RuleCheckResult(
            rule_id="A-02", rule_name="constraint_coverage",
            status=VerificationStatus.PASS,
            message="Constraint coverage OK",
        )

    def _a03_scope_consistency(
        self, answer: StructuredAnswer, spec: QuestionSpec
    ) -> RuleCheckResult:
        """Article refs should cite documents in scope (unless explicitly noting replacement)."""
        if not spec.scope_documents or not answer.article_refs:
            return RuleCheckResult(
                rule_id="A-03", rule_name="scope_consistency",
                status=VerificationStatus.PASS,
                message="No scope to verify",
            )

        scope_docs_lower = [d.lower() for d in spec.scope_documents]
        out_of_scope: list[str] = []

        for ref in answer.article_refs:
            doc_lower = ref.document.lower()
            if doc_lower and not any(sd in doc_lower or doc_lower in sd for sd in scope_docs_lower):
                out_of_scope.append(ref.document)

        if out_of_scope:
            # Warn, not fail — might be legitimate cross-reference
            return RuleCheckResult(
                rule_id="A-03", rule_name="scope_consistency",
                status=VerificationStatus.WARN,
                message=f"Trích dẫn văn bản ngoài phạm vi: {', '.join(out_of_scope)}",
            )
        return RuleCheckResult(
            rule_id="A-03", rule_name="scope_consistency",
            status=VerificationStatus.PASS,
            message="Scope consistency OK",
        )

    def _a04_temporal_validity(
        self, answer: StructuredAnswer, spec: QuestionSpec, kg_result: KGResult
    ) -> RuleCheckResult:
        """If temporal constraint exists, evidence must be in force."""
        if spec.time_reference is None and spec.effective_date is None:
            return RuleCheckResult(
                rule_id="A-04", rule_name="temporal_validity",
                status=VerificationStatus.PASS,
                message="No temporal constraint",
            )

        # Check if any KG record indicates repeal / replacement
        revoked_keywords = ("hết hiệu lực", "bị bãi bỏ", "bị thay thế")
        for record in kg_result.records:
            for v in record.data.values():
                if isinstance(v, str) and any(kw in v.lower() for kw in revoked_keywords):
                    return RuleCheckResult(
                        rule_id="A-04", rule_name="temporal_validity",
                        status=VerificationStatus.FAIL,
                        message="Dữ liệu KG cho thấy quy định đã hết hiệu lực / bị thay thế",
                    )

        return RuleCheckResult(
            rule_id="A-04", rule_name="temporal_validity",
            status=VerificationStatus.PASS,
            message="Temporal validity OK",
        )

    def _a05_no_new_facts(
        self, answer: StructuredAnswer, kg_result: KGResult
    ) -> RuleCheckResult:
        """
        Every important claim must have an evidence_id mapping to a KGRecord.
        If the answer contains claims without evidence → might be hallucination.
        """
        # If KG result is empty, any substantive answer is suspicious
        if kg_result.is_empty and answer.natural_language and len(answer.natural_language) > 100:
            if not answer.assumptions:
                return RuleCheckResult(
                    rule_id="A-05", rule_name="no_new_facts",
                    status=VerificationStatus.FAIL,
                    message="KG trả về rỗng nhưng câu trả lời có nội dung — nghi ngờ hallucination",
                )

        # If answer has article_refs, they should map to KG records
        if answer.article_refs and not answer.evidence_ids:
            return RuleCheckResult(
                rule_id="A-05", rule_name="no_new_facts",
                status=VerificationStatus.WARN,
                message="Câu trả lời có trích dẫn nhưng không có evidence_ids",
            )

        # Validate evidence_ids are within range
        if answer.evidence_ids:
            max_idx = len(kg_result.records) - 1
            invalid_ids = [
                eid for eid in answer.evidence_ids
                if not eid.isdigit() or int(eid) > max_idx
            ]
            if invalid_ids:
                return RuleCheckResult(
                    rule_id="A-05", rule_name="no_new_facts",
                    status=VerificationStatus.WARN,
                    message=f"evidence_ids không hợp lệ: {invalid_ids}",
                )

        return RuleCheckResult(
            rule_id="A-05", rule_name="no_new_facts",
            status=VerificationStatus.PASS,
            message="No new facts OK",
        )

    def _a06_amount_sanity(
        self, answer: StructuredAnswer, spec: QuestionSpec
    ) -> RuleCheckResult:
        """If question asks for amount, answer must have numeric data."""
        if spec.answer_type != AnswerType.AMOUNT_RANGE:
            return RuleCheckResult(
                rule_id="A-06", rule_name="amount_sanity",
                status=VerificationStatus.PASS,
                message="Not an amount question",
            )

        if answer.amount_range is None:
            return RuleCheckResult(
                rule_id="A-06", rule_name="amount_sanity",
                status=VerificationStatus.FAIL,
                message="Câu hỏi mức phạt nhưng câu trả lời không có amount_range",
            )

        ar = answer.amount_range
        if ar.min_amount is None and ar.max_amount is None:
            return RuleCheckResult(
                rule_id="A-06", rule_name="amount_sanity",
                status=VerificationStatus.FAIL,
                message="amount_range không có min_amount hoặc max_amount",
            )

        return RuleCheckResult(
            rule_id="A-06", rule_name="amount_sanity",
            status=VerificationStatus.PASS,
            message="Amount sanity OK",
        )
