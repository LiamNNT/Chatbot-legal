"""
Cypher Query Generator — Stage 1 of the Symbolic Verification Pipeline.

Given a ``QuestionSpec``, asks the LLM to produce a Cypher query that
retrieves exactly the legal provisions needed to answer the question.

The LLM is NOT allowed to answer the question itself — only to produce
a Cypher query + entity mappings.  The actual answer comes from KG data.

Adapts the SPARQL-generation concept from Rademaker et al. (2024) to
the Neo4j/Cypher world used by this project's Legal KG.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from ....shared.ports import AgentPort
from ....shared.domain import AgentRequest, ConversationContext
from .models import (
    AnswerType,
    EntityMapping,
    GeneratedCypher,
    QuestionSpec,
)

logger = logging.getLogger(__name__)

# -- KG schema summary injected into the prompt so the LLM knows
#    what labels / relationship types are available.

_KG_SCHEMA = """
## Neo4j Knowledge Graph Schema — Vietnamese Legal Documents

### Node labels (use Vietnamese values)
Văn bản:  Luật, Nghị định, Thông tư, Quyết định
Cấu trúc: Phần, Chương, Mục, Điều, Khoản, Điểm
Thực thể: Cơ quan, Tổ chức, Cá nhân, Chủ thể
Khái niệm: Khái niệm, Thuật ngữ, Nguyên tắc, Chính sách
Quyền/NV:  Quyền, Nghĩa vụ, Trách nhiệm
Hành vi:   Hành vi cấm, Hành vi được phép, Vi phạm
Chế tài:   Chế tài, Xử lý
Thủ tục:   Thủ tục, Điều kiện, Trình tự
Phạm vi:   Lĩnh vực, Phạm vi

### Common node properties
Văn bản:   name, document_number, title, effective_date, status, issuing_authority
Điều:      name, article_number, title, content
Khoản:     name, clause_number, content
Chế tài:   name, content, penalty_type, min_amount, max_amount, currency
Hành vi:   name, content, description

### Relationship types (UPPER_SNAKE_CASE)
Cấu trúc:   THUOC_VE (belongs-to), CHUA (contains), KE_TIEP (next)
Tham chiếu:  THAM_CHIEU, DAN_CHIEU, VIEN_DAN
Hiệu lực:   THAY_THE (replace), SUA_DOI (amend), BO_SUNG (supplement), BAI_BO (repeal)
Ngữ nghĩa:  DINH_NGHIA, LA_LOAI, BAO_GOM, LIEN_QUAN, DONG_NGHIA
Pháp lý:    QUY_DINH, AP_DUNG, DIEU_CHINH, RANG_BUOC
Chủ thể:    CO_QUYEN, CO_NGHIA_VU, CHIU_TRACH_NHIEM, QUAN_LY, THUOC_THAM_QUYEN
Hành vi:     DAN_DEN (leads-to), BI_XU_LY (sanctioned-by)
Điều kiện:   YEU_CAU, NGOAI_TRU
"""

_SYSTEM_PROMPT = f"""Bạn là trợ lý chuyên sinh truy vấn Cypher cho đồ thị tri thức pháp luật Việt Nam trên Neo4j.

QUAN TRỌNG:
- KHÔNG trả lời câu hỏi. Chỉ sinh truy vấn Cypher.
- Sử dụng ĐÚNG label và relationship type bên dưới.
- Trả về JSON duy nhất, KHÔNG markdown, KHÔNG giải thích.
- Cypher phải trả về đủ thông tin cần thiết (mọi trường cần thiết).
- Dùng tham số $param thay vì chèn giá trị trực tiếp.

{_KG_SCHEMA}

### JSON output schema:
{{
  "cypher": "<Cypher query>",
  "params": {{"key": "value"}},
  "entity_mappings": [
    {{"mention": "text trong câu hỏi", "node_type": "label", "kg_identifier": "giá trị KG", "confidence": 1.0}}
  ],
  "explanation": "giải thích ngắn Cypher query làm gì",
  "expected_return_fields": ["field1", "field2"]
}}"""

# Pre-built Cypher templates for common intents
_CYPHER_TEMPLATES: dict[str, str] = {
    "sanction_lookup": """
MATCH (doc)-[:CHUA*1..3]->(dieu:`Điều`)-[:CHUA*0..2]->(khoan)
WHERE doc.name CONTAINS $doc_name OR doc.document_number CONTAINS $doc_name
MATCH (hv)-[:BI_XU_LY]->(ct:`Chế tài`)
WHERE hv.content CONTAINS $behaviour OR hv.name CONTAINS $behaviour
MATCH (hv)-[:THUOC_VE|LIEN_QUAN*1..2]->(dieu)
RETURN dieu.name AS article, khoan.content AS clause_content,
       ct.name AS sanction, ct.content AS sanction_detail,
       ct.min_amount AS min_amount, ct.max_amount AS max_amount,
       doc.name AS document
LIMIT 10
""",
    "definition_lookup": """
MATCH (kn)-[:DINH_NGHIA|LA_LOAI]->(target)
WHERE kn.name CONTAINS $term OR kn.content CONTAINS $term
OPTIONAL MATCH (kn)-[:THUOC_VE*1..3]->(dieu:`Điều`)-[:THUOC_VE*1..3]->(doc)
RETURN kn.name AS concept, kn.content AS definition,
       dieu.name AS article, doc.name AS document
LIMIT 5
""",
    "prohibition_check": """
MATCH (hv:`Hành vi cấm`)
WHERE hv.content CONTAINS $behaviour OR hv.name CONTAINS $behaviour
OPTIONAL MATCH (hv)-[:THUOC_VE|LIEN_QUAN*1..3]->(dieu:`Điều`)-[:THUOC_VE*1..3]->(doc)
OPTIONAL MATCH (hv)-[:BI_XU_LY]->(ct:`Chế tài`)
RETURN hv.name AS prohibited_act, hv.content AS description,
       dieu.name AS article, doc.name AS document,
       ct.content AS sanction
LIMIT 10
""",
    "article_lookup": """
MATCH (doc)-[:CHUA*1..3]->(dieu:`Điều`)
WHERE (doc.name CONTAINS $doc_name OR doc.document_number CONTAINS $doc_name)
  AND (dieu.article_number = $article_number OR dieu.name CONTAINS $article_name)
OPTIONAL MATCH (dieu)-[:CHUA]->(khoan:`Khoản`)
RETURN dieu.name AS article, dieu.content AS article_content,
       collect(khoan.content) AS clauses, doc.name AS document
""",
}


class CypherQueryGenerator:
    """Generate a Cypher query from a ``QuestionSpec``."""

    MAX_RETRIES = 2

    def __init__(self, llm_port: AgentPort):
        self._llm = llm_port

    async def generate(
        self,
        spec: QuestionSpec,
        corrective_hint: str = "",
    ) -> GeneratedCypher:
        """
        Ask the LLM to produce a Cypher query for *spec*.

        If *corrective_hint* is provided (e.g. from a failed verification),
        it is appended to the prompt so the LLM can fix its query.
        """
        prompt = self._build_prompt(spec, corrective_hint)

        request = AgentRequest(
            prompt=prompt,
            context=ConversationContext(
                session_id="cypher_gen",
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
            return self._parse_response(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"LLM returned invalid JSON for Cypher generation: {e}")
            # Try extracting Cypher from raw text
            return self._fallback_parse(raw, spec)

    def generate_from_template(self, spec: QuestionSpec) -> Optional[GeneratedCypher]:
        """
        Try to build a Cypher query from a pre-built template
        (no LLM needed).  Returns None if no template matches.
        """
        template = _CYPHER_TEMPLATES.get(spec.intent.value)
        if template is None:
            return None

        params = self._build_template_params(spec)
        return GeneratedCypher(
            cypher=template.strip(),
            params=params,
            entity_mappings=self._build_entity_mappings(spec),
            explanation=f"Template-based query for {spec.intent.value}",
            expected_return_fields=self._expected_fields_for(spec),
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_prompt(self, spec: QuestionSpec, corrective_hint: str) -> str:
        parts = [
            f"Câu hỏi gốc: \"{spec.original_question}\"",
            f"Loại câu trả lời mong đợi: {spec.answer_type.value}",
            f"Intent: {spec.intent.value}",
        ]

        if spec.scope_documents:
            parts.append(f"Văn bản liên quan: {', '.join(spec.scope_documents)}")
        if spec.scope_articles:
            parts.append(f"Điều/khoản liên quan: {', '.join(spec.scope_articles)}")
        if spec.act_or_behaviour:
            parts.append(f"Hành vi: {spec.act_or_behaviour}")
        if spec.subject:
            parts.append(f"Chủ thể: {spec.subject}")
        if spec.context:
            parts.append(f"Bối cảnh: {spec.context}")
        if spec.vehicle_or_object:
            parts.append(f"Phương tiện/đối tượng: {spec.vehicle_or_object}")
        if spec.time_reference:
            parts.append(f"Thời điểm: {spec.time_reference}")
        if spec.required_fields:
            parts.append(f"Trường bắt buộc trong kết quả: {', '.join(spec.required_fields)}")

        if corrective_hint:
            parts.append(f"\n⚠ LƯU Ý SỬA LỖI: {corrective_hint}")

        parts.append("\nHãy sinh Cypher query phù hợp cho câu hỏi trên.")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(data: dict) -> GeneratedCypher:
        mappings = [
            EntityMapping(
                mention=m.get("mention", ""),
                node_type=m.get("node_type", ""),
                kg_identifier=m.get("kg_identifier", ""),
                confidence=m.get("confidence", 1.0),
            )
            for m in data.get("entity_mappings", [])
        ]
        return GeneratedCypher(
            cypher=data["cypher"],
            params=data.get("params", {}),
            entity_mappings=mappings,
            explanation=data.get("explanation", ""),
            expected_return_fields=data.get("expected_return_fields", []),
        )

    @staticmethod
    def _fallback_parse(raw: str, spec: QuestionSpec) -> GeneratedCypher:
        """Best-effort: extract a Cypher query from free text."""
        # Try to find MATCH ... RETURN block
        m = re.search(r"(MATCH\s.+?RETURN\s.+?)(?:\n\n|$)", raw, re.DOTALL | re.IGNORECASE)
        cypher = m.group(1).strip() if m else raw
        return GeneratedCypher(
            cypher=cypher,
            params={},
            entity_mappings=[],
            explanation="Fallback parse — LLM did not return valid JSON",
            expected_return_fields=[],
        )

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_template_params(spec: QuestionSpec) -> dict:
        params: dict = {}
        if spec.scope_documents:
            params["doc_name"] = spec.scope_documents[0]
        if spec.act_or_behaviour:
            params["behaviour"] = spec.act_or_behaviour
        if spec.scope_articles:
            # Try to extract number
            for art in spec.scope_articles:
                m = re.search(r"\d+", art)
                if m:
                    params["article_number"] = int(m.group())
                    params["article_name"] = art
                    break
        # Definition lookup
        if spec.intent.value == "definition_lookup":
            params["term"] = spec.act_or_behaviour or spec.original_question
        return params

    @staticmethod
    def _build_entity_mappings(spec: QuestionSpec) -> list[EntityMapping]:
        mappings: list[EntityMapping] = []
        for doc in spec.scope_documents:
            mappings.append(EntityMapping(
                mention=doc, node_type="Document", kg_identifier=doc,
            ))
        if spec.act_or_behaviour:
            mappings.append(EntityMapping(
                mention=spec.act_or_behaviour, node_type="Hành vi",
                kg_identifier=spec.act_or_behaviour,
            ))
        return mappings

    @staticmethod
    def _expected_fields_for(spec: QuestionSpec) -> list[str]:
        mapping = {
            AnswerType.AMOUNT_RANGE: ["article", "sanction", "min_amount", "max_amount", "document"],
            AnswerType.BOOLEAN: ["article", "result", "document"],
            AnswerType.ARTICLE_REF: ["article", "article_content", "document"],
            AnswerType.DEFINITION: ["concept", "definition", "article", "document"],
            AnswerType.PROCEDURE: ["article", "procedure_steps", "document"],
            AnswerType.LIST: ["article", "items", "document"],
            AnswerType.TEMPORAL: ["article", "effective_date", "document"],
        }
        return mapping.get(spec.answer_type, ["article", "document"])
