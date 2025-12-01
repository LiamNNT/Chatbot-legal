"""
Answer Agent implementation.

This agent generates comprehensive answers based on retrieved context and user queries.
Uses Qwen3 Coder model for structured reasoning and answer generation.

Enhanced with:
- Detailed source citations with char_spans
- Document metadata (doc_type, faculty, year, subject)
"""

import json
from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, AnswerResult, DetailedSource


class AnswerAgent(SpecializedAgent):
    """
    Answer Agent responsible for generating comprehensive answers from context.
    
    This agent:
    1. Analyzes retrieved documents and context
    2. Synthesizes information from multiple sources
    3. Generates structured, comprehensive answers
    4. Provides reasoning steps and source citations
    5. Handles Vietnamese academic language appropriately
    """
    
    def __init__(self, config: AgentConfig, agent_port):
        """
        Initialize the Answer Agent.
        
        Args:
            config: Agent configuration containing model settings and parameters
            agent_port: Port for communicating with the underlying LLM
        """
        super().__init__(config, agent_port)
        
        # Extract agent-specific parameters from config
        params = getattr(config, 'parameters', {})
        self.min_answer_length = params.get('min_answer_length', 50)
        self.max_sources = params.get('max_sources', 5)
        self.confidence_thresholds = params.get('confidence_thresholds', {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        })
    
    async def process(self, input_data: Dict[str, Any]) -> AnswerResult:
        """
        Generate comprehensive answer from context and query.
        
        Args:
            input_data: Dictionary containing:
                - query: str - User query
                - context_documents: List[Dict] - Retrieved documents
                - rewritten_queries: Optional[List[str]] - Alternative queries
                - previous_context: Optional[str] - Conversation context
        
        Returns:
            AnswerResult containing the generated answer and metadata
        """
        query = input_data.get("query", "")
        context_documents = input_data.get("context_documents", [])
        rewritten_queries = input_data.get("rewritten_queries", [])
        previous_context = input_data.get("previous_context", "")
        
        # Build the answer generation prompt
        prompt = self._build_answer_prompt(query, context_documents, rewritten_queries, previous_context)
        
        # Get response from the agent
        response = await self._make_agent_request(prompt)
        
        # Parse the response
        try:
            answer_data = json.loads(response.content)
            return self._create_answer_result(answer_data, query)
        except json.JSONDecodeError:
            # Fallback to extracting answer from text response
            return self._create_fallback_answer(query, response.content, context_documents)
    
    def _build_answer_prompt(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        rewritten_queries: List[str],
        previous_context: str
    ) -> str:
        """Build the comprehensive answer generation prompt."""
        # System prompt from config already contains all instructions
        # Just provide the data: query, documents, context
        prompt_parts = [f"Query: {query}"]
        
        if rewritten_queries:
            prompt_parts.append(f"Query Variations: {', '.join(rewritten_queries)}")
        
        if previous_context:
            prompt_parts.append(f"Context: {previous_context}")
        
        # Add context documents with full content
        if context_documents:
            prompt_parts.append("\nDocuments:")
            for i, doc in enumerate(context_documents, 1):
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")
                score = doc.get("score", 0.0)
                
                prompt_parts.append(f"[{i}] {title} (Score: {score:.2f})")
                prompt_parts.append(content)
        
        return "\n".join(prompt_parts)
        
        return "\n".join(prompt_parts)
    
    def _create_answer_result(self, answer_data: Dict[str, Any], original_query: str) -> AnswerResult:
        """Create AnswerResult from parsed JSON data."""
        return AnswerResult(
            query=original_query,
            answer=answer_data.get("answer", ""),
            confidence=answer_data.get("confidence", 0.5),
            sources_used=answer_data.get("sources_used", []),
            reasoning_steps=answer_data.get("reasoning_steps", []),
            metadata=answer_data.get("metadata", {}),
            detailed_sources=[]  # JSON response doesn't include detailed sources
        )
    
    def _create_fallback_answer(
        self, 
        query: str, 
        response_content: str, 
        context_documents: List[Dict[str, Any]]
    ) -> AnswerResult:
        """Create fallback answer when JSON parsing fails."""
        # Extract the main answer from response content
        answer = self._extract_answer_from_text(response_content)
        
        # Determine confidence based on context quality
        confidence = self._estimate_confidence(context_documents, answer)
        
        # Extract sources from context documents using configured max_sources
        sources_used = [
            doc.get("title", f"Document {i+1}")
            for i, doc in enumerate(context_documents[:self.max_sources])
        ]
        
        # Create detailed sources with citation information
        detailed_sources = self._create_detailed_sources(context_documents[:self.max_sources])
        
        return AnswerResult(
            query=query,
            answer=answer,
            confidence=confidence,
            sources_used=sources_used,
            reasoning_steps=["Sử dụng thông tin từ tài liệu tham khảo", "Tổng hợp và phân tích nội dung"],
            metadata={
                "fallback": True,
                "method": "text_extraction",
                "original_length": len(response_content)
            },
            detailed_sources=detailed_sources
        )
    
    def _create_detailed_sources(self, context_documents: List[Dict[str, Any]]) -> List[DetailedSource]:
        """
        Create detailed source citations from context documents.
        
        Args:
            context_documents: List of retrieved documents with citation data
            
        Returns:
            List of DetailedSource objects with citation information
        """
        detailed_sources = []
        
        for doc in context_documents:
            # Get basic info
            title = doc.get("title", "Unknown")
            score = doc.get("score", 0.0)
            
            # Get document ID and chunk info
            meta = doc.get("meta", doc.get("metadata", {}))
            doc_id = meta.get("doc_id")
            chunk_id = meta.get("chunk_id")
            
            # Get citation data
            citation = doc.get("citation", {})
            char_spans = doc.get("char_spans", [])
            highlighted_text = doc.get("highlighted_text", [])
            
            # If citation is a dict, extract char_spans from it
            if isinstance(citation, dict):
                if not char_spans and citation.get("char_spans"):
                    char_spans = citation.get("char_spans", [])
                if not highlighted_text and citation.get("highlighted_text"):
                    highlighted_text = citation.get("highlighted_text", [])
            
            # Get document classification
            doc_type = doc.get("doc_type")
            faculty = doc.get("faculty")
            year = doc.get("year")
            subject = doc.get("subject")
            
            # Create citation text from highlighted spans or first char_span
            citation_text = None
            if highlighted_text:
                citation_text = highlighted_text[0] if isinstance(highlighted_text, list) else highlighted_text
            elif char_spans and isinstance(char_spans, list) and len(char_spans) > 0:
                first_span = char_spans[0]
                if isinstance(first_span, dict):
                    citation_text = first_span.get("text", "")
            
            detailed_source = DetailedSource(
                title=title,
                doc_id=doc_id,
                chunk_id=chunk_id,
                score=score,
                citation_text=citation_text,
                char_spans=char_spans if char_spans else None,
                highlighted_text=highlighted_text if highlighted_text else None,
                doc_type=doc_type,
                faculty=faculty,
                year=year,
                subject=subject
            )
            
            detailed_sources.append(detailed_source)
        
        return detailed_sources
    
    def _extract_answer_from_text(self, text: str) -> str:
        """Extract the main answer from text response."""
        # Clean up the response text
        lines = text.strip().split('\n')
        answer_lines = []
        
        # Skip JSON markers or system messages
        for line in lines:
            line = line.strip()
            if line and not line.startswith('{') and not line.startswith('}'):
                if not line.startswith('"') or line.endswith('",'):
                    answer_lines.append(line)
        
        if answer_lines:
            answer = ' '.join(answer_lines)
        else:
            answer = text.strip()
        
        # Ensure minimum answer length using configured threshold
        if len(answer) < self.min_answer_length:
            answer = f"Dựa trên thông tin có sẵn: {answer}"
        
        return answer
    
    def _estimate_confidence(self, context_documents: List[Dict[str, Any]], answer: str) -> float:
        """Estimate confidence based on context quality and answer characteristics."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence based on number of relevant documents
        if context_documents:
            doc_count = len(context_documents)
            confidence += min(0.2, doc_count * 0.05)
            
            # Check document relevance scores
            avg_score = sum(doc.get("score", 0) for doc in context_documents) / doc_count
            confidence += avg_score * 0.3
        
        # Boost confidence based on answer length and structure
        if len(answer) > 100:
            confidence += 0.1
        
        if any(keyword in answer.lower() for keyword in ["uit", "trường", "đại học", "quy định"]):
            confidence += 0.1
        
        # Cap confidence at reasonable levels
        return min(0.95, max(0.1, confidence))
    
    def _analyze_answer_type(self, query: str, answer: str) -> str:
        """Analyze the type of answer generated."""
        query_lower = query.lower()
        answer_lower = answer.lower()
        
        # Procedural answers (how-to questions)
        if any(word in query_lower for word in ["làm thế nào", "hướng dẫn", "cách", "thủ tục", "quy trình"]):
            return "procedural"
        
        # Comparative answers
        if any(word in query_lower for word in ["so sánh", "khác nhau", "giống", "phân biệt"]):
            return "comparative"
        
        # Informative answers (default)
        return "informative"
    
    def _assess_completeness(self, answer: str, context_documents: List[Dict[str, Any]]) -> str:
        """Assess the completeness of the generated answer."""
        if not context_documents:
            return "insufficient_data"
        
        # Basic heuristics for completeness using configured thresholds
        min_partial_length = self.min_answer_length * 2  # 2x minimum for partial
        min_complete_length = self.min_answer_length * 6  # 6x minimum for complete
        
        if len(answer) < min_partial_length:
            return "partial"
        
        # Check if answer addresses multiple aspects
        aspect_indicators = ["đầu tiên", "thứ hai", "cuối cùng", "ngoài ra", "bên cạnh đó"]
        if any(indicator in answer.lower() for indicator in aspect_indicators):
            return "complete"
        
        return "partial" if len(answer) < min_complete_length else "complete"