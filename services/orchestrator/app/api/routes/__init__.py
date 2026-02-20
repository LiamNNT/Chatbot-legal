"""
Orchestrator API routes package.

Combines all domain-specific routers into one ``router`` that can be
mounted by the FastAPI application (backward-compatible with the old
monolithic ``routes.py``).
"""

from fastapi import APIRouter

from .chat_routes import router as chat_router
from .conversation_routes import router as conversation_router
from .admin_routes import router as admin_router

router = APIRouter()
router.include_router(chat_router)
router.include_router(conversation_router)
router.include_router(admin_router)
