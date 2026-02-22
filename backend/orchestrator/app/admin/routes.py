"""
Admin / debug route handlers for the orchestrator API.

Endpoints:
    GET  /health       – Health check
    GET  /debug/graph  – Debug graph adapter status
    GET  /agents/info  – Agent system information
    POST /agents/test  – Test multi-agent system
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import os
import logging

from ..shared.container.container import get_orchestration_service, get_multi_agent_orchestrator
from ..shared.domain import OrchestrationRequest
from ..shared.schemas import HealthResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of all orchestrator components",
)
async def health_check() -> HealthResponse:
    """Perform health check on all orchestrator components."""
    try:
        orchestration_service = get_orchestration_service()
        health_status = await orchestration_service.health_check()

        return HealthResponse(
            status=health_status["overall"],
            timestamp=datetime.fromisoformat(health_status["timestamp"]),
            services={k: v for k, v in health_status.items() if k not in ("overall", "timestamp")},
        )
    except Exception as e:
        return HealthResponse(status="error", timestamp=datetime.now(), services={"error": str(e)})


# ---------------------------------------------------------------------------
# GET /debug/graph
# ---------------------------------------------------------------------------

@router.get(
    "/debug/graph",
    summary="Debug Graph Adapter status",
    description="Check if Graph Adapter is initialized and working",
)
async def debug_graph_adapter():
    """Debug endpoint to check Graph Adapter initialization."""
    from ..shared.container.container import get_container

    try:
        container = get_container()
        graph_adapter = container.get_graph_adapter()

        return {
            "enabled": os.getenv("ENABLE_GRAPH_REASONING", "true").lower() == "true",
            "graph_adapter_initialized": graph_adapter is not None,
            "neo4j_uri": os.getenv("NEO4J_URI", "not set"),
            "neo4j_user": os.getenv("NEO4J_USER", "not set"),
            "neo4j_database": os.getenv("NEO4J_DATABASE", "not set"),
            "adapter_type": str(type(graph_adapter)) if graph_adapter else "None",
        }
    except Exception as e:
        return {"error": str(e), "enabled": os.getenv("ENABLE_GRAPH_REASONING", "not set")}


# ---------------------------------------------------------------------------
# GET /agents/info
# ---------------------------------------------------------------------------

@router.get(
    "/agents/info",
    summary="Get multi-agent system information",
    description="Get detailed information about all configured agents and their models",
)
async def get_agents_info() -> dict:
    """Get information about all configured agents in the multi-agent system."""
    try:
        multi_agent_orchestrator = get_multi_agent_orchestrator()
        health_info = await multi_agent_orchestrator.health_check()

        return {
            "multi_agent_system": {
                "enabled": True,
                "agents": health_info.get("agents", {}),
                "pipeline_steps": [
                    "1. Planning (DeepSeek V3.1) - Analyze query and create execution plan",
                    "2. Query Rewriting (LongCat Flash Chat) - Optimize queries for search",
                    "3. RAG Retrieval - Get relevant context using optimized queries",
                    "4. Answer Generation (Qwen3 Coder) - Generate comprehensive answers",
                    "5. Response Formatting (DeepSeek R1) - Verify and create user-friendly responses",
                ],
            },
            "models_used": {
                "smart_planner": "mistralai/mistral-7b-instruct:free",
                "answer_agent": "qwen/qwen-3-coder-free",
                "response_formatter": "deepseek/deepseek-r1-free",
            },
            "capabilities": {
                "smart_planning": "Analyzes intent, complexity, and rewrites queries in single LLM call",
                "rag_integration": "Retrieves relevant context from knowledge base (KG + Vector)",
                "answer_generation": "Creates comprehensive, structured answers",
                "response_formatting": "Verifies accuracy and ensures user-friendly output",
            },
            "configuration": {
                "verification_enabled": health_info.get("verification_enabled", True),
                "planning_enabled": health_info.get("planning_enabled", True),
                "providers": "OpenRouter API",
                "optimization": "40% fewer LLM calls vs 5-agent pipeline",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents info: {str(e)}")


# ---------------------------------------------------------------------------
# POST /agents/test
# ---------------------------------------------------------------------------

@router.post(
    "/agents/test",
    summary="Test multi-agent system",
    description="Test all agents with a simple query to verify system functionality",
)
async def test_agents() -> dict:
    """Test all agents in the multi-agent system with a simple query."""
    try:
        test_request = OrchestrationRequest(
            user_query="Xin chào, hệ thống multi-agent hoạt động như thế nào?",
            use_rag=False,
            rag_top_k=3,
            metadata={"test": True},
        )

        multi_agent_orchestrator = get_multi_agent_orchestrator()
        response = await multi_agent_orchestrator.process_request(test_request)

        return {
            "test_successful": True,
            "timestamp": datetime.now().isoformat(),
            "response_preview": (
                response.response[:200] + "..." if len(response.response) > 200 else response.response
            ),
            "processing_stats": response.processing_stats,
            "agents_tested": {
                "smart_planner": "✅ Executed" if "smart_planning_time" in response.processing_stats else "⚠️ Skipped",
                "answer_agent": "✅ Executed" if "answer_generation_time" in response.processing_stats else "❌ Failed",
                "response_formatter": "✅ Executed" if "response_formatting_time" in response.processing_stats else "❌ Failed",
            },
            "performance": {
                "total_time": f"{response.processing_stats.get('total_time', 0):.2f}s",
                "fastest_agent": min(
                    [(k, v) for k, v in response.processing_stats.items() if k.endswith("_time") and isinstance(v, (int, float))],
                    key=lambda x: x[1],
                    default=("none", 0),
                )[0],
                "slowest_agent": max(
                    [(k, v) for k, v in response.processing_stats.items() if k.endswith("_time") and isinstance(v, (int, float))],
                    key=lambda x: x[1],
                    default=("none", 0),
                )[0],
            },
            "quality_metrics": {
                "response_length": len(response.response),
                "has_structure": "✅" if any(w in response.response.lower() for w in ("đầu tiên", "thứ hai", "cuối cùng")) else "❌",
                "has_greeting": "✅" if any(w in response.response.lower() for w in ("xin chào", "chào bạn", "cảm ơn")) else "❌",
                "mentions_multiagent": "✅" if "multi" in response.response.lower() or "agent" in response.response.lower() else "❌",
            },
        }
    except Exception as e:
        return {
            "test_successful": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "suggestion": "Check OpenRouter API key and service connectivity",
        }
