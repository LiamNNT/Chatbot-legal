"""
Multi-Agent Orchestrator implementation.

This orchestrator coordinates all specialized agents to provide comprehensive
and high-quality responses through a multi-step pipeline.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..agents.base import (
    AgentConfig, AgentType, PlanResult, QueryRewriteResult, 
    AnswerResult, VerificationResult, ResponseResult
)
from ..ports.agent_ports import AgentPort, RAGServicePort
from ..core.domain import OrchestrationRequest, OrchestrationResponse, RAGContext
from ..core.agent_factory import AgentFactory

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Multi-Agent Orchestrator that coordinates specialized agents.
    
    This orchestrator implements a sophisticated pipeline:
    1. Planner Agent - Analyzes query and creates execution plan
    2. Query Rewriter Agent - Optimizes queries for search (if needed)
    3. RAG Retrieval - Gets relevant context using optimized queries
    4. Answer Agent - Generates comprehensive answers from context
    5. Verifier Agent - Validates answer quality and accuracy
    6. Response Agent - Creates final user-friendly response
    """
    
    def __init__(
        self,
        agent_port: AgentPort,
        rag_port: RAGServicePort,
        agent_factory,
        enable_verification: bool = True,
        enable_planning: bool = True
    ):
        """
        Initialize the multi-agent orchestrator.
        
        Args:
            agent_port: Port for communicating with LLM services
            rag_port: Port for RAG service communication
            agent_factory: Factory for creating configured agents
            enable_verification: Whether to use verification step
            enable_planning: Whether to use planning step
        """
        self.agent_port = agent_port
        self.rag_port = rag_port
        self.enable_verification = enable_verification
        self.enable_planning = enable_planning
        self.agent_factory = agent_factory
        
        # Initialize specialized agents using factory
        self.planner = self.agent_factory.create_agent("planner", agent_port)
        self.query_rewriter = self.agent_factory.create_agent("query_rewriter", agent_port)
        self.answer_agent = self.agent_factory.create_agent("answer_agent", agent_port)
        self.verifier = self.agent_factory.create_agent("verifier", agent_port)
        self.response_agent = self.agent_factory.create_agent("response_agent", agent_port)
        
        # Log agent configurations for debugging
        logger.info(f"✓ Planner Agent initialized with model: {self.planner.config.model}")
        logger.info(f"✓ Query Rewriter initialized with model: {self.query_rewriter.config.model}")
        logger.info(f"✓ Answer Agent initialized with model: {self.answer_agent.config.model}")
        logger.info(f"✓ Verifier Agent initialized with model: {self.verifier.config.model}")
        logger.info(f"✓ Response Agent initialized with model: {self.response_agent.config.model}")
    
    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Process a request through the multi-agent pipeline.
        
        Args:
            request: The orchestration request
            
        Returns:
            OrchestrationResponse with comprehensive results
        """
        start_time = time.time()
        processing_stats = {}
        
        try:
            # Step 1: Planning (if enabled)
            plan_result = None
            if self.enable_planning:
                plan_result = await self._execute_planning_step(request, processing_stats)
            
            # Step 2: Query optimization and RAG retrieval
            rag_context = await self._execute_retrieval_step(request, plan_result, processing_stats)
            
            # Step 3: Answer generation
            answer_result = await self._execute_answer_step(request, rag_context, processing_stats)
            
            # Step 4: Verification (if enabled)
            verification_result = None
            if self.enable_verification and answer_result:
                verification_result = await self._execute_verification_step(
                    request, answer_result, rag_context, processing_stats
                )
            
            # Step 5: Final response generation
            response_result = await self._execute_response_step(
                request, answer_result, verification_result, processing_stats
            )
            
            # Calculate total processing time
            total_time = time.time() - start_time
            processing_stats["total_time"] = total_time
            processing_stats["pipeline_steps"] = self._get_pipeline_steps_info()
            
            return OrchestrationResponse(
                response=response_result.final_response if response_result else "Xin lỗi, có lỗi xảy ra trong quá trình xử lý.",
                session_id=request.session_id or "unknown",
                rag_context=rag_context,
                agent_metadata={
                    "pipeline": "multi_agent",
                    "plan_result": plan_result.__dict__ if plan_result else None,
                    "answer_confidence": answer_result.confidence if answer_result else 0.0,
                    "verification_result": verification_result.__dict__ if verification_result else None,
                    "response_metadata": response_result.metadata if response_result else {}
                },
                processing_stats=processing_stats,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            # Handle pipeline errors gracefully
            total_time = time.time() - start_time
            processing_stats["total_time"] = total_time
            processing_stats["error"] = str(e)
            
            # Fallback to simple response
            fallback_response = f"Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại hoặc liên hệ hỗ trợ. Lỗi: {str(e)}"
            
            return OrchestrationResponse(
                response=fallback_response,
                session_id=request.session_id or "unknown",
                rag_context=None,
                agent_metadata={"error": str(e), "pipeline": "multi_agent_failed"},
                processing_stats=processing_stats,
                timestamp=datetime.now()
            )
    
    async def _execute_planning_step(
        self, 
        request: OrchestrationRequest, 
        processing_stats: Dict[str, Any]
    ) -> Optional[PlanResult]:
        """Execute the planning step."""
        import os
        step_start = time.time()
        
        try:
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"\n{'='*80}")
                logger.debug(f"📋 STEP 1: PLANNING")
                logger.debug(f"{'='*80}")
                logger.debug(f"Query: {request.user_query}")
            
            plan_input = {
                "query": request.user_query,
                "context": {},
                "user_profile": {}
            }
            
            plan_result = await self.planner.process(plan_input)
            processing_stats["planning_time"] = time.time() - step_start
            processing_stats["plan_complexity"] = plan_result.complexity
            processing_stats["estimated_tokens"] = plan_result.estimated_tokens
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Plan Intent: {plan_result.intent}")
                logger.debug(f"Plan Complexity: {plan_result.complexity}")
                logger.debug(f"Estimated Tokens: {plan_result.estimated_tokens}")
                logger.debug(f"{'='*80}\n")
            
            return plan_result
        
        except Exception as e:
            processing_stats["planning_time"] = time.time() - step_start
            processing_stats["planning_error"] = str(e)
            logger.error(f"Planning step failed: {e}")
            return None
    
    async def _execute_retrieval_step(
        self,
        request: OrchestrationRequest,
        plan_result: Optional[PlanResult],
        processing_stats: Dict[str, Any]
    ) -> Optional[RAGContext]:
        """Execute query rewriting and RAG retrieval."""
        import os
        
        if not request.use_rag:
            return None
        
        step_start = time.time()
        
        try:
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"\n{'='*80}")
                logger.debug(f"🔍 STEP 2: QUERY REWRITING & RAG RETRIEVAL")
                logger.debug(f"{'='*80}")
            
            # Query rewriting (if plan suggests it or for complex queries)
            rewrite_queries = [request.user_query]  # Default to original query
            
            should_rewrite = (
                plan_result and plan_result.complexity in ["medium", "complex"] or
                len(request.user_query) > 50
            )
            
            if should_rewrite:
                if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                    logger.debug(f"Original Query: {request.user_query}")
                
                rewrite_input = {
                    "query": request.user_query,
                    "intent": plan_result.intent if plan_result else "",
                    "context": {},
                    "search_history": []
                }
                
                rewrite_result = await self.query_rewriter.process(rewrite_input)
                if rewrite_result.rewritten_queries:
                    rewrite_queries = rewrite_result.rewritten_queries[:3]  # Use top 3
                
                processing_stats["query_rewrite_time"] = time.time() - step_start
                processing_stats["rewritten_queries_count"] = len(rewrite_queries)
                
                if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                    logger.debug(f"Rewritten Queries ({len(rewrite_queries)}):")
                    for i, q in enumerate(rewrite_queries, 1):
                        logger.debug(f"  {i}. {q}")
            
            # RAG retrieval using best query
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Performing RAG retrieval with top_k={request.rag_top_k}...")
            
            rag_data = await self._perform_rag_retrieval(rewrite_queries, request.rag_top_k)
            
            processing_stats["rag_time"] = time.time() - step_start - processing_stats.get("query_rewrite_time", 0)
            processing_stats["documents_retrieved"] = len(rag_data.get("retrieved_documents", []))
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Documents Retrieved: {len(rag_data.get('retrieved_documents', []))}")
            
            # 🔧 FIX: Map RAG service response format to answer_agent expected format
            # RAG service returns 'text' field, but answer_agent expects 'content'
            mapped_documents = []
            
            logger.info(f"Mapping {len(rag_data.get('retrieved_documents', []))} documents from RAG response")
            
            for idx, doc in enumerate(rag_data.get("retrieved_documents", [])):
                try:
                    # Extract text content (RAG returns 'text' field)
                    text_content = doc.get("text", doc.get("content", ""))
                    
                    # Get metadata with fallbacks
                    doc_metadata = doc.get("metadata", doc.get("meta", {}))
                    
                    mapped_doc = {
                        "content": text_content,  # Map 'text' → 'content'
                        "score": doc.get("score", 0.0),
                        "metadata": doc_metadata,
                        "title": doc.get("title", doc_metadata.get("title", f"Document {idx+1}")),
                        "source": doc.get("source", doc_metadata.get("source", "Unknown"))
                    }
                    
                    logger.debug(f"Mapped doc {idx+1}: content_length={len(text_content)}, title={mapped_doc['title']}")
                    
                    if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                        logger.debug(f"  Doc {idx+1}: {mapped_doc['title']} (score: {mapped_doc['score']:.4f}, {len(text_content)} chars)")
                    
                    mapped_documents.append(mapped_doc)
                    
                except Exception as map_error:
                    logger.error(f"Error mapping document {idx+1}: {map_error}")
                    continue
            
            logger.info(f"Successfully mapped {len(mapped_documents)} documents for answer_agent")
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"{'='*80}\n")
            
            return RAGContext(
                query=request.user_query,
                retrieved_documents=mapped_documents,  # Use mapped documents
                search_metadata=rag_data.get("search_metadata"),
                relevance_scores=rag_data.get("relevance_scores", []),
                rewritten_queries=rewrite_queries  # Pass rewritten queries to Answer Agent
            )
        
        except Exception as e:
            processing_stats["retrieval_error"] = str(e)
            processing_stats["retrieval_time"] = time.time() - step_start
            logger.error(f"Retrieval step failed: {e}")
            return None
    
    async def _perform_rag_retrieval(self, queries: List[str], top_k: int) -> Dict[str, Any]:
        """Perform RAG retrieval with multiple queries."""
        all_results = []
        
        # Try each query and collect results
        for query in queries:
            try:
                result = await self.rag_port.retrieve_context(query, top_k=top_k)
                if result and result.get("retrieved_documents"):
                    all_results.extend(result["retrieved_documents"])
            except Exception:
                continue  # Skip failed queries
        
        # Deduplicate and rank results
        unique_results = self._deduplicate_documents(all_results)
        top_results = unique_results[:top_k]
        
        return {
            "retrieved_documents": top_results,
            "search_metadata": {
                "queries_used": len(queries),
                "total_results_found": len(all_results),
                "unique_results": len(unique_results),
                "final_results": len(top_results)
            },
            "relevance_scores": [doc.get("score", 0.0) for doc in top_results]
        }
    
    def _deduplicate_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents based on content similarity."""
        if not documents:
            return []
        
        unique_docs = []
        seen_contents = set()
        
        for doc in documents:
            # RAG service returns 'text' field, fallback to 'content'
            content = doc.get("text", doc.get("content", ""))
            # Simple deduplication based on first 100 characters
            content_signature = content[:100].strip().lower()
            
            # Skip if content is empty or already seen
            if content_signature and content_signature not in seen_contents:
                seen_contents.add(content_signature)
                unique_docs.append(doc)
        
        # Sort by relevance score
        return sorted(unique_docs, key=lambda x: x.get("score", 0.0), reverse=True)
    
    async def _execute_answer_step(
        self,
        request: OrchestrationRequest,
        rag_context: Optional[RAGContext],
        processing_stats: Dict[str, Any]
    ) -> Optional[AnswerResult]:
        """Execute answer generation step."""
        import os
        step_start = time.time()
        
        try:
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"\n{'='*80}")
                logger.debug(f"💡 STEP 3: ANSWER GENERATION")
                logger.debug(f"{'='*80}")
                logger.debug(f"Query: {request.user_query}")
                logger.debug(f"Documents: {len(rag_context.retrieved_documents) if rag_context else 0}")
            
            answer_input = {
                "query": request.user_query,
                "context_documents": rag_context.retrieved_documents if rag_context else [],
                "rewritten_queries": rag_context.rewritten_queries if rag_context and rag_context.rewritten_queries else [],
                "previous_context": ""
            }
            
            answer_result = await self.answer_agent.process(answer_input)
            processing_stats["answer_generation_time"] = time.time() - step_start
            processing_stats["answer_confidence"] = answer_result.confidence
            processing_stats["sources_used"] = len(answer_result.sources_used)
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Answer Length: {len(answer_result.answer)} chars")
                logger.debug(f"Confidence: {answer_result.confidence}")
                logger.debug(f"Sources Used: {len(answer_result.sources_used)}")
                logger.debug(f"{'='*80}\n")
            
            return answer_result
        
        except Exception as e:
            processing_stats["answer_generation_error"] = str(e)
            processing_stats["answer_generation_time"] = time.time() - step_start
            logger.error(f"Answer generation failed: {e}", exc_info=True)  # Add full traceback
            return None
    
    async def _execute_verification_step(
        self,
        request: OrchestrationRequest,
        answer_result: AnswerResult,
        rag_context: Optional[RAGContext],
        processing_stats: Dict[str, Any]
    ) -> Optional[VerificationResult]:
        """Execute verification step."""
        import os
        step_start = time.time()
        
        try:
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"\n{'='*80}")
                logger.debug(f"✅ STEP 4: VERIFICATION")
                logger.debug(f"{'='*80}")
                logger.debug(f"Verifying answer...")
            
            verification_input = {
                "query": request.user_query,
                "answer": answer_result.answer,
                "context_documents": rag_context.retrieved_documents if rag_context else [],
                "reasoning_steps": answer_result.reasoning_steps,
                "confidence": answer_result.confidence
            }
            
            verification_result = await self.verifier.process(verification_input)
            processing_stats["verification_time"] = time.time() - step_start
            processing_stats["verification_confidence"] = verification_result.confidence
            processing_stats["issues_found"] = len(verification_result.issues_found)
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Verification Confidence: {verification_result.confidence}")
                logger.debug(f"Issues Found: {len(verification_result.issues_found)}")
                if verification_result.issues_found:
                    logger.debug(f"Issues: {verification_result.issues_found}")
                logger.debug(f"{'='*80}\n")
            
            return verification_result
        
        except Exception as e:
            processing_stats["verification_error"] = str(e)
            processing_stats["verification_time"] = time.time() - step_start
            logger.error(f"Verification failed: {e}")
            return None
    
    async def _execute_response_step(
        self,
        request: OrchestrationRequest,
        answer_result: Optional[AnswerResult],
        verification_result: Optional[VerificationResult],
        processing_stats: Dict[str, Any]
    ) -> Optional[ResponseResult]:
        """Execute final response generation step."""
        import os
        step_start = time.time()
        
        try:
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"\n{'='*80}")
                logger.debug(f"🎯 STEP 5: RESPONSE FORMATTING")
                logger.debug(f"{'='*80}")
            
            # Use verified answer if available, otherwise use original answer
            final_answer = answer_result.answer if answer_result else "Không thể tạo câu trả lời."
            
            response_input = {
                "query": request.user_query,
                "verified_answer": final_answer,
                "verification_result": verification_result.__dict__ if verification_result else {},
                "user_context": {},
                "conversation_history": []
            }
            
            response_result = await self.response_agent.process(response_input)
            processing_stats["response_generation_time"] = time.time() - step_start
            processing_stats["response_friendliness_score"] = response_result.user_friendliness_score
            
            if os.getenv('LOG_LEVEL', 'INFO').upper() == 'DEBUG':
                logger.debug(f"Final Response Length: {len(response_result.final_response)} chars")
                logger.debug(f"Tone: {response_result.tone}")
                logger.debug(f"Friendliness Score: {response_result.user_friendliness_score}")
                logger.debug(f"{'='*80}\n")
            
            return response_result
        
        except Exception as e:
            processing_stats["response_generation_error"] = str(e)
            processing_stats["response_generation_time"] = time.time() - step_start
            logger.error(f"Response generation failed: {e}")
            
            # Fallback response
            fallback_response = ResponseResult(
                final_response=answer_result.answer if answer_result else "Xin lỗi, có lỗi xảy ra trong quá trình tạo phản hồi.",
                tone="professional",
                completeness_score=0.5,
                user_friendliness_score=0.5,
                metadata={"fallback": True, "error": str(e)}
            )
            return fallback_response
    
    def _get_pipeline_steps_info(self) -> Dict[str, Any]:
        """Get information about pipeline steps."""
        return {
            "steps_enabled": {
                "planning": self.enable_planning,
                "query_rewriting": True,
                "rag_retrieval": True,
                "answer_generation": True,
                "verification": self.enable_verification,
                "response_formatting": True
            },
            "agents_used": {
                "planner": self.planner.get_agent_info(),
                "query_rewriter": self.query_rewriter.get_agent_info(),
                "answer_agent": self.answer_agent.get_agent_info(),
                "verifier": self.verifier.get_agent_info(),
                "response_agent": self.response_agent.get_agent_info()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents."""
        health_info = {
            "multi_agent_orchestrator": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
        # Check agent port connectivity
        try:
            agent_healthy = await self.agent_port.validate_connection()
            health_info["agent_service"] = "healthy" if agent_healthy else "unhealthy"
        except Exception as e:
            health_info["agent_service"] = f"error: {str(e)}"
        
        # Check RAG service connectivity
        try:
            rag_healthy = await self.rag_port.health_check()
            health_info["rag_service"] = "healthy" if rag_healthy else "unhealthy"
        except Exception as e:
            health_info["rag_service"] = f"error: {str(e)}"
        
        # Agent configurations
        health_info["agents"] = {
            "planner": {
                "model": self.planner.config.model,
                "status": "configured"
            },
            "query_rewriter": {
                "model": self.query_rewriter.config.model,
                "status": "configured"
            },
            "answer_agent": {
                "model": self.answer_agent.config.model,
                "status": "configured"
            },
            "verifier": {
                "model": self.verifier.config.model,
                "status": "configured"
            },
            "response_agent": {
                "model": self.response_agent.config.model,  
                "status": "configured"
            }
        }
        
        # Overall status
        service_issues = [
            k for k, v in health_info.items() 
            if isinstance(v, str) and ("unhealthy" in v or "error:" in v)
        ]
        
        health_info["overall"] = "healthy" if not service_issues else "degraded"
        
        return health_info