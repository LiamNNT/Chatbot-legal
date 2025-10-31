"""
Verifier Agent implementation.

This agent verifies the accuracy and quality of generated answers.
Uses DeepSeek R1 model for critical thinking and verification.
"""

import json
from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, VerificationResult


class VerifierAgent(SpecializedAgent):
    """
    Verifier Agent responsible for quality assurance and fact-checking.
    
    This agent:
    1. Evaluates answer accuracy against source documents
    2. Checks logical consistency and completeness
    3. Identifies potential errors or misleading information
    4. Provides improvement suggestions
    5. Assigns confidence scores and reliability ratings
    """
    
    async def process(self, input_data: Dict[str, Any]) -> VerificationResult:
        """
        Verify the quality and accuracy of a generated answer.
        
        Args:
            input_data: Dictionary containing:
                - query: str - Original user query
                - answer: str - Generated answer to verify
                - context_documents: List[Dict] - Source documents used
                - reasoning_steps: Optional[List[str]] - Answer generation steps
                - confidence: Optional[float] - Original confidence score
        
        Returns:
            VerificationResult containing verification analysis
        """
        query = input_data.get("query", "")
        answer = input_data.get("answer", "")
        context_documents = input_data.get("context_documents", [])
        reasoning_steps = input_data.get("reasoning_steps", [])
        original_confidence = input_data.get("confidence", 0.5)
        
        # Build the verification prompt
        prompt = self._build_verification_prompt(
            query, answer, context_documents, reasoning_steps, original_confidence
        )
        
        # Get response from the agent
        response = await self._make_agent_request(prompt)
        
        # Parse the response
        try:
            verification_data = json.loads(response.content)
            return self._create_verification_result(verification_data, query, answer)
        except json.JSONDecodeError:
            # Fallback to rule-based verification
            return self._create_fallback_verification(query, answer, context_documents, response.content)
    
    def _build_verification_prompt(
        self,
        query: str,
        answer: str,
        context_documents: List[Dict[str, Any]],
        reasoning_steps: List[str],
        original_confidence: float
    ) -> str:
        """Build the comprehensive verification prompt."""
        # System prompt from config contains all verification instructions
        # Just provide the data to verify
        prompt_parts = [
            f"Query: {query}",
            f"\nAnswer to verify:\n{answer}",
            f"\nOriginal confidence: {original_confidence:.2f}"
        ]
        
        if reasoning_steps:
            prompt_parts.append(f"\nReasoning: {'; '.join(reasoning_steps)}")
        
        if context_documents:
            prompt_parts.append("\nSource Documents:")
            for i, doc in enumerate(context_documents, 1):
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")[:800]  # First 800 chars for verification
                prompt_parts.append(f"[{i}] {title}: {content}")
        
        return "\n".join(prompt_parts)
    
    def _create_verification_result(
        self, 
        verification_data: Dict[str, Any], 
        original_query: str, 
        answer: str
    ) -> VerificationResult:
        """Create VerificationResult from parsed JSON data."""
        return VerificationResult(
            original_query=original_query,
            answer=answer,
            is_accurate=verification_data.get("is_accurate", True),
            confidence=verification_data.get("confidence", 0.5),
            issues_found=verification_data.get("issues_found", []),
            suggestions=verification_data.get("suggestions", []),
            metadata=verification_data.get("metadata", {})
        )
    
    def _create_fallback_verification(
        self,
        query: str,
        answer: str,
        context_documents: List[Dict[str, Any]],
        response_content: str
    ) -> VerificationResult:
        """Create fallback verification when JSON parsing fails."""
        # Apply rule-based verification
        issues = self._identify_basic_issues(answer, context_documents)
        suggestions = self._generate_basic_suggestions(answer, issues)
        
        # Estimate accuracy based on basic heuristics
        is_accurate = len(issues) == 0
        confidence = max(0.3, 0.8 - len(issues) * 0.1)
        
        return VerificationResult(
            original_query=query,
            answer=answer,
            is_accurate=is_accurate,
            confidence=confidence,
            issues_found=issues,
            suggestions=suggestions,
            metadata={
                "fallback": True,
                "method": "rule_based",
                "original_response": response_content[:300],
                "basic_checks_performed": True
            }
        )
    
    def _identify_basic_issues(self, answer: str, context_documents: List[Dict[str, Any]]) -> List[str]:
        """Identify basic issues using rule-based approach."""
        issues = []
        
        # Check answer length
        if len(answer.strip()) < 30:
            issues.append("Câu trả lời quá ngắn, thiếu thông tin chi tiết")
        
        # Check if answer is too generic
        generic_phrases = ["tùy thuộc vào", "có thể", "thường thì", "nói chung"]
        if sum(phrase in answer.lower() for phrase in generic_phrases) > 3:
            issues.append("Câu trả lời quá chung chung, thiếu thông tin cụ thể")
        
        # Check for contradiction indicators
        contradiction_indicators = ["tuy nhiên", "nhưng", "mặt khác", "ngược lại"]
        contradictions = sum(indicator in answer.lower() for indicator in contradiction_indicators)
        if contradictions > 2:
            issues.append("Có dấu hiệu mâu thuẫn trong câu trả lời")
        
        # Check if context documents were utilized
        if context_documents and not self._check_context_utilization(answer, context_documents):
            issues.append("Có vẻ không sử dụng đầy đủ thông tin từ tài liệu tham khảo")
        
        return issues
    
    def _check_context_utilization(self, answer: str, context_documents: List[Dict[str, Any]]) -> bool:
        """Check if the answer appropriately uses context documents."""
        if not context_documents:
            return True
        
        answer_lower = answer.lower()
        
        # Look for specific terms from context documents
        for doc in context_documents[:3]:  # Check top 3 documents
            content = doc.get("content", "").lower()
            
            # Extract key terms from document (simple approach)
            doc_words = set(content.split())
            answer_words = set(answer_lower.split())
            
            # Check overlap
            common_words = doc_words.intersection(answer_words)
            significant_words = [w for w in common_words if len(w) > 4]
            
            if len(significant_words) > 2:
                return True
        
        return False
    
    def _generate_basic_suggestions(self, answer: str, issues: List[str]) -> List[str]:
        """Generate basic improvement suggestions."""
        suggestions = []
        
        if any("ngắn" in issue for issue in issues):
            suggestions.append("Cung cấp thêm chi tiết và ví dụ cụ thể")
        
        if any("chung chung" in issue for issue in issues):
            suggestions.append("Bổ sung thông tin cụ thể như số liệu, quy định, thủ tục")
        
        if any("mâu thuẫn" in issue for issue in issues):
            suggestions.append("Kiểm tra và làm rõ các thông tin có vẻ trái ngược nhau")
        
        if any("tài liệu" in issue for issue in issues):
            suggestions.append("Tham khảo và trích dẫn rõ ràng hơn từ tài liệu nguồn")
        
        # Default suggestions if no specific issues
        if not suggestions:
            suggestions.extend([
                "Có thể bổ sung ví dụ minh họa để làm rõ thông tin",
                "Xem xét cung cấp thêm thông tin về các bước thực hiện cụ thể"
            ])
        
        return suggestions
    
    def _calculate_quality_scores(self, answer: str, issues: List[str], context_documents: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate quality scores for different aspects."""
        base_score = 0.8
        
        # Accuracy score (penalized by issues)
        accuracy_score = max(0.1, base_score - len(issues) * 0.15)
        
        # Completeness score (based on length and structure)
        completeness_score = min(1.0, len(answer) / 300)  # Assume 300 chars = complete
        if any(indicator in answer.lower() for indicator in ["đầu tiên", "thứ hai", "cuối cùng"]):
            completeness_score += 0.1
        
        # Clarity score (based on structure and readability)
        clarity_score = base_score
        if len(answer.split('.')) > 1:  # Multiple sentences
            clarity_score += 0.1
        if any("ví dụ" in answer.lower() for _ in [1]):  # Contains examples
            clarity_score += 0.1
        
        return {
            "accuracy_score": min(1.0, accuracy_score),
            "completeness_score": min(1.0, completeness_score),
            "clarity_score": min(1.0, clarity_score)
        }