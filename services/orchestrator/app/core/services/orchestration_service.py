import uuid
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from ..domain.domain import (
    OrchestrationRequest,
    OrchestrationResponse,
    AgentRequest,
    RAGContext,
    ConversationMessage,
    ConversationRole,
    MessageType
)
from ...ports.agent_ports import AgentPort, RAGServicePort, ConversationManagerPort
from .context_domain_service import ContextDomainService
from ..domain.exceptions import AgentProcessingFailedException, RAGRetrievalFailedException
from ..config.ircot_config import IRCoTConfig, IRCoTMode

# Type checking only import to avoid circular imports
if TYPE_CHECKING:
    from ..langgraph.langgraph_workflow import LangGraphOrchestrator

logger = logging.getLogger(__name__)


class OrchestrationService:
    def __init__(
        self,
        agent_port: AgentPort,
        rag_port: RAGServicePort,
        conversation_manager: ConversationManagerPort,
        default_system_prompt: Optional[str] = None,
        ircot_config: Optional[IRCoTConfig] = None,
        langgraph_orchestrator: Optional["LangGraphOrchestrator"] = None
    ):
        self.agent_port = agent_port
        self.rag_port = rag_port
        self.conversation_manager = conversation_manager
        self.default_system_prompt = default_system_prompt or self._get_default_system_prompt()
        
        # IRCoT configuration
        self.ircot_config = ircot_config or IRCoTConfig()
        
        # LangGraph orchestrator for IRCoT (replaces manual IRCoTReasoningService)
        self._langgraph_orchestrator = langgraph_orchestrator
        
        # Log initialization status
        if self._langgraph_orchestrator:
            logger.info("✓ OrchestrationService initialized with LangGraph IRCoT support")
        else:
            logger.info("⚠ OrchestrationService initialized without LangGraph (IRCoT disabled)")
    
    @property
    def langgraph_orchestrator(self) -> Optional["LangGraphOrchestrator"]:
        """Get the LangGraph orchestrator (lazy initialization supported)."""
        return self._langgraph_orchestrator
    
    @langgraph_orchestrator.setter
    def langgraph_orchestrator(self, value: Optional["LangGraphOrchestrator"]) -> None:
        """Set the LangGraph orchestrator."""
        self._langgraph_orchestrator = value
        if value:
            logger.info("✓ LangGraph orchestrator attached to OrchestrationService")
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for the agent."""
        return """Bạn là một trợ lý AI thông minh và hữu ích cho Chatbot-UIT. Nhiệm vụ của bạn là:

1. Trả lời câu hỏi dựa trên thông tin được cung cấp từ hệ thống tìm kiếm
2. Nếu thông tin không đủ để trả lời, hãy thành thật nói rằng bạn không có đủ thông tin
3. Luôn trả lời bằng tiếng Việt một cách tự nhiên và dễ hiểu
4. Cung cấp thông tin chính xác và hữu ích cho người dùng
5. Nếu cần, hãy yêu cầu người dùng cung cấp thêm thông tin để trả lời tốt hơn

Hãy trả lời một cách thân thiện và chuyên nghiệp."""
    
    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Process a complete orchestration request.
        
        Args:
            request: The orchestration request
            
        Returns:
            OrchestrationResponse containing the generated response and metadata
        """
        start_time = time.time()
        
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get or create conversation context
        context = await self._get_or_create_context(session_id, request.conversation_context)
        
        # Add user message to context
        user_message = ConversationMessage(
            role=ConversationRole.USER,
            content=request.user_query,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        context.add_message(user_message)
        
        rag_context = None
        processing_stats = {}
        
        # Retrieve context using RAG if enabled
        if request.use_rag:
            try:
                rag_start = time.time()
                rag_data = await self.rag_port.retrieve_context(
                    query=request.user_query,
                    top_k=request.rag_top_k
                )
                rag_end = time.time()
                
                rag_context = RAGContext(
                    query=request.user_query,
                    retrieved_documents=rag_data.get("retrieved_documents", []),
                    search_metadata=rag_data.get("search_metadata"),
                    relevance_scores=rag_data.get("relevance_scores", [])
                )
                
                processing_stats["rag_time"] = rag_end - rag_start
                processing_stats["documents_retrieved"] = len(rag_context.retrieved_documents)
                
            except Exception as e:
                # For non-critical RAG failures, continue without RAG context
                # Critical failures should be handled by caller
                processing_stats["rag_error"] = str(e)
                rag_context = None
        
        # Prepare agent request
        agent_request = self._prepare_agent_request(
            user_query=request.user_query,
            rag_context=rag_context,
            context=context,
            model=request.agent_model,
            metadata=request.metadata
        )
        
        # Generate response using agent
        try:
            agent_start = time.time()
            agent_response = await self.agent_port.generate_response(agent_request)
            agent_end = time.time()
            
            processing_stats["agent_time"] = agent_end - agent_start
            processing_stats["tokens_used"] = agent_response.tokens_used
            
            agent_response_content = agent_response.content
            agent_metadata = agent_response.metadata
            
        except Exception as e:
            # Raise domain exception - let presentation layer handle user messages
            raise AgentProcessingFailedException(
                agent_error=str(e),
                details={
                    "session_id": session_id,
                    "user_query": request.user_query,
                    "processing_stats": processing_stats
                },
                cause=e
            )
        
        # Add assistant message to context
        assistant_message = ConversationMessage(
            role=ConversationRole.ASSISTANT,
            content=agent_response_content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        context.add_message(assistant_message)
        
        # Update conversation context
        await self.conversation_manager.update_context(context)
        
        # Calculate total processing time
        total_time = time.time() - start_time
        processing_stats["total_time"] = total_time
        
        return OrchestrationResponse(
            response=agent_response_content,
            session_id=session_id,
            rag_context=rag_context,
            agent_metadata=agent_metadata,
            processing_stats=processing_stats,
            timestamp=datetime.now()
        )
    
    async def _get_or_create_context(
        self, 
        session_id: str, 
        provided_context: Optional[Any] = None
    ) -> Any:
        """
        Get existing or create new conversation context.
        
        Args:
            session_id: Session identifier
            provided_context: Optionally provided context
            
        Returns:
            ConversationContext instance
        """
        # Try to get existing context
        context = await self.conversation_manager.get_context(session_id)
        
        if context is None:
            # Create new context
            context = await self.conversation_manager.create_context(
                session_id=session_id,
                system_prompt=self.default_system_prompt
            )
        
        return context
    
    def _prepare_agent_request(
        self,
        user_query: str,
        rag_context: Optional[RAGContext],
        context: Any,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentRequest:
        """
        Prepare the agent request with RAG context if available.
        
        Args:
            user_query: The user's query
            rag_context: Retrieved context from RAG system
            context: Conversation context
            model: Optional model specification
            metadata: Optional request metadata
            
        Returns:
            AgentRequest ready for agent processing
        """
        # Prepare the prompt with RAG context if available
        enhanced_prompt = user_query
        context_data = None
        
        if rag_context and rag_context.retrieved_documents:
            # Extract context data using domain service (no formatting)
            context_data = self._extract_context_data(rag_context)
            
            # Store context data in conversation context for agent to use
            if context:
                context.metadata = context.metadata or {}
                context.metadata["rag_context"] = context_data
        
        return AgentRequest(
            prompt=enhanced_prompt,
            context=context,
            model=model,
            max_tokens=metadata.get("max_tokens") if metadata else None,
            temperature=metadata.get("temperature") if metadata else None,
            stream=False,
            metadata=metadata
        )
    
    def _extract_context_data(self, rag_context: RAGContext) -> Dict[str, Any]:
        """
        Extract relevant context data (pure domain logic).
        
        Args:
            rag_context: RAG context containing retrieved documents
            
        Returns:
            Processed context data for agent consumption
        """
        context_service = ContextDomainService()
        
        # Extract relevant documents using domain service
        relevant_docs = context_service.extract_relevant_documents(rag_context)
        
        # Assess context quality
        quality_assessment = context_service.assess_context_quality(relevant_docs)
        
        return {
            "documents": relevant_docs,
            "quality": quality_assessment,
            "total_documents": len(rag_context.retrieved_documents),
            "search_metadata": rag_context.search_metadata or {}
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.
        
        Returns:
            Dictionary containing health status of all components
        """
        health_status = {
            "orchestrator": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ircot_enabled": self.ircot_config.enabled
        }
        
        # Check agent service
        try:
            agent_healthy = await self.agent_port.validate_connection()
            health_status["agent"] = "healthy" if agent_healthy else "unhealthy"
        except Exception as e:
            health_status["agent"] = f"error: {str(e)}"
        
        # Check RAG service
        try:
            rag_healthy = await self.rag_port.health_check()
            health_status["rag"] = "healthy" if rag_healthy else "unhealthy"
        except Exception as e:
            health_status["rag"] = f"error: {str(e)}"
        
        # Check conversation manager (always healthy for in-memory implementation)
        health_status["conversation_manager"] = "healthy"
        
        # Overall status
        all_healthy = all(
            status == "healthy" 
            for key, status in health_status.items() 
            if key not in ["timestamp", "orchestrator", "ircot_enabled"]
        )
        health_status["overall"] = "healthy" if all_healthy else "degraded"
        
        return health_status
    
    async def process_request_with_ircot(
        self,
        request: OrchestrationRequest,
        complexity: str = "complex",
        complexity_score: float = 7.0
    ) -> OrchestrationResponse:
        """
        Process request using LangGraph-based IRCoT workflow.
        
        This method delegates to LangGraphOrchestrator for stateful
        multi-agent orchestration with automatic state management.
        
        LangGraph IRCoT Workflow:
        1. PLAN: Analyze query, extract filters, determine complexity
        2. RETRIEVE: RAG + Knowledge Graph retrieval (parallel)
        3. REASON: Generate Chain-of-Thought reasoning step
        4. LOOP: Conditional edge decides to continue or answer
        5. ANSWER: Generate final answer with citations
        
        Args:
            request: The orchestration request
            complexity: Complexity level ("simple", "medium", "complex")
            complexity_score: Numeric complexity score (0-10)
            
        Returns:
            OrchestrationResponse with LangGraph-enhanced context
        """
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        
        # Check if IRCoT should be used based on config
        use_ircot = self.ircot_config.should_use_ircot(complexity, complexity_score)
        
        if not use_ircot:
            # Fall back to standard processing
            logger.info(f"IRCoT not triggered for query (complexity={complexity})")
            return await self.process_request(request)
        
        # Check if LangGraph orchestrator is available
        if self._langgraph_orchestrator is None:
            logger.warning("⚠ LangGraph orchestrator not available, falling back to standard RAG")
            return await self._fallback_ircot_processing(request, complexity, complexity_score)
        
        logger.info(f"🔄 Processing with LangGraph IRCoT: {request.user_query[:50]}...")
        
        try:
            # Delegate to LangGraph orchestrator
            response = await self._langgraph_orchestrator.process_request(request)
            
            # Add timing info
            total_time = time.time() - start_time
            if response.processing_stats:
                response.processing_stats["total_time_with_delegation"] = total_time
                response.processing_stats["complexity"] = complexity
                response.processing_stats["complexity_score"] = complexity_score
            
            logger.info(f"✅ LangGraph IRCoT completed in {total_time:.2f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"LangGraph processing error: {e}", exc_info=True)
            
            # Fallback to standard processing on error
            logger.warning("⚠ Falling back to standard RAG due to LangGraph error")
            return await self._fallback_ircot_processing(request, complexity, complexity_score)
    
    async def _fallback_ircot_processing(
        self,
        request: OrchestrationRequest,
        complexity: str,
        complexity_score: float
    ) -> OrchestrationResponse:
        """
        Fallback IRCoT processing when LangGraph is not available.
        
        This uses standard RAG retrieval without iterative reasoning.
        
        Args:
            request: The orchestration request
            complexity: Complexity level
            complexity_score: Numeric complexity score
            
        Returns:
            OrchestrationResponse with standard RAG context
        """
        start_time = time.time()
        session_id = request.session_id or str(uuid.uuid4())
        processing_stats = {
            "ircot_mode": False,
            "fallback_reason": "langgraph_unavailable",
            "complexity": complexity,
            "complexity_score": complexity_score
        }
        
        # Get or create conversation context
        context = await self._get_or_create_context(session_id, request.conversation_context)
        
        # Add user message to context
        user_message = ConversationMessage(
            role=ConversationRole.USER,
            content=request.user_query,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        context.add_message(user_message)
        
        rag_context = None
        
        # Standard RAG retrieval
        if request.use_rag:
            try:
                rag_start = time.time()
                rag_data = await self.rag_port.retrieve_context(
                    query=request.user_query,
                    top_k=request.rag_top_k
                )
                rag_end = time.time()
                
                rag_context = RAGContext(
                    query=request.user_query,
                    retrieved_documents=rag_data.get("retrieved_documents", []),
                    search_metadata=rag_data.get("search_metadata"),
                    relevance_scores=rag_data.get("relevance_scores", [])
                )
                
                processing_stats["rag_time"] = rag_end - rag_start
                processing_stats["documents_retrieved"] = len(rag_context.retrieved_documents)
                
            except Exception as e:
                processing_stats["rag_error"] = str(e)
        
        # Prepare agent request
        agent_request = self._prepare_agent_request(
            user_query=request.user_query,
            rag_context=rag_context,
            context=context,
            model=request.agent_model,
            metadata=request.metadata
        )
        
        # Generate response
        try:
            agent_start = time.time()
            agent_response = await self.agent_port.generate_response(agent_request)
            agent_end = time.time()
            
            processing_stats["agent_time"] = agent_end - agent_start
            processing_stats["tokens_used"] = agent_response.tokens_used
            
            agent_response_content = agent_response.content
            agent_metadata = agent_response.metadata or {}
            
        except Exception as e:
            raise AgentProcessingFailedException(
                agent_error=str(e),
                details={
                    "session_id": session_id,
                    "user_query": request.user_query,
                    "fallback_mode": True,
                    "processing_stats": processing_stats
                },
                cause=e
            )
        
        # Add assistant message to context
        assistant_message = ConversationMessage(
            role=ConversationRole.ASSISTANT,
            content=agent_response_content,
            timestamp=datetime.now(),
            message_type=MessageType.TEXT
        )
        context.add_message(assistant_message)
        
        # Update conversation context
        await self.conversation_manager.update_context(context)
        
        # Calculate total processing time
        total_time = time.time() - start_time
        processing_stats["total_time"] = total_time
        
        return OrchestrationResponse(
            response=agent_response_content,
            session_id=session_id,
            rag_context=rag_context,
            agent_metadata=agent_metadata,
            processing_stats=processing_stats,
            timestamp=datetime.now()
        )