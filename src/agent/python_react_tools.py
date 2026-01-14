"""Helper tools for PythonReactAgent.

This module provides a simplified tool set for the PythonReactAgent:
- validate_orders: Validates proposed orders before submission
- python_repl: Allows the agent to write and execute Python code for game analysis

The agent can use the REPL to perform complex calculations and strategic analysis
that would be difficult with predefined tools.
"""

import logging

from langchain_core.tools import tool

from ..analysis.game_stage import calculate_game_stage
from ..models.game import Game
from ..models.star import Star

logger = logging.getLogger(__name__)


def create_python_react_tools(game: Game, player_id: str) -> list:
    """Create tools with PythonREPL for code execution.

    This tool set is minimal compared to ReactPlayer:
    - validate_orders: Check if proposed orders are legal
    - PythonREPL: Execute Python code for game analysis

    The REPL has access to game state variables in its global namespace:
    - stars: List of all star objects
    - my_player_id: The agent's player ID
    - game: Full game state object
    - game_turn: Current turn number

    Args:
        game: Game object reference (mutated by TurnExecutor each turn)
        player_id: Player ID for this agent

    Returns:
        List of tool instances
    """

    def _get_star_by_id(star_id: str) -> Star | None:
        """Get a star object by its ID."""
        for star in game.stars:
            if star.id.upper() == star_id.upper():
                return star
        return None

    def _get_available_ships(star: Star) -> int:
        """Get number of ships available at a star for this player."""
        if star.owner != player_id:
            return 0
        return star.stationed_ships.get(player_id, 0)

    @tool
    def validate_orders(orders: list[dict]) -> dict:
        """Validate if proposed orders are legal.

        Use this tool to check if your planned orders are valid before submitting them.
        Multiple orders from the same star are CUMULATIVE - make sure total ships
        don't exceed available ships at that star.

        Args:
            orders: List of order dicts with keys: from, to, ships, rationale

        Returns:
            Dictionary with validation results for each order
        """
        logger.info(f"[TOOL] validate_orders: Validating {len(orders)} order(s)")
        results = []
        ships_moved_from_star: dict[str, int] = {}  # Track cumulative ships from each star

        for i, order_dict in enumerate(orders):
            # Check required fields
            if "from" not in order_dict:
                results.append({"order_index": i, "valid": False, "error": "Missing 'from' field"})
                continue

            if "to" not in order_dict:
                results.append({"order_index": i, "valid": False, "error": "Missing 'to' field"})
                continue

            if "ships" not in order_dict:
                results.append({"order_index": i, "valid": False, "error": "Missing 'ships' field"})
                continue

            from_star_id = order_dict["from"].upper()
            to_star_id = order_dict["to"].upper()
            ships = order_dict["ships"]

            # Check if from_star exists
            from_star = _get_star_by_id(from_star_id)
            if not from_star:
                results.append(
                    {
                        "order_index": i,
                        "order": order_dict,
                        "valid": False,
                        "error": f"Star {from_star_id} does not exist",
                    }
                )
                continue

            # Check ownership
            if from_star.owner != player_id:
                results.append(
                    {
                        "order_index": i,
                        "order": order_dict,
                        "valid": False,
                        "error": f"You don't own {from_star_id} (owner: {from_star.owner or 'NPC'})",
                    }
                )
                continue

            # Check if to_star exists
            to_star = _get_star_by_id(to_star_id)
            if not to_star:
                results.append(
                    {
                        "order_index": i,
                        "order": order_dict,
                        "valid": False,
                        "error": f"Star {to_star_id} does not exist",
                    }
                )
                continue

            # Check ships is positive integer
            if not isinstance(ships, int) or ships <= 0:
                results.append(
                    {
                        "order_index": i,
                        "order": order_dict,
                        "valid": False,
                        "error": f"Ships must be positive integer, got {ships}",
                    }
                )
                continue

            # Check cumulative ships available (track across all orders)
            ships_moved_from_star[from_star_id] = ships_moved_from_star.get(from_star_id, 0) + ships
            available_ships = _get_available_ships(from_star)

            if ships_moved_from_star[from_star_id] > available_ships:
                results.append(
                    {
                        "order_index": i,
                        "order": order_dict,
                        "valid": False,
                        "error": f"Only {available_ships} ships at {from_star_id}, "
                        f"but trying to move {ships_moved_from_star[from_star_id]} total across all orders",
                    }
                )
                continue

            # Order is valid
            results.append({"order_index": i, "order": order_dict, "valid": True})

        # Summary
        valid_count = sum(1 for r in results if r["valid"])
        return {"results": results, "summary": f"{valid_count}/{len(results)} orders valid"}

    @tool
    def python_repl(code: str) -> str:
        """Execute Python code to analyze game state and calculate strategies.

        The following variables are available in your code:
        - stars: List of all Star objects with attributes (id, name, x, y, base_ru, owner, stationed_ships, npc_ships)
        - my_player_id: Your player ID (str)
        - game: Full Game object with all game state
        - game_turn: Current turn number (int)
        - game_stage: Current game phase ("early", "mid", or "late") based on opponent contact
        - math: Python math module (pre-imported)

        Note: Each execution has a fresh context, so imports are not persistent.
        Useful for:
        - Computing distances between stars
        - Analyzing strategic positions
        - Calculating combat outcomes
        - Optimizing fleet distributions
        - Finding shortest paths
        - Evaluating risk/reward scenarios

        Args:
            code: Python code to execute (string)

        Returns:
            String output from code execution or error message
        """
        logger.info(f"[TOOL] python_repl: Executing code:\n{code}")

        # Prepare context with game state
        import math

        context = {
            "stars": game.stars,
            "my_player_id": player_id,
            "game": game,
            "game_turn": game.turn,
            "game_stage": calculate_game_stage(game, player_id),
            # Add useful utility functions
            "max": max,
            "min": min,
            "abs": abs,
            "sum": sum,
            "len": len,
            "sorted": sorted,
            "enumerate": enumerate,
            "range": range,
            "list": list,
            "dict": dict,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            # Add commonly used standard library modules
            "math": math,
        }

        # Execute code with context
        # We need to inject the context into the REPL's globals
        try:
            # Create a temporary REPL instance with our context
            import sys
            from io import StringIO

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            # Execute code with context
            exec(code, context)

            # Get output
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            logger.info(f"[TOOL] python_repl: Output:\n{output}")
            return output if output else "Code executed successfully (no output)"

        except Exception as e:
            sys.stdout = old_stdout
            error_msg = f"Error executing code: {e}"
            logger.error(f"[TOOL] python_repl: {error_msg}")
            return error_msg

    return [validate_orders, python_repl]
