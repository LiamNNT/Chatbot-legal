"""
Response Agent implementation.

This agent creates final, user-friendly responses from verified answers.
Uses Meituan LongCat Flash Chat model for natural language generation.
"""

import json
from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, ResponseResult


class ResponseAgent(SpecializedAgent):
    """
    Response Agent responsible for creating final user-friendly responses.
    
    This agent:
    1. Takes verified answers and transforms them into natural responses
    2. Adapts tone and style based on user context and query type
    3. Adds appropriate greetings, closings, and helpful suggestions
    4. Ensures responses are engaging and easy to understand
    5. Maintains consistency with UIT's communication style
    """
    
    async def process(self, input_data: Dict[str, Any]) -> ResponseResult:
        """
        Create final user-friendly response from verified answer.
        
        Args:
            input_data: Dictionary containing:
                - query: str - Original user query
                - verified_answer: str - Verified answer content
                - verification_result: Dict - Verification analysis
                - user_context: Optional[Dict] - User information
                - conversation_history: Optional[List] - Previous messages
        
        Returns:
            ResponseResult containing the final formatted response
        """
        query = input_data.get("query", "")
        verified_answer = input_data.get("verified_answer", "")
        verification_result = input_data.get("verification_result", {})
        user_context = input_data.get("user_context", {})
        conversation_history = input_data.get("conversation_history", [])
        
        # Build the response generation prompt
        prompt = self._build_response_prompt(
            query, verified_answer, verification_result, user_context, conversation_history
        )
        
        # Get response from the agent
        response = await self._make_agent_request(prompt)
        
        # Parse the response
        try:
            response_data = json.loads(response.content)
            return self._create_response_result(response_data)
        except json.JSONDecodeError:
            # Fallback to extracting response from text
            return self._create_fallback_response(query, verified_answer, response.content)
    
    def _build_response_prompt(
        self,
        query: str,
        verified_answer: str,
        verification_result: Dict[str, Any],
        user_context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> str:
        """Build the response generation prompt."""
        prompt_parts = [
            "NHIỆM VỤ TẠO PHẢN HỒI CUỐI CÙNG",
            "=" * 40,
            "",
            f"CÂU HỎI CỦA NGƯỜI DÙNG: {query}",
            "",
            f"THÔNG TIN ĐÃ KIỂM CHỨNG:",
            f"{verified_answer}",
            ""
        ]
        
        # Add verification insights
        if verification_result:
            is_accurate = verification_result.get("is_accurate", True)
            confidence = verification_result.get("confidence", 0.5)
            issues = verification_result.get("issues_found", [])
            suggestions = verification_result.get("suggestions", [])
            
            prompt_parts.append(f"ĐÁNH GIÁ CHẤT LƯỢNG:")
            prompt_parts.append(f"- Độ chính xác: {'Cao' if is_accurate else 'Cần cải thiện'}")
            prompt_parts.append(f"- Độ tin cậy: {confidence:.1f}/1.0")
            
            if issues:
                prompt_parts.append("- Vấn đề cần lưu ý:")
                for issue in issues:
                    prompt_parts.append(f"  * {issue}")
            
            if suggestions:
                prompt_parts.append("- Gợi ý cải thiện:")
                for suggestion in suggestions:
                    prompt_parts.append(f"  * {suggestion}")
            
            prompt_parts.append("")
        
        # Add user context
        if user_context:
            prompt_parts.append("THÔNG TIN NGƯỜI DÙNG:")
            for key, value in user_context.items():
                prompt_parts.append(f"- {key}: {value}")
            prompt_parts.append("")
        
        # Add conversation context
        if conversation_history:
            prompt_parts.append("NGỮ CẢNH CUỘC TRÒ CHUYỆN:")
            for i, msg in enumerate(conversation_history[-3:], 1):  # Last 3 messages
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:100]
                prompt_parts.append(f"{i}. {role}: {content}...")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "YÊU CẦU TẠO PHẢN HỒI:",
            "",
            "1. PHONG CÁCH:",
            "   - Thân thiện và chuyên nghiệp",
            "   - Phù hợp với sinh viên đại học",
            "   - Tự nhiên như cuộc trò chuyện thực",
            "",
            "2. NỘI DUNG:",
            "   - Giữ nguyên tất cả thông tin factual đã kiểm chứng",
            "   - Cải thiện cách trình bày để dễ hiểu hơn",
            "   - Thêm ví dụ hoặc gợi ý nếu phù hợp",
            "   - Bao gồm lời kết và mời câu hỏi tiếp theo",
            "",
            "3. CẤU TRÚC:",
            "   - Mở đầu phù hợp với ngữ cảnh",
            "   - Nội dung chính được tổ chức rõ ràng",
            "   - Kết thúc tích cực và hỗ trợ",
            "",
            "4. LƯU Ý ĐẶC BIỆT:",
            "   - Sử dụng ngôn ngữ UIT phù hợp",
            "   - Không bịa đặt thông tin mới",
            "   - Tạo cảm giác hữu ích và đáng tin cậy",
            "",
            "5. TRẢ VỀ KẾT QUẢ JSON theo định dạng đã cho"
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_response_result(self, response_data: Dict[str, Any]) -> ResponseResult:
        """Create ResponseResult from parsed JSON data."""
        return ResponseResult(
            final_response=response_data.get("final_response", ""),
            tone=response_data.get("tone", "friendly"),
            completeness_score=response_data.get("completeness_score", 0.7),
            user_friendliness_score=response_data.get("user_friendliness_score", 0.8),
            metadata=response_data.get("metadata", {})
        )
    
    def _create_fallback_response(
        self, 
        query: str, 
        verified_answer: str, 
        response_content: str
    ) -> ResponseResult:
        """Create fallback response when JSON parsing fails."""
        # Extract the response from text content
        final_response = self._extract_response_from_text(response_content, verified_answer)
        
        # Analyze the response characteristics
        tone = self._analyze_tone(query, final_response)
        
        # Calculate scores based on heuristics
        completeness_score = self._calculate_completeness_score(final_response, verified_answer)
        user_friendliness_score = self._calculate_friendliness_score(final_response)
        
        return ResponseResult(
            final_response=final_response,
            tone=tone,
            completeness_score=completeness_score,
            user_friendliness_score=user_friendliness_score,
            metadata={
                "fallback": True,
                "method": "text_extraction",
                "word_count": len(final_response.split()),
                "includes_greeting": self._has_greeting(final_response)
            }
        )
    
    def _extract_response_from_text(self, text_content: str, verified_answer: str) -> str:
        """Extract the final response from text content."""
        # Clean the text content
        cleaned_text = text_content.strip()
        
        # If the content looks like it might be JSON fragments, try to extract
        lines = cleaned_text.split('\n')
        response_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('{') and not line.startswith('}'):
                if not line.startswith('"') or line.endswith('",'):
                    response_lines.append(line.strip('"').strip(','))
        
        if response_lines:
            final_response = ' '.join(response_lines)
        else:
            final_response = cleaned_text
        
        # If response is too short or seems invalid, enhance the verified answer
        if len(final_response) < 50 or final_response == verified_answer:
            final_response = self._enhance_answer(verified_answer)
        
        return final_response
    
    def _enhance_answer(self, verified_answer: str) -> str:
        """Enhance the verified answer with friendly formatting."""
        if not verified_answer:
            return "Xin lỗi, tôi không có đủ thông tin để trả lời câu hỏi của bạn. Bạn có thể cung cấp thêm chi tiết hoặc liên hệ trực tiếp với UIT để được hỗ trợ tốt hơn."
        
        # Add friendly opening
        enhanced = f"Dựa trên thông tin có sẵn, {verified_answer.lower()}"
        
        # Add helpful closing
        enhanced += "\n\nNếu bạn cần thêm thông tin chi tiết hoặc có câu hỏi khác về UIT, đừng ngần ngại hỏi tôi nhé!"
        
        return enhanced
    
    def _analyze_tone(self, query: str, response: str) -> str:
        """Analyze the tone of the response."""
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Greeting/casual queries
        if any(greeting in query_lower for greeting in ["xin chào", "hello", "hi", "cảm ơn"]):
            return "friendly"
        
        # Complex procedural queries
        if any(word in query_lower for word in ["hướng dẫn", "thủ tục", "quy trình", "làm thế nào"]):
            return "helpful"
        
        # Information-seeking queries
        if any(word in query_lower for word in ["thông tin", "chi tiết", "giải thích"]):
            return "informative"
        
        # Default professional tone
        return "professional"
    
    def _calculate_completeness_score(self, final_response: str, verified_answer: str) -> float:
        """Calculate completeness score based on response characteristics."""
        score = 0.5  # Base score
        
        # Length-based scoring
        if len(final_response) >= len(verified_answer):
            score += 0.2
        
        # Structure indicators
        structure_indicators = ["đầu tiên", "thứ hai", "cuối cùng", "ngoài ra", "đặc biệt"]
        if any(indicator in final_response.lower() for indicator in structure_indicators):
            score += 0.1
        
        # Helpful additions
        helpful_phrases = ["ví dụ", "lưu ý", "gợi ý", "nếu bạn cần", "có thể liên hệ"]
        if any(phrase in final_response.lower() for phrase in helpful_phrases):
            score += 0.2
        
        return min(1.0, score)
    
    def _calculate_friendliness_score(self, response: str) -> float:
        """Calculate user-friendliness score."""
        score = 0.5  # Base score
        response_lower = response.lower()
        
        # Friendly language indicators
        friendly_words = ["bạn", "chúng tôi", "hỗ trợ", "giúp đỡ", "vui lòng"]
        score += min(0.3, len([w for w in friendly_words if w in response_lower]) * 0.1)
        
        # Polite expressions
        polite_expressions = ["xin lỗi", "cảm ơn", "mong", "hy vọng", "chúc"]
        if any(expr in response_lower for expr in polite_expressions):
            score += 0.1
        
        # Encouraging closing
        encouraging_closings = ["đừng ngần ngại", "sẵn sàng hỗ trợ", "hỏi tôi", "liên hệ"]
        if any(closing in response_lower for closing in encouraging_closings):
            score += 0.1
        
        return min(1.0, score)
    
    def _has_greeting(self, response: str) -> bool:
        """Check if response includes a greeting or acknowledgment."""
        greetings = ["xin chào", "chào bạn", "cảm ơn", "chào", "dựa trên"]
        return any(greeting in response.lower() for greeting in greetings)