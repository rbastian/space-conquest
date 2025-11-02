"""Middleware for LangGraph agent lifecycle management.

Provides middleware components for:
- Context management (message trimming, token tracking)
- Threat assessment (updating threat level based on observations)
- Error recovery (graceful fallbacks when tools fail)
- Tool result processing (enhancing tool outputs with additional context)
"""

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, trim_messages

from .state_models import AgentState, GameContext

logger = logging.getLogger(__name__)


# Maximum messages to keep in history before trimming
MAX_MESSAGES = 20
# Token budget for message history (approximate)
MAX_TOKENS = 8000


def trim_message_history(state: AgentState) -> AgentState:
    """Trim message history to prevent unbounded growth.

    Uses LangChain's trim_messages utility to keep recent messages
    while staying under token budget.

    Args:
        state: Current agent state

    Returns:
        Updated state with trimmed messages
    """
    messages = state["messages"]

    if len(messages) <= 4:  # System + initial user message + response + result
        return state

    logger.debug(f"Trimming message history: {len(messages)} messages")

    # Trim messages but keep system message and recent context
    # We want to preserve:
    # - Recent observations (last 2-3 tool results)
    # - Recent assistant reasoning
    # - Current turn context
    trimmed = trim_messages(
        messages,
        max_tokens=MAX_TOKENS,
        strategy="last",  # Keep most recent messages
        token_counter=len,  # Simple character count (good enough)
        include_system=False,  # We'll add system separately
        start_on="human",  # Ensure valid conversation structure
    )

    logger.debug(f"Trimmed to {len(trimmed)} messages")

    return {**state, "messages": trimmed}


def assess_threat_level(game_context: GameContext) -> Literal["low", "medium", "high", "critical"]:
    """Assess threat level based on enemy proximity and strength.

    Args:
        game_context: Current game context with enemy information

    Returns:
        Threat level: low, medium, high, or critical
    """
    nearest_enemy = game_context.get("nearest_enemy_distance")

    if nearest_enemy is None:
        # No enemy stars known yet - low threat (early game)
        return "low"

    # Critical: Enemy within striking distance (1-2 parsecs from home)
    if nearest_enemy <= 2:
        return "critical"

    # High: Enemy nearby (3-4 parsecs)
    if nearest_enemy <= 4:
        return "high"

    # Medium: Enemy known but distant (5-6 parsecs)
    if nearest_enemy <= 6:
        return "medium"

    # Low: Enemy far away (7+ parsecs)
    return "low"


def update_game_context_from_observation(
    observation: dict, turn: int, home_star_id: str
) -> GameContext:
    """Extract game context from observation data.

    This function analyzes the observation to determine:
    - Game phase (early/mid/late based on turn)
    - Threat level (based on enemy proximity)
    - Strategic metrics (production, ships, stars)

    Args:
        observation: Observation dict from get_observation tool
        turn: Current turn number
        home_star_id: Player's home star ID

    Returns:
        GameContext with analyzed information
    """
    # Determine game phase
    if turn <= 10:
        phase = "early"
    elif turn <= 30:
        phase = "mid"
    else:
        phase = "late"

    # Extract strategic dashboard
    dashboard = observation.get("strategic_dashboard", {})
    controlled_stars = dashboard.get("controlled_stars_count", 1)
    total_production = dashboard.get("total_production_per_turn", 4)
    total_ships = dashboard.get("total_ships", 4)

    # Find home garrison
    home_garrison = 0
    for star in observation.get("stars", []):
        if star.get("is_home"):
            home_garrison = star.get("stationed_ships") or 0
            break

    # Find nearest enemy star
    nearest_enemy_distance = None
    enemy_stars_known = 0

    for star in observation.get("stars", []):
        if star.get("owner") == "p1":  # Enemy (from p2's perspective)
            enemy_stars_known += 1
            distance = star.get("distance_from_home")
            if distance is not None:
                if nearest_enemy_distance is None or distance < nearest_enemy_distance:
                    nearest_enemy_distance = distance

    # Build context
    context: GameContext = {
        "turn": turn,
        "game_phase": phase,
        "threat_level": "low",  # Will be updated below
        "controlled_stars_count": controlled_stars,
        "total_production": total_production,
        "total_ships": total_ships,
        "enemy_stars_known": enemy_stars_known,
        "nearest_enemy_distance": nearest_enemy_distance,
        "home_garrison": home_garrison,
        "orders_submitted": False,
    }

    # Assess threat level
    context["threat_level"] = assess_threat_level(context)

    logger.debug(
        f"Game context: phase={phase}, threat={context['threat_level']}, "
        f"enemy_distance={nearest_enemy_distance}, stars={controlled_stars}, "
        f"ships={total_ships}"
    )

    return context


def handle_tool_error(state: AgentState, error: Exception, tool_name: str) -> AgentState:
    """Handle tool execution errors with graceful recovery.

    Tracks error counts and provides helpful error messages to the LLM
    so it can adjust its strategy.

    Args:
        state: Current agent state
        error: Exception that occurred
        tool_name: Name of the tool that failed

    Returns:
        Updated state with error information
    """
    error_count = state.get("error_count", 0) + 1
    error_msg = f"Tool '{tool_name}' failed: {str(error)}"

    logger.warning(f"Tool error (#{error_count}): {error_msg}")

    # Circuit breaker: After 5 errors, suggest passing turn
    if error_count >= 5:
        error_msg += (
            "\n\nMultiple tool errors detected. Consider submitting empty orders "
            "to pass this turn and try again next turn."
        )
        logger.error("Circuit breaker triggered: too many consecutive errors")

    # Add error message to conversation
    error_message = HumanMessage(content=f"Error: {error_msg}\n\nPlease try a different approach.")

    return {
        **state,
        "error_count": error_count,
        "last_error": error_msg,
        "messages": [*state["messages"], error_message],
    }


def reset_error_tracking(state: AgentState) -> AgentState:
    """Reset error tracking after successful tool execution.

    Args:
        state: Current agent state

    Returns:
        Updated state with reset error counts
    """
    if state.get("error_count", 0) > 0:
        logger.debug("Resetting error tracking after successful tool execution")

    return {**state, "error_count": 0, "last_error": None}


def filter_tools_by_game_state(state: AgentState) -> list[str]:
    """Determine which tools should be available based on game state.

    This implements dynamic tool filtering to prevent the LLM from
    making invalid tool calls based on the current situation.

    Rules:
    - Turn 1: Don't show memory_query (no history yet)
    - After orders submitted: Don't show submit_orders again
    - Always available: get_observation, query_star, estimate_route,
      get_ascii_map, propose_orders

    Args:
        state: Current agent state

    Returns:
        List of tool names that should be available
    """
    game_context = state.get("game_context")
    if not game_context:
        # No context yet, return all tools (initial state)
        return [
            "get_observation",
            "get_ascii_map",
            "query_star",
            "estimate_route",
            "propose_orders",
            "submit_orders",
            "memory_query",
        ]

    # Base tools always available
    tools = [
        "get_observation",
        "get_ascii_map",
        "query_star",
        "estimate_route",
        "propose_orders",
    ]

    # Add submit_orders only if not already submitted
    if not game_context.get("orders_submitted", False):
        tools.append("submit_orders")

    # Add memory_query only after turn 1 (need history to query)
    if game_context.get("turn", 1) > 1:
        tools.append("memory_query")

    return tools


def enhance_observation_context(observation: dict, game_context: GameContext) -> str:
    """Enhance observation with contextual insights.

    Adds a brief analysis of the observation based on the current
    game context to help guide the LLM's decision-making.

    Args:
        observation: Raw observation dict
        game_context: Current game context

    Returns:
        Enhanced observation with contextual notes
    """
    insights = []

    # Threat level insights
    threat = game_context.get("threat_level")
    if threat == "critical":
        insights.append("CRITICAL THREAT: Enemy very close to home! Prioritize home defense.")
    elif threat == "high":
        insights.append("HIGH THREAT: Enemy nearby. Consider defensive positioning.")
    elif threat == "low" and game_context.get("game_phase") == "early":
        insights.append("Early game, low threat. Focus on aggressive expansion.")

    # Production insights
    production = game_context.get("total_production", 0)
    stars = game_context.get("controlled_stars_count", 1)
    if production < stars * 2:  # Less than average RU per star
        insights.append(
            f"Low production ({production}/turn from {stars} stars). "
            "Prioritize capturing high-RU stars."
        )

    if insights:
        return "\n\nTactical Analysis:\n- " + "\n- ".join(insights)

    return ""
