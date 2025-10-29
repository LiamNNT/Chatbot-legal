"""
Query Rewriter Agent implementation.

This agent optimizes user queries for better search performance in the RAG system.
Uses Meituan LongCat Flash Chat model for query optimization.
"""

import json
from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, QueryRewriteResult


class QueryRewriterAgent(SpecializedAgent):
    """
    Query Rewriter Agent responsible for optimizing queries for search.
    
    This agent:
    1. Analyzes the original query structure and intent
    2. Rewrites queries to improve search effectiveness
    3. Generates alternative search terms and phrases
    4. Maintains semantic meaning while improving searchability
    5. Handles Vietnamese language nuances specific to UIT context
    """
    
    async def process(self, input_data: Dict[str, Any]) -> QueryRewriteResult:
        """
        Process and rewrite user query for optimal search.
        
        Args:
            input_data: Dictionary containing:
                - query: str - Original user query
                - intent: Optional[str] - Detected intent from planner
                - context: Optional[Dict] - Additional context
                - search_history: Optional[List] - Previous search queries
        
        Returns:
            QueryRewriteResult containing optimized queries and search terms
        """
        query = input_data.get("query", "")
        intent = input_data.get("intent", "")
        context = input_data.get("context", {})
        search_history = input_data.get("search_history", [])
        
        # Build the optimization prompt
        prompt = self._build_optimization_prompt(query, intent, context, search_history)
        
        # Get response from the agent
        response = await self._make_agent_request(prompt)
        
        # Parse the response
        try:
            rewrite_data = json.loads(response.content)
            return self._create_rewrite_result(rewrite_data, query)
        except json.JSONDecodeError:
            # Fallback to rule-based rewriting if JSON parsing fails
            return self._create_fallback_rewrite(query, response.content)
    
    def _build_optimization_prompt(
        self,
        query: str,
        intent: str,
        context: Dict[str, Any],
        search_history: List[str]
    ) -> str:
        """Build the optimization prompt for query rewriting."""
        prompt_parts = [
            f"TỐI ƯU CÂU HỎI: {query}",
            ""
        ]
        
        if intent:
            prompt_parts.append(f"Ý ĐỊNH PHÁT HIỆN: {intent}")
            prompt_parts.append("")
        
        if context:
            prompt_parts.append("THÔNG TIN NGỮ CẢNH:")
            prompt_parts.append(f"{json.dumps(context, ensure_ascii=False, indent=2)}")
            prompt_parts.append("")
        
        if search_history:
            prompt_parts.append("LỊCH SỬ TÌM KIẾM:")
            for i, prev_query in enumerate(search_history[-3:], 1):  # Last 3 queries
                prompt_parts.append(f"{i}. {prev_query}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "NHIỆM VỤ:",
            "1. Phân tích câu hỏi và xác định ý định chính",
            "2. Viết lại câu hỏi thành 3-5 biến thể tối ưu cho tìm kiếm",
            "3. Trích xuất từ khóa và thuật ngữ quan trọng",
            "4. Đảm bảo phù hợp với ngữ cảnh UIT",
            "5. Trả về kết quả dạng JSON theo định dạng đã cho",
            "",
            "LƯU Ý ĐẶC BIỆT:",
            "- Xử lý thuật ngữ UIT: ĐKMT (Đăng ký môn tín), ĐHQG-HCM, etc.",
            "- Bổ sung từ đồng nghĩa: học phần = môn học = subject",
            "- Tối ưu cho tìm kiếm: ngắn gọn, rõ ràng, đầy đủ từ khóa",
            "- Giữ nguyên ý nghĩa gốc của câu hỏi"
        ])
        
        return "\n".join(prompt_parts)
    
    def _create_rewrite_result(self, rewrite_data: Dict[str, Any], original_query: str) -> QueryRewriteResult:
        """Create QueryRewriteResult from parsed JSON data."""
        return QueryRewriteResult(
            original_query=original_query,
            rewritten_queries=rewrite_data.get("rewritten_queries", []),
            search_terms=rewrite_data.get("search_terms", []),
            intent_preserved=rewrite_data.get("intent_preserved", True),
            confidence=rewrite_data.get("confidence", 0.7),
            metadata=rewrite_data.get("metadata", {})
        )
    
    def _create_fallback_rewrite(self, query: str, response_content: str) -> QueryRewriteResult:
        """Create fallback rewrite result when JSON parsing fails."""
        # Apply rule-based query optimization
        rewritten_queries = self._apply_rule_based_rewriting(query)
        search_terms = self._extract_keywords(query)
        
        return QueryRewriteResult(
            original_query=query,
            rewritten_queries=rewritten_queries,
            search_terms=search_terms,
            intent_preserved=True,
            confidence=0.5,
            metadata={
                "fallback": True,
                "method": "rule_based",
                "original_response": response_content[:200]
            }
        )
    
    def _apply_rule_based_rewriting(self, query: str) -> List[str]:
        """Apply rule-based query rewriting as fallback."""
        query_lower = query.lower()
        rewritten = []
        
        # Original query (cleaned)
        cleaned_query = self._clean_query(query)
        if cleaned_query != query:
            rewritten.append(cleaned_query)
        
        # Add UIT-specific variations
        uit_variations = self._add_uit_variations(query_lower)
        rewritten.extend(uit_variations)
        
        # Add keyword-focused version
        keywords = self._extract_keywords(query)
        if keywords:
            keyword_query = " ".join(keywords)
            if keyword_query not in rewritten:
                rewritten.append(keyword_query)
        
        # Ensure we have at least one rewrite
        if not rewritten:
            rewritten = [query]
        
        return rewritten[:5]  # Maximum 5 variations
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query."""
        # Remove question words that don't help with search
        question_words = [
            "làm thế nào để", "làm sao để", "hướng dẫn", 
            "cho tôi biết", "tôi muốn biết", "bạn có thể",
            "xin hỏi", "có thể cho biết"
        ]
        
        cleaned = query
        for phrase in question_words:
            cleaned = cleaned.replace(phrase, "").strip()
        
        return cleaned if cleaned else query
    
    def _add_uit_variations(self, query: str) -> List[str]:
        """Add UIT-specific query variations."""
        variations = []
        
        # UIT terminology mappings
        uit_mappings = {
            "trường": ["UIT", "Đại học Công nghệ Thông tin", "ĐHQG-HCM"],
            "học phần": ["môn học", "subject", "course"],
            "đăng ký": ["ĐKMT", "đăng ký môn tín", "enrollment"],
            "học phí": ["chi phí học tập", "tuition fee", "học bổng"],
            "nhập học": ["tuyển sinh", "admission", "thủ tục nhập học"],
            "quy định": ["quy chế", "regulation", "policy", "thể lệ"]
        }
        
        # Apply mappings
        for original, alternatives in uit_mappings.items():
            if original in query:
                for alt in alternatives:
                    variation = query.replace(original, alt)
                    if variation != query and variation not in variations:
                        variations.append(variation)
        
        return variations[:3]  # Limit to 3 variations
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Vietnamese stop words (simplified list)
        stop_words = {
            "là", "của", "và", "có", "trong", "với", "để", "về", "tại", "từ",
            "này", "đó", "những", "các", "một", "hai", "ba", "như", "được",
            "sẽ", "đã", "đang", "thì", "nếu", "khi", "mà", "hay", "hoặc"
        }
        
        # UIT-specific important terms
        important_terms = {
            "uit", "đhqg", "hcm", "đăng ký", "học phần", "môn học", "tín chỉ",
            "học phí", "nhập học", "tuyển sinh", "khoa", "ngành", "chuyên ngành",
            "đại học", "thạc sĩ", "tiến sĩ", "quy định", "thủ tục", "hướng dẫn"
        }
        
        # Tokenize and filter
        words = query.lower().replace(",", " ").replace(".", " ").split()
        keywords = []
        
        for word in words:
            word = word.strip("?!.,;:")
            if (len(word) > 2 and 
                word not in stop_words and 
                (word in important_terms or not word.isdigit())):
                keywords.append(word)
        
        return keywords[:10]  # Limit to 10 keywords