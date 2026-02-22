"""
Chat route handlers for the orchestrator API.

Endpoints:
    POST /chat           – Multi-agent orchestration (streaming / non-streaming)
    POST /chat/simple    – Single-agent simple orchestration
    POST /chat/stream    – Experimental streaming via OrchestrationService
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import json
import logging
from typing import AsyncGenerator

from ..shared.container.container import get_orchestration_service, get_multi_agent_orchestrator
from ..shared.domain import OrchestrationRequest, RAGContext
from ..shared.exceptions import OrchestrationDomainException
from .agents.base import AgentType
from ..shared.schemas import (
    ChatRequest,
    ChatResponse,
    ProcessingStats,
)
from .exception_handlers import ExceptionMessageHandler
from .response_mappers import build_chat_response, build_rag_context_info, build_processing_stats

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Generate response using optimized 2-agent orchestration pipeline",
    description=(
        "Process user query through optimized 2-agent pipeline "
        "(Smart Planner + Answer Agent with built-in formatting). "
        "Supports both streaming and non-streaming responses."
    ),
)
async def chat(request: ChatRequest):
    """Multi-agent chat endpoint (stream-aware)."""
    if request.stream:
        return await _chat_stream_multi_agent(request)

    try:
        multi_agent_orchestrator = get_multi_agent_orchestrator()

        orch_request = OrchestrationRequest(
            user_query=request.query,
            session_id=request.session_id,
            use_rag=request.use_rag,
            use_knowledge_graph=request.use_knowledge_graph,
            rag_top_k=request.rag_top_k,
            agent_model=request.model,
            metadata={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": request.stream,
            },
        )

        response = await multi_agent_orchestrator.process_request(orch_request)
        return build_chat_response(response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /chat/simple
# ---------------------------------------------------------------------------

@router.post(
    "/chat/simple",
    response_model=ChatResponse,
    summary="Generate response using simple orchestration pipeline",
    description="Process user query through simple single-agent pipeline (faster but less sophisticated)",
)
async def simple_chat(request: ChatRequest) -> ChatResponse:
    """Single-agent simple chat endpoint."""
    try:
        orchestration_service = get_orchestration_service()

        orch_request = OrchestrationRequest(
            user_query=request.query,
            session_id=request.session_id,
            use_rag=request.use_rag,
            rag_top_k=request.rag_top_k,
            agent_model=request.model,
            metadata={
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": request.stream,
                "endpoint": "simple_chat",
            },
        )

        response = await orchestration_service.process_request(orch_request)
        return build_chat_response(response, search_mode_fallback="simple")

    except OrchestrationDomainException as domain_ex:
        fallback = ExceptionMessageHandler.create_fallback_response(
            exception=domain_ex,
            session_id=request.session_id or "unknown",
            user_query=request.query,
        )
        return ChatResponse(
            response=fallback["response"],
            session_id=fallback["session_id"],
            timestamp=datetime.now(),
            rag_context=None,
            processing_stats=ProcessingStats(
                total_time=0.0,
                rag_error=domain_ex.details.get("agent_error") if hasattr(domain_ex, "details") else None,
            ),
            model_used="error_handler",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simple chat processing failed: {str(e)}")


# ---------------------------------------------------------------------------
# POST /chat/stream
# ---------------------------------------------------------------------------

@router.post(
    "/chat/stream",
    summary="Stream response using orchestration pipeline",
    description="Stream response from agent with RAG context (experimental)",
)
async def chat_stream(request: ChatRequest):
    """Experimental streaming endpoint via OrchestrationService."""
    if not request.stream:
        raise HTTPException(status_code=400, detail="Stream must be enabled for this endpoint")

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            orchestration_service = get_orchestration_service()
            session_id = request.session_id or "temp_session"
            context = await orchestration_service._get_or_create_context(session_id)

            rag_context = None
            if request.use_rag:
                try:
                    rag_data = await orchestration_service.rag_port.retrieve_context(
                        query=request.query, top_k=request.rag_top_k
                    )
                    rag_context = RAGContext(
                        query=request.query,
                        retrieved_documents=rag_data.get("retrieved_documents", []),
                        search_metadata=rag_data.get("search_metadata"),
                    )
                except Exception:
                    pass

            agent_request = orchestration_service._prepare_agent_request(
                user_query=request.query,
                rag_context=rag_context,
                context=context,
                model=request.model,
                metadata={
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True,
                },
            )

            async for chunk in orchestration_service.agent_port.stream_response(agent_request):
                yield f"data: {json.dumps({'content': chunk})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except OrchestrationDomainException as domain_ex:
            user_message = ExceptionMessageHandler.get_user_message(domain_ex)
            yield f"data: {json.dumps({'error': user_message, 'is_user_error': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': f'Đã có lỗi hệ thống: {str(e)}', 'is_system_error': True})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------------------------------------------------------------------------
# Internal: multi-agent streaming helper
# ---------------------------------------------------------------------------

async def _chat_stream_multi_agent(request: ChatRequest):
    """Stream a response using the multi-agent orchestration pipeline (SSE)."""

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            multi_agent_orchestrator = get_multi_agent_orchestrator()

            # Step 1: Planning
            planning_result = None
            if multi_agent_orchestrator.enable_planning:
                try:
                    smart_planner = multi_agent_orchestrator.agent_factory.create_agent(AgentType.SMART_PLANNER)
                    planning_result = await smart_planner.process({"query": request.query, "conversation_history": []})
                    yield f"data: {json.dumps({'type': 'planning', 'content': 'Đang phân tích câu hỏi...'})}\n\n"
                except Exception as e:
                    logger.warning(f"Planning failed, continuing without it: {e}")

            # Step 2: RAG Retrieval
            rag_context = None
            context_documents = []
            if request.use_rag:
                try:
                    yield f"data: {json.dumps({'type': 'status', 'content': 'Đang tìm kiếm thông tin liên quan...'})}\n\n"
                    queries_to_use = [request.query]
                    if planning_result and hasattr(planning_result, "rewritten_queries"):
                        queries_to_use = planning_result.rewritten_queries or [request.query]

                    rag_data = await multi_agent_orchestrator.rag_port.retrieve_context(
                        query=queries_to_use[0], top_k=request.rag_top_k
                    )
                    rag_context = RAGContext(
                        query=queries_to_use[0],
                        retrieved_documents=rag_data.get("retrieved_documents", []),
                        search_metadata=rag_data.get("search_metadata"),
                    )
                    context_documents = rag_context.retrieved_documents
                    yield f"data: {json.dumps({'type': 'status', 'content': f'Đã tìm thấy {len(context_documents)} tài liệu liên quan'})}\n\n"
                except Exception as e:
                    logger.warning(f"RAG retrieval failed: {e}")
                    yield f"data: {json.dumps({'type': 'warning', 'content': 'Không tìm thấy tài liệu tham khảo, sẽ trả lời dựa trên kiến thức chung'})}\n\n"

            # Step 3: Stream answer
            yield f"data: {json.dumps({'type': 'status', 'content': 'Đang tạo câu trả lời...'})}\n\n"
            answer_agent = multi_agent_orchestrator.agent_factory.create_agent(AgentType.ANSWER_AGENT)
            answer_input = {
                "query": request.query,
                "context_documents": context_documents,
                "rewritten_queries": planning_result.rewritten_queries if planning_result else [],
                "previous_context": "",
            }
            async for chunk in answer_agent.stream_process(answer_input):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'content': 'Hoàn thành'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Đã có lỗi xảy ra: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
