"""
Answer Generator — Stage 4 of the Symbolic Verification Pipeline.

The LLM is given ONLY the KG result data and must:
  1. Produce a natural-language answer in Vietnamese
  2. Produce a ``StructuredAnswer`` (machine-checkable) alongside it
  3. NOT add any facts that are not in the KG result

The prompt explicitly forbids hallucination — every claim must map
to a KGRecord evidence_id.
"""

from __future__ import annotations

import json
import logging
import re
from typing import List, Optional

from ....shared.ports import AgentPort
from ....shared.domain import AgentRequest, ConversationContext
from .models import (
    AmountRange,
    AnswerType,
    ArticleRef,
    KGResult,
    QuestionSpec,
    StructuredAnswer,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Bạn là trợ lý pháp luật Việt Nam.

NGUYÊN TẮC TUYỆT ĐỐI:
1. Chỉ được sử dụng thông tin từ "Kết quả Knowledge Graph" bên dưới.
2. KHÔNG được bịa thêm bất kỳ thông tin nào không có trong kết quả.
3. Mọi mệnh đề quan trọng PHẢI có trích dẫn (Điều/Khoản/Văn bản).
4. Nếu thông tin thiếu, nói rõ "Không tìm thấy đủ dữ liệu trong KG".

Trả về JSON duy nhất theo schema bên dưới. KHÔNG markdown, KHÔNG giải thích bên ngoài JSON.

Schema:
{
  "natural_language": "<Câu trả lời bằng tiếng Việt, kèm trích dẫn>",
  "answer_type": "boolean|amount_range|article_ref|list|definition|procedure|comparison|temporal",
  "article_refs": [{"document": "tên VB", "article": "Điều X", "clause": "Khoản Y", "point": "Điểm Z"}],
  "amount_range": {"min_amount": null, "max_amount": null, "currency": "VND", "unit": "đồng"} or null,
  "boolean_answer": true/false/null,
  "list_items": ["item1", "item2"],
  "definition_text": "nội dung định nghĩa hoặc rỗng",
  "evidence_ids": [0, 1, 2],
  "assumptions": ["giả định nếu thiếu dữ liệu"],
  "citations": ["Điều X Khoản Y Nghị định Z"]
}"""


class AnswerGenerator:
    """Generate a verified answer from KG results only."""

    def __init__(self, llm_port: AgentPort):
        self._llm = llm_port

    async def generate(
        self,
        spec: QuestionSpec,
        kg_result: KGResult,
    ) -> StructuredAnswer:
        """
        Ask LLM to formulate an answer using ONLY ``kg_result`` data.
        """
        if kg_result.is_empty:
            return self._empty_answer(spec)

        prompt = self._build_prompt(spec, kg_result)

        request = AgentRequest(
            prompt=prompt,
            context=ConversationContext(
                session_id="answer_gen",
                messages=[],
                system_prompt=_SYSTEM_PROMPT,
            ),
            temperature=0.0,
        )

        response = await self._llm.generate_response(request)
        raw: str = response.content.strip()

        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            data = json.loads(raw)
            return self._parse_answer(data, spec)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"LLM returned invalid JSON for answer: {e}")
            # Fallback: use raw text as the answer
            return StructuredAnswer(
                answer_type=spec.answer_type,
                natural_language=response.content,
                assumptions=["LLM không trả về đúng format JSON"],
            )

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, spec: QuestionSpec, kg_result: KGResult) -> str:
        # Format KG records for the prompt
        records_text = self._format_kg_records(kg_result)

        parts = [
            f"Câu hỏi gốc: \"{spec.original_question}\"",
            f"Loại câu trả lời mong đợi: {spec.answer_type.value}",
            "",
            "=== Kết quả Knowledge Graph ===",
            records_text,
            "=== Hết kết quả ===",
            "",
            f"Các trường bắt buộc: {', '.join(spec.required_fields)}" if spec.required_fields else "",
            "",
            "Hãy dựa HOÀN TOÀN vào kết quả KG để trả lời. Trả về JSON.",
        ]
        return "\n".join(parts)

    @staticmethod
    def _format_kg_records(kg_result: KGResult) -> str:
        parts: list[str] = []
        for idx, record in enumerate(kg_result.records):
            parts.append(f"[Record {idx}]")
            for k, v in record.data.items():
                parts.append(f"  {k}: {v}")
        return "\n".join(parts) if parts else "(không có dữ liệu)"

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_answer(data: dict, spec: QuestionSpec) -> StructuredAnswer:
        try:
            answer_type = AnswerType(data.get("answer_type", spec.answer_type.value))
        except ValueError:
            answer_type = spec.answer_type

        article_refs = [
            ArticleRef(
                document=r.get("document", ""),
                article=r.get("article", ""),
                clause=r.get("clause", ""),
                point=r.get("point", ""),
            )
            for r in data.get("article_refs", [])
        ]

        amount = data.get("amount_range")
        amount_range = None
        if amount and isinstance(amount, dict):
            amount_range = AmountRange(
                min_amount=amount.get("min_amount"),
                max_amount=amount.get("max_amount"),
                currency=amount.get("currency", "VND"),
                unit=amount.get("unit", ""),
            )

        return StructuredAnswer(
            answer_type=answer_type,
            article_refs=article_refs,
            amount_range=amount_range,
            evidence_ids=[str(e) for e in data.get("evidence_ids", [])],
            boolean_answer=data.get("boolean_answer"),
            list_items=data.get("list_items", []),
            definition_text=data.get("definition_text", ""),
            assumptions=data.get("assumptions", []),
            natural_language=data.get("natural_language", ""),
            citations=data.get("citations", []),
        )

    @staticmethod
    def _empty_answer(spec: QuestionSpec) -> StructuredAnswer:
        return StructuredAnswer(
            answer_type=spec.answer_type,
            natural_language=(
                "Không tìm thấy dữ liệu trong Knowledge Graph để trả lời câu hỏi này. "
                "Vui lòng kiểm tra lại tên văn bản, điều khoản hoặc nội dung câu hỏi."
            ),
            assumptions=["KG trả về kết quả rỗng"],
        )
