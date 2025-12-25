"""Agent tools for LLM player.

Provides tools that the LLM can use to observe the game state,
query information, validate orders, and submit moves. All tools
respect fog-of-war constraints and only expose Player 2's view.
"""

import logging
from typing import Any

from pydantic import ValidationError

from ..models.game import Game
from ..models.order import Order
from ..models.star import Star
from .tool_models import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class AgentTools:
    """Collection of tools available to the LLM agent.

    Tools are designed to be pure functions (except submit_orders)
    that expose only Player 2's fog-of-war filtered view of the game.
    """

    def __init__(self, game: Game, player_id: str = "p2"):
        """Initialize agent tools.

        Args:
            game: Current game state
            player_id: Player ID for this agent (default: "p2")
        """
        self.game = game
        self.player_id = player_id
        self.player = game.players[player_id]
        self.opponent_id = "p1" if player_id == "p2" else "p2"

        # Simple memory store (dict for now)
        self.memory: dict[str, list[dict]] = {
            "battle_log": [],  # Auto-populated: PvP combat history only
            "discovery_log": [],  # Auto-populated: star discoveries
        }

        # Restore memory from previous turns if available
        if self.player_id in self.game.agent_memory:
            self.memory = self.game.agent_memory[self.player_id]
            logger.debug(
                f"Restored agent memory: {len(self.memory['battle_log'])} battles, "
                f"{len(self.memory['discovery_log'])} discoveries"
            )

        # Pending orders (for validation before submission)
        self.pending_orders: list[Order] | None = None
        self.orders_submitted = False

    def _resolve_star_id(self, star_ref: str) -> str:
        """Resolve a star reference to a valid star ID.

        Handles both letter IDs and numeric array indices. This makes the tools
        more robust when the LLM confuses array indices with star IDs.

        Args:
            star_ref: Either a letter ID ("A"-"P") or numeric string ("0"-"15")

        Returns:
            Valid letter ID for the star

        Raises:
            ValueError: If star_ref is invalid or out of range
        """
        # Try as numeric index first
        if star_ref.isdigit():
            index = int(star_ref)
            if 0 <= index < len(self.game.stars):
                return self.game.stars[index].id
            else:
                raise ValueError(
                    f"Invalid star index: {star_ref} (must be 0-{len(self.game.stars) - 1})"
                )

        # Check if it's a valid letter ID (case-insensitive)
        star_ref_upper = star_ref.upper()
        for star in self.game.stars:
            if star.id == star_ref_upper:
                return star_ref_upper

        raise ValueError(
            f"Invalid star reference: {star_ref} "
            f"(must be a letter ID like 'A' or numeric index like '0')"
        )

    def _get_star_by_id(self, star_id: str) -> Star | None:
        """Get a star object by its ID.

        Args:
            star_id: Star ID to look up

        Returns:
            Star object if found, None otherwise
        """
        for star in self.game.stars:
            if star.id == star_id:
                return star
        return None

    def propose_orders(self, draft_orders: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate draft orders without submitting.

        WARNING: Multiple orders from the same star are CUMULATIVE.

        Example - Star B has 10 ships available:
          CORRECT: Order B->A (6 ships), Order B->C (4 ships) = 10 total from B
          WRONG: Order B->A (8 ships), Order B->C (5 ships) = 13 total (OVER-COMMITTED!)

        Before proposing orders, ADD UP all ships from each origin star.
        If total exceeds available ships at that star, validation will FAIL.

        Common mistake: Ordering from the same star twice without accounting for the first order.

        Checks that orders are valid according to game rules:
        - Origin stars must be controlled by Player 2
        - Cannot exceed stationed ships at origin (cumulative across all orders)
        - Ships must be positive integers
        - Stars must exist

        Args:
            draft_orders: List of order dicts with "from", "to", "ships" keys

        Returns:
            Validation result: {"ok": True} or {"ok": False, "errors": [...]}
        """
        errors = []

        # Track ships moved from each star (using resolved IDs)
        ships_moved: dict[str, int] = {}

        for i, order_dict in enumerate(draft_orders):
            # Validate schema
            if "from" not in order_dict:
                errors.append(f"Order {i}: missing 'from' field")
                continue
            if "to" not in order_dict:
                errors.append(f"Order {i}: missing 'to' field")
                continue
            if "ships" not in order_dict:
                errors.append(f"Order {i}: missing 'ships' field")
                continue

            from_star_ref = order_dict["from"]
            to_star_ref = order_dict["to"]
            ships = order_dict["ships"]

            # Resolve star IDs (handles both letters and numeric indices)
            try:
                from_star = self._resolve_star_id(str(from_star_ref))
            except ValueError as e:
                errors.append(f"Order {i}: {str(e)}")
                continue

            try:
                to_star = self._resolve_star_id(str(to_star_ref))
            except ValueError as e:
                errors.append(f"Order {i}: {str(e)}")
                continue

            # Validate ships is integer
            if not isinstance(ships, int) or ships <= 0:
                errors.append(f"Order {i}: ships must be positive integer, got {ships}")
                continue

            # Find stars (should always succeed after _resolve_star_id)
            origin_star = None
            dest_star = None
            for star in self.game.stars:
                if star.id == from_star:
                    origin_star = star
                if star.id == to_star:
                    dest_star = star

            if origin_star is None:
                errors.append(f"Order {i}: invalid origin star '{from_star_ref}'")
                continue
            if dest_star is None:
                errors.append(f"Order {i}: invalid destination star '{to_star_ref}'")
                continue

            # Validate origin is controlled by player
            if origin_star.owner != self.player_id:
                errors.append(
                    f"Order {i}: origin star '{from_star}' not controlled by {self.player_id}"
                )
                continue

            # Track cumulative ships moved from this star
            ships_moved[from_star] = ships_moved.get(from_star, 0) + ships

            # Check if we have enough ships
            stationed = origin_star.stationed_ships.get(self.player_id, 0)
            if ships_moved[from_star] > stationed:
                errors.append(
                    f"Order {i}: cannot move {ships_moved[from_star]} ships from '{from_star}' "
                    f"(only {stationed} stationed)"
                )

        if errors:
            return {"ok": False, "errors": errors}
        else:
            # Store pending orders with resolved IDs
            resolved_orders = []
            for o in draft_orders:
                from_star = self._resolve_star_id(str(o["from"]))
                to_star = self._resolve_star_id(str(o["to"]))
                resolved_orders.append(
                    Order(
                        from_star=from_star,
                        to_star=to_star,
                        ships=o["ships"],
                        rationale=o["rationale"],  # Required field from validated input
                    )
                )
            self.pending_orders = resolved_orders
            return {"ok": True}

    def submit_orders(self, orders: list[dict[str, Any]]) -> dict[str, Any]:
        """Submit validated orders for this turn.

        This is the only mutating tool. Orders are committed and will
        be executed by the game engine.

        Args:
            orders: List of order dicts with "from", "to", "ships" keys

        Returns:
            Acknowledgment with order count

        Raises:
            ValueError: If orders are invalid or already submitted
        """
        if self.orders_submitted:
            raise ValueError("Orders already submitted for this turn")

        # Validate first
        validation = self.propose_orders(orders)
        if not validation["ok"]:
            raise ValueError(f"Invalid orders: {validation['errors']}")

        # Mark as submitted
        self.orders_submitted = True

        return {
            "status": "submitted",
            "order_count": len(orders),
            "turn": self.game.turn,
        }

    def calculate_distance(self, from_star: str, to_star: str) -> dict[str, Any]:
        """Calculate travel distance and arrival time between two stars.

        Args:
            from_star: Origin star ID
            to_star: Destination star ID

        Returns:
            Dict with distance_turns and arrival_turn

        Raises:
            ValueError: If either star ID is invalid
        """
        from ..utils.distance import chebyshev_distance

        # Resolve star IDs (handles both letters and numeric indices, case-insensitive)
        try:
            from_star_id = self._resolve_star_id(from_star)
        except ValueError as e:
            raise ValueError(f"Invalid from_star: {e}")

        try:
            to_star_id = self._resolve_star_id(to_star)
        except ValueError as e:
            raise ValueError(f"Invalid to_star: {e}")

        # Find star objects
        from_star_obj = self._get_star_by_id(from_star_id)
        to_star_obj = self._get_star_by_id(to_star_id)

        if from_star_obj is None:
            raise ValueError(f"Star not found: {from_star}")
        if to_star_obj is None:
            raise ValueError(f"Star not found: {to_star}")

        # Calculate distance
        distance = chebyshev_distance(
            from_star_obj.x, from_star_obj.y, to_star_obj.x, to_star_obj.y
        )

        # Calculate arrival turn (current turn + distance)
        arrival = self.game.turn + distance

        # Calculate hyperspace loss probability
        # Each turn has 2% chance of fleet destruction (binary outcome)
        # Cumulative loss = 1 - (survival_rate)^distance
        from ..utils.constants import HYPERSPACE_LOSS_PROB

        survival_rate = 1 - HYPERSPACE_LOSS_PROB
        hyperspace_loss_prob = 1 - (survival_rate**distance)

        return {
            "from_star": from_star_obj.id,
            "from_star_name": from_star_obj.name,
            "to_star": to_star_obj.id,
            "to_star_name": to_star_obj.name,
            "distance_turns": distance,
            "current_turn": self.game.turn,
            "arrival_turn": arrival,
            "hyperspace_loss_probability": round(hyperspace_loss_prob, 4),
        }

    def get_pending_orders(self) -> list[Order] | None:
        """Get the pending validated orders.

        Returns:
            List of Order objects if orders were validated, None otherwise
        """
        return self.pending_orders

    def execute_tool(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with Pydantic validation.

        This is the unified entry point for all tool execution. It:
        1. Validates input using the appropriate Pydantic model
        2. Calls the tool's handler method
        3. Validates output using the appropriate Pydantic model
        4. Returns dict for JSON serialization

        Args:
            tool_name: Name of the tool to execute
            tool_input: Raw input dictionary from LLM

        Returns:
            Validated output dictionary

        Raises:
            ValueError: If tool_name is unknown or validation fails
        """
        # Look up tool in registry
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_info = TOOL_REGISTRY[tool_name]
        input_model = tool_info["input_model"]
        output_model = tool_info["output_model"]

        # Validate input
        try:
            validated_input = input_model(**tool_input)
        except ValidationError as e:
            raise ValueError(f"Input validation failed for {tool_name}: {e}")

        # Execute the tool
        try:
            if tool_name == "submit_orders":
                # Convert OrderModel list to dict list for internal method
                orders_dict = [
                    {"from": o.from_, "to": o.to, "ships": o.ships, "rationale": o.rationale}
                    for o in validated_input.orders
                ]
                # submit_orders validates internally and sets pending_orders
                result = self.submit_orders(orders_dict)
            elif tool_name == "calculate_distance":
                result = self.calculate_distance(validated_input.from_, validated_input.to)
            else:
                raise ValueError(f"Tool handler not implemented: {tool_name}")

        except Exception as e:
            # Re-raise with better context
            raise ValueError(f"Tool execution failed for {tool_name}: {str(e)}")

        # Validate output
        try:
            # For some outputs, we already have validated dicts
            # Just validate and return
            validated_output = output_model(**result)
            return validated_output.model_dump()
        except ValidationError as e:
            raise ValueError(f"Output validation failed for {tool_name}: {e}")

    def reset_turn(self):
        """Reset turn state for next turn.

        Should be called at the start of each turn to clear submission flags
        and auto-populate memory from game observations.
        """
        self.orders_submitted = False
        self.pending_orders = None

        # Auto-populate memory from game observations
        self._auto_populate_memory()

    def _auto_populate_memory(self) -> None:
        """Auto-populate memory tables from current game state.

        Populates:
        - battle_log: From combats_last_turn (PvP only, no NPC battles)
        - discovery_log: From newly visited stars
        """
        current_turn = self.game.turn

        # 1. Populate battle_log from combats_last_turn (PvP only)
        for combat in self.game.combats_last_turn:
            self._add_battle_record(current_turn, combat)

        # 2. Populate discovery_log from newly visited stars
        for star in self.game.stars:
            if star.id in self.player.visited_stars:  # Star has been visited
                self._add_discovery_record(current_turn, star)

    def _add_battle_record(self, turn: int, combat_dict: dict) -> None:
        """Add battle record for PvP combats only (excludes NPC battles).

        Args:
            turn: Current turn number
            combat_dict: Combat data from game.combats_last_turn
        """
        attacker_id = combat_dict["attacker"]
        defender_id = combat_dict["defender"]

        # Only record PvP battles (both players are p1 or p2, not NPC)
        # Skip: p1 vs npc, p2 vs npc, p1 vs combined, etc.
        if attacker_id not in ["p1", "p2"] or defender_id not in ["p1", "p2"]:
            return  # Skip NPC battles

        star_id = combat_dict["star_id"]

        # Check if this battle already recorded (avoid duplicates)
        existing = any(
            r.get("turn") == turn and r.get("star") == star_id for r in self.memory["battle_log"]
        )

        if not existing:
            # Transform perspective (p1/p2 -> me/opp)
            def transform_player(pid: str) -> str:
                return "me" if pid == self.player_id else "opp"

            # Transform winner
            winner_role = combat_dict.get("winner")
            if winner_role is None:
                winner = "draw"
            else:
                winner_entity = attacker_id if winner_role == "attacker" else defender_id
                winner = transform_player(winner_entity)

            self.memory["battle_log"].append(
                {
                    "turn": turn,
                    "star": star_id,
                    "star_name": combat_dict["star_name"],
                    "attacker": transform_player(attacker_id),
                    "defender": transform_player(defender_id),
                    "attacker_ships_before": combat_dict["attacker_ships"],
                    "defender_ships_before": combat_dict["defender_ships"],
                    "attacker_survived": combat_dict["attacker_survivors"],
                    "defender_survived": combat_dict["defender_survivors"],
                    "winner": winner,
                }
            )

    def _add_discovery_record(self, turn: int, star) -> None:
        """Add discovery record for newly visited stars.

        Args:
            turn: Current turn number
            star: Star object from game.stars
        """
        star_id = star.id

        # Check if already recorded
        existing = any(r.get("star") == star_id for r in self.memory["discovery_log"])

        if not existing:
            # Transform owner perspective
            owner = None
            if star.owner is not None:
                if star.owner == "npc":
                    owner = "npc"
                elif star.owner == self.player_id:
                    owner = "me"
                else:
                    owner = "opp"

            self.memory["discovery_log"].append(
                {
                    "turn": turn,
                    "star": star_id,
                    "star_name": star.name,
                    "ru": star.base_ru,
                    "owner": owner,
                }
            )

            logger.info(
                f"Recorded star discovery: {star_id} ({star.name}) with {star.base_ru} RU (turn {turn})"
            )
