# frontend/config.py
"""
Centralized configuration for frontend.
All API URLs and defaults are defined here.
"""

import os

# ── API Endpoints ──
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001/api/v1")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8002")

# ── Defaults ──
DEFAULT_SESSION_ID = "streamlit_default"
DEFAULT_RAG_TOP_K = 5
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000
REQUEST_TIMEOUT = 120  # seconds
