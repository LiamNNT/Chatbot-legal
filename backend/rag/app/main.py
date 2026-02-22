# main.py
#
# Description:
# This script serves as the main entry point for the RAG (Retrieval-Augmented Generation) service.
# It initializes the FastAPI application, configures necessary middleware such as CORS,
# and includes all the API routers from their respective modules.
#
# Key Responsibilities:
# - Instantiate the FastAPI application.
# - Configure Cross-Origin Resource Sharing (CORS) to allow requests from any origin.
# - Include API routers for health checks, embedding, search, and admin functionalities.
# - Define a root endpoint for basic service information.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import application-specific settings and routers
from app.shared.config.settings import settings
from app.health.routes import router as health_router
from app.embedding.routes import router as embed_router
from app.search.routes import router as search_router
from app.admin.routes import router as admin_router
from app.ingest.opensearch_routes import router as opensearch_router
from app.extraction.routes import router as extraction_router  # KG Extraction Pipeline
from app.ingest.routes import router as ingest_router  # Document Ingestion Pipeline
from app.search.retrieval_routes import router as retrieval_router  # Legal Retrieval Pipeline
from app.knowledge_graph.routes import router as kg_router  # Knowledge Graph Query API
from app.health.health_v2 import router as health_v2_router  # Week 2 comprehensive health checks

app = FastAPI(title="RAG Service", version="0.1.0")

# --- Middleware Configuration ---
# Configure CORS middleware to define which origins, methods, and headers are allowed.
# This is crucial for enabling cross-domain requests from web frontends.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Router Inclusion ---
# Include the routers for different API functionalities.
# Each router is prefixed with "/v1" to version the API.
app.include_router(health_router, prefix="/v1")
app.include_router(embed_router, prefix="/v1")
app.include_router(search_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")
app.include_router(opensearch_router, prefix="/v1")
app.include_router(extraction_router, prefix="/v1")  # KG Extraction Pipeline
app.include_router(ingest_router, prefix="/v1")  # Document Ingestion Pipeline
app.include_router(retrieval_router, prefix="/v1")  # Legal Retrieval Pipeline
app.include_router(kg_router, prefix="/v1")  # Knowledge Graph Query API

# Week 2: Comprehensive health checks for all dependencies
app.include_router(health_v2_router, prefix="/v2")


# --- Root Endpoint ---
@app.get("/")
def root():
    """
    Root endpoint to provide basic information about the running service.
    
    Returns:
        dict: A dictionary containing the service name and its current environment.
    """
    return {"service": "rag", "env": settings.app_env}