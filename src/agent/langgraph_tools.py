"""Factory function for creating LangGraph agent tools.

Provides dependency injection pattern for LangGraphPlayer.
"""

from ..models.game import Game


def create_langgraph_tools(game: Game, player_id: str) -> tuple:
    """Create AgentTools instance and TOOL_DEFINITIONS for LangGraph.

    Factory function that instantiates AgentTools and returns tool definitions.
    Used for dependency injection pattern in LangGraphPlayer.

    Args:
        game: Game object reference (mutated each turn by TurnExecutor)
        player_id: Player ID ("p1" or "p2")

    Returns:
        Tuple of (AgentTools instance, TOOL_DEFINITIONS list)
    """
    from .tool_models import TOOL_DEFINITIONS
    from .tools import AgentTools

    tools_instance = AgentTools(game, player_id)
    return tools_instance, TOOL_DEFINITIONS
