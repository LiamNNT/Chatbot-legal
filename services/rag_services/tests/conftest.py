"""
Pytest configuration and shared fixtures for RAG Services tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_query():
    """Sample Vietnamese query for testing."""
    return "Hướng dẫn đăng ký học phần tại UIT?"


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "id": "test_doc_001",
        "title": "Hướng dẫn đăng ký học phần",
        "content": "Sinh viên đăng ký học phần qua hệ thống DAA-UIT...",
        "source": "test",
        "metadata": {"category": "academic"}
    }


@pytest.fixture
def mock_embedding():
    """Mock embedding vector for testing."""
    import numpy as np
    return np.random.rand(384).tolist()
