"""
Answer Agent — generates the final answer from retrieved context.

Responsibilities:
1. Build prompt from context documents + query
2. Call LLM (sync or streaming)
3. Parse JSON or fallback to text extraction
4. Estimate confidence & create detailed source citations

The system prompt is loaded from YAML config at runtime.
"""

import json
import logging
import os
from typing import Dict, Any, List, AsyncGenerator

from ..base import SpecializedAgent, AgentConfig, AnswerResult, DetailedSource
from .prompts import build_answer_prompt
from .utils import (
    extract_answer_from_text,
    estimate_confidence,
    create_detailed_sources,
)


logger = logging.getLogger(__name__)


class AnswerAgent(SpecializedAgent):
    """Answer Agent — single LLM call to produce the user-facing answer."""

    def __init__(self, config: AgentConfig, agent_port):
        super().__init__(config, agent_port)
        params = getattr(config, "parameters", {}) or {}
        self.min_answer_length = params.get("min_answer_length", 50)
        self.max_sources = params.get("max_sources", 5)
        self.confidence_thresholds = params.get(
            "confidence_thresholds", {"high": 0.8, "medium": 0.6, "low": 0.4}
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process(self, input_data: Dict[str, Any]) -> AnswerResult:
        query = input_data.get("query", "")
        prompt = build_answer_prompt(
            query,
            input_data.get("context_documents", []),
            input_data.get("rewritten_queries", []),
            input_data.get("previous_context", ""),
            input_data.get("previous_feedback", ""),
        )

        response = await self._make_agent_request(prompt)

        try:
            answer_data = json.loads(response.content)
            return self._create_answer_result(answer_data, query)
        except json.JSONDecodeError:
            return self._create_fallback_answer(
                query, response.content, input_data.get("context_documents", [])
            )

    async def stream_process(self, input_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        query = input_data.get("query", "")
        prompt = build_answer_prompt(
            query,
            input_data.get("context_documents", []),
            input_data.get("rewritten_queries", []),
            input_data.get("previous_context", ""),
            input_data.get("previous_feedback", ""),
        )
        async for chunk in self._stream_agent_request(prompt):
            yield chunk

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def _stream_agent_request(self, prompt: str) -> AsyncGenerator[str, None]:
        from ....shared.domain import ConversationContext, AgentRequest

        if os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG":
            logger.debug(f"\n{'='*80}")
            logger.debug(f"🔵 AGENT STREAMING INPUT - {self.config.agent_type.value.upper()}")
            logger.debug(f"{'='*80}")
            logger.debug(f"System Prompt Length: {len(self.config.system_prompt)} chars")
            logger.debug(
                f"User Prompt: {prompt[:500]}..." if len(prompt) > 500 else f"User Prompt: {prompt}"
            )
            logger.debug(f"Model: {self.config.model}")
            logger.debug(f"Temperature: {self.config.temperature}")
            logger.debug(f"{'='*80}\n")

        conversation_context = ConversationContext(
            session_id="agent_stream_session",
            messages=[],
            system_prompt=self.config.system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        request = AgentRequest(
            prompt=prompt,
            context=conversation_context,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
            metadata={"agent_type": self.config.agent_type.value},
        )

        async for chunk in self.agent_port.stream_response(request):
            yield chunk

    # ------------------------------------------------------------------
    # Result construction
    # ------------------------------------------------------------------

    def _create_answer_result(self, answer_data: Dict[str, Any], original_query: str) -> AnswerResult:
        return AnswerResult(
            query=original_query,
            answer=answer_data.get("answer", ""),
            confidence=answer_data.get("confidence", 0.5),
            sources_used=answer_data.get("sources_used", []),
            reasoning_steps=answer_data.get("reasoning_steps", []),
            metadata=answer_data.get("metadata", {}),
            detailed_sources=[],
        )

    def _create_fallback_answer(
        self,
        query: str,
        response_content: str,
        context_documents: List[Dict[str, Any]],
    ) -> AnswerResult:
        answer = extract_answer_from_text(response_content, self.min_answer_length)
        confidence = estimate_confidence(context_documents, answer)
        sources_used = [
            doc.get("title", f"Document {i+1}")
            for i, doc in enumerate(context_documents[: self.max_sources])
        ]
        detailed = create_detailed_sources(context_documents[: self.max_sources])

        return AnswerResult(
            query=query,
            answer=answer,
            confidence=confidence,
            sources_used=sources_used,
            reasoning_steps=[
                "Sử dụng thông tin từ tài liệu tham khảo",
                "Tổng hợp và phân tích nội dung",
            ],
            metadata={
                "fallback": True,
                "method": "text_extraction",
                "original_length": len(response_content),
            },
            detailed_sources=detailed,
        )
