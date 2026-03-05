"""
Ctx AI Core Backend Module

This module contains the core business logic for the Ctx AI framework,
including agent definitions, model configurations, and core utilities.
"""

from .agent import Agent, AgentConfig, AgentContext, AgentContextType, UserMessage
from .models import (
    BrowserCompatibleChatWrapper,
    LiteLLMChatWrapper,
    LiteLLMEmbeddingWrapper,
    ModelConfig,
    ModelType,
    get_browser_model,
    get_chat_model,
    get_embedding_model,
)

__all__ = [
    "Agent",
    "AgentContext",
    "AgentContextType",
    "AgentConfig",
    "UserMessage",
    "ModelConfig",
    "ModelType",
    "LiteLLMChatWrapper",
    "LiteLLMEmbeddingWrapper",
    "BrowserCompatibleChatWrapper",
    "get_chat_model",
    "get_embedding_model",
    "get_browser_model",
]
