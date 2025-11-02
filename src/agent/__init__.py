"""LLM Player Agent Module.

This module provides an AI opponent powered by various LLM providers
(AWS Bedrock, OpenAI, Anthropic, Ollama). The agent uses a set of tools
to observe the game state, make decisions, and submit orders while
respecting fog-of-war constraints.

Two implementations are available:
- LLMPlayer: Simple stateless implementation (original)
- LangGraphPlayer: Advanced implementation with state management,
  dynamic prompts, and middleware (recommended for production)
"""

from .langgraph_player import LangGraphPlayer
from .llm_player import LLMPlayer

__all__ = ["LLMPlayer", "LangGraphPlayer"]
