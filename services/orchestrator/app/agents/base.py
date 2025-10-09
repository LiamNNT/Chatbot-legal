"""
Base classes and interfaces for specialized agents.

This module defines the base agent interface and common functionality
for all specialized agents in the multi-agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..core.domain import AgentRequest, AgentResponse
from ..ports.agent_ports import AgentPort


class AgentType(Enum):
    """Types of specialized agents."""
    PLANNER = "planner"
    QUERY_REWRITER = "query_rewriter"
    ANSWER_AGENT = "answer_agent"
    VERIFIER = "verifier"
    RESPONSE_AGENT = "response_agent"


@dataclass
class AgentConfig:
    """Configuration for a specialized agent."""
    agent_type: AgentType
    model: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    max_retries: int = 3
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_id: str
    action: str
    description: str
    dependencies: List[str]
    parameters: Dict[str, Any]


@dataclass
class PlanResult:
    """Result from the planner agent."""
    query: str
    intent: str
    complexity: str  # "simple", "medium", "complex"
    steps: List[PlanStep]
    estimated_tokens: int
    requires_verification: bool
    metadata: Dict[str, Any]


@dataclass
class QueryRewriteResult:
    """Result from query rewriter agent."""
    original_query: str
    rewritten_queries: List[str]
    search_terms: List[str]
    intent_preserved: bool
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class AnswerResult:
    """Result from answer agent."""
    query: str
    answer: str
    confidence: float
    sources_used: List[str]
    reasoning_steps: List[str]
    metadata: Dict[str, Any]


@dataclass
class VerificationResult:
    """Result from verifier agent."""
    original_query: str
    answer: str
    is_accurate: bool
    confidence: float
    issues_found: List[str]
    suggestions: List[str]
    metadata: Dict[str, Any]


@dataclass
class ResponseResult:
    """Result from response agent."""
    final_response: str
    tone: str
    completeness_score: float
    user_friendliness_score: float
    metadata: Dict[str, Any]


class SpecializedAgent(ABC):
    """
    Base class for all specialized agents.
    
    This class provides common functionality and defines the interface
    that all specialized agents must implement.
    """
    
    def __init__(self, config: AgentConfig, agent_port: AgentPort):
        """
        Initialize the specialized agent.
        
        Args:
            config: Agent configuration
            agent_port: Port for communicating with the underlying LLM
        """
        self.config = config
        self.agent_port = agent_port
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return results.
        
        Args:
            input_data: Input data specific to the agent type
            
        Returns:
            Processing results specific to the agent type
        """
        pass
    
    async def _make_agent_request(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Make a request to the underlying agent.
        
        Args:
            prompt: The prompt to send to the agent
            context: Optional context information
            
        Returns:
            Agent response
        """
        request = AgentRequest(
            prompt=prompt,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            metadata={"agent_type": self.config.agent_type.value}
        )
        
        return await self.agent_port.generate_response(request)
    
    def _build_system_prompt(self, user_prompt: str) -> str:
        """
        Build the complete system prompt.
        
        Args:
            user_prompt: User-specific prompt content
            
        Returns:
            Complete system prompt
        """
        return f"{self.config.system_prompt}\n\n{user_prompt}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent."""
        return {
            "type": self.config.agent_type.value,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }