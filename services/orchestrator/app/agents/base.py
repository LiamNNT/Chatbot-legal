"""Backward-compat wrapper — canonical code in app.core.agents.base"""
from ..chat.agents.base import *  # noqa: F401,F403
from ..chat.agents.base import (
    AgentType, AgentConfig, SpecializedAgent,
    AnswerResult, DetailedSource,
)
