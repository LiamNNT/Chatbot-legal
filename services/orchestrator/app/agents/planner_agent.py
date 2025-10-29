"""
Planner Agent implementation.

This agent analyzes user queries and creates execution plans for the multi-agent system.
Uses DeepSeek V3.1 model for planning and reasoning.
"""

from typing import Dict, Any, List
from ..agents.base import SpecializedAgent, AgentConfig, AgentType, PlanResult, PlanStep
from ..core.planner_domain_service import PlannerDomainService


class PlannerAgent(SpecializedAgent):
    """
    Planner Agent responsible for analyzing queries and creating execution plans.
    
    This agent:
    1. Analyzes user intent and query complexity
    2. Determines the best approach for handling the query
    3. Creates a step-by-step execution plan
    4. Estimates resource requirements
    """
    
    def __init__(self, config: AgentConfig, agent_port):
        """
        Initialize the Planner Agent.
        
        Args:
            config: Agent configuration containing model settings and parameters
            agent_port: Port for communicating with the underlying LLM
        """
        super().__init__(config, agent_port)
        
        # Extract agent-specific parameters from config
        self.complexity_thresholds = getattr(config, 'parameters', {}).get('complexity_thresholds', {
            'simple_max_length': 50,
            'complex_min_length': 100
        })
        self.plan_templates = getattr(config, 'parameters', {}).get('plan_templates', {})
    
    async def process(self, input_data: Dict[str, Any]) -> PlanResult:
        """
        Process user query and create execution plan.
        
        Args:
            input_data: Dictionary containing:
                - query: str - User query to analyze
                - context: Optional[Dict] - Additional context
                - user_profile: Optional[Dict] - User information
        
        Returns:
            PlanResult containing the execution plan
        """
        query = input_data.get("query", "")
        
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(query)
        
        # Get response from the agent
        response = await self._make_agent_request(prompt)
        
        # Use domain service to parse response (no JSON dependency)
        domain_service = PlannerDomainService()
        return domain_service.parse_plan_response(response, query)
    
    def _build_analysis_prompt(self, query: str) -> str:
        """Build prompt for query analysis."""
        return f"""Hãy phân tích câu hỏi sau và tạo kế hoạch xử lý chi tiết:

Câu hỏi: {query}

Hãy đưa ra một phân tích toàn diện về:
1. Ý định của người dùng
2. Độ phức tạp của câu hỏi  
3. Các bước cần thực hiện để trả lời
4. Tài nguyên cần thiết

Trả lời bằng tiếng Việt một cách tự nhiên và chi tiết."""
    
    def _create_plan_result(self, plan_data: Dict[str, Any], original_query: str) -> PlanResult:
        """Create PlanResult from parsed JSON data."""
        steps = []
        
        for step_data in plan_data.get("steps", []):
            step = PlanStep(
                step_id=str(step_data.get("step_id", "")),
                action=step_data.get("action", ""),
                description=step_data.get("description", ""),
                dependencies=step_data.get("dependencies", []),
                parameters=step_data.get("parameters", {})
            )
            steps.append(step)
        
        return PlanResult(
            query=original_query,
            intent=plan_data.get("intent", "unknown"),
            complexity=plan_data.get("complexity", "medium"),
            steps=steps,
            estimated_tokens=plan_data.get("estimated_tokens", 500),
            requires_verification=plan_data.get("requires_verification", True),
            metadata=plan_data.get("metadata", {})
        )
    
    def _create_fallback_plan(self, query: str, response_content: str) -> PlanResult:
        """Create a fallback plan when JSON parsing fails."""
        # Determine complexity based on query length and keywords
        complexity = self._estimate_complexity(query)
        
        # Create basic steps based on complexity
        steps = self._create_basic_steps(complexity)
        
        return PlanResult(
            query=query,
            intent="information_request",
            complexity=complexity,
            steps=steps,
            estimated_tokens=500,
            requires_verification=complexity != "simple",
            metadata={
                "fallback": True,
                "original_response": response_content[:200],
                "confidence": 0.5
            }
        )
    
    def _estimate_complexity(self, query: str) -> str:
        """Estimate query complexity based on heuristics and configuration."""
        query_lower = query.lower()
        
        # Use configured thresholds
        simple_max_length = self.complexity_thresholds.get('simple_max_length', 50)
        complex_min_length = self.complexity_thresholds.get('complex_min_length', 100)
        
        # Simple queries
        simple_patterns = [
            "xin chào", "hello", "hi", "cảm ơn", "thank", 
            "tạm biệt", "bye", "ok", "được", "vâng"
        ]
        
        if any(pattern in query_lower for pattern in simple_patterns) or len(query) <= simple_max_length:
            return "simple"
        
        # Complex queries
        complex_patterns = [
            "so sánh", "phân tích", "đánh giá", "hướng dẫn chi tiết",
            "quy trình", "thủ tục", "các bước", "làm thế nào"
        ]
        
        if any(pattern in query_lower for pattern in complex_patterns) or len(query) >= complex_min_length:
            return "complex"
        
        return "medium"
    
    def _create_basic_steps(self, complexity: str) -> List[PlanStep]:
        """Create basic steps based on complexity and configuration templates."""
        # Try to use configured templates first
        if self.plan_templates and complexity in self.plan_templates:
            template_steps = self.plan_templates[complexity]
            steps = []
            for i, template in enumerate(template_steps, 1):
                step = PlanStep(
                    step_id=str(i),
                    action=template.get("action", "unknown"),
                    description=template.get("description", f"Execute {template.get('action', 'action')}"),
                    dependencies=template.get("dependencies", [] if i == 1 else [str(i-1)]),
                    parameters=template.get("parameters", {})
                )
                steps.append(step)
            return steps
        
        # Fallback to hardcoded templates
        if complexity == "simple":
            return [
                PlanStep(
                    step_id="1",
                    action="direct_response",
                    description="Trả lời trực tiếp câu hỏi đơn giản",
                    dependencies=[],
                    parameters={"use_rag": False}
                )
            ]
        
        elif complexity == "complex":
            return [
                PlanStep(
                    step_id="1",
                    action="rewrite_query",
                    description="Viết lại câu hỏi để tối ưu tìm kiếm",
                    dependencies=[],
                    parameters={}
                ),
                PlanStep(
                    step_id="2", 
                    action="retrieve_context",
                    description="Tìm kiếm thông tin liên quan",
                    dependencies=["1"],
                    parameters={"top_k": 7, "use_hybrid": True}
                ),
                PlanStep(
                    step_id="3",
                    action="generate_answer",
                    description="Sinh câu trả lời dựa trên context",
                    dependencies=["2"],
                    parameters={}
                ),
                PlanStep(
                    step_id="4",
                    action="verify_answer",
                    description="Kiểm tra chất lượng câu trả lời",
                    dependencies=["3"],
                    parameters={}
                ),
                PlanStep(
                    step_id="5",
                    action="format_response",
                    description="Định dạng phản hồi cuối cùng",
                    dependencies=["4"],
                    parameters={}
                )
            ]
        
        else:  # medium
            return [
                PlanStep(
                    step_id="1",
                    action="retrieve_context", 
                    description="Tìm kiếm thông tin liên quan",
                    dependencies=[],
                    parameters={"top_k": 5}
                ),
                PlanStep(
                    step_id="2",
                    action="generate_answer",
                    description="Sinh câu trả lời dựa trên context",
                    dependencies=["1"],
                    parameters={}
                ),
                PlanStep(
                    step_id="3",
                    action="format_response",
                    description="Định dạng phản hồi cuối cùng",
                    dependencies=["2"],
                    parameters={}
                )
            ]