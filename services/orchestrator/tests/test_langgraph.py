"""
Tests for LangGraph IRCoT Orchestration.

This module tests the LangGraph-based orchestration workflow.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Test state creation
def test_create_initial_state():
    """Test creating initial IRCoT state."""
    from app.core.langgraph_state import create_initial_state, WorkflowPhase
    
    state = create_initial_state(
        query="Điều kiện tốt nghiệp UIT là gì?",
        session_id="test-session",
        use_rag=True,
        rag_top_k=5,
        use_knowledge_graph=False,
        max_iterations=2
    )
    
    assert state["original_query"] == "Điều kiện tốt nghiệp UIT là gì?"
    assert state["session_id"] == "test-session"
    assert state["use_rag"] == True
    assert state["rag_top_k"] == 5
    assert state["use_knowledge_graph"] == False
    assert state["max_iterations"] == 2
    assert state["current_iteration"] == 0
    assert state["current_phase"] == WorkflowPhase.PLANNING.value
    assert state["accumulated_documents"] == []
    assert state["reasoning_steps"] == []


def test_merge_documents():
    """Test document merging with deduplication."""
    from app.core.langgraph_state import merge_documents
    
    existing = [
        {"doc_id": "1", "content": "Document 1 content..."},
        {"doc_id": "2", "content": "Document 2 content..."}
    ]
    
    new_docs = [
        {"doc_id": "2", "content": "Document 2 content..."},  # Duplicate
        {"doc_id": "3", "content": "Document 3 content..."}   # New
    ]
    
    result = merge_documents(existing, new_docs)
    
    assert len(result) == 3
    assert any(d["doc_id"] == "1" for d in result)
    assert any(d["doc_id"] == "2" for d in result)
    assert any(d["doc_id"] == "3" for d in result)


def test_workflow_phase_enum():
    """Test WorkflowPhase enum values."""
    from app.core.langgraph_state import WorkflowPhase
    
    assert WorkflowPhase.PLANNING.value == "planning"
    assert WorkflowPhase.RETRIEVING.value == "retrieving"
    assert WorkflowPhase.REASONING.value == "reasoning"
    assert WorkflowPhase.ANSWERING.value == "answering"
    assert WorkflowPhase.COMPLETED.value == "completed"
    assert WorkflowPhase.ERROR.value == "error"


class TestLangGraphNodes:
    """Tests for LangGraph node functions."""
    
    @pytest.fixture
    def mock_agent_port(self):
        """Create mock agent port."""
        mock = AsyncMock()
        mock.generate_response = AsyncMock(return_value=MagicMock(
            content='{"reasoning_step": "Test reasoning", "confidence": 0.8, "can_answer_now": true}',
            tokens_used=100
        ))
        return mock
    
    @pytest.fixture
    def mock_rag_port(self):
        """Create mock RAG port."""
        mock = AsyncMock()
        mock.retrieve_context = AsyncMock(return_value={
            "retrieved_documents": [
                {"content": "Test document", "score": 0.9, "title": "Test"}
            ]
        })
        return mock
    
    @pytest.fixture
    def mock_smart_planner(self):
        """Create mock smart planner."""
        mock = AsyncMock()
        mock.process = AsyncMock(return_value=MagicMock(
            intent="information_query",
            complexity="medium",
            complexity_score=5.5,
            requires_rag=True,
            use_knowledge_graph=False,
            rewritten_queries=["test query"],
            search_terms=["test"],
            strategy="standard_rag",
            top_k=5,
            extracted_filters=MagicMock(
                is_empty=MagicMock(return_value=True),
                to_dict=MagicMock(return_value={})
            )
        ))
        return mock
    
    @pytest.fixture
    def nodes(self, mock_agent_port, mock_rag_port, mock_smart_planner):
        """Create LangGraphNodes instance with mocks."""
        from app.core.langgraph_nodes import LangGraphNodes
        
        return LangGraphNodes(
            agent_port=mock_agent_port,
            rag_port=mock_rag_port,
            smart_planner=mock_smart_planner
        )
    
    @pytest.mark.asyncio
    async def test_plan_node(self, nodes):
        """Test plan node execution."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(
            query="Test query",
            session_id="test"
        )
        
        result = await nodes.plan_node(state)
        
        assert "plan_result" in result
        assert "complexity" in result
        assert result["complexity"] == "medium"
    
    @pytest.mark.asyncio
    async def test_retrieve_node(self, nodes):
        """Test retrieve node execution."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(
            query="Test query",
            session_id="test"
        )
        state["plan_result"] = {
            "rewritten_queries": ["test query"],
            "top_k": 5,
            "extracted_filters": None
        }
        
        result = await nodes.retrieve_node(state)
        
        assert "accumulated_documents" in result
        assert result["current_iteration"] == 1
    
    @pytest.mark.asyncio
    async def test_reason_node(self, nodes):
        """Test reason node execution."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(
            query="Test query",
            session_id="test"
        )
        state["current_iteration"] = 1
        state["accumulated_documents"] = [
            {"content": "Test content", "title": "Test", "score": 0.9}
        ]
        
        result = await nodes.reason_node(state)
        
        assert "reasoning_steps" in result
        assert "current_confidence" in result
    
    def test_should_continue_ircot_max_iterations(self, nodes):
        """Test should_continue when max iterations reached."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(query="Test", session_id="test")
        state["current_iteration"] = 3
        state["max_iterations"] = 3
        
        result = nodes.should_continue_ircot(state)
        
        assert result == "answer"
    
    def test_should_continue_ircot_high_confidence(self, nodes):
        """Test should_continue when confidence is high."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(query="Test", session_id="test")
        state["current_iteration"] = 1
        state["max_iterations"] = 3
        state["current_confidence"] = 0.85
        
        result = nodes.should_continue_ircot(state)
        
        assert result == "answer"
    
    def test_should_continue_ircot_continue(self, nodes):
        """Test should_continue when should continue."""
        from app.core.langgraph_state import create_initial_state
        
        state = create_initial_state(query="Test", session_id="test")
        state["current_iteration"] = 1
        state["max_iterations"] = 3
        state["current_confidence"] = 0.5
        state["can_answer_now"] = False
        
        result = nodes.should_continue_ircot(state)
        
        assert result == "continue"


class TestLangGraphOrchestrator:
    """Tests for LangGraph orchestrator integration."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_creation(self):
        """Test creating LangGraph orchestrator."""
        # Skip if langgraph not installed
        pytest.importorskip("langgraph")
        
        from app.core.langgraph_workflow import LangGraphOrchestrator
        
        mock_agent_port = AsyncMock()
        mock_rag_port = AsyncMock()
        
        orchestrator = LangGraphOrchestrator(
            agent_port=mock_agent_port,
            rag_port=mock_rag_port
        )
        
        assert orchestrator.compiled_graph is not None
    
    @pytest.mark.asyncio
    async def test_graph_visualization(self):
        """Test graph visualization output."""
        pytest.importorskip("langgraph")
        
        from app.core.langgraph_workflow import LangGraphOrchestrator
        
        mock_agent_port = AsyncMock()
        mock_rag_port = AsyncMock()
        
        orchestrator = LangGraphOrchestrator(
            agent_port=mock_agent_port,
            rag_port=mock_rag_port
        )
        
        viz = orchestrator.get_graph_visualization()
        
        assert "PLAN" in viz
        assert "RETRIEVE" in viz
        assert "REASON" in viz
        assert "ANSWER" in viz


# Integration test (requires actual services)
class TestLangGraphIntegration:
    """Integration tests for LangGraph orchestrator."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow(self):
        """Test full workflow execution (requires services running)."""
        pytest.importorskip("langgraph")
        
        import os
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY not set")
        
        from app.core.container import get_langgraph_orchestrator
        from app.core.domain import OrchestrationRequest
        
        # Enable LangGraph temporarily
        os.environ["USE_LANGGRAPH"] = "true"
        
        try:
            orchestrator = get_langgraph_orchestrator()
            
            if orchestrator is None:
                pytest.skip("LangGraph orchestrator not available")
            
            request = OrchestrationRequest(
                user_query="Điều kiện tốt nghiệp UIT là gì?",
                session_id="test-integration",
                use_rag=True,
                rag_top_k=3
            )
            
            response = await orchestrator.process_request(request)
            
            assert response is not None
            assert response.response != ""
            assert response.processing_stats.get("pipeline") == "langgraph_ircot"
            
        finally:
            os.environ.pop("USE_LANGGRAPH", None)


if __name__ == "__main__":
    # Run basic tests
    test_create_initial_state()
    test_merge_documents()
    test_workflow_phase_enum()
    print("✓ All basic tests passed!")
    
    # Run async tests
    asyncio.run(TestLangGraphNodes().test_plan_node(
        AsyncMock(),
        AsyncMock(),
        AsyncMock()
    ))
    print("✓ Async tests require pytest-asyncio")
