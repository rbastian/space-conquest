"""Helper tools for ReactPlayer agent.

These tools help the agent make decisions but don't store orders.
The agent returns orders in its final text response as JSON.
"""

import heapq
import logging
from collections import defaultdict

from langchain.tools import tool

from ..models.game import Game
from ..models.star import Star
from ..utils.constants import calculate_hyperspace_cumulative_risk
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

        NOTE: For journeys over 4 turns, consider using find_safest_route to
        discover multi-hop routes that may be significantly safer.

        Args:
            from_star: Origin star ID
            to_star: Destination star ID

        Returns:
            Dictionary with distance_turns, arrival_turn, current_turn,
            hyperspace_survival_probability (percentage string like "90%" showing chance fleet survives), or error
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

        # Calculate hyperspace survival probability using n log n scaling
        # Cumulative risk = k × distance × log(distance)
        # Survival probability = 1 - cumulative_risk
        cumulative_risk = calculate_hyperspace_cumulative_risk(distance_turns)
        hyperspace_survival_prob = 1.0 - cumulative_risk

        result = {
            "from": from_star_id,
            "to": to_star_id,
            "distance_turns": distance_turns,
            "arrival_turn": arrival_turn,
            "current_turn": game.turn,
            "hyperspace_survival_probability": f"{round(hyperspace_survival_prob * 100)}%",
        }

        logger.info(
            f"[TOOL] calculate_distance result: {from_star_id} → {to_star_id} = "
            f"{distance_turns} turns, arrives turn {arrival_turn}, "
            f"{result['hyperspace_survival_probability']} survival"
        )

        return result

    @tool
    def get_nearby_garrisons(target: str) -> dict:
        """Find your 3 closest garrisons to a target star.

        Use this to identify which of your controlled stars can send reinforcements
        fastest to a target location. Helps answer: "Which of my bases can respond
        to this threat/opportunity?"

        Args:
            target: Target star ID (letter like 'A' or 'K')

        Returns:
            Dictionary with target info and up to 3 closest garrisons sorted by distance
        """
        logger.info(f"[TOOL] get_nearby_garrisons: Finding garrisons near {target.upper()}")
        target_id = target.upper()

        # Get target star
        target_star = _get_star_by_id(target_id)
        if not target_star:
            return {
                "target": {"id": target_id, "name": "Unknown", "location": [0, 0]},
                "garrisons": [],
            }

        # Find all garrisons (owned stars with ships > 0)
        garrisons = []
        for star in game.stars:
            if star.owner != player_id:
                continue

            ships = _get_available_ships(star)
            if ships <= 0:
                continue

            # Calculate distance
            distance_turns = chebyshev_distance(star.x, star.y, target_star.x, target_star.y)

            # Check if home star
            is_home = star.id == game.players[player_id].home_star

            garrisons.append(
                {
                    "star_id": star.id,
                    "star_name": star.name,
                    "location": [star.x, star.y],
                    "stationed_ships": ships,
                    "distance_turns": distance_turns,
                    "arrival_turn": game.turn + distance_turns,
                    "ru": star.base_ru,
                    "is_home": is_home,
                }
            )

        # Sort by distance (closest first) and take top 3
        garrisons.sort(key=lambda g: g["distance_turns"])
        garrisons = garrisons[:3]

        return {
            "target": {
                "id": target_star.id,
                "name": target_star.name,
                "location": [target_star.x, target_star.y],
            },
            "garrisons": garrisons,
        }

    def _dijkstra_safest_path(
        from_star_obj: Star, to_star_obj: Star, max_hops: int, prefer_controlled: bool
    ) -> tuple[list[str], float, int] | None:
        """Find safest path using Dijkstra's algorithm with cumulative risk as edge weight.

        Args:
            from_star_obj: Origin star object
            to_star_obj: Destination star object
            max_hops: Maximum number of intermediate waypoints allowed
            prefer_controlled: If True, reduce edge weight by 20% for player-controlled destinations

        Returns:
            Tuple of (path, total_risk, total_distance) or None if no path within max_hops
            - path: List of star IDs from origin to destination
            - total_risk: Cumulative hyperspace risk for entire route
            - total_distance: Total distance in turns
        """
        # Priority queue: (cumulative_risk, cumulative_distance, current_star_id, path)
        # path is list of star IDs
        pq = [(0.0, 0, from_star_obj.id, [from_star_obj.id])]

        # Track best risk to reach each (star_id, hop_count) state
        # This allows revisiting a star if we get there with fewer hops
        best_risk: dict[tuple[str, int], float] = defaultdict(lambda: float("inf"))
        best_risk[(from_star_obj.id, 0)] = 0.0

        while pq:
            curr_risk, curr_distance, curr_star_id, path = heapq.heappop(pq)

            # Current hop count is path length minus 1 (path includes origin)
            curr_hops = len(path) - 1

            # If we reached destination, return this path
            if curr_star_id == to_star_obj.id:
                return (path, curr_risk, curr_distance)

            # If we've exceeded max_hops, skip this path
            if curr_hops >= max_hops + 1:  # max_hops waypoints = max_hops+1 total segments
                continue

            # Get current star object
            curr_star = _get_star_by_id(curr_star_id)
            if not curr_star:
                continue

            # Explore all neighboring stars
            for next_star in game.stars:
                # Skip if already in path (avoid cycles)
                if next_star.id in path:
                    continue

                # Calculate edge distance and risk
                edge_distance = chebyshev_distance(
                    curr_star.x, curr_star.y, next_star.x, next_star.y
                )
                edge_risk = calculate_hyperspace_cumulative_risk(edge_distance)

                # Apply preference for controlled stars (reduce risk by 20%)
                if prefer_controlled and next_star.owner == player_id:
                    edge_risk *= 0.8

                # Calculate new cumulative values
                new_risk = curr_risk + edge_risk
                new_distance = curr_distance + edge_distance
                new_path = path + [next_star.id]
                new_hops = len(new_path) - 1

                # Check if this is better than previous best for this state
                state = (next_star.id, new_hops)
                if new_risk < best_risk[state]:
                    best_risk[state] = new_risk
                    heapq.heappush(pq, (new_risk, new_distance, next_star.id, new_path))

        # No path found within max_hops
        return None

    @tool
    def find_safest_route(
        from_star: str, to_star: str, max_hops: int = 3, prefer_controlled: bool = True
    ) -> dict:
        """Find the safest route between two stars, considering hyperspace loss risk.

        IMPORTANT: Use this tool for any journey over 4 turns to discover safer multi-hop
        routes. Due to n log n hyperspace risk scaling, longer direct routes are much
        riskier than shorter multi-hop routes with waypoints.

        Example: A direct 8-turn journey has 48% loss risk, but routing through a
        waypoint (4+4 turns) reduces risk to 32% - a 33% improvement!

        Uses pathfinding to find optimal routes that minimize cumulative hyperspace loss.
        Prefer routes through your controlled stars for safer waypoints.

        Args:
            from_star: Origin star ID (e.g., 'A')
            to_star: Destination star ID (e.g., 'K')
            max_hops: Maximum number of waypoint stops (default 3, max 5)
            prefer_controlled: If True, prefer routes through your controlled stars (default True)

        Returns:
            Dictionary with:
            - direct_route: Info about direct route (distance, risk, arrival_turn)
            - optimal_route: Best route found (path, total_distance, total_risk, arrival_turn, waypoints)
            - recommendation: Summary text explaining why this route is better
        """
        logger.info(
            f"[TOOL] find_safest_route: {from_star.upper()} → {to_star.upper()}, "
            f"max_hops={max_hops}, prefer_controlled={prefer_controlled}"
        )

        # Input validation
        max_hops = min(max(max_hops, 1), 5)  # Clamp to 1-5

        from_star_obj = _get_star_by_id(from_star.upper())
        to_star_obj = _get_star_by_id(to_star.upper())

        if not from_star_obj:
            return {"error": f"Star {from_star.upper()} does not exist"}
        if not to_star_obj:
            return {"error": f"Star {to_star.upper()} does not exist"}

        # Handle same star case
        if from_star_obj.id == to_star_obj.id:
            return {
                "from": from_star_obj.id,
                "to": to_star_obj.id,
                "direct_route": {
                    "distance_turns": 0,
                    "cumulative_risk": "0%",
                    "arrival_turn": game.turn,
                },
                "optimal_route": {
                    "path": [from_star_obj.id],
                    "waypoints": [],
                    "total_distance_turns": 0,
                    "cumulative_risk": "0%",
                    "arrival_turn": game.turn,
                    "risk_reduction": "0%",
                },
                "recommendation": "Origin and destination are the same star",
            }

        # Calculate direct route
        direct_distance = chebyshev_distance(
            from_star_obj.x, from_star_obj.y, to_star_obj.x, to_star_obj.y
        )
        direct_risk = calculate_hyperspace_cumulative_risk(direct_distance)
        direct_arrival = game.turn + direct_distance

        # Find optimal multi-hop route
        optimal_path_result = _dijkstra_safest_path(
            from_star_obj, to_star_obj, max_hops, prefer_controlled
        )

        if not optimal_path_result:
            # No path found within max_hops
            return {
                "error": f"No path found from {from_star.upper()} to {to_star.upper()} within {max_hops} hops"
            }

        path, total_risk, total_distance = optimal_path_result

        # Calculate risk reduction
        risk_reduction = direct_risk - total_risk
        risk_reduction_pct = (risk_reduction / direct_risk * 100) if direct_risk > 0 else 0

        # Format result
        result = {
            "from": from_star.upper(),
            "to": to_star.upper(),
            "direct_route": {
                "distance_turns": direct_distance,
                "cumulative_risk": f"{round(direct_risk * 100)}%",
                "arrival_turn": direct_arrival,
            },
            "optimal_route": {
                "path": path,  # List of star IDs
                "waypoints": path[1:-1] if len(path) > 2 else [],  # Intermediate stops
                "total_distance_turns": total_distance,
                "cumulative_risk": f"{round(total_risk * 100)}%",
                "arrival_turn": game.turn + total_distance,
                "risk_reduction": f"{round(risk_reduction_pct)}%" if risk_reduction > 0 else "0%",
            },
        }

        # Add recommendation
        if len(path) == 2:
            result["recommendation"] = "Direct route is optimal (no waypoints needed)"
        elif risk_reduction_pct >= 5:  # At least 5% risk reduction
            waypoint_names = [_get_star_by_id(s).name for s in path[1:-1]]
            result["recommendation"] = (
                f"Multi-hop route reduces risk by {result['optimal_route']['risk_reduction']} via waypoints: {', '.join(waypoint_names)}"
            )
        else:
            result["recommendation"] = "Multi-hop route has similar risk to direct route"

        logger.info(f"[TOOL] find_safest_route result: {result['recommendation']}")
        return result

    return [validate_orders, calculate_distance, get_nearby_garrisons, find_safest_route]
