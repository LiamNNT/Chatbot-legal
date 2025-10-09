"""
Main FastAPI application for orchestrator service.

This module sets up the FastAPI application with all routes and middleware.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from .api.routes import router as api_router
from .core.container import cleanup_container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting orchestrator service...")
    
    # Verify required environment variables
    required_env_vars = ["OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")
    
    logger.info("Orchestrator service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down orchestrator service...")
    await cleanup_container()
    logger.info("Orchestrator service shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Chatbot-UIT Orchestrator Service",
        description="Orchestration service that coordinates RAG retrieval and agent generation",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "Chatbot-UIT Orchestrator",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/api/v1/health",
                "chat": "/api/v1/chat",
                "chat_stream": "/api/v1/chat/stream",
                "conversations": "/api/v1/conversations",
                "docs": "/docs"
            }
        }
    
    return app


# Create the application instance
app = create_app()