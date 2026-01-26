"""
Pytest configuration and shared fixtures for Orchestrator tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_chat_request():
    """Sample chat request for testing."""
    return {
        "query": "Hướng dẫn đăng ký học phần tại UIT?",
        "session_id": "test_session_001",
        "use_rag": True
    }


@pytest.fixture
def mock_rag_response():
    """Mock RAG service response."""
    return {
        "documents": [
            {
                "content": "Sinh viên đăng ký học phần qua hệ thống DAA-UIT...",
                "score": 0.85,
                "source": "academic_guide"
            }
        ],
        "query": "Hướng dẫn đăng ký học phần",
        "search_type": "hybrid"
    }


@pytest.fixture
def mock_rag_adapter():
    """Mock RAG adapter for testing."""
    adapter = MagicMock()
    adapter.search = AsyncMock(return_value={
        "documents": [],
        "total": 0
    })
    return adapter
