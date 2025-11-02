"""LangGraph state management models for the agent.

Defines the state structure used throughout the agent's decision-making
process, including game context, threat assessment, and conversation history.
"""

from typing import Any, Literal, TypedDict

from langchain_core.messages import BaseMessage


class GameContext(TypedDict):
    """Runtime context about the game state.

    This captures strategic information derived from observations
    that helps guide decision-making and system prompt generation.
    """

    turn: int
    game_phase: Literal["early", "mid", "late"]  # Derived from turn number
    threat_level: Literal["low", "medium", "high", "critical"]  # Derived from enemy proximity

    # Strategic metrics (from observation)
    controlled_stars_count: int
    total_production: int
    total_ships: int

    # Tactical situation
    enemy_stars_known: int  # Number of enemy-controlled stars we know about
    nearest_enemy_distance: int | None  # Distance to nearest known enemy star
    home_garrison: int  # Ships stationed at home star

    # Decision state
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

    # Tool filtering state
    available_tools: list[str]  # Which tools are available based on game state

    # Error recovery state
    error_count: int  # Track consecutive errors for circuit breaker
    last_error: str | None  # Most recent error message

    # Internal: AgentTools instance for tool execution (set by get_orders)
    # Note: Using Any to avoid circular import; actual type is AgentTools
    _tools_instance: Any  # Private field for internal use
