"""LangGraph state management models for the agent.

Defines the state structure used throughout the agent's decision-making
process, including conversation history and order submission tracking.
"""

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class GameContext(TypedDict):
    """Runtime context about the game state.

    Tracks whether orders have been submitted for the current turn.
    """

    orders_submitted: bool


class AgentState(TypedDict):
    """Complete state for the LangGraph agent.

    This is the main state object that flows through all nodes in the graph.
    It includes both persistent data (messages) and transient context (game state).
    """

    # Conversation history - persistent across tool calls
    messages: list[BaseMessage]

    # Game context - updated each turn
    game_context: GameContext

    # Error recovery state
    error_count: int  # Track consecutive errors for circuit breaker
    last_error: str | None  # Most recent error message

    # Internal: AgentTools instance for tool execution (set by get_orders)
    # Note: Using Any to avoid circular import; actual type is AgentTools
    _tools_instance: Any  # Private field for internal use
