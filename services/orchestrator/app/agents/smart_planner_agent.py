"""
Smart Planner Agent implementation.

This agent combines the functionality of Planner and Query Rewriter agents
into a single optimized agent to reduce LLM calls.

Merged from:
- PlannerAgent: Query analysis, complexity scoring, execution planning
- QueryRewriterAgent: Query optimization, abbreviation expansion, UIT context
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..agents.base import SpecializedAgent, AgentConfig, AgentType


@dataclass
class SmartPlanResult:
    """Result from the Smart Planner agent (combined planning + query rewriting)."""
    # Planning fields
    query: str
    intent: str
    complexity: str  # "simple", "medium", "complex"
    complexity_score: float
    requires_rag: bool
    strategy: str  # "direct_response", "standard_rag", "advanced_rag"
    
    # Query rewriting fields
    rewritten_queries: List[str]
    search_terms: List[str]
    
    # RAG parameters
    top_k: int
    hybrid_search: bool
    reranking: bool
    
    # Metadata
    reasoning: str
    confidence: float
    metadata: Dict[str, Any]


class SmartPlannerAgent(SpecializedAgent):
    """
    Smart Planner Agent - Optimized combination of Planner + Query Rewriter.
    
    This agent performs in a single LLM call:
    1. Intent classification
    2. Complexity scoring (0-10 scale)
    3. Strategy determination (direct/standard_rag/advanced_rag)
    4. Query rewriting and optimization
    5. Search term extraction
    
    Cost optimization: Reduces 2 LLM calls to 1 LLM call.
    """
    
    # UIT-specific abbreviation mappings for fallback
    UIT_ABBREVIATIONS = {
        "hp": "học phần",
        "đkhp": "đăng ký học phần",
        "khmt": "khoa học máy tính",
        "cntt": "công nghệ thông tin",
        "httt": "hệ thống thông tin",
        "mmt": "mạng máy tính và truyền thông",
        "mmtt": "mạng máy tính và truyền thông",
        "sv": "sinh viên",
        "gv": "giảng viên",
        "đtbc": "điểm trung bình chung",
        "ctđt": "chương trình đào tạo",
        "uit": "đại học công nghệ thông tin",
        "đhqg": "đại học quốc gia",
        "hcm": "hồ chí minh",
    }
    
    # Complexity thresholds
    SIMPLE_MAX_SCORE = 3.5
    COMPLEX_MIN_SCORE = 6.5
    
    def __init__(self, config: AgentConfig, agent_port):
        """
        Initialize the Smart Planner Agent.
        
        Args:
            config: Agent configuration containing model settings and parameters
            agent_port: Port for communicating with the underlying LLM
        """
        super().__init__(config, agent_port)
        
        # Extract agent-specific parameters from config
        params = getattr(config, 'parameters', {}) or {}
        self.complexity_thresholds = params.get('complexity_thresholds', {
            'simple_max': 3.5,
            'complex_min': 6.5
        })
        self.default_top_k = params.get('default_top_k', 5)
        self.max_rewritten_queries = params.get('max_rewritten_queries', 3)
    
    async def process(self, input_data: Dict[str, Any]) -> SmartPlanResult:
        """
        Process user query and create combined plan with optimized queries.
        
        Args:
            input_data: Dictionary containing:
                - query: str - User query to analyze
                - context: Optional[Dict] - Additional context
                - user_profile: Optional[Dict] - User information
        
        Returns:
            SmartPlanResult containing planning + query rewriting results
        """
        query = input_data.get("query", "")
        
        # Quick check for very simple queries (no LLM needed)
        simple_result = self._check_simple_query(query)
        if simple_result:
            return simple_result
        
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(query)
        
        # Get response from the agent (single LLM call)
        response = await self._make_agent_request(prompt)
        
        # Parse and return result
        return self._parse_response(response.content, query)
    
    def _check_simple_query(self, query: str) -> Optional[SmartPlanResult]:
        """
        Check if query is simple enough to handle without LLM.
        
        Returns SmartPlanResult for simple queries, None otherwise.
        """
        query_lower = query.lower().strip()
        
        # Social/greeting patterns
        social_patterns = [
            "xin chào", "hello", "hi", "chào", "cảm ơn", "thanks", "thank you",
            "tạm biệt", "bye", "ok", "được", "vâng", "dạ", "ừ", "oke"
        ]
        
        for pattern in social_patterns:
            if query_lower == pattern or query_lower.startswith(pattern + " "):
                return SmartPlanResult(
                    query=query,
                    intent="social_greeting",
                    complexity="simple",
                    complexity_score=0.0,
                    requires_rag=False,
                    strategy="direct_response",
                    rewritten_queries=[],
                    search_terms=[],
                    top_k=0,
                    hybrid_search=False,
                    reranking=False,
                    reasoning="Detected social/greeting query, no RAG needed",
                    confidence=1.0,
                    metadata={"rule_based": True, "pattern_matched": pattern}
                )
        
        return None
    
    def _build_analysis_prompt(self, query: str) -> str:
        """Build prompt for combined analysis and query rewriting."""
        # System prompt already contains all instructions from config
        # Just pass the user's query directly
        return query
    
    def _parse_response(self, response_content: str, original_query: str) -> SmartPlanResult:
        """Parse LLM response into SmartPlanResult."""
        try:
            # Try to parse JSON response
            data = json.loads(response_content)
            return self._create_result_from_json(data, original_query)
        except json.JSONDecodeError:
            # Fallback to rule-based analysis
            return self._create_fallback_result(original_query, response_content)
    
    def _create_result_from_json(self, data: Dict[str, Any], original_query: str) -> SmartPlanResult:
        """Create SmartPlanResult from parsed JSON data."""
        complexity_score = data.get("complexity_score", 5.0)
        complexity = data.get("complexity", self._score_to_complexity(complexity_score))
        requires_rag = data.get("requires_rag", True)
        
        # Determine RAG parameters based on complexity
        if complexity == "simple" or not requires_rag:
            top_k = 0
            hybrid_search = False
            reranking = False
        elif complexity == "complex":
            top_k = data.get("top_k", 10)
            hybrid_search = data.get("hybrid_search", True)
            reranking = data.get("reranking", True)
        else:  # medium
            top_k = data.get("top_k", 5)
            hybrid_search = data.get("hybrid_search", False)
            reranking = False
        
        return SmartPlanResult(
            query=original_query,
            intent=data.get("intent", "informational"),
            complexity=complexity,
            complexity_score=complexity_score,
            requires_rag=requires_rag,
            strategy=data.get("strategy", "standard_rag"),
            rewritten_queries=data.get("rewritten_queries", [original_query]),
            search_terms=data.get("search_terms", self._extract_keywords(original_query)),
            top_k=top_k,
            hybrid_search=hybrid_search,
            reranking=reranking,
            reasoning=data.get("reasoning", ""),
            confidence=0.85,
            metadata={"source": "llm_response"}
        )
    
    def _create_fallback_result(self, query: str, response_content: str) -> SmartPlanResult:
        """Create fallback result using rule-based analysis."""
        # Estimate complexity
        complexity_score = self._estimate_complexity_score(query)
        complexity = self._score_to_complexity(complexity_score)
        
        # Determine if RAG is needed
        requires_rag = complexity != "simple"
        
        # Generate rewritten queries
        rewritten_queries = self._apply_rule_based_rewriting(query) if requires_rag else []
        
        # Extract search terms
        search_terms = self._extract_keywords(query) if requires_rag else []
        
        # Determine RAG parameters
        if complexity == "simple":
            top_k, hybrid_search, reranking = 0, False, False
            strategy = "direct_response"
        elif complexity == "complex":
            top_k, hybrid_search, reranking = 10, True, True
            strategy = "advanced_rag"
        else:
            top_k, hybrid_search, reranking = 5, False, False
            strategy = "standard_rag"
        
        return SmartPlanResult(
            query=query,
            intent=self._detect_intent(query),
            complexity=complexity,
            complexity_score=complexity_score,
            requires_rag=requires_rag,
            strategy=strategy,
            rewritten_queries=rewritten_queries,
            search_terms=search_terms,
            top_k=top_k,
            hybrid_search=hybrid_search,
            reranking=reranking,
            reasoning="Fallback to rule-based analysis",
            confidence=0.6,
            metadata={
                "fallback": True,
                "original_response": response_content[:200]
            }
        )
    
    def _score_to_complexity(self, score: float) -> str:
        """Convert complexity score to label."""
        if score <= self.SIMPLE_MAX_SCORE:
            return "simple"
        elif score >= self.COMPLEX_MIN_SCORE:
            return "complex"
        return "medium"
    
    def _estimate_complexity_score(self, query: str) -> float:
        """Estimate complexity score using heuristics."""
        score = 5.0  # Default medium
        query_lower = query.lower()
        
        # Simple indicators (reduce score)
        simple_patterns = ["xin chào", "hello", "cảm ơn", "tạm biệt", "ok"]
        if any(p in query_lower for p in simple_patterns):
            return 1.0
        
        # Short queries tend to be simpler
        if len(query) < 20:
            score -= 2.0
        elif len(query) < 40:
            score -= 1.0
        
        # Complex indicators (increase score)
        complex_patterns = [
            "so sánh", "phân tích", "đánh giá", "quy trình chi tiết",
            "hướng dẫn", "các bước", "làm thế nào", "khác biệt"
        ]
        if any(p in query_lower for p in complex_patterns):
            score += 2.5
        
        # Multiple question indicators
        if query.count("?") > 1:
            score += 1.0
        
        # Long queries tend to be more complex
        if len(query) > 100:
            score += 1.5
        elif len(query) > 60:
            score += 0.5
        
        return max(0, min(10, score))  # Clamp to 0-10
    
    def _detect_intent(self, query: str) -> str:
        """Detect query intent using rule-based approach."""
        query_lower = query.lower()
        
        # Social
        if any(p in query_lower for p in ["xin chào", "hello", "cảm ơn", "tạm biệt"]):
            return "social_greeting"
        
        # Comparative
        if any(p in query_lower for p in ["so sánh", "khác biệt", "giống nhau", "vs"]):
            return "comparative"
        
        # Procedural
        if any(p in query_lower for p in ["cách", "làm sao", "thế nào", "quy trình", "hướng dẫn"]):
            return "procedural"
        
        # Informational (default)
        return "informational"
    
    def _apply_rule_based_rewriting(self, query: str) -> List[str]:
        """Apply rule-based query rewriting."""
        query_lower = query.lower()
        rewritten = []
        
        # Expand abbreviations
        expanded = query_lower
        for abbr, full in self.UIT_ABBREVIATIONS.items():
            if abbr in expanded:
                expanded = expanded.replace(abbr, full)
        
        if expanded != query_lower:
            rewritten.append(expanded)
        
        # Add UIT context if not present
        if "uit" not in query_lower and "đại học công nghệ" not in query_lower:
            rewritten.append(f"{query} tại UIT")
        
        # Original query as fallback
        if query not in rewritten:
            rewritten.insert(0, query)
        
        return rewritten[:self.max_rewritten_queries]
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query."""
        # Vietnamese stop words
        stop_words = {
            "là", "của", "và", "có", "trong", "với", "để", "về", "tại", "từ",
            "này", "đó", "những", "các", "một", "như", "được", "sẽ", "đã",
            "đang", "thì", "nếu", "khi", "mà", "hay", "hoặc", "gì", "nào"
        }
        
        # Important UIT terms
        important_terms = {
            "uit", "đhqg", "học phần", "môn học", "tín chỉ", "học phí",
            "tuyển sinh", "khoa", "ngành", "quy định", "thủ tục", "đăng ký",
            "tốt nghiệp", "điều kiện", "điểm", "sinh viên", "giảng viên"
        }
        
        # Tokenize and filter
        words = query.lower().replace(",", " ").replace(".", " ").split()
        keywords = []
        
        for word in words:
            word = word.strip("?!.,;:")
            if len(word) > 2 and word not in stop_words:
                keywords.append(word)
        
        return keywords[:10]
