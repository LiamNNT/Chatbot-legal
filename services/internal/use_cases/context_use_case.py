import logging
from typing import Any, Dict, List, Optional

from ..domain.entities import RAGContext
from ..ports.agent_port import AgentPort
from ..domain.value_objects import AgentRequest

logger = logging.getLogger(__name__)

_CONTEXTUALIZE_SYSTEM_PROMPT = (
    "Given a chat history and the latest user question which might reference "
    "context in the chat history, formulate a standalone question which can be "
    "understood without the chat history. Do NOT answer the question, just "
    "rewrite it if needed, otherwise return it as is."
)


class ContextUseCase:
    def __init__(self, agent_port: AgentPort):
        self._agent_port = agent_port

    async def rewrite_query(self, query: str, history: List[Dict[str, str]]) -> str:
        if not history:
            logger.debug("No history — returning original query")
            return query

        try:
            history_text = self._format_history(history)
            user_prompt = (
                f"Chat history:\n{history_text}\n\n"
                f"Latest question: {query}\n\n"
                f"Standalone question:"
            )

            request = AgentRequest(
                prompt=user_prompt,
                temperature=0.0,
                max_tokens=150,
                stream=False,
            )
            from ..domain.entities import ConversationContext

            request = AgentRequest(
                prompt=user_prompt,
                context=ConversationContext(
                    session_id="__context_rewrite__",
                    messages=[],
                    system_prompt=_CONTEXTUALIZE_SYSTEM_PROMPT,
                ),
                temperature=0.0,
                max_tokens=150,
                stream=False,
            )

            response = await self._agent_port.generate_response(request)
            rewritten = response.content.strip()
            logger.info("Query rewritten: '%s' → '%s'", query, rewritten)
            return rewritten

        except Exception as e:
            logger.error("Query rewriting failed: %s — returning original", e)
            return query

    def extract_relevant_documents(self, rag_context: RAGContext, max_docs: int = 5) -> List[Dict[str, Any]]:
        relevant: List[Dict[str, Any]] = []

        for i, doc in enumerate(rag_context.retrieved_documents[:max_docs]):
            content = doc.get("text", doc.get("content", "")).strip()
            if not content or len(content) <= 10:
                continue

            score = 0.0
            if (
                rag_context.relevance_scores
                and i < len(rag_context.relevance_scores)
            ):
                score = rag_context.relevance_scores[i]

            relevant.append(
                {
                    "rank": i + 1,
                    "content": content,
                    "title": doc.get("title", f"Document {i + 1}"),
                    "metadata": doc.get("metadata", {}),
                    "relevance_score": score,
                }
            )

        return relevant

    @staticmethod
    def _format_history(history: List[Dict[str, str]],max_entries: int = 6) -> str:
        recent = history[-max_entries:] if len(history) > max_entries else history
        lines = [
            f"{entry.get('role', 'user').capitalize()}: {entry.get('content', '')}"
            for entry in recent
        ]
        return "\n".join(lines)
