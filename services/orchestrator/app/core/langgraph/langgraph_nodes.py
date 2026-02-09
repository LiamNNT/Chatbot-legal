import time
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime

from .langgraph_state import IRCoTState, WorkflowPhase, merge_documents

logger = logging.getLogger(__name__)


class LangGraphNodes:
    def __init__(
        self,
        agent_port,  # AgentPort for LLM communication
        rag_port,    # RAGServicePort for retrieval
        smart_planner=None,  # SmartPlannerAgent
        answer_agent=None,   # AnswerAgent
        graph_reasoning_agent=None,  # GraphReasoningAgent
        conversation_manager=None,   # ConversationManager
        context_service=None,        # ContextDomainService
        ircot_config=None            # IRCoT configuration
    ):
        self.agent_port = agent_port
        self.rag_port = rag_port
        self.smart_planner = smart_planner
        self.answer_agent = answer_agent
        self.graph_reasoning_agent = graph_reasoning_agent
        self.conversation_manager = conversation_manager
        self.context_service = context_service
        self.ircot_config = ircot_config
        
        # CoT system prompt for reasoning
        self.cot_system_prompt = """Bạn là một trợ lý AI chuyên về suy luận logic và phân tích thông tin.

Nhiệm vụ của bạn là:
1. Phân tích thông tin được cung cấp
2. Thực hiện một bước suy luận logic
3. Xác định những thông tin còn thiếu
4. Đề xuất câu truy vấn để tìm thêm thông tin (nếu cần)

Luôn trả lời bằng JSON hợp lệ theo format yêu cầu.
Sử dụng tiếng Việt cho nội dung reasoning và thông tin."""
    
    async def plan_node(self, state: IRCoTState) -> Dict[str, Any]:
        """
        Planning node: Analyze query and determine processing strategy.
        
        This node:
        1. Rewrites query based on conversation context
        2. Uses SmartPlanner to analyze complexity
        3. Extracts filters and search terms
        4. Determines if IRCoT/KG is needed
        
        Args:
            state: Current workflow state
            
        Returns:
            State updates from planning
        """
        step_start = time.time()
        logger.info(f"📋 PLAN NODE: Analyzing query...")
        
        updates: Dict[str, Any] = {
            "current_phase": WorkflowPhase.PLANNING.value
        }
        
        try:
            original_query = state["original_query"]
            session_id = state["session_id"]
            standalone_query = original_query
            
            # Step 1: Contextual Query Rewriting
            if self.conversation_manager and self.context_service:
                chat_history = self.conversation_manager.get_history(session_id, limit=6)
                
                if chat_history:
                    standalone_query = await self.context_service.contextualize_query(
                        current_query=original_query,
                        chat_history=chat_history
                    )
                    
                    if standalone_query != original_query:
                        logger.info(f"🔄 Query rewritten: '{original_query}' → '{standalone_query}'")
                        updates["processing_stats"] = {
                            **state.get("processing_stats", {}),
                            "query_rewritten": True,
                            "original_query": original_query,
                            "standalone_query": standalone_query
                        }
            
            updates["standalone_query"] = standalone_query
            updates["current_search_query"] = standalone_query
            
            # Step 2: Smart Planning
            if self.smart_planner:
                plan_input = {
                    "query": standalone_query,
                    "context": {},
                    "user_profile": {}
                }
                
                plan_result = await self.smart_planner.process(plan_input)
                
                # Convert to dict for serialization
                plan_dict = {
                    "intent": plan_result.intent,
                    "complexity": plan_result.complexity,
                    "complexity_score": plan_result.complexity_score,
                    "requires_rag": plan_result.requires_rag,
                    "use_knowledge_graph": plan_result.use_knowledge_graph,
                    "graph_query_type": getattr(plan_result, 'graph_query_type', 'local'),
                    "rewritten_queries": plan_result.rewritten_queries,
                    "search_terms": plan_result.search_terms,
                    "strategy": plan_result.strategy,
                    "top_k": plan_result.top_k,
                    "extracted_filters": plan_result.extracted_filters.to_dict() if plan_result.extracted_filters and not plan_result.extracted_filters.is_empty() else None
                }
                
                updates["plan_result"] = plan_dict
                updates["complexity"] = plan_result.complexity
                updates["complexity_score"] = plan_result.complexity_score
                
                # Determine if KG should be used (from plan or request)
                should_use_kg = state["use_knowledge_graph"] or plan_result.use_knowledge_graph
                updates["use_knowledge_graph"] = should_use_kg
                
                # Set max iterations based on complexity
                if plan_result.complexity == "complex" and plan_result.complexity_score >= 7.0:
                    updates["max_iterations"] = 3
                elif plan_result.complexity == "complex":
                    updates["max_iterations"] = 2
                else:
                    updates["max_iterations"] = 1
                
                logger.info(f"   Intent: {plan_result.intent}")
                logger.info(f"   Complexity: {plan_result.complexity} (score: {plan_result.complexity_score})")
                logger.info(f"   Strategy: {plan_result.strategy}")
                logger.info(f"   Use KG: {should_use_kg}")
                logger.info(f"   Max IRCoT iterations: {updates.get('max_iterations', 2)}")
            
            else:
                # Default planning without SmartPlanner
                updates["plan_result"] = {
                    "intent": "information_query",
                    "complexity": "medium",
                    "complexity_score": 5.0,
                    "requires_rag": True,
                    "rewritten_queries": [standalone_query]
                }
                updates["complexity"] = "medium"
                updates["complexity_score"] = 5.0
            
            # Record timing
            planning_time = time.time() - step_start
            updates["processing_stats"] = {
                **updates.get("processing_stats", state.get("processing_stats", {})),
                "planning_time": planning_time
            }
            
            logger.info(f"✅ PLAN NODE completed in {planning_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ PLAN NODE error: {e}")
            updates["error"] = f"Planning failed: {str(e)}"
            updates["current_phase"] = WorkflowPhase.ERROR.value
        
        return updates
    
    async def retrieve_node(self, state: IRCoTState) -> Dict[str, Any]:
        step_start = time.time()
        iteration = state["current_iteration"] + 1
        logger.info(f"🔍 RETRIEVE NODE: Iteration {iteration}/{state['max_iterations']}")
        
        updates: Dict[str, Any] = {
            "current_phase": WorkflowPhase.RETRIEVING.value,
            "current_iteration": iteration
        }
        
        try:
            plan_result = state.get("plan_result", {})
            search_query = state["current_search_query"]
            use_kg = state["use_knowledge_graph"]
            
            # Get search queries (from plan or current query)
            search_queries = plan_result.get("rewritten_queries", [search_query])
            if not search_queries:
                search_queries = [search_query]
            
            # Get top_k from plan or state
            top_k = plan_result.get("top_k", state["rag_top_k"])
            
            # Extract filters if available
            extracted_filters = plan_result.get("extracted_filters")
            
            new_documents = []
            graph_context = None
            
            # === PARALLEL EXECUTION: RAG + KG ===
            if use_kg and self.graph_reasoning_agent:
                logger.info("⚡ Parallel execution: RAG + Knowledge Graph")
                
                # Import GraphQueryType
                from ...agents.graph_reasoning_agent import GraphQueryType
                
                graph_query_type_str = plan_result.get("graph_query_type", "local")
                try:
                    graph_query_type = GraphQueryType(graph_query_type_str)
                except ValueError:
                    graph_query_type = GraphQueryType.LOCAL
                
                # Create parallel tasks
                graph_task = self.graph_reasoning_agent.reason(
                    query=state["original_query"],
                    query_type=graph_query_type,
                    context={
                        "extracted_filters": extracted_filters or {},
                        "search_terms": plan_result.get("search_terms", [])
                    }
                )
                
                rag_task = self._perform_rag_retrieval(
                    search_queries=search_queries,
                    top_k=top_k,
                    filters=extracted_filters
                )
                
                # Run both in parallel
                graph_result, rag_result = await asyncio.gather(graph_task, rag_task)
                
                # Process graph results
                updates["graph_context"] = graph_result.synthesized_context
                updates["graph_nodes_found"] = len(graph_result.nodes)
                updates["graph_paths_found"] = len(graph_result.paths)
                updates["graph_confidence"] = graph_result.confidence
                
                # Add graph context as a document if useful
                if (graph_result.synthesized_context and 
                    len(graph_result.synthesized_context) > 50 and
                    graph_result.confidence >= 0.5):
                    
                    graph_doc = {
                        "content": graph_result.synthesized_context,
                        "score": 1.0,
                        "title": "Knowledge Graph Context",
                        "source": "Knowledge Graph",
                        "metadata": {"source_type": "graph_reasoning"}
                    }
                    new_documents.append(graph_doc)
                
                # Process RAG results
                new_documents.extend(self._process_rag_results(rag_result))
                
                logger.info(f"   Graph: {len(graph_result.nodes)} nodes, confidence={graph_result.confidence}")
                logger.info(f"   RAG: {len(rag_result.get('retrieved_documents', []))} documents")
                
            else:
                # RAG only
                rag_result = await self._perform_rag_retrieval(
                    search_queries=search_queries,
                    top_k=top_k,
                    filters=extracted_filters
                )
                new_documents = self._process_rag_results(rag_result)
                logger.info(f"   RAG: {len(new_documents)} documents retrieved")
            
            # Record which queries were used
            updates["search_queries_used"] = search_queries
            
            # Merge with existing documents (deduplication handled by operator.add + merge)
            updates["accumulated_documents"] = new_documents
            
            # Record timing
            retrieval_time = time.time() - step_start
            updates["processing_stats"] = {
                **state.get("processing_stats", {}),
                f"retrieval_time_iter_{iteration}": retrieval_time,
                "total_documents": len(state.get("accumulated_documents", [])) + len(new_documents)
            }
            
            logger.info(f"✅ RETRIEVE NODE completed in {retrieval_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ RETRIEVE NODE error: {e}")
            updates["error"] = f"Retrieval failed: {str(e)}"
        
        return updates
    
    async def reason_node(self, state: IRCoTState) -> Dict[str, Any]:
        """
        Reasoning node: Generate chain-of-thought reasoning step.
        
        This node:
        1. Analyzes accumulated context
        2. Generates intermediate reasoning
        3. Identifies information gaps
        4. Proposes next search query if needed
        
        Args:
            state: Current workflow state
            
        Returns:
            State updates with reasoning results
        """
        step_start = time.time()
        iteration = state["current_iteration"]
        logger.info(f"🧠 REASON NODE: Iteration {iteration}/{state['max_iterations']}")
        
        updates: Dict[str, Any] = {
            "current_phase": WorkflowPhase.REASONING.value
        }
        
        try:
            # Build context summary for reasoning
            accumulated_docs = state.get("accumulated_documents", [])
            context_text = self._build_context_text(accumulated_docs)
            
            # Build previous reasoning summary
            previous_steps = state.get("reasoning_steps", [])
            previous_reasoning = "\n".join([
                f"Bước {step['iteration']}: {step['reasoning']}"
                for step in previous_steps
            ])
            
            # Generate CoT reasoning
            prompt = f"""
Dựa trên thông tin đã có và câu hỏi của người dùng, hãy thực hiện một bước suy luận.

**Câu hỏi gốc:** {state["original_query"]}

**Thông tin đã thu thập:**
{context_text[:4000]}  # Limit context length

**Các bước suy luận trước đó:**
{previous_reasoning if previous_reasoning else "Chưa có"}

**Bước suy luận hiện tại:** {iteration}/{state['max_iterations']}

Hãy:
1. Phân tích thông tin hiện có
2. Xác định thông tin còn thiếu để trả lời đầy đủ câu hỏi
3. Đưa ra một câu suy luận/kết luận trung gian
4. Nếu cần thêm thông tin, đề xuất câu truy vấn tìm kiếm tiếp theo

Trả lời theo format JSON:
{{
    "reasoning_step": "<Bước suy luận/kết luận trung gian>",
    "information_gaps": ["<Thông tin còn thiếu 1>", "<Thông tin còn thiếu 2>"],
    "next_search_query": "<Câu truy vấn để tìm thêm thông tin, hoặc null nếu đủ>",
    "confidence": <0.0-1.0>,
    "can_answer_now": <true/false>
}}"""
            
            # Call LLM for reasoning
            from ..domain.domain import AgentRequest, ConversationContext
            
            cot_request = AgentRequest(
                prompt=prompt,
                context=ConversationContext(
                    session_id=state["session_id"],
                    messages=[],  # Empty messages list
                    system_prompt=self.cot_system_prompt
                ),
                temperature=0.3
            )
            
            cot_response = await self.agent_port.generate_response(cot_request)
            
            # Parse JSON response
            cot_result = self._parse_cot_response(cot_response.content)
            
            # Create reasoning step record
            reasoning_step = {
                "iteration": iteration,
                "reasoning": cot_result.get("reasoning_step", ""),
                "next_query": cot_result.get("next_search_query"),
                "confidence": cot_result.get("confidence", 0.0),
                "can_answer": cot_result.get("can_answer_now", False),
                "information_gaps": cot_result.get("information_gaps", [])
            }
            
            updates["reasoning_steps"] = [reasoning_step]
            updates["current_confidence"] = cot_result.get("confidence", 0.0)
            updates["can_answer_now"] = cot_result.get("can_answer_now", False)
            updates["information_gaps"] = cot_result.get("information_gaps", [])
            
            # Update search query for next iteration
            next_query = cot_result.get("next_search_query")
            if next_query:
                updates["current_search_query"] = next_query
            
            logger.info(f"   Confidence: {cot_result.get('confidence', 0.0):.2f}")
            logger.info(f"   Can answer: {cot_result.get('can_answer_now', False)}")
            
            # Record timing
            reasoning_time = time.time() - step_start
            updates["processing_stats"] = {
                **state.get("processing_stats", {}),
                f"reasoning_time_iter_{iteration}": reasoning_time
            }
            
            logger.info(f"✅ REASON NODE completed in {reasoning_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ REASON NODE error: {e}")
            updates["error"] = f"Reasoning failed: {str(e)}"
            # Default to allowing answer on error
            updates["can_answer_now"] = True
        
        return updates
    
    async def answer_node(self, state: IRCoTState) -> Dict[str, Any]:
        """
        Answer node: Generate final answer from accumulated context.
        
        This node:
        1. Compiles all reasoning steps
        2. Uses accumulated context to generate answer
        3. Produces citations and sources
        
        Args:
            state: Current workflow state
            
        Returns:
            State updates with final answer
        """
        step_start = time.time()
        logger.info("📝 ANSWER NODE: Generating final answer...")
        
        updates: Dict[str, Any] = {
            "current_phase": WorkflowPhase.ANSWERING.value
        }
        
        try:
            accumulated_docs = state.get("accumulated_documents", [])
            reasoning_steps = state.get("reasoning_steps", [])
            
            # Compile reasoning chain
            final_reasoning = "\n\n".join([
                f"**Bước {step['iteration']}:** {step['reasoning']}"
                for step in reasoning_steps
            ])
            updates["final_reasoning"] = final_reasoning
            
            # Generate answer using AnswerAgent
            if self.answer_agent:
                # Build context for answer agent
                from ..domain.domain import RAGContext
                
                rag_context = RAGContext(
                    query=state["original_query"],
                    retrieved_documents=accumulated_docs,
                    search_metadata={
                        "ircot_iterations": state["current_iteration"],
                        "reasoning_chain": final_reasoning
                    },
                    relevance_scores=[doc.get("score", 0.0) for doc in accumulated_docs]
                )
                
                answer_input = {
                    "query": state["original_query"],
                    "context": accumulated_docs,
                    "rag_context": rag_context
                }
                
                answer_result = await self.answer_agent.process(answer_input)
                
                updates["final_answer"] = answer_result.answer
                
                # Extract detailed sources
                if answer_result.detailed_sources:
                    detailed_sources = []
                    for ds in answer_result.detailed_sources:
                        detailed_sources.append({
                            "title": ds.title,
                            "doc_id": ds.doc_id,
                            "chunk_id": ds.chunk_id,
                            "score": ds.score,
                            "citation_text": ds.citation_text,
                            "char_spans": ds.char_spans,
                            "highlighted_text": ds.highlighted_text
                        })
                    updates["detailed_sources"] = detailed_sources
                
            else:
                # Fallback: Simple answer without AnswerAgent
                updates["final_answer"] = "Xin lỗi, không thể tạo câu trả lời."
            
            updates["current_phase"] = WorkflowPhase.COMPLETED.value
            
            # Record timing
            answer_time = time.time() - step_start
            total_time = time.time() - state["start_time"]
            
            updates["processing_stats"] = {
                **state.get("processing_stats", {}),
                "answer_time": answer_time,
                "total_time": total_time,
                "total_iterations": state["current_iteration"],
                "total_documents": len(accumulated_docs),
                "llm_calls": state["current_iteration"] + 2  # plan + reasoning*iterations + answer
            }
            
            logger.info(f"✅ ANSWER NODE completed in {answer_time:.2f}s")
            logger.info(f"📊 Total time: {total_time:.2f}s, Iterations: {state['current_iteration']}")
            
        except Exception as e:
            logger.error(f"❌ ANSWER NODE error: {e}")
            updates["error"] = f"Answer generation failed: {str(e)}"
            updates["final_answer"] = f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
            updates["current_phase"] = WorkflowPhase.ERROR.value
        
        return updates
    
    def should_continue_ircot(self, state: IRCoTState) -> Literal["continue", "answer"]:
        """
        Conditional edge: Decide whether to continue IRCoT loop or generate answer.
        
        Decision factors:
        1. Max iterations reached
        2. Confidence threshold met
        3. No more information gaps
        4. Error occurred
        
        Args:
            state: Current workflow state
            
        Returns:
            "continue" to loop back to retrieve, "answer" to proceed to answer
        """
        iteration = state["current_iteration"]
        max_iterations = state["max_iterations"]
        confidence = state.get("current_confidence", 0.0)
        can_answer = state.get("can_answer_now", False)
        error = state.get("error")
        
        # Always answer on error
        if error:
            logger.info(f"⏹️ Stopping due to error: {error}")
            return "answer"
        
        # Check if max iterations reached
        if iteration >= max_iterations:
            logger.info(f"⏹️ Max iterations reached ({iteration}/{max_iterations})")
            return "answer"
        
        # Check confidence threshold
        early_stopping_threshold = 0.70
        if self.ircot_config:
            early_stopping_threshold = getattr(self.ircot_config, 'early_stopping_threshold', 0.70)
        
        if confidence >= early_stopping_threshold:
            logger.info(f"⏹️ Confidence threshold met ({confidence:.2f} >= {early_stopping_threshold})")
            return "answer"
        
        # Check if model thinks it can answer
        if can_answer:
            logger.info(f"⏹️ Model confident it can answer now")
            return "answer"
        
        # Continue iterating
        logger.info(f"🔄 Continuing IRCoT (iteration {iteration}, confidence {confidence:.2f})")
        return "continue"
    
    # === Helper Methods ===
    
    async def _perform_rag_retrieval(
        self,
        search_queries: List[str],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform RAG retrieval with multiple queries."""
        all_documents = []
        
        for query in search_queries:
            try:
                result = await self.rag_port.retrieve_context(
                    query=query,
                    top_k=top_k,
                    filters=filters
                )
                docs = result.get("retrieved_documents", [])
                all_documents.extend(docs)
            except Exception as e:
                logger.warning(f"RAG query failed: {query[:50]}... - {e}")
        
        # Deduplicate by content similarity
        unique_docs = []
        seen_content = set()
        
        for doc in all_documents:
            content_key = doc.get("content", "")[:200]
            if content_key not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_key)
        
        return {"retrieved_documents": unique_docs}
    
    def _process_rag_results(self, rag_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process RAG results into standard document format."""
        documents = []
        
        for idx, doc in enumerate(rag_result.get("retrieved_documents", [])):
            text_content = doc.get("text", doc.get("content", ""))
            doc_metadata = doc.get("metadata", doc.get("meta", {}))
            
            processed_doc = {
                "content": text_content,
                "score": doc.get("score", 0.0),
                "title": doc.get("title", doc_metadata.get("title", f"Document {idx+1}")),
                "source": doc.get("source", doc_metadata.get("source", "Unknown")),
                "metadata": doc_metadata,
                "doc_id": doc.get("doc_id"),
                "chunk_id": doc.get("chunk_id")
            }
            documents.append(processed_doc)
        
        return documents
    
    def _build_context_text(self, documents: List[Dict[str, Any]]) -> str:
        """Build context text from documents for reasoning."""
        context_parts = []
        
        for i, doc in enumerate(documents[:10]):  # Limit to 10 docs
            title = doc.get("title", f"Document {i+1}")
            content = doc.get("content", "")[:1000]  # Limit content length
            score = doc.get("score", 0.0)
            
            context_parts.append(f"[{i+1}] {title} (score: {score:.2f})\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _parse_cot_response(self, response: str) -> Dict[str, Any]:
        """Parse Chain-of-Thought response from LLM."""
        # Try to extract JSON from response
        try:
            # Find JSON block in response
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback: return default structure
        return {
            "reasoning_step": response[:500] if response else "Unable to reason",
            "information_gaps": [],
            "next_search_query": None,
            "confidence": 0.5,
            "can_answer_now": True
        }
