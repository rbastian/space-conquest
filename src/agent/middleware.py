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
    - Game phase (early/mid/late based on strategic state, not turns)
    - Threat level (based on enemy proximity)
    - Strategic metrics (production, ships, stars)

    Game phases are state-based (like chess):
    - EARLY: No enemy contact yet (expansion phase)
    - MID: Enemy located but distant (positioning phase)
    - LATE: Enemy close or decisive battle (endgame phase)

    Args:
        observation: Observation dict from get_observation tool
        turn: Current turn number
        home_star_id: Player's home star ID

    Returns:
        GameContext with analyzed information
    """
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

    # Determine game phase based on strategic state (not turns)
    # Like chess: phases are defined by board state, not move count
    if enemy_stars_known == 0:
        # Early Game: No enemy contact yet - pure expansion phase
        phase = "early"
    elif nearest_enemy_distance is not None and nearest_enemy_distance <= 3:
        # Late Game: Enemy within striking distance - decisive battle phase
        phase = "late"
    else:
        # Mid Game: Enemy located but distant - positioning/buildup phase
        phase = "mid"

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


def inject_defensive_urgency(game_context: dict) -> str:
    """Generate dynamic defensive context based on threat level.

    Returns additional prompt text to inject when threat is elevated.
    This amplifies the importance of home defense when the LLM might
    otherwise prioritize offense.

    Args:
        game_context: Current game context with threat_level, nearest_enemy_distance, home_garrison

    Returns:
        Additional prompt text for elevated threats, empty string otherwise
    """
    threat_level = game_context.get("threat_level")
    nearest_enemy = game_context.get("nearest_enemy_distance")
    home_garrison = game_context.get("home_garrison", 0)

    # No injection needed for low/medium threat
    if threat_level not in ("high", "critical"):
        return ""

    # Build urgency message based on threat level
    if threat_level == "critical":
        # Enemy within 2 parsecs - maximum urgency
        urgency_msg = f"""

DEFENSIVE URGENCY ALERT (CRITICAL):
========================
IMMEDIATE THREAT DETECTED: Enemy forces are within {nearest_enemy} parsecs of your home star.
Current home garrison: {home_garrison} ships.

CRITICAL ACTIONS REQUIRED:
1. CALCULATE enemy strike capability from ALL enemy stars within 4 parsecs
2. VERIFY home garrison exceeds enemy strike force by at least 2 ships
3. If home is under-defended: IMMEDIATELY pull back fleets OR redirect production
4. Consider pre-emptive strikes on enemy staging bases to eliminate threat

WARNING: The enemy can reach your home in {nearest_enemy} turns. If they attack with superior force,
you will LOSE THE GAME regardless of all other achievements. Home defense is your FIRST priority.

Do NOT proceed with offensive operations until home defense gate condition is satisfied.
"""

    else:  # threat_level == "high"
        # Enemy within 3-4 parsecs - elevated urgency
        urgency_msg = f"""

DEFENSIVE URGENCY ALERT (HIGH):
========================
ELEVATED THREAT: Enemy forces detected {nearest_enemy} parsecs from your home star.
Current home garrison: {home_garrison} ships.

REQUIRED ACTIONS:
1. Calculate max enemy strike force from stars within 4 parsecs of home
2. Ensure home garrison > enemy potential strike + 2 ships buffer
3. If home garrison insufficient: adjust force deployment to prioritize home defense
4. Monitor enemy movements and prepare counter-measures

The enemy can reach your home in {nearest_enemy} turns. Losing your home = instant defeat.
Balance offensive ambitions with defensive requirements. Verify gate condition before major offensives.
"""

    return urgency_msg


def inject_threat_vector_analysis(threat_vectors: list[dict]) -> str:
    """Generate dynamic threat analysis prompt based on pre-calculated threat vectors.

    This middleware function converts the threat_vectors data from observation
    into actionable prompts that the LLM cannot ignore. It amplifies critical
    threats and provides specific defensive requirements.

    Args:
        threat_vectors: List of threat vector dicts from observation

    Returns:
        Additional prompt text injected into system context when threats exist
    """
    if not threat_vectors:
        return ""

    # Count threats by severity
    critical_threats = [t for t in threat_vectors if t.get("threat_severity") == "critical"]
    high_threats = [t for t in threat_vectors if t.get("threat_severity") == "high"]

    # Build urgency message
    urgency_lines = []

    if critical_threats:
        urgency_lines.append("\nCRITICAL THREAT ALERT:")
        urgency_lines.append("=" * 50)
        for threat in critical_threats:
            urgency_lines.append(
                f"\nENEMY POSITION: {threat['enemy_star_name']} ({threat['enemy_star_id']}) "
                f"- {threat['distance_to_home']} parsecs from home"
            )
            urgency_lines.append(f"  Estimated Force: {threat['estimated_ships']} ships")
            urgency_lines.append(f"  Can Arrive: Turn {threat['estimated_arrival_turn']}")
            urgency_lines.append(
                f"  Required Home Garrison: {threat['required_home_garrison']} ships"
            )
            urgency_lines.append(f"  Analysis: {threat['explanation']}")

        urgency_lines.append(
            "\nIMMEDIATE ACTION REQUIRED: Verify your home garrison meets or exceeds the "
            "required defense level. If insufficient, IMMEDIATELY redirect forces to home. "
            "Losing home = instant defeat regardless of other achievements."
        )

    elif high_threats:
        urgency_lines.append("\nHIGH THREAT ALERT:")
        urgency_lines.append("=" * 50)
        for threat in high_threats:
            urgency_lines.append(
                f"\nENEMY POSITION: {threat['enemy_star_name']} ({threat['enemy_star_id']}) "
                f"- {threat['distance_to_home']} parsecs from home"
            )
            urgency_lines.append(f"  Estimated Force: {threat['estimated_ships']} ships")
            urgency_lines.append(f"  Can Arrive: Turn {threat['estimated_arrival_turn']}")
            urgency_lines.append(
                f"  Required Home Garrison: {threat['required_home_garrison']} ships"
            )

        urgency_lines.append(
            "\nRECOMMENDED ACTION: Ensure home garrison exceeds threat requirements. "
            "Consider pre-emptive strikes or defensive reinforcements."
        )

    # Add summary of all threats
    if len(threat_vectors) > len(critical_threats) + len(high_threats):
        other_count = len(threat_vectors) - len(critical_threats) - len(high_threats)
        urgency_lines.append(
            f"\nAdditional threats detected: {other_count} medium/low priority enemy positions. "
            "See active_threat_vectors in observation for full details."
        )

    return "\n".join(urgency_lines) if urgency_lines else ""
