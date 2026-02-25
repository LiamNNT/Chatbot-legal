"""
Question Spec Extractor — Stage A of the Symbolic Verification Pipeline.

Normalises a natural-language legal question into a machine-readable
``QuestionSpec`` so that downstream verification rules can check
coverage, type-match, and temporal validity.

The extraction is done by a single LLM call with a JSON-mode prompt.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Optional

from ....shared.ports import AgentPort
from ....shared.domain import AgentRequest, ConversationContext
from .models import AnswerType, QuestionIntent, QuestionSpec

logger = logging.getLogger(__name__)

# Maps Vietnamese question cues → AnswerType (deterministic fallback)
_CUE_MAP: dict[str, AnswerType] = {
    "bao nhiêu": AnswerType.AMOUNT_RANGE,
    "mức phạt": AnswerType.AMOUNT_RANGE,
    "phạt bao nhiêu": AnswerType.AMOUNT_RANGE,
    "tiền phạt": AnswerType.AMOUNT_RANGE,
    "có được": AnswerType.BOOLEAN,
    "có phải": AnswerType.BOOLEAN,
    "có bị": AnswerType.BOOLEAN,
    "đúng hay sai": AnswerType.BOOLEAN,
    "điều nào": AnswerType.ARTICLE_REF,
    "khoản nào": AnswerType.ARTICLE_REF,
    "theo điều": AnswerType.ARTICLE_REF,
    "định nghĩa": AnswerType.DEFINITION,
    "là gì": AnswerType.DEFINITION,
    "nghĩa là gì": AnswerType.DEFINITION,
    "thủ tục": AnswerType.PROCEDURE,
    "trình tự": AnswerType.PROCEDURE,
    "hồ sơ": AnswerType.PROCEDURE,
    "hiệu lực": AnswerType.TEMPORAL,
    "khi nào": AnswerType.TEMPORAL,
    "từ ngày": AnswerType.TEMPORAL,
    "so sánh": AnswerType.COMPARISON,
    "khác nhau": AnswerType.COMPARISON,
}

_INTENT_MAP: dict[str, QuestionIntent] = {
    "phạt": QuestionIntent.SANCTION_LOOKUP,
    "mức phạt": QuestionIntent.SANCTION_LOOKUP,
    "bị xử phạt": QuestionIntent.SANCTION_LOOKUP,
    "chế tài": QuestionIntent.SANCTION_LOOKUP,
    "điều": QuestionIntent.ARTICLE_LOOKUP,
    "khoản": QuestionIntent.ARTICLE_LOOKUP,
    "định nghĩa": QuestionIntent.DEFINITION_LOOKUP,
    "là gì": QuestionIntent.DEFINITION_LOOKUP,
    "cấm": QuestionIntent.PROHIBITION_CHECK,
    "nghiêm cấm": QuestionIntent.PROHIBITION_CHECK,
    "hành vi bị cấm": QuestionIntent.PROHIBITION_CHECK,
    "quyền": QuestionIntent.RIGHT_OBLIGATION,
    "nghĩa vụ": QuestionIntent.RIGHT_OBLIGATION,
    "trách nhiệm": QuestionIntent.RIGHT_OBLIGATION,
    "thủ tục": QuestionIntent.PROCEDURE_LOOKUP,
    "trình tự": QuestionIntent.PROCEDURE_LOOKUP,
    "hiệu lực": QuestionIntent.VALIDITY_CHECK,
    "còn hiệu lực": QuestionIntent.VALIDITY_CHECK,
}

_SYSTEM_PROMPT = """Bạn là trợ lý phân tích câu hỏi pháp luật Việt Nam.
Nhiệm vụ: phân tích câu hỏi và trả về JSON chính xác theo schema bên dưới.

QUAN TRỌNG: Chỉ trả về JSON, KHÔNG kèm markdown hay giải thích.

Schema:
{
  "answer_type": "boolean|amount_range|article_ref|list|definition|procedure|comparison|temporal",
  "intent": "sanction_lookup|article_lookup|definition_lookup|prohibition_check|right_obligation|procedure_lookup|validity_check|comparison|general",
  "scope_documents": ["tên văn bản nếu được đề cập"],
  "scope_articles": ["Điều X", "Khoản Y"],
  "subject": "cá nhân / tổ chức / null",
  "act_or_behaviour": "hành vi được hỏi hoặc null",
  "context": "bối cảnh nếu có",
  "vehicle_or_object": "phương tiện/đối tượng nếu có",
  "time_reference": "thời điểm nếu có",
  "required_fields": ["các trường bắt buộc phải có trong câu trả lời"]
}"""


class QuestionSpecExtractor:
    """Extract a ``QuestionSpec`` from a natural-language question."""

    def __init__(self, llm_port: AgentPort):
        self._llm = llm_port

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def extract(self, question: str) -> QuestionSpec:
        """
        Analyse *question* and return a ``QuestionSpec``.

        The method tries LLM extraction first.  If it fails or returns
        garbage, a deterministic fallback based on keyword cues is used.
        """
        try:
            spec = await self._extract_via_llm(question)
            if spec is not None:
                return spec
        except Exception as e:
            logger.warning(f"LLM question-spec extraction failed: {e}")

        return self._extract_deterministic(question)

    # ------------------------------------------------------------------
    # LLM extraction
    # ------------------------------------------------------------------

    async def _extract_via_llm(self, question: str) -> Optional[QuestionSpec]:
        prompt = (
            f"Phân tích câu hỏi pháp luật sau và trả về JSON:\n\n"
            f"Câu hỏi: \"{question}\"\n\n"
            f"Trả về JSON theo schema đã cho."
        )

        request = AgentRequest(
            prompt=prompt,
            context=ConversationContext(
                session_id="question_spec",
                messages=[],
                system_prompt=_SYSTEM_PROMPT,
            ),
            temperature=0.0,
        )

        response = await self._llm.generate_response(request)
        raw: str = response.content.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        return self._dict_to_spec(question, data)

    # ------------------------------------------------------------------
    # Deterministic fallback
    # ------------------------------------------------------------------

    def _extract_deterministic(self, question: str) -> QuestionSpec:
        q_lower = question.lower()

        answer_type = AnswerType.ARTICLE_REF  # safe default
        for cue, at in _CUE_MAP.items():
            if cue in q_lower:
                answer_type = at
                break

        intent = QuestionIntent.GENERAL
        for cue, it in _INTENT_MAP.items():
            if cue in q_lower:
                intent = it
                break

        # Extract document references
        scope_docs: list[str] = re.findall(
            r"(?:Luật|Nghị định|Thông tư|Quyết định)\s+[\w/\-]+",
            question,
        )

        scope_articles: list[str] = re.findall(
            r"(?:Điều|Khoản|Điểm)\s+\d+\w*",
            question,
        )

        required_fields = self._infer_required_fields(answer_type)

        return QuestionSpec(
            original_question=question,
            answer_type=answer_type,
            intent=intent,
            scope_documents=scope_docs,
            scope_articles=scope_articles,
            required_fields=required_fields,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dict_to_spec(question: str, d: dict) -> QuestionSpec:
        """Convert a raw dict (from LLM JSON) into a validated QuestionSpec."""
        try:
            answer_type = AnswerType(d.get("answer_type", "article_ref"))
        except ValueError:
            answer_type = AnswerType.ARTICLE_REF

        try:
            intent = QuestionIntent(d.get("intent", "general"))
        except ValueError:
            intent = QuestionIntent.GENERAL

        time_ref = d.get("time_reference")
        effective_date = None
        if time_ref and time_ref not in ("null", "None", ""):
            try:
                effective_date = datetime.strptime(time_ref, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        return QuestionSpec(
            original_question=question,
            answer_type=answer_type,
            intent=intent,
            scope_documents=d.get("scope_documents") or [],
            scope_articles=d.get("scope_articles") or [],
            subject=d.get("subject"),
            act_or_behaviour=d.get("act_or_behaviour"),
            context=d.get("context"),
            vehicle_or_object=d.get("vehicle_or_object"),
            time_reference=time_ref,
            effective_date=effective_date,
            required_fields=d.get("required_fields") or [],
        )

    @staticmethod
    def _infer_required_fields(answer_type: AnswerType) -> list[str]:
        mapping: dict[AnswerType, list[str]] = {
            AnswerType.AMOUNT_RANGE: ["penalty_amount", "currency", "article_ref"],
            AnswerType.BOOLEAN: ["boolean_answer", "article_ref"],
            AnswerType.ARTICLE_REF: ["article_ref"],
            AnswerType.DEFINITION: ["definition_text", "article_ref"],
            AnswerType.PROCEDURE: ["procedure_steps", "article_ref"],
            AnswerType.TEMPORAL: ["effective_date", "article_ref"],
            AnswerType.LIST: ["list_items", "article_ref"],
            AnswerType.COMPARISON: ["list_items", "article_ref"],
        }
        return mapping.get(answer_type, ["article_ref"])
