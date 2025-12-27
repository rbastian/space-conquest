"""Middleware for LangGraph agent lifecycle management.

Provides middleware components for:
- Context management (message trimming, token tracking)
- Error recovery (graceful fallbacks when tools fail)
- Tool result processing (enhancing tool outputs with additional context)
"""

import logging

from langchain_core.messages import HumanMessage, trim_messages

from .state_models import AgentState

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
