"""LLM Player Agent Module.

This module provides an AI opponent powered by AWS Bedrock (Claude).
The agent uses a set of tools to observe the game state, make decisions,
and submit orders while respecting fog-of-war constraints.
"""

from .llm_player import LLMPlayer

__all__ = ["LLMPlayer"]
