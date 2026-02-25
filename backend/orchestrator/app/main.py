from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

# Load .env file before anything else
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path, override=True)  # Override existing env vars

from .chat.routes import router as chat_router
from .conversation.routes import router as conversation_router
from .admin.routes import router as admin_router
from .shared.container.container import cleanup_container, get_container

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log the logging level
logger.info(f"Logging level set to: {log_level}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting orchestrator service...")
    
    # Verify required environment variables
    required_env_vars = ["OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        raise RuntimeError(f"Missing required environment variables: {missing_vars}")
    
    # Initialize multi-agent orchestrator early to verify Graph Reasoning
    try:
        container = get_container()
        orchestrator = container.get_multi_agent_orchestrator()
        if orchestrator.verification_pipeline:
            logger.info("✓ Legal Verification Pipeline is available")
        else:
            logger.warning("⚠ Legal Verification Pipeline is NOT available")
    except Exception as e:
        logger.warning(f"⚠ Could not initialize multi-agent orchestrator: {e}")
    
    logger.info("Orchestrator service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down orchestrator service...")
    await cleanup_container()
    logger.info("Orchestrator service shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Chatbot-UIT Orchestrator Service",
        description="Orchestration service that coordinates RAG retrieval and agent generation",
        version="1.0.0",
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(conversation_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    
    @app.get("/", tags=["Root"])
    async def root():
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
