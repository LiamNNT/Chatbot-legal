"""
Legal Verification Pipeline — main orchestrator for Symbolic Verification.

End-to-end flow:
  A.  QuestionSpec extraction  (LLM)
  1.  Cypher generation        (LLM)
  2.  Cypher verification      (deterministic rules)
      — if FAIL → LLM retries with corrective hint (up to MAX_RETRIES)
  3.  Execute Cypher on KG     (Neo4j)
  4.  Answer generation        (LLM — reformulate KG data only)
  C.  Answer verification      (deterministic rules)
      — if REJECTED/NEEDS_REGEN → LLM re-generates (up to 1 retry)

Reference:
  Rademaker, A. et al. (2024) "Deductive Verification of LLM generated
  SPARQL queries" — adapted for Cypher/Neo4j.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from ....shared.ports import AgentPort
from .models import (
    AnswerVerdictStatus,
    VerificationPipelineResult,
)
from .question_spec import QuestionSpecExtractor
from .query_generator import CypherQueryGenerator
from .query_verifier import CypherQueryVerifier
from .kg_executor import KGExecutor
from .answer_generator import AnswerGenerator
from .answer_verifier import AnswerVerifier

logger = logging.getLogger(__name__)


class LegalVerificationPipeline:
    """
    Orchestrates the full symbolic-verification pipeline.

    Dependencies:
        llm_port      — ``AgentPort`` for LLM calls
        graph_adapter — object with ``execute_cypher(cypher, params)``
    """

    MAX_CYPHER_RETRIES = 2
    MAX_ANSWER_RETRIES = 1

    def __init__(
        self,
        llm_port: AgentPort,
        graph_adapter: Any,
    ):
        self._spec_extractor = QuestionSpecExtractor(llm_port)
        self._query_generator = CypherQueryGenerator(llm_port)
        self._query_verifier = CypherQueryVerifier()
        self._kg_executor = KGExecutor(graph_adapter)
        self._answer_generator = AnswerGenerator(llm_port)
        self._answer_verifier = AnswerVerifier()
        self._graph_adapter = graph_adapter

        logger.info("✓ LegalVerificationPipeline initialized")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self, question: str) -> VerificationPipelineResult:
        """
        Process a legal question through the full verification pipeline.

        Returns ``VerificationPipelineResult`` with:
        - ``final_answer``   — verified prose answer (Vietnamese)
        - ``is_verified``    — True if all checks passed
        - ``fallback_reason``— explanation if pipeline fell back
        """
        start = time.time()
        result = VerificationPipelineResult()

        try:
            # ── Stage A: Question Spec ────────────────────────────
            logger.info("📋 Stage A: Extracting QuestionSpec")
            spec = await self._spec_extractor.extract(question)
            result.question_spec = spec
            result.llm_calls += 1
            logger.info(
                f"   answer_type={spec.answer_type.value}, "
                f"intent={spec.intent.value}, "
                f"scope={spec.scope_documents}"
            )

            # ── Stage 1 + 2: Generate & Verify Cypher ────────────
            cypher = None
            verification = None
            corrective_hint = ""

            for attempt in range(1 + self.MAX_CYPHER_RETRIES):
                # 1. Generate
                logger.info(f"🔧 Stage 1: Generating Cypher (attempt {attempt + 1})")

                # Try template first (0 LLM calls)
                if attempt == 0:
                    cypher = self._query_generator.generate_from_template(spec)
                    if cypher:
                        logger.info("   Using template-based Cypher")
                    else:
                        cypher = await self._query_generator.generate(spec, corrective_hint)
                        result.llm_calls += 1
                else:
                    cypher = await self._query_generator.generate(spec, corrective_hint)
                    result.llm_calls += 1

                result.generated_cypher = cypher

                # 2. Verify
                logger.info("🔍 Stage 2: Verifying Cypher")
                verification = self._query_verifier.verify(cypher, spec)
                result.cypher_verification = verification

                if verification.passed:
                    logger.info("   ✅ Cypher verification PASSED")
                    break

                # Failed — retry with hint
                corrective_hint = verification.corrective_hint
                result.cypher_retries += 1
                logger.warning(
                    f"   ❌ Cypher verification FAILED (attempt {attempt + 1}): "
                    f"{verification.failure_reasons}"
                )

            # If Cypher still fails after retries, fallback
            if verification and not verification.passed:
                result.fallback_reason = (
                    f"Cypher không hợp lệ sau {self.MAX_CYPHER_RETRIES + 1} lần: "
                    f"{'; '.join(verification.failure_reasons)}"
                )
                result.final_answer = (
                    "Xin lỗi, hệ thống không thể tạo truy vấn hợp lệ cho câu hỏi này. "
                    "Vui lòng thử diễn đạt lại câu hỏi chi tiết hơn."
                )
                result.total_time_s = time.time() - start
                return result

            # ── Stage 3: Execute on KG ────────────────────────────
            logger.info("⚡ Stage 3: Executing Cypher on Neo4j")
            try:
                kg_result = await self._kg_executor.execute(cypher)
                result.kg_result = kg_result
                logger.info(
                    f"   {len(kg_result.records)} records, "
                    f"{kg_result.execution_time_ms:.0f}ms"
                )
            except RuntimeError as e:
                result.fallback_reason = str(e)
                result.final_answer = (
                    "Xin lỗi, hệ thống gặp lỗi khi truy vấn Knowledge Graph. "
                    "Vui lòng thử lại sau."
                )
                result.total_time_s = time.time() - start
                return result

            # ── Stage 4 + C: Generate & Verify Answer ─────────────
            for answer_attempt in range(1 + self.MAX_ANSWER_RETRIES):
                logger.info(f"📝 Stage 4: Generating answer (attempt {answer_attempt + 1})")
                answer = await self._answer_generator.generate(spec, kg_result)
                result.structured_answer = answer
                result.llm_calls += 1

                logger.info("🔎 Stage C: Verifying answer")
                verdict = self._answer_verifier.verify(answer, spec, kg_result)
                result.answer_verdict = verdict

                if verdict.status == AnswerVerdictStatus.ACCEPTED:
                    logger.info("   ✅ Answer ACCEPTED")
                    result.final_answer = answer.natural_language
                    result.is_verified = True
                    break
                elif verdict.status == AnswerVerdictStatus.NEEDS_REGEN:
                    logger.warning(
                        f"   ⚠ Answer NEEDS_REGEN: {verdict.rejection_reasons}"
                    )
                    continue
                else:
                    # REJECTED
                    logger.warning(
                        f"   ❌ Answer REJECTED: {verdict.rejection_reasons}"
                    )
                    if answer_attempt < self.MAX_ANSWER_RETRIES:
                        continue
                    # After retries, use answer but mark as unverified
                    result.final_answer = answer.natural_language
                    result.is_verified = False
                    result.fallback_reason = (
                        f"Câu trả lời không qua kiểm chứng: "
                        f"{'; '.join(verdict.rejection_reasons)}"
                    )

            # If no answer was set (edge case), use whatever we have
            if not result.final_answer and result.structured_answer:
                result.final_answer = result.structured_answer.natural_language
                result.is_verified = False

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            result.fallback_reason = f"Pipeline error: {e}"
            result.final_answer = (
                "Xin lỗi, đã có lỗi xảy ra trong quá trình xử lý. "
                "Vui lòng thử lại."
            )

        result.total_time_s = time.time() - start
        logger.info(
            f"📊 Pipeline done: verified={result.is_verified}, "
            f"llm_calls={result.llm_calls}, "
            f"cypher_retries={result.cypher_retries}, "
            f"time={result.total_time_s:.2f}s"
        )
        return result
