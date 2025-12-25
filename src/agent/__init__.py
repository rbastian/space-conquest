"""LLM Player Agent Module.

This module provides an AI opponent powered by various LLM providers
(AWS Bedrock, OpenAI, Anthropic, Ollama). The agent uses a set of tools
to observe the game state, make decisions, and submit orders while
respecting fog-of-war constraints.

Uses LangGraph StateGraph architecture with state management,
dynamic prompts, and middleware for production-ready AI gameplay.
"""

from .langgraph_player import LangGraphPlayer

__all__ = ["LangGraphPlayer"]
