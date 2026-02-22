"""Chat agents — package-by-feature structure."""

from .base import (
    SpecializedAgent,
    AgentConfig,
    AgentType,
    AnswerResult,
)
from .smart_planner import SmartPlannerAgent, SmartPlanResult, ExtractedFilters
from .answer import AnswerAgent
from .orchestrator import OptimizedMultiAgentOrchestrator

# Backward compat — ResponseFormatterAgent is deprecated but still importable
from .response_formatter_agent import ResponseFormatterAgent, FormattedResponseResult

__all__ = [
    "SpecializedAgent",
    "AgentConfig",
    "AgentType",
    "AnswerResult",
    "SmartPlannerAgent",
    "SmartPlanResult",
    "ExtractedFilters",
    "AnswerAgent",
    "OptimizedMultiAgentOrchestrator",
    # Deprecated
    "ResponseFormatterAgent",
    "FormattedResponseResult",
]
