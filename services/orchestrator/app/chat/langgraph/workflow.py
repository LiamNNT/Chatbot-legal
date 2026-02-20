"""
LangGraph Workflow for IRCoT Orchestration.

This module defines the complete LangGraph workflow that implements
the IRCoT (Interleaving Retrieval with Chain-of-Thought) algorithm.

The workflow is a StateGraph that:
1. Plans the query processing strategy
2. Iteratively retrieves and reasons
3. Generates the final answer

Graph Structure:
    START → plan → retrieve → reason → [condition] → retrieve (loop) OR answer → END
                                           ↑__________________________|

Benefits:
- Visual debugging with LangGraph studio
- Automatic checkpointing for long-running tasks
- Human-in-the-loop interrupts
- Easy extension to more agents
"""

import logging
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import IRCoTState, create_initial_state, WorkflowPhase
from .nodes import LangGraphNodes
from ...shared.domain import OrchestrationRequest, OrchestrationResponse, RAGContext

logger = logging.getLogger(__name__)


class LangGraphOrchestrator:
    """
    LangGraph-based Orchestrator implementing IRCoT workflow.
    
    This orchestrator replaces the manual IRCoT loop implementation with
    a LangGraph StateGraph that automatically manages state and transitions.
    
    Pipeline:
        plan → retrieve ⟷ reason → answer
              (loop based on confidence)
    
    Features:
    - Automatic state management
    - Checkpointing for recovery
    - Visual debugging support
    - Easy extension to more agents
    """
    
    def __init__(
        self,
        agent_port,  # AgentPort
        rag_port,    # RAGServicePort
        smart_planner=None,
        answer_agent=None,
        graph_reasoning_agent=None,
        conversation_manager=None,
        context_service=None,
        ircot_config=None,
        enable_checkpointing: bool = False
    ):
        """
        Initialize the LangGraph orchestrator.
        
        Args:
            agent_port: Port for LLM communication
            rag_port: Port for RAG retrieval
            smart_planner: SmartPlanner agent
            answer_agent: Answer generation agent
            graph_reasoning_agent: Knowledge Graph reasoning agent
            conversation_manager: Conversation history manager
            context_service: Query contextualization service
            ircot_config: IRCoT configuration
            enable_checkpointing: Whether to enable state checkpointing
        """
        self.agent_port = agent_port
        self.rag_port = rag_port
        self.ircot_config = ircot_config
        
        # Initialize nodes with dependencies
        self.nodes = LangGraphNodes(
            agent_port=agent_port,
            rag_port=rag_port,
            smart_planner=smart_planner,
            answer_agent=answer_agent,
            graph_reasoning_agent=graph_reasoning_agent,
            conversation_manager=conversation_manager,
            context_service=context_service,
            ircot_config=ircot_config
        )
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Compile with optional checkpointing
        if enable_checkpointing:
            self.checkpointer = MemorySaver()
            self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)
            logger.info("✓ LangGraph compiled with checkpointing enabled")
        else:
            self.checkpointer = None
            self.compiled_graph = self.graph.compile()
            logger.info("✓ LangGraph compiled (no checkpointing)")
        
        logger.info("🚀 LangGraph IRCoT Orchestrator initialized")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph StateGraph.
        
        Graph structure:
            START
              ↓
            plan
              ↓
            retrieve
              ↓
            reason
              ↓
         [should_continue?]
           /         \\
        continue    answer
           ↓           ↓
        retrieve      END
        
        Returns:
            Configured StateGraph ready for compilation
        """
        # Create the graph with our state type
        graph = StateGraph(IRCoTState)
        
        # Add nodes
        graph.add_node("plan", self.nodes.plan_node)
        graph.add_node("retrieve", self.nodes.retrieve_node)
        graph.add_node("reason", self.nodes.reason_node)
        graph.add_node("answer", self.nodes.answer_node)
        
        # Set entry point
        graph.set_entry_point("plan")
        
        # Add edges
        graph.add_edge("plan", "retrieve")
        graph.add_edge("retrieve", "reason")
        
        # Add conditional edge from reason
        graph.add_conditional_edges(
            "reason",
            self.nodes.should_continue_ircot,
            {
                "continue": "retrieve",  # Loop back for more retrieval
                "answer": "answer"       # Proceed to answer generation
            }
        )
        
        # Answer leads to END
        graph.add_edge("answer", END)
        
        logger.info("📊 LangGraph structure: plan → retrieve ⟷ reason → answer")
        
        return graph
    
    async def process_request(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """
        Process a request through the LangGraph IRCoT workflow.
        
        Args:
            request: The orchestration request
            
        Returns:
            OrchestrationResponse with the generated answer and metadata
        """
        logger.info(f"🔄 Processing request with LangGraph: {request.user_query[:50]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            query=request.user_query,
            session_id=request.session_id or "default",
            use_rag=request.use_rag,
            rag_top_k=request.rag_top_k,
            use_knowledge_graph=getattr(request, 'use_knowledge_graph', False),
            max_iterations=self.ircot_config.max_iterations if self.ircot_config else 2
        )
        
        # Run the graph
        try:
            # Configure for async execution
            config = {}
            if self.checkpointer:
                config["configurable"] = {"thread_id": request.session_id or "default"}
            
            # Invoke the compiled graph
            final_state = await self.compiled_graph.ainvoke(initial_state, config)
            
            # Build response from final state
            return self._build_response(final_state, request)
            
        except Exception as e:
            logger.error(f"LangGraph execution error: {e}", exc_info=True)
            return OrchestrationResponse(
                response=f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                session_id=request.session_id or "unknown",
                rag_context=None,
                agent_metadata={"error": str(e), "pipeline": "langgraph_failed"},
                processing_stats={},
                timestamp=datetime.now()
            )
    
    async def process_request_stream(
        self,
        request: OrchestrationRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a request with streaming updates.
        
        Yields intermediate state updates as the graph executes,
        useful for showing progress in real-time.
        
        Args:
            request: The orchestration request
            
        Yields:
            Dict containing phase and progress information
        """
        logger.info(f"🔄 Streaming request with LangGraph: {request.user_query[:50]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            query=request.user_query,
            session_id=request.session_id or "default",
            use_rag=request.use_rag,
            rag_top_k=request.rag_top_k,
            use_knowledge_graph=getattr(request, 'use_knowledge_graph', False),
            max_iterations=self.ircot_config.max_iterations if self.ircot_config else 2
        )
        
        try:
            config = {}
            if self.checkpointer:
                config["configurable"] = {"thread_id": request.session_id or "default"}
            
            # Stream the graph execution
            async for event in self.compiled_graph.astream(initial_state, config):
                # Extract node name and state from event
                for node_name, state in event.items():
                    yield {
                        "type": "progress",
                        "node": node_name,
                        "phase": state.get("current_phase", "unknown"),
                        "iteration": state.get("current_iteration", 0),
                        "confidence": state.get("current_confidence", 0.0),
                        "documents_count": len(state.get("accumulated_documents", [])),
                    }
                    
                    # If this is the final answer, yield it
                    if node_name == "answer" and state.get("final_answer"):
                        yield {
                            "type": "answer",
                            "content": state.get("final_answer"),
                            "reasoning": state.get("final_reasoning"),
                            "sources": state.get("detailed_sources", []),
                            "stats": state.get("processing_stats", {})
                        }
            
        except Exception as e:
            logger.error(f"LangGraph streaming error: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    def _build_response(
        self,
        final_state: IRCoTState,
        request: OrchestrationRequest
    ) -> OrchestrationResponse:
        """
        Build OrchestrationResponse from final LangGraph state.
        
        Args:
            final_state: The final state after graph execution
            request: Original request
            
        Returns:
            OrchestrationResponse with all results
        """
        # Build RAG context from accumulated documents
        accumulated_docs = final_state.get("accumulated_documents", [])
        
        rag_context = RAGContext(
            query=final_state.get("original_query", request.user_query),
            retrieved_documents=accumulated_docs,
            search_metadata={
                "langgraph_iterations": final_state.get("current_iteration", 0),
                "ircot_queries": final_state.get("search_queries_used", []),
                "reasoning_chain": final_state.get("final_reasoning", ""),
                "graph_context": final_state.get("graph_context"),
                "graph_nodes_found": final_state.get("graph_nodes_found", 0)
            },
            relevance_scores=[doc.get("score", 0.0) for doc in accumulated_docs]
        )
        
        # Get processing stats
        processing_stats = final_state.get("processing_stats", {})
        processing_stats["pipeline"] = "langgraph_ircot"
        processing_stats["early_stopped"] = final_state.get("early_stopped", False)
        processing_stats["final_confidence"] = final_state.get("current_confidence", 0.0)
        
        # Build agent metadata
        agent_metadata = {
            "pipeline": "langgraph_ircot",
            "plan_result": final_state.get("plan_result"),
            "answer_confidence": final_state.get("current_confidence", 0.0),
            "detailed_sources": final_state.get("detailed_sources", []),
            "reasoning_steps": final_state.get("reasoning_steps", []),
            "complexity": final_state.get("complexity"),
            "complexity_score": final_state.get("complexity_score")
        }
        
        # Handle errors
        if final_state.get("error"):
            agent_metadata["error"] = final_state.get("error")
            processing_stats["error"] = final_state.get("error")
        
        return OrchestrationResponse(
            response=final_state.get("final_answer", "Xin lỗi, không thể tạo câu trả lời."),
            session_id=request.session_id or final_state.get("session_id", "unknown"),
            rag_context=rag_context,
            agent_metadata=agent_metadata,
            processing_stats=processing_stats,
            timestamp=datetime.now()
        )
    
    def get_graph_visualization(self) -> str:
        """
        Get a text representation of the graph structure.
        
        Returns:
            String describing the graph structure
        """
        return """
LangGraph IRCoT Workflow:
========================

    ┌─────────┐
    │  START  │
    └────┬────┘
         │
    ┌────▼────┐
    │  PLAN   │ ← Analyze query, extract filters
    └────┬────┘
         │
    ┌────▼────┐
    │RETRIEVE │ ← RAG + Knowledge Graph
    └────┬────┘
         │
    ┌────▼────┐
    │ REASON  │ ← Chain-of-Thought step
    └────┬────┘
         │
    ┌────▼────┐
    │CONTINUE?│ ← Check confidence
    └────┬────┘
        /│\\
       / │ \\
      ▼  │  ▼
[continue]│[answer]
      │   │   │
      │   │   ▼
      │   │ ┌────────┐
      └───┴→│ ANSWER │ ← Generate final answer
            └────┬───┘
                 │
            ┌────▼────┐
            │   END   │
            └─────────┘

Legend:
- PLAN: SmartPlanner analyzes query
- RETRIEVE: RAG + optional KG retrieval  
- REASON: CoT reasoning with confidence check
- ANSWER: Final answer generation with citations
"""


def create_langgraph_orchestrator(
    agent_port,
    rag_port,
    agent_factory=None,
    graph_adapter=None,
    conversation_manager=None,
    context_service=None,
    ircot_config=None,
    enable_checkpointing: bool = False
) -> LangGraphOrchestrator:
    """
    Factory function to create a LangGraph orchestrator with all dependencies.
    
    Args:
        agent_port: Port for LLM communication
        rag_port: Port for RAG retrieval
        agent_factory: Factory for creating agents
        graph_adapter: Neo4j adapter for graph reasoning
        conversation_manager: Conversation history manager
        context_service: Query contextualization service
        ircot_config: IRCoT configuration
        enable_checkpointing: Enable state checkpointing
        
    Returns:
        Configured LangGraphOrchestrator instance
    """
    # Create agents using factory if provided
    smart_planner = None
    answer_agent = None
    graph_reasoning_agent = None
    
    if agent_factory:
        try:
            smart_planner = agent_factory.create_agent("smart_planner", agent_port)
            logger.info("✓ SmartPlanner created for LangGraph")
        except Exception as e:
            logger.warning(f"SmartPlanner not available: {e}")
        
        try:
            answer_agent = agent_factory.create_agent("answer_agent", agent_port)
            logger.info("✓ AnswerAgent created for LangGraph")
        except Exception as e:
            logger.warning(f"AnswerAgent not available: {e}")
    
    if graph_adapter:
        from ...reasoning.graph_reasoning_agent import GraphReasoningAgent
        graph_reasoning_agent = GraphReasoningAgent(
            graph_adapter=graph_adapter,
            llm_port=agent_port
        )
        logger.info("✓ GraphReasoningAgent created for LangGraph")
    
    return LangGraphOrchestrator(
        agent_port=agent_port,
        rag_port=rag_port,
        smart_planner=smart_planner,
        answer_agent=answer_agent,
        graph_reasoning_agent=graph_reasoning_agent,
        conversation_manager=conversation_manager,
        context_service=context_service,
        ircot_config=ircot_config,
        enable_checkpointing=enable_checkpointing
    )
