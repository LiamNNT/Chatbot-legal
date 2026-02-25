"""
Optimized Multi-Agent Orchestrator — 2-agent pipeline.

Agents:
1. Smart Planner  (planning + query rewriting)
2. Answer Agent   (answer generation with built-in formatting)

Enhanced with:
- Filter support (doc_types, legal_domains, years, legal_references)
- Citation with char_spans for precise source attribution
- Graph Reasoning: local, global (community), multi-hop dynamic reasoning
- IRCoT (Interleaving Retrieval with Chain-of-Thought)
- Conversation memory (sliding window)
- Contextual query rewriting for follow-up questions

Cost savings: ~60 % fewer LLM calls + 33 % lower latency vs original 5-agent pipeline.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..base import AgentConfig, AgentType, AnswerResult
from ..smart_planner import SmartPlannerAgent, SmartPlanResult, ExtractedFilters
from ...adapters.rag_adapter import RAGFilters
from ....conversation.conversation_manager import InMemoryConversationManagerAdapter
from ....shared.ports import AgentPort, RAGServicePort
from ....shared.domain import OrchestrationRequest, OrchestrationResponse, RAGContext
from ....shared.config.ircot_config import IRCoTConfig, IRCoTMode, IRCoTResult
from ...services.ircot_service import IRCoTReasoningService
from ...services.context_service import ContextDomainService
from ..reasoning.pipeline import LegalVerificationPipeline
from .direct_responses import get_direct_response

logger = logging.getLogger(__name__)


class OptimizedMultiAgentOrchestrator:
    """Two-agent orchestrator with optional Graph Reasoning and IRCoT."""

    def __init__(
        self,
        agent_port: AgentPort,
        rag_port: RAGServicePort,
        agent_factory,
        enable_verification: bool = True,
        enable_planning: bool = True,
        graph_adapter=None,
        ircot_config: Optional[IRCoTConfig] = None,
    ):
        self.agent_port = agent_port
        self.rag_port = rag_port
        self.enable_planning = enable_planning
        self.agent_factory = agent_factory
        self.graph_adapter = graph_adapter

        # IRCoT
        self.ircot_config = ircot_config or IRCoTConfig()
        self.ircot_service = IRCoTReasoningService(
            agent_port=agent_port, rag_port=rag_port, config=self.ircot_config
        )

        # Agents via factory
        try:
            self.smart_planner = self.agent_factory.create_agent("smart_planner", agent_port)
            logger.info(f"✓ Smart Planner initialized with model: {self.smart_planner.config.model}")
        except Exception as e:
            logger.warning(f"Smart Planner not found in config, using fallback: {e}")
            self.smart_planner = None

        self.answer_agent = self.agent_factory.create_agent("answer_agent", agent_port)
        logger.info(f"✓ Answer Agent initialized with model: {self.answer_agent.config.model}")
        logger.info("✓ Response formatting built into Answer Agent (optimized pipeline)")

        # Legal Verification Pipeline (Symbolic Verification for KG)
        if graph_adapter:
            self.verification_pipeline = LegalVerificationPipeline(
                llm_port=agent_port, graph_adapter=graph_adapter
            )
            logger.info("✓ Legal Verification Pipeline initialized")
        else:
            self.verification_pipeline = None
            logger.info("⚠ Legal Verification Pipeline not initialized (no graph_adapter)")

        # IRCoT
        if self.ircot_config.enabled:
            logger.info(
                f"✓ IRCoT enabled (mode={self.ircot_config.mode.value}, "
                f"max_iterations={self.ircot_config.max_iterations})"
            )
        else:
            logger.info("⚠ IRCoT disabled")

        # Conversation memory
        self.conversation_manager = InMemoryConversationManagerAdapter(max_messages=20)
        self.context_service = ContextDomainService(llm_client=agent_port)

        logger.info("=" * 60)
        logger.info("🚀 OPTIMIZED ORCHESTRATOR INITIALIZED (2 Agents + Verification Pipeline + IRCoT + Memory)")
        logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        start_time = time.time()
        processing_stats: Dict[str, Any] = {
            "pipeline": "optimized_2_agents_direct",
            "retry_attempts": 0,
            "feedback_history": [],
        }

        try:
            # Step 0 — Contextual query rewriting (follow-up questions)
            original_query = request.user_query
            standalone_query = original_query
            session_id = request.session_id or "default"

            chat_history = self.conversation_manager.get_history(session_id, limit=6)
            if chat_history:
                standalone_query = await self.context_service.contextualize_query(
                    current_query=original_query, chat_history=chat_history
                )
                if standalone_query != original_query:
                    logger.info(f"🔄 Query rewritten: '{original_query}' → '{standalone_query}'")
                    processing_stats.update(
                        query_rewritten=True,
                        original_query=original_query,
                        standalone_query=standalone_query,
                    )
                    request = OrchestrationRequest(
                        user_query=standalone_query,
                        session_id=request.session_id,
                        use_rag=request.use_rag,
                        rag_top_k=request.rag_top_k,
                        use_knowledge_graph=getattr(request, "use_knowledge_graph", None),
                        agent_model=getattr(request, "agent_model", None),
                        conversation_context=getattr(request, "conversation_context", None),
                        metadata=getattr(request, "metadata", None),
                    )
                else:
                    processing_stats["query_rewritten"] = False
            else:
                processing_stats["chat_history_empty"] = True

            # Step 1 — Smart Planning
            plan_result = None
            if self.enable_planning and self.smart_planner:
                plan_result = await self._execute_smart_planning_step(request, processing_stats)

            requires_rag = True
            if plan_result and not plan_result.requires_rag:
                requires_rag = False
                processing_stats["skipped_rag"] = True

            # Step 1.5 — Direct response for social greetings
            if plan_result and plan_result.strategy == "direct_response":
                direct = get_direct_response(request.user_query, plan_result.intent)
                if direct:
                    total_time = time.time() - start_time
                    processing_stats.update(total_time=total_time, direct_response=True, llm_calls=1)
                    return OrchestrationResponse(
                        response=direct,
                        session_id=request.session_id or "unknown",
                        rag_context=None,
                        agent_metadata={
                            "pipeline": "direct_response",
                            "plan_result": plan_result.__dict__ if plan_result else None,
                            "answer_confidence": 1.0,
                            "detailed_sources": [],
                        },
                        processing_stats=processing_stats,
                        timestamp=datetime.now(),
                    )

            # Step 2 — RAG Retrieval
            rag_context = None
            if request.use_rag and requires_rag:
                rag_context = await self._execute_retrieval_step(request, plan_result, processing_stats)

            # Step 3 — Answer Generation (includes formatting)
            answer_result = await self._execute_answer_step(request, rag_context, processing_stats)
            final_response = answer_result.answer if answer_result else "Xin lỗi, có lỗi xảy ra."

            # Save conversation
            self.conversation_manager.add_message(session_id, "user", original_query)
            self.conversation_manager.add_message(session_id, "assistant", final_response)

            # Stats
            total_time = time.time() - start_time
            processing_stats["total_time"] = total_time
            processing_stats["llm_calls"] = self._count_llm_calls(processing_stats)
            processing_stats["pipeline_steps"] = self._get_pipeline_steps_info()

            detailed_sources_data = []
            if answer_result and answer_result.detailed_sources:
                for ds in answer_result.detailed_sources:
                    detailed_sources_data.append({
                        "title": ds.title,
                        "doc_id": ds.doc_id,
                        "chunk_id": ds.chunk_id,
                        "score": ds.score,
                        "citation_text": ds.citation_text,
                        "char_spans": ds.char_spans,
                        "highlighted_text": ds.highlighted_text,
                        "doc_type": ds.doc_type,
                        "faculty": ds.faculty,
                        "year": ds.year,
                        "subject": ds.subject,
                    })

            return OrchestrationResponse(
                response=final_response,
                session_id=request.session_id or "unknown",
                rag_context=rag_context,
                agent_metadata={
                    "pipeline": "optimized_2_agents_direct",
                    "plan_result": plan_result.__dict__ if plan_result else None,
                    "answer_confidence": answer_result.confidence if answer_result else 0.0,
                    "detailed_sources": detailed_sources_data,
                    "filters_applied": (
                        plan_result.extracted_filters.to_dict()
                        if plan_result and plan_result.extracted_filters and not plan_result.extracted_filters.is_empty()
                        else None
                    ),
                },
                processing_stats=processing_stats,
                timestamp=datetime.now(),
            )

        except Exception as e:
            total_time = time.time() - start_time
            processing_stats.update(total_time=total_time, error=str(e))
            logger.error(f"Optimized pipeline error: {e}", exc_info=True)
            return OrchestrationResponse(
                response=f"Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại. Lỗi: {e}",
                session_id=request.session_id or "unknown",
                rag_context=None,
                agent_metadata={"error": str(e), "pipeline": "optimized_3_agents_failed"},
                processing_stats=processing_stats,
                timestamp=datetime.now(),
            )

    # ------------------------------------------------------------------
    # Step 1 — Smart Planning
    # ------------------------------------------------------------------

    async def _execute_smart_planning_step(
        self, request: OrchestrationRequest, processing_stats: Dict[str, Any]
    ) -> Optional[SmartPlanResult]:
        import os

        step_start = time.time()
        try:
            if os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG":
                logger.debug(f"\n{'='*80}\n📋 STEP 1: SMART PLANNING\n{'='*80}\nQuery: {request.user_query}")

            plan_result = await self.smart_planner.process(
                {"query": request.user_query, "context": {}, "user_profile": {}}
            )
            processing_stats.update(
                planning_time=time.time() - step_start,
                plan_complexity=plan_result.complexity,
                plan_complexity_score=plan_result.complexity_score,
                requires_rag=plan_result.requires_rag,
                rewritten_queries_count=len(plan_result.rewritten_queries),
            )
            return plan_result
        except Exception as e:
            processing_stats.update(planning_time=time.time() - step_start, planning_error=str(e))
            logger.error(f"Smart planning step failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Step 2 — RAG Retrieval (router)
    # ------------------------------------------------------------------

    async def _execute_retrieval_step(
        self,
        request: OrchestrationRequest,
        plan_result: Optional[SmartPlanResult],
        processing_stats: Dict[str, Any],
    ) -> Optional[RAGContext]:
        import os

        step_start = time.time()

        # IRCoT for complex queries?
        use_ircot = (
            plan_result
            and self.ircot_config.enabled
            and self.ircot_config.should_use_ircot(plan_result.complexity, plan_result.complexity_score)
        )
        if use_ircot:
            return await self._execute_ircot_retrieval(request, plan_result, processing_stats)

        # Standard retrieval
        try:
            if os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG":
                logger.debug(f"\n{'='*80}\n🔍 STEP 2: RAG RETRIEVAL + GRAPH REASONING\n{'='*80}")

            search_queries = plan_result.rewritten_queries if plan_result and plan_result.rewritten_queries else [request.user_query]
            top_k = plan_result.top_k if plan_result and plan_result.top_k > 0 else request.rag_top_k
            extracted_filters = plan_result.extracted_filters if plan_result else None
            use_rerank = plan_result.reranking if plan_result else True

            # Should we use Knowledge Graph?
            should_use_graph = False
            if hasattr(request, "use_knowledge_graph") and request.use_knowledge_graph:
                should_use_graph = True
            elif plan_result and plan_result.use_knowledge_graph:
                should_use_graph = True

            graph_context = None

            if should_use_graph and self.verification_pipeline is not None:
                # Parallel: verification pipeline + vector
                graph_context, rag_data = await self._parallel_graph_and_vector(
                    request, plan_result, search_queries, top_k, extracted_filters, use_rerank, processing_stats
                )
            elif should_use_graph and self.verification_pipeline is None:
                logger.warning("⚠️ KG requested but verification_pipeline unavailable — vector only")
                processing_stats["kg_unavailable_warning"] = True
                rag_data = await self._perform_rag_retrieval(search_queries, top_k, extracted_filters, use_rerank)
            else:
                rag_data = await self._perform_rag_retrieval(search_queries, top_k, extracted_filters, use_rerank)

            processing_stats.update(
                rag_time=time.time() - step_start,
                documents_retrieved=len(rag_data.get("retrieved_documents", [])),
                filters_applied=extracted_filters.to_dict() if extracted_filters and not extracted_filters.is_empty() else None,
                use_knowledge_graph=should_use_graph,
                use_vector_search=plan_result.use_vector_search if plan_result else True,
                complexity=plan_result.complexity if plan_result else "medium",
                strategy=plan_result.strategy if plan_result else "standard_rag",
            )

            # Map documents
            mapped_documents = self._map_rag_documents(rag_data)

            # Prepend graph context if meaningful
            if (
                graph_context
                and len(graph_context) > 50
                and processing_stats.get("graph_confidence", 0) >= 0.5
                and processing_stats.get("graph_nodes_found", 0) > 0
            ):
                mapped_documents.insert(0, {
                    "content": graph_context,
                    "score": 1.0,
                    "metadata": {"source_type": "graph_reasoning"},
                    "title": "Graph Reasoning Context",
                    "source": "Knowledge Graph",
                })

            return RAGContext(
                query=request.user_query,
                retrieved_documents=mapped_documents,
                search_metadata=rag_data.get("search_metadata"),
                relevance_scores=rag_data.get("relevance_scores", []),
                rewritten_queries=search_queries,
            )
        except Exception as e:
            processing_stats.update(retrieval_error=str(e), retrieval_time=time.time() - step_start)
            logger.error(f"Retrieval step failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Parallel graph + vector helper
    # ------------------------------------------------------------------

    async def _parallel_graph_and_vector(
        self,
        request: OrchestrationRequest,
        plan_result: Optional[SmartPlanResult],
        search_queries: List[str],
        top_k: int,
        extracted_filters: Optional[ExtractedFilters],
        use_rerank: bool,
        processing_stats: Dict[str, Any],
    ):
        graph_task = self.verification_pipeline.run(request.user_query)
        vector_task = self._perform_rag_retrieval(search_queries, top_k, extracted_filters, use_rerank)

        graph_start = time.time()
        pipeline_result, rag_data = await asyncio.gather(graph_task, vector_task)
        elapsed = time.time() - graph_start

        processing_stats.update(
            graph_reasoning_time=elapsed,
            graph_nodes_found=pipeline_result.kg_result.record_count if pipeline_result.kg_result else 0,
            graph_confidence=pipeline_result.confidence,
            verification_passed=pipeline_result.success,
            cypher_retries=pipeline_result.cypher_retries,
            answer_retries=pipeline_result.answer_retries,
        )
        if pipeline_result.cypher_verification:
            processing_stats["cypher_rules_checked"] = [
                r.rule_id for r in pipeline_result.cypher_verification.rules_checked
            ]
        if pipeline_result.answer_verdict:
            processing_stats["answer_verdict"] = pipeline_result.answer_verdict.status.value

        # Build graph context string from pipeline result
        if pipeline_result.success and pipeline_result.structured_answer:
            graph_context = pipeline_result.structured_answer.natural_language
            if pipeline_result.structured_answer.citations:
                graph_context += "\n\nNguồn tham khảo:\n" + "\n".join(
                    f"- {c}" for c in pipeline_result.structured_answer.citations
                )
        elif pipeline_result.kg_result and pipeline_result.kg_result.records:
            # Fallback: raw KG data
            graph_context = "Dữ liệu từ Knowledge Graph:\n" + "\n".join(
                str(r.data) for r in pipeline_result.kg_result.records[:10]
            )
        else:
            graph_context = ""

        logger.info(
            f"✅ Parallel: Verification Pipeline (success={pipeline_result.success}) / "
            f"Vector {len(rag_data.get('retrieved_documents', []))} docs in {elapsed:.2f}s"
        )
        return graph_context, rag_data

    # ------------------------------------------------------------------
    # IRCoT retrieval
    # ------------------------------------------------------------------

    async def _execute_ircot_retrieval(
        self,
        request: OrchestrationRequest,
        plan_result: SmartPlanResult,
        processing_stats: Dict[str, Any],
    ) -> Optional[RAGContext]:
        step_start = time.time()
        logger.info(
            f"🔄 IRCoT retrieval (complexity={plan_result.complexity}, score={plan_result.complexity_score})"
        )

        try:
            extracted_filters = plan_result.extracted_filters
            should_use_graph = False
            graph_context = None
            pipeline_result = None

            if hasattr(request, "use_knowledge_graph") and request.use_knowledge_graph:
                should_use_graph = True
            elif plan_result and plan_result.use_knowledge_graph:
                should_use_graph = True

            complexity_score = getattr(plan_result, "complexity_score", 7.0)
            ircot_max_iterations = 3 if complexity_score >= 7.0 else 2

            if should_use_graph and self.verification_pipeline is not None:
                graph_task = self.verification_pipeline.run(request.user_query)
                ircot_task = self.ircot_service.reason_with_retrieval(
                    query=request.user_query,
                    initial_context=None,
                    extracted_filters=extracted_filters,
                    max_iterations_override=ircot_max_iterations,
                )

                graph_start = time.time()
                pipeline_result, ircot_result = await asyncio.gather(graph_task, ircot_task)
                parallel_time = time.time() - graph_start

                processing_stats.update(
                    graph_reasoning_time=parallel_time,
                    graph_nodes_found=pipeline_result.kg_result.record_count if pipeline_result.kg_result else 0,
                    graph_confidence=pipeline_result.confidence,
                    verification_passed=pipeline_result.success,
                )
                if pipeline_result.success and pipeline_result.structured_answer:
                    graph_context = pipeline_result.structured_answer.natural_language
                elif pipeline_result.kg_result and pipeline_result.kg_result.records:
                    graph_context = "Dữ liệu từ Knowledge Graph:\n" + "\n".join(
                        str(r.data) for r in pipeline_result.kg_result.records[:10]
                    )
            elif should_use_graph and self.verification_pipeline is None:
                logger.warning("⚠️ KG unavailable in IRCoT — vector only")
                processing_stats["kg_unavailable_warning"] = True
                ircot_result = await self.ircot_service.reason_with_retrieval(
                    query=request.user_query,
                    initial_context=None,
                    extracted_filters=extracted_filters,
                    max_iterations_override=ircot_max_iterations,
                )
            else:
                ircot_result = await self.ircot_service.reason_with_retrieval(
                    query=request.user_query,
                    initial_context=None,
                    extracted_filters=extracted_filters,
                    max_iterations_override=ircot_max_iterations,
                )

            # Stats
            processing_stats.update(
                ircot_mode=True,
                ircot_time=time.time() - step_start,
                ircot_iterations=ircot_result.total_iterations,
                ircot_early_stopped=ircot_result.early_stopped,
                ircot_confidence=ircot_result.final_confidence,
                ircot_documents_accumulated=len(ircot_result.accumulated_context),
                ircot_queries_used=ircot_result.get_all_search_queries(),
                use_knowledge_graph=should_use_graph,
                use_vector_search=plan_result.use_vector_search if plan_result else True,
                complexity=plan_result.complexity if plan_result else "complex",
                strategy=plan_result.strategy if plan_result else "ircot",
            )
            if should_use_graph and pipeline_result:
                processing_stats["verification_pipeline_used"] = True

            # Map accumulated context
            mapped_documents = []
            for idx, doc in enumerate(ircot_result.accumulated_context):
                text_content = doc.get("text", doc.get("content", ""))
                doc_metadata = doc.get("metadata", doc.get("meta", {}))
                mapped_documents.append({
                    "content": text_content,
                    "score": doc.get("score", 0.0),
                    "metadata": doc_metadata,
                    "title": doc.get("title", doc_metadata.get("title", f"Document {idx+1}")),
                    "source": doc.get("source", doc_metadata.get("source", "Unknown")),
                    "ircot_iteration": doc.get("ircot_iteration", idx // self.ircot_config.retrieval_top_k + 1),
                })

            # IRCoT reasoning summary
            if ircot_result.final_reasoning:
                mapped_documents.insert(0, {
                    "content": f"[Chain-of-Thought Reasoning]\n{ircot_result.final_reasoning}",
                    "score": 1.0,
                    "metadata": {"source_type": "ircot_reasoning"},
                    "title": "IRCoT Reasoning Summary",
                    "source": "IRCoT Chain-of-Thought",
                })

            # Graph context
            if graph_context:
                mapped_documents.insert(0, {
                    "content": graph_context,
                    "score": 1.0,
                    "metadata": {"source_type": "graph_reasoning"},
                    "title": "Graph Reasoning Context",
                    "source": "Knowledge Graph",
                })

            logger.info(
                f"✅ IRCoT done: {ircot_result.total_iterations} iterations, {len(mapped_documents)} docs"
            )

            return RAGContext(
                query=request.user_query,
                retrieved_documents=mapped_documents,
                search_metadata={
                    "ircot_mode": True,
                    "ircot_iterations": ircot_result.total_iterations,
                    "ircot_queries": ircot_result.get_all_search_queries(),
                    "ircot_reasoning": ircot_result.final_reasoning,
                    "ircot_confidence": ircot_result.final_confidence,
                    "filters_applied": extracted_filters.to_dict() if extracted_filters else None,
                },
                relevance_scores=[doc.get("score", 0.0) for doc in mapped_documents],
                rewritten_queries=ircot_result.get_all_search_queries(),
            )
        except Exception as e:
            processing_stats.update(ircot_error=str(e), ircot_time=time.time() - step_start)
            logger.error(f"IRCoT failed, falling back to standard retrieval: {e}")
            return await self._execute_standard_retrieval(request, plan_result, processing_stats)

    # ------------------------------------------------------------------
    # Standard retrieval (fallback from IRCoT)
    # ------------------------------------------------------------------

    async def _execute_standard_retrieval(
        self,
        request: OrchestrationRequest,
        plan_result: Optional[SmartPlanResult],
        processing_stats: Dict[str, Any],
    ) -> Optional[RAGContext]:
        step_start = time.time()
        try:
            search_queries = plan_result.rewritten_queries if plan_result else [request.user_query]
            top_k = plan_result.top_k if plan_result and plan_result.top_k > 0 else request.rag_top_k
            extracted_filters = plan_result.extracted_filters if plan_result else None
            use_rerank = plan_result.reranking if plan_result else True

            rag_data = await self._perform_rag_retrieval(search_queries, top_k, extracted_filters, use_rerank)
            processing_stats.update(
                rag_time=time.time() - step_start,
                documents_retrieved=len(rag_data.get("retrieved_documents", [])),
            )
            mapped_documents = self._map_rag_documents(rag_data)
            return RAGContext(
                query=request.user_query,
                retrieved_documents=mapped_documents,
                search_metadata=rag_data.get("search_metadata"),
                relevance_scores=rag_data.get("relevance_scores", []),
                rewritten_queries=search_queries,
            )
        except Exception as e:
            processing_stats["retrieval_error"] = str(e)
            logger.error(f"Standard retrieval also failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Low-level RAG retrieval
    # ------------------------------------------------------------------

    async def _perform_rag_retrieval(
        self,
        queries: List[str],
        top_k: int,
        extracted_filters: Optional[ExtractedFilters] = None,
        use_rerank: bool = True,
    ) -> Dict[str, Any]:
        rag_filters = None
        if extracted_filters and not extracted_filters.is_empty():
            rag_filters = RAGFilters(
                doc_types=extracted_filters.doc_types or None,
                legal_domains=extracted_filters.legal_domains or None,
                years=extracted_filters.years or None,
                legal_references=extracted_filters.legal_references or None,
            )

        async def _retrieve_one(query: str) -> List[Dict[str, Any]]:
            try:
                result = await self.rag_port.retrieve_context(
                    query, top_k=top_k, filters=rag_filters,
                    use_rerank=use_rerank, need_citation=True, include_char_spans=True,
                )
                return result.get("retrieved_documents", []) if result else []
            except Exception as e:
                logger.warning(f"Query failed: {query[:50]}… — {e}")
                return []

        results_per_query = await asyncio.gather(*[_retrieve_one(q) for q in queries])
        all_results = [doc for docs in results_per_query for doc in docs]
        unique_results = self._deduplicate_documents(all_results)
        top_results = unique_results[:top_k]

        return {
            "retrieved_documents": top_results,
            "search_metadata": {
                "queries_used": len(queries),
                "total_results_found": len(all_results),
                "unique_results": len(unique_results),
                "final_results": len(top_results),
                "filters_applied": extracted_filters.to_dict() if extracted_filters else None,
            },
            "relevance_scores": [doc.get("score", 0.0) for doc in top_results],
        }

    # ------------------------------------------------------------------
    # Document helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not documents:
            return []
        unique, seen = [], set()
        for doc in documents:
            sig = doc.get("text", doc.get("content", ""))[:100].strip().lower()
            if sig and sig not in seen:
                seen.add(sig)
                unique.append(doc)
        return sorted(unique, key=lambda x: x.get("score", 0.0), reverse=True)

    @staticmethod
    def _map_rag_documents(rag_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        mapped = []
        for idx, doc in enumerate(rag_data.get("retrieved_documents", [])):
            text_content = doc.get("text", doc.get("content", ""))
            doc_metadata = doc.get("metadata", doc.get("meta", {}))
            mapped.append({
                "content": text_content,
                "score": doc.get("score", 0.0),
                "metadata": doc_metadata,
                "title": doc.get("title", doc_metadata.get("title", f"Document {idx+1}")),
                "source": doc.get("source", doc_metadata.get("source", "Unknown")),
            })
        return mapped

    # ------------------------------------------------------------------
    # Step 3 — Answer generation
    # ------------------------------------------------------------------

    async def _execute_answer_step(
        self,
        request: OrchestrationRequest,
        rag_context: Optional[RAGContext],
        processing_stats: Dict[str, Any],
    ) -> Optional[AnswerResult]:
        import os

        step_start = time.time()
        try:
            if os.getenv("LOG_LEVEL", "INFO").upper() == "DEBUG":
                logger.debug(
                    f"\n{'='*80}\n💡 STEP 3: ANSWER GENERATION\n{'='*80}\n"
                    f"Query: {request.user_query}\n"
                    f"Documents: {len(rag_context.retrieved_documents) if rag_context else 0}"
                )

            answer_input = {
                "query": request.user_query,
                "context_documents": rag_context.retrieved_documents if rag_context else [],
                "rewritten_queries": rag_context.rewritten_queries if rag_context else [],
                "previous_context": "",
            }
            answer_result = await self.answer_agent.process(answer_input)
            processing_stats.update(
                answer_generation_time=time.time() - step_start,
                answer_confidence=answer_result.confidence,
                sources_used=len(answer_result.sources_used),
            )
            return answer_result
        except Exception as e:
            processing_stats.update(answer_generation_error=str(e), answer_generation_time=time.time() - step_start)
            logger.error(f"Answer generation failed: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _count_llm_calls(self, stats: Dict[str, Any]) -> int:
        calls = 0
        if "planning_time" in stats and "planning_error" not in stats:
            calls += 1
        if "answer_generation_time" in stats and "answer_generation_error" not in stats:
            calls += 1
        if "ircot_iterations" in stats:
            calls += stats["ircot_iterations"]
        return calls

    def _get_pipeline_steps_info(self) -> Dict[str, Any]:
        base_calls = 2
        max_ircot = self.ircot_config.max_iterations if self.ircot_config.enabled else 0
        return {
            "pipeline_type": (
                "optimized_2_agents_with_ircot" if self.ircot_config.enabled else "optimized_2_agents_direct"
            ),
            "steps_enabled": {
                "smart_planning": self.enable_planning and self.smart_planner is not None,
                "rag_retrieval": True,
                "ircot_retrieval": self.ircot_config.enabled,
                "answer_generation": True,
                "built_in_formatting": True,
            },
            "agents_used": {
                "smart_planner": self.smart_planner.get_agent_info() if self.smart_planner else None,
                "answer_agent": self.answer_agent.get_agent_info(),
            },
            "ircot_config": {
                "enabled": self.ircot_config.enabled,
                "mode": self.ircot_config.mode.value,
                "max_iterations": self.ircot_config.max_iterations,
                "complexity_threshold": self.ircot_config.complexity_threshold,
                "early_stopping_enabled": self.ircot_config.early_stopping_enabled,
            },
            "cost_info": {
                "base_llm_calls": base_calls,
                "max_ircot_calls": max_ircot,
                "savings_vs_original": "60% fewer calls",
            },
        }

    async def health_check(self) -> Dict[str, Any]:
        health: Dict[str, Any] = {
            "optimized_orchestrator": "healthy",
            "pipeline_type": (
                "optimized_2_agents_with_ircot" if self.ircot_config.enabled else "optimized_2_agents_direct"
            ),
            "timestamp": datetime.now().isoformat(),
            "ircot_enabled": self.ircot_config.enabled,
        }

        try:
            health["agent_service"] = "healthy" if await self.agent_port.validate_connection() else "unhealthy"
        except Exception as e:
            health["agent_service"] = f"error: {e}"

        try:
            health["rag_service"] = "healthy" if await self.rag_port.health_check() else "unhealthy"
        except Exception as e:
            health["rag_service"] = f"error: {e}"

        health["agents"] = {
            "smart_planner": {
                "model": self.smart_planner.config.model if self.smart_planner else "N/A",
                "status": "configured" if self.smart_planner else "not_configured",
            },
            "answer_agent": {
                "model": self.answer_agent.config.model,
                "status": "configured",
                "includes_formatting": True,
            },
        }
        issues = [k for k, v in health.items() if isinstance(v, str) and ("unhealthy" in v or "error:" in v)]
        health["overall"] = "healthy" if not issues else "degraded"
        return health
