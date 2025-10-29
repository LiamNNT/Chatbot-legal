"""
Answer Agent implementation.

This agent generates comprehensive answers based on retrieved context and user queries.
Uses Qwen3 Coder model for structured reasoning and answer generation.
"""

import json
from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, AnswerResult


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
        prompt_parts = [
            f"CÂU HỎI CẦN TRẢ LỜI: {query}",
            ""
        ]
        
        # Add rewritten queries if available
        if rewritten_queries:
            prompt_parts.append("CÁC BIẾN THỂ CÂU HỎI:")
            for i, rq in enumerate(rewritten_queries, 1):
                prompt_parts.append(f"{i}. {rq}")
            prompt_parts.append("")
        
        # Add previous conversation context
        if previous_context:
            prompt_parts.append("NGỮ CẢNH CUỘC TRÒ CHUYỆN:")
            prompt_parts.append(previous_context)
            prompt_parts.append("")
        
        # Add context documents
        if context_documents:
            prompt_parts.append("TÀI LIỆU THAM KHẢO:")
            for i, doc in enumerate(context_documents, 1):
                title = doc.get("title", f"Tài liệu {i}")
                content = doc.get("content", "")
                score = doc.get("score", 0.0)
                source = doc.get("source", "Unknown")
                
                prompt_parts.append(f"[{i}] {title} (Score: {score:.2f}, Source: {source})")
                prompt_parts.append(f"Nội dung: {content[:1000]}...")  # Limit content length
                prompt_parts.append("")
        else:
            prompt_parts.append("KHÔNG CÓ TÀI LIỆU THAM KHẢO CỤ THỂ")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "NHIỆM VỤ:",
            "1. Phân tích tất cả thông tin được cung cấp",
            "2. Tạo câu trả lời đầy đủ, chính xác và có cấu trúc",
            "3. Sử dụng thông tin từ tài liệu tham khảo làm bằng chứng",
            "4. Cung cấp các bước suy luận rõ ràng",
            "5. Trả về kết quả dạng JSON theo định dạng đã cho",
            "",
            "YÊU CẦU ĐẶC BIỆT:",
            "- Ưu tiên thông tin chính thức từ UIT",
            "- Cung cấp thông tin hành động cụ thể (các bước, thủ tục, quy định)",
            "- Sử dụng ngôn ngữ phù hợp với sinh viên đại học",
            "- Thừa nhận khi thông tin không đủ để trả lời đầy đủ",
            "- Đảm bảo JSON output hợp lệ và đầy đủ"
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_answer_result(self, answer_data: Dict[str, Any], original_query: str) -> AnswerResult:
        """Create AnswerResult from parsed JSON data."""
        return AnswerResult(
            query=original_query,
            answer=answer_data.get("answer", ""),
            confidence=answer_data.get("confidence", 0.5),
            sources_used=answer_data.get("sources_used", []),
            reasoning_steps=answer_data.get("reasoning_steps", []),
            metadata=answer_data.get("metadata", {})
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
            }
        )
    
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