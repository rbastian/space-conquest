"""Helper tools for ReactPlayer agent.

These tools help the agent make decisions but don't store orders.
The agent returns orders in its final text response as JSON.
"""

import logging

from langchain.tools import tool

from ..models.game import Game
from ..models.star import Star
from ..utils.distance import chebyshev_distance

logger = logging.getLogger(__name__)


def create_react_tools(game: Game, player_id: str) -> list:
    """Create helper tools with game state captured in closures.

    These are HELPER tools - they don't store orders, just help the agent make decisions.
    The agent returns orders in its final text response as JSON.

    Args:
        game: Game object reference (mutated by TurnExecutor each turn)
        player_id: Player ID for this agent

    Returns:
        List of @tool decorated functions
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
    def calculate_distance(from_star: str, to_star: str) -> dict:
        """Calculate distance and travel time between two stars.

        Use this to plan your fleet movements and assess risks.

        Args:
            from_star: Origin star ID
            to_star: Destination star ID

        Returns:
            Dictionary with distance, turns, arrival_turn, or error
        """
        logger.info(f"[TOOL] calculate_distance: {from_star.upper()} → {to_star.upper()}")
        from_star_id = from_star.upper()
        to_star_id = to_star.upper()

        star1 = _get_star_by_id(from_star_id)
        star2 = _get_star_by_id(to_star_id)

        if not star1:
            return {"error": f"Star {from_star_id} does not exist"}

        if not star2:
            return {"error": f"Star {to_star_id} does not exist"}

        # Calculate Chebyshev distance (max of abs differences)
        distance_turns = chebyshev_distance(star1.x, star1.y, star2.x, star2.y)

        # Arrival turn is current turn + distance
        arrival_turn = game.turn + distance_turns

        return {
            "from": from_star_id,
            "to": to_star_id,
            "distance_turns": distance_turns,
            "arrival_turn": arrival_turn,
            "current_turn": game.turn,
        }

    return [validate_orders, calculate_distance]
