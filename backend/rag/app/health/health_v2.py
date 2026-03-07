"""
Health Check Endpoints for RAG Services

Provides comprehensive health monitoring for all service dependencies:
- Neo4j Graph Database
- OpenAI LLM API
- Qdrant Vector Database
- OpenSearch Keyword Search
- Overall service health aggregation

Each endpoint returns detailed status, latency metrics, and diagnostics.

Author: GitHub Copilot
Date: November 2025
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
import time
import asyncio
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/health", tags=["health"])


# Health Status Models
class HealthStatus(str, Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    """Health status for a single component"""
    status: HealthStatus
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    message: str = Field(description="Status message or error details")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic info")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class AggregatedHealth(BaseModel):
    """Aggregated health status for entire service"""
    status: HealthStatus
    components: Dict[str, ComponentHealth]
    uptime_seconds: Optional[float] = None
    version: str = "2.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


# Startup time for uptime calculation
SERVICE_START_TIME = time.time()


# Health Check Functions
async def check_neo4j_health() -> ComponentHealth:
    """
    Check Neo4j graph database health
    
    Returns:
        ComponentHealth with Neo4j status
    """
    try:
        from app.knowledge_graph.stores.neo4j_store import Neo4jGraphAdapter
        from app.shared.config.settings import settings
        
        start_time = time.time()
        
        # Try to connect and run simple query
        repo = Neo4jGraphAdapter(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password
        )
        
        # Test query: count nodes
        async with repo.driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) as count LIMIT 1")
            record = await result.single()
            node_count = record["count"] if record else 0
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            message="Neo4j connection successful",
            details={
                "uri": settings.neo4j_uri.split("@")[-1],  # Hide credentials
                "node_count": node_count,
                "database": "neo4j",
            }
        )
    
    except ImportError as e:
        return ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Neo4j repository not configured: {str(e)}",
            details={"error_type": "import_error"}
        )
    
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"Neo4j connection failed: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


async def check_llm_health() -> ComponentHealth:
    """
    Check OpenAI LLM API health
    
    Returns:
        ComponentHealth with LLM API status
    """
    try:
        from app.llm.openai_client import OpenAIClient
        from app.shared.config.settings import settings
        
        if not settings.openai_api_key:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="OpenAI API key not configured",
                details={"configured": False}
            )
        
        start_time = time.time()
        
        # Create client and test with simple completion
        client = OpenAIClient(api_key=settings.openai_api_key)
        
        # Simple test prompt
        test_response = await client.complete(
            "Test health check",
            model="gpt-3.5-turbo",
            max_tokens=5
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            message="OpenAI API accessible",
            details={
                "model": "gpt-3.5-turbo",
                "api_configured": True,
                "response_length": len(test_response),
            }
        )
    
    except ImportError as e:
        return ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"LLM client not configured: {str(e)}",
            details={"error_type": "import_error"}
        )
    
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        
        # Check if it's an auth error vs connection error
        if "auth" in str(e).lower() or "api key" in str(e).lower():
            status = HealthStatus.UNHEALTHY
            message = "OpenAI API authentication failed"
        else:
            status = HealthStatus.DEGRADED
            message = f"OpenAI API error: {str(e)}"
        
        return ComponentHealth(
            status=status,
            message=message,
            details={"error": str(e), "error_type": type(e).__name__}
        )


async def check_qdrant_health() -> ComponentHealth:
    """
    Check Qdrant vector database health
    
    Returns:
        ComponentHealth with Qdrant status
    """
    try:
        from qdrant_client import QdrantClient
        from app.shared.config.settings import settings
        
        start_time = time.time()
        
        # Connect to Qdrant
        client = QdrantClient(
            url=settings.qdrant_url,
            timeout=15,
        )
        
        # Check connectivity by listing collections
        collections = client.get_collections().collections
        
        latency_ms = (time.time() - start_time) * 1000
        
        collection_names = [c.name for c in collections]
        
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            message="Qdrant connection successful",
            details={
                "url": settings.qdrant_url,
                "collection_count": len(collections),
                "collections": collection_names,
                "ready": True,
            }
        )
    
    except ImportError as e:
        return ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Qdrant client not configured: {str(e)}",
            details={"error_type": "import_error"}
        )
    
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"Qdrant connection failed: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


async def check_opensearch_health() -> ComponentHealth:
    """
    Check OpenSearch keyword search health
    
    Returns:
        ComponentHealth with OpenSearch status
    """
    try:
        from opensearchpy import AsyncOpenSearch
        from app.shared.config.settings import settings
        
        start_time = time.time()
        
        # Connect to OpenSearch
        client = AsyncOpenSearch(
            hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
            http_auth=(settings.opensearch_user, settings.opensearch_password),
            use_ssl=True,
            verify_certs=False,
            timeout=5,
        )
        
        # Check cluster health
        health_info = await client.cluster.health()
        
        latency_ms = (time.time() - start_time) * 1000
        
        cluster_status = health_info.get("status", "unknown")
        
        # Map cluster status to health status
        status_mapping = {
            "green": HealthStatus.HEALTHY,
            "yellow": HealthStatus.DEGRADED,
            "red": HealthStatus.UNHEALTHY,
        }
        status = status_mapping.get(cluster_status, HealthStatus.UNKNOWN)
        
        await client.close()
        
        return ComponentHealth(
            status=status,
            latency_ms=latency_ms,
            message=f"OpenSearch cluster status: {cluster_status}",
            details={
                "cluster_name": health_info.get("cluster_name"),
                "number_of_nodes": health_info.get("number_of_nodes"),
                "active_shards": health_info.get("active_shards"),
            }
        )
    
    except ImportError as e:
        return ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"OpenSearch client not configured: {str(e)}",
            details={"error_type": "import_error"}
        )
    
    except Exception as e:
        logger.error(f"OpenSearch health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"OpenSearch connection failed: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


def aggregate_health_status(components: Dict[str, ComponentHealth]) -> HealthStatus:
    """
    Aggregate health status from all components
    
    Args:
        components: Dictionary of component health statuses
        
    Returns:
        Overall aggregated health status
    """
    statuses = [comp.status for comp in components.values()]
    
    # If any component is unhealthy, overall is unhealthy
    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.UNHEALTHY
    
    # If any component is degraded, overall is degraded
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    
    # If any component is unknown, overall is degraded
    if HealthStatus.UNKNOWN in statuses:
        return HealthStatus.DEGRADED
    
    # All healthy
    return HealthStatus.HEALTHY


# API Endpoints
@router.get("/", response_model=AggregatedHealth)
async def get_overall_health() -> AggregatedHealth:
    """
    Get overall service health status
    
    Checks all components in parallel and aggregates results.
    
    Returns:
        AggregatedHealth with status of all components
    """
    # Run all health checks in parallel
    neo4j_task = check_neo4j_health()
    llm_task = check_llm_health()
    qdrant_task = check_qdrant_health()
    opensearch_task = check_opensearch_health()
    
    components_health = await asyncio.gather(
        neo4j_task,
        llm_task,
        qdrant_task,
        opensearch_task,
        return_exceptions=True
    )
    
    # Build components dictionary
    components = {
        "neo4j": components_health[0] if not isinstance(components_health[0], Exception) else ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Health check error: {str(components_health[0])}"
        ),
        "llm": components_health[1] if not isinstance(components_health[1], Exception) else ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Health check error: {str(components_health[1])}"
        ),
        "qdrant": components_health[2] if not isinstance(components_health[2], Exception) else ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Health check error: {str(components_health[2])}"
        ),
        "opensearch": components_health[3] if not isinstance(components_health[3], Exception) else ComponentHealth(
            status=HealthStatus.UNKNOWN,
            message=f"Health check error: {str(components_health[3])}"
        ),
    }
    
    # Aggregate status
    overall_status = aggregate_health_status(components)
    
    # Calculate uptime
    uptime_seconds = time.time() - SERVICE_START_TIME
    
    return AggregatedHealth(
        status=overall_status,
        components=components,
        uptime_seconds=uptime_seconds,
    )


@router.get("/graph", response_model=ComponentHealth)
async def get_graph_health() -> ComponentHealth:
    """
    Get Neo4j graph database health status
    
    Returns:
        ComponentHealth with detailed Neo4j diagnostics
    """
    return await check_neo4j_health()


@router.get("/llm", response_model=ComponentHealth)
async def get_llm_health() -> ComponentHealth:
    """
    Get LLM API health status
    
    Returns:
        ComponentHealth with OpenAI API status
    """
    return await check_llm_health()


@router.get("/vector", response_model=ComponentHealth)
async def get_vector_health() -> ComponentHealth:
    """
    Get Qdrant vector database health status
    
    Returns:
        ComponentHealth with Qdrant diagnostics
    """
    return await check_qdrant_health()


@router.get("/search", response_model=ComponentHealth)
async def get_search_health() -> ComponentHealth:
    """
    Get OpenSearch keyword search health status
    
    Returns:
        ComponentHealth with OpenSearch cluster status
    """
    return await check_opensearch_health()


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint
    
    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is not ready.
    
    Returns:
        Simple ready/not ready status
    """
    overall_health = await get_overall_health()
    
    if overall_health.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
        return {
            "ready": True,
            "status": overall_health.status,
        }
    else:
        raise HTTPException(
            status_code=503,
            detail={
                "ready": False,
                "status": overall_health.status,
                "message": "Service not ready"
            }
        )


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint
    
    Returns 200 if service is alive (even if degraded).
    Only returns error if service is completely down.
    
    Returns:
        Simple alive status
    """
    # For liveness, we just check if the service can respond
    # Don't check dependencies - service is alive even if dependencies are down
    return {
        "alive": True,
        "uptime_seconds": time.time() - SERVICE_START_TIME,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/metrics")
async def get_health_metrics() -> Dict[str, Any]:
    """
    Get detailed health metrics for monitoring
    
    Returns:
        Detailed metrics for all components
    """
    overall_health = await get_overall_health()
    
    # Calculate component availability
    component_availability = {}
    for name, comp in overall_health.components.items():
        component_availability[name] = {
            "status": comp.status,
            "available": comp.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
            "latency_ms": comp.latency_ms,
        }
    
    return {
        "overall_status": overall_health.status,
        "uptime_seconds": overall_health.uptime_seconds,
        "components": component_availability,
        "timestamp": datetime.now().isoformat(),
    }
