"""Agent tools for LLM player.

Provides tools that the LLM can use to observe the game state,
query information, validate orders, and submit moves. All tools
respect fog-of-war constraints and only expose Player 2's view.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

logger = logging.getLogger(__name__)

from ..models.game import Game
from ..models.order import Order
from ..utils.constants import HYPERSPACE_LOSS_PROB, REBELLION_PROB
from ..utils.distance import chebyshev_distance
from .tool_models import (
    TOOL_REGISTRY,
    TOOL_DEFINITIONS,
    ObservationOutput,
    StarObservation,
    FleetObservation,
    ArrivalObservation,
    ProductionReport,
    RebellionReport,
    HyperspaceLossReport,
    CombatReport,
    GameRules,
    GarrisonWarning,
)


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
        self.memory: Dict[str, List[Dict]] = {
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
        self.pending_orders: Optional[List[Order]] = None
        self.orders_submitted = False

    def _determine_participation(
        self, combat_dict: Dict[str, Any]
    ) -> tuple[bool, bool]:
        """Determine if player participated in combat and their role.

        Args:
            combat_dict: Combat event dictionary with combat_type, attacker, defender

        Returns:
            Tuple of (player_participated, is_attacker)
            - player_participated: True if this player was involved in the combat
            - is_attacker: True if player was attacker, False if defender
        """
        combat_type = combat_dict.get("combat_type")
        attacker = combat_dict.get("attacker")
        defender = combat_dict.get("defender")

        if combat_type == "npc":
            # NPC combat: attacker can be "p1", "p2", or "combined"
            # Combined means both players attacked NPC together
            if attacker == self.player_id or attacker == "combined":
                return True, True
            return False, False

        elif combat_type == "pvp":
            # PvP combat: check if player is attacker or defender
            if attacker == self.player_id:
                return True, True
            elif defender == self.player_id:
                return True, False
            return False, False

        return False, False

    def _translate_winner(
        self, winner_role: Optional[str], attacker: str, defender: str
    ) -> str:
        """Translate combat winner role to player ID format.

        Args:
            winner_role: "attacker", "defender", or None (tie)
            attacker: Attacker entity ID (can be "p1", "p2", "combined", or "npc")
            defender: Defender entity ID (can be "p1", "p2", or "npc")

        Returns:
            Winner in player ID format: "p1", "p2", "npc", or "tie"
            Note: Reports winner from this player's perspective (e.g., if p1 is observing,
            returns "p1" when p1 won, "p2" when opponent won)
        """
        # Handle tie case first
        if winner_role is None:
            return "tie"

        # Determine which entity won
        winner_entity = attacker if winner_role == "attacker" else defender

        # Handle combined attacker case (both players attacked NPC)
        # If combined attackers won, credit to this player
        if winner_entity == "combined":
            winner_entity = self.player_id

        # Map entity to player ID format (relative to this observer)
        if winner_entity == self.player_id:
            return self.player_id  # Return actual player ID ("p1" or "p2")
        elif winner_entity == self.opponent_id:
            return self.opponent_id  # Return opponent's actual ID
        elif winner_entity == "npc":
            return "npc"
        else:
            return "tie"

    def _did_control_change(self, combat_type: str, winner_role: Optional[str]) -> bool:
        """Determine if star control changed hands.

        Args:
            combat_type: "npc" or "pvp"
            winner_role: "attacker", "defender", or None

        Returns:
            True if star ownership changed, False otherwise

        Notes:
            - For NPC combat: Control changes only if attackers won (defeated NPC forces)
            - For PvP combat: Control always changes if there's a winner (winner takes star)
        """
        if combat_type == "npc":
            return winner_role == "attacker"
        else:  # pvp
            return winner_role is not None

    def get_observation(self) -> Dict[str, Any]:
        """Get Player 2's current game state observation.

        Returns observation JSON with fog-of-war filtering applied.
        All stars are visible (coordinates, names) from turn 0 - "you can see the stars in space"
        Strategic details (RU values, ownership) are only known for visited stars (where fleets have arrived)
        Real-time intelligence: Once visited, you always see current RU and ownership

        Returns:
            Dictionary containing turn, grid, stars, fleets, events, and rules
        """
        # Build star list with fog-of-war
        stars = []
        for star in self.game.stars:
            star_id = star.id
            is_home = star_id == self.player.home_star

            # Check if star has been visited
            visited = star_id in self.player.visited_stars

            if visited:
                # Full real-time information for visited stars
                if star.owner == self.player_id:
                    owner = "p2"
                    stationed_ships = star.stationed_ships.get(self.player_id, 0)
                elif star.owner == self.opponent_id:
                    owner = "p1"
                    stationed_ships = None  # Hidden for enemy stars (fog-of-war)
                else:
                    owner = None
                    stationed_ships = None  # Hidden for NPC stars

                known_ru = star.base_ru  # Real-time RU value
                control = (
                    "controlled"
                    if star.owner == self.player_id
                    else "enemy"
                    if star.owner == self.opponent_id
                    else "neutral"
                )
            else:
                # Star is visible but strategic details unknown
                owner = None
                known_ru = None
                stationed_ships = None  # Hidden for unvisited stars
                control = "unknown"

            stars.append(
                StarObservation(
                    id=star_id,
                    x=star.x,
                    y=star.y,
                    letter=star_id,  # Using ID as letter
                    name=star.name,
                    owner=owner,
                    known_ru=known_ru,
                    last_seen_control=control,
                    is_home=is_home,
                    stationed_ships=stationed_ships,
                )
            )

        # Get Player 2's fleets
        my_fleets = []
        for fleet in self.game.fleets:
            if fleet.owner == self.player_id:
                my_fleets.append(
                    FleetObservation(
                        id=fleet.id,
                        ships=fleet.ships,
                        origin=fleet.origin,
                        dest=fleet.dest,
                        dist_remaining=fleet.dist_remaining,
                    )
                )

        # Find arrivals this turn (fleets with dist_remaining == 0)
        arrivals = [
            ArrivalObservation(fleet_id=f.id, dest=f.dest)
            for f in self.game.fleets
            if f.owner == self.player_id and f.dist_remaining == 0
        ]

        # Get combat reports from last turn (filter by player participation)
        def transform_combat_dict(combat_dict: Dict[str, Any]) -> Optional[CombatReport]:
            """Transform a single combat dict to CombatReport with perspective.

            Returns None if player didn't participate in this combat.
            """
            # Check if player participated and in what role
            player_participated, is_attacker = self._determine_participation(
                combat_dict
            )

            if not player_participated:
                return None

            # Extract basic combat data
            star_id = combat_dict["star_id"]
            attacker_id = combat_dict.get("attacker")
            defender_id = combat_dict.get("defender")

            # Transform perspective: convert player IDs to "me"/"opp"/"npc"
            def transform_player(pid: Optional[str]) -> Optional[str]:
                if pid is None:
                    return None
                if pid == "npc":
                    return "npc"  # Keep NPC distinct from real opponents
                if pid == "combined":
                    return "me"  # Combined attack with this player involved
                return "me" if pid == self.player_id else "opp"

            attacker_perspective = transform_player(attacker_id)
            defender_perspective = transform_player(defender_id)
            control_before = transform_player(combat_dict.get("control_before"))
            control_after = transform_player(combat_dict.get("control_after"))

            return CombatReport(
                star=star_id,
                attacker=attacker_perspective,
                defender=defender_perspective,
                attacker_ships_before=combat_dict["attacker_ships"],
                defender_ships_before=combat_dict["defender_ships"],
                attacker_losses=combat_dict["attacker_losses"],
                defender_losses=combat_dict["defender_losses"],
                control_before=control_before,
                control_after=control_after,
            )

        # Transform last turn's combats
        combats = []
        for combat_dict in self.game.combats_last_turn:
            combat_report = transform_combat_dict(combat_dict)
            if combat_report:
                combats.append(combat_report)

        # Transform combat history (last 5 turns)
        combats_last_5_turns = []
        for turn_combats in self.game.combats_history:
            turn_reports = []
            for combat_dict in turn_combats:
                combat_report = transform_combat_dict(combat_dict)
                if combat_report:
                    turn_reports.append(combat_report)
            combats_last_5_turns.append(turn_reports)

        # Get rebellion reports from last turn (filter by owner)
        rebellions = []
        for rebellion_dict in self.game.rebellions_last_turn:
            # Only include rebellions that affected this player
            if rebellion_dict.get("owner") == self.player_id:
                rebellions.append(
                    RebellionReport(
                        star=rebellion_dict["star"],
                        star_name=rebellion_dict["star_name"],
                        ru=rebellion_dict["ru"],
                        garrison_before=rebellion_dict["garrison_before"],
                        rebel_ships=rebellion_dict["rebel_ships"],
                        outcome=rebellion_dict["outcome"],
                        garrison_after=rebellion_dict["garrison_after"],
                        rebel_survivors=rebellion_dict["rebel_survivors"],
                    )
                )

        # Get hyperspace loss reports from last turn (filter by owner)
        hyperspace_losses = []
        for loss_dict in self.game.hyperspace_losses_last_turn:
            # Only include losses of this player's fleets
            if loss_dict.get("owner") == self.player_id:
                hyperspace_losses.append(
                    HyperspaceLossReport(
                        fleet_id=loss_dict["fleet_id"],
                        origin=loss_dict["origin"],
                        dest=loss_dict["dest"],
                        ships_lost=loss_dict["ships"],
                    )
                )

        # Get production report
        production = []
        for star in self.game.stars:
            if star.owner == self.player_id:
                # Ships produced = base_ru
                production.append(
                    ProductionReport(star=star.id, ships_produced=star.base_ru)
                )

        # Calculate strategic dashboard
        controlled_stars = [s for s in self.game.stars if s.owner == self.player_id]

        total_ships_stationed = sum(
            s.stationed_ships.get(self.player_id, 0) for s in controlled_stars
        )

        total_ships_in_transit = sum(f.ships for f in my_fleets)

        total_production = sum(s.base_ru for s in controlled_stars)

        # Count stars by RU value
        stars_by_ru = {1: 0, 2: 0, 3: 0, 4: 0}
        for star in controlled_stars:
            stars_by_ru[star.base_ru] = stars_by_ru.get(star.base_ru, 0) + 1

        avg_fleet_size = (
            total_ships_in_transit / len(my_fleets) if my_fleets else 0.0
        )

        from .tool_models import StrategicDashboard

        dashboard = StrategicDashboard(
            total_ships_stationed=total_ships_stationed,
            total_ships_in_transit=total_ships_in_transit,
            total_ships=total_ships_stationed + total_ships_in_transit,
            total_production_per_turn=total_production,
            controlled_stars_count=len(controlled_stars),
            stars_by_ru=stars_by_ru,
            fleet_count=len(my_fleets),
            avg_fleet_size=round(avg_fleet_size, 1),
        )

        # Create validated output
        output = ObservationOutput(
            turn=self.game.turn,
            seed=self.game.seed,
            grid={"width": 12, "height": 10},
            strategic_dashboard=dashboard,
            stars=stars,
            my_fleets=my_fleets,
            arrivals_this_turn=arrivals,
            combats_last_turn=combats,
            combats_last_5_turns=combats_last_5_turns,
            rebellions_last_turn=rebellions,
            hyperspace_losses_last_turn=hyperspace_losses,
            production_report=production,
            rules=GameRules(
                hyperspace_loss=HYPERSPACE_LOSS_PROB,
                rebellion_chance=REBELLION_PROB,
                production_formula="ships_per_turn = star_ru",
            ),
        )

        return output.model_dump()

    def get_ascii_map(self, view: str = "current") -> str:
        """Get ASCII representation of Player 2's map.

        Shows stars with their control status and RU values.
        Unknown RU values (unvisited stars) are shown as '?'.

        Args:
            view: Map view mode (only "current" is supported)

        Returns:
            ASCII art string representing the map
        """
        # Create empty grid
        grid = [["." for _ in range(12)] for _ in range(10)]

        # Place stars on grid
        for star in self.game.stars:
            x, y = star.x, star.y

            # Check if star has been visited (fog-of-war check)
            visited = star.id in self.player.visited_stars

            # Determine symbol based on ownership and RU
            if visited:
                known_ru = star.base_ru  # Real-time RU value
            else:
                known_ru = None  # Unknown RU

            if star.owner == self.player_id:
                # Our star - show with RU
                symbol = f"{star.id}{known_ru if known_ru else '?'}"
            elif star.owner == self.opponent_id:
                # Opponent star - show with RU if visited
                symbol = f"{star.id}{known_ru if known_ru else '?'}"
            else:
                # NPC or unknown - show with RU if visited
                symbol = f"{star.id}{known_ru if known_ru else '?'}"

            grid[y][x] = symbol.ljust(2)

        # Build ASCII string
        lines = []
        lines.append("   " + "".join(f"{i:2d}" for i in range(12)))
        lines.append("   " + "--" * 12)

        for y in range(10):
            row = f"{y:2d}|" + "".join(grid[y])
            lines.append(row)

        return "\n".join(lines)

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

        # Check if it's a valid letter ID
        for star in self.game.stars:
            if star.id == star_ref:
                return star_ref

        raise ValueError(
            f"Invalid star reference: {star_ref} "
            f"(must be a letter ID like 'A' or numeric index like '0')"
        )

    def query_star(self, star_ref: str) -> Dict[str, Any]:
        """Query information about a specific star.

        Returns all available information. If the star hasn't been visited,
        strategic details (RU, ownership) will be None.

        Args:
            star_ref: Star ID or letter to query

        Returns:
            Dictionary with star info and distance matrix

        Raises:
            ValueError: If star_ref is invalid
        """
        # Resolve star reference (handles both letters and numeric indices)
        star_id = self._resolve_star_id(star_ref)

        # Find the star
        star = None
        for s in self.game.stars:
            if s.id == star_id:
                star = s
                break

        if star is None:
            raise ValueError(f"Invalid star reference: {star_ref}")

        # Check if visited
        visited = star_id in self.player.visited_stars

        if visited:
            # Full information available
            known_ru = star.base_ru

            if star.owner == self.player_id:
                owner_display = "p2"
                stationed_ships = star.stationed_ships.get(self.player_id, 0)
            elif star.owner == self.opponent_id:
                owner_display = "p1"
                stationed_ships = None  # Hidden for enemy stars (fog-of-war)
            else:
                owner_display = None
                stationed_ships = None  # Hidden for NPC stars

            control = (
                "controlled"
                if star.owner == self.player_id
                else "enemy"
                if star.owner == self.opponent_id
                else "neutral"
            )
        else:
            # Limited information - star is visible but not visited
            known_ru = None
            owner_display = None
            stationed_ships = None  # Hidden for unvisited stars
            control = "unknown"

        # Calculate distances to all controlled stars
        distances = {}
        for s in self.game.stars:
            if s.owner == self.player_id:
                dist = chebyshev_distance(star.x, star.y, s.x, s.y)
                distances[s.id] = dist

        result = {
            "id": star.id,
            "name": star.name,
            "x": star.x,
            "y": star.y,
            "visited": visited,
            "known_ru": known_ru,
            "owner": owner_display,
            "last_seen_control": control,
            "stationed_ships": stationed_ships,
            "distances_from_my_stars": distances,
        }

        if not visited:
            result["note"] = (
                "This star has not been visited. Send a fleet to reveal strategic details (RU, ownership)."
            )

        return result

    def estimate_route(self, from_star: str, to_star: str) -> Dict[str, Any]:
        """Estimate route distance and hyperspace risk.

        Calculates Chebyshev distance and cumulative hyperspace loss
        probability for a route between two stars.

        Args:
            from_star: Origin star ID
            to_star: Destination star ID

        Returns:
            Dictionary with distance and risk

        Raises:
            ValueError: If star IDs are invalid
        """
        # Resolve star references (handles both letters and numeric indices)
        from_star_id = self._resolve_star_id(from_star)
        to_star_id = self._resolve_star_id(to_star)

        # Find stars
        origin = None
        dest = None

        for star in self.game.stars:
            if star.id == from_star_id:
                origin = star
            if star.id == to_star_id:
                dest = star

        if origin is None:
            raise ValueError(f"Invalid origin star: {from_star}")
        if dest is None:
            raise ValueError(f"Invalid destination star: {to_star}")

        # Calculate distance
        distance = chebyshev_distance(origin.x, origin.y, dest.x, dest.y)

        # Calculate cumulative risk: 1 - (1 - p)^distance
        risk = 1.0 - ((1.0 - HYPERSPACE_LOSS_PROB) ** distance)

        return {"distance": distance, "risk": round(risk, 4)}

    def propose_orders(self, draft_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        ships_moved: Dict[str, int] = {}

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

        # Calculate garrison warnings even if there are errors
        # (useful to show both errors and warnings)
        warnings = self._calculate_garrison_warnings(draft_orders)

        if errors:
            return {"ok": False, "errors": errors, "warnings": [w.model_dump() for w in warnings]}
        else:
            # Store pending orders with resolved IDs
            resolved_orders = []
            for o in draft_orders:
                from_star = self._resolve_star_id(str(o["from"]))
                to_star = self._resolve_star_id(str(o["to"]))
                resolved_orders.append(
                    Order(from_star=from_star, to_star=to_star, ships=o["ships"])
                )
            self.pending_orders = resolved_orders
            return {"ok": True, "warnings": [w.model_dump() for w in warnings]}

    def _calculate_garrison_warnings(self, draft_orders: List[Dict[str, Any]]) -> list[GarrisonWarning]:
        """Calculate garrison warnings for draft orders.

        Simulates order execution to detect stars that will be under-garrisoned
        (garrison < RU) after orders execute, which creates 50% rebellion risk.

        Args:
            draft_orders: List of order dicts with "from", "to", "ships" keys

        Returns:
            List of GarrisonWarning objects for at-risk stars
        """
        from collections import defaultdict

        warnings = []

        # Build map of ships leaving/arriving per star
        ships_leaving: dict[str, int] = defaultdict(int)
        ships_arriving_immediate: dict[str, int] = defaultdict(int)

        for order_dict in draft_orders:
            # Skip invalid orders (they'll be caught by validation)
            if "from" not in order_dict or "to" not in order_dict or "ships" not in order_dict:
                continue

            try:
                from_star = self._resolve_star_id(str(order_dict["from"]))
                to_star = self._resolve_star_id(str(order_dict["to"]))
                ships = order_dict["ships"]
            except (ValueError, KeyError):
                # Skip invalid orders
                continue

            if not isinstance(ships, int) or ships <= 0:
                continue

            ships_leaving[from_star] += ships

            # Calculate distance to determine if arrival is immediate (distance=1)
            origin = None
            dest = None
            for star in self.game.stars:
                if star.id == from_star:
                    origin = star
                if star.id == to_star:
                    dest = star

            if origin and dest:
                distance = chebyshev_distance(origin.x, origin.y, dest.x, dest.y)
                if distance == 1:
                    ships_arriving_immediate[to_star] += ships

        # Check garrison levels for owned stars
        for star in self.game.stars:
            if star.owner != self.player_id:
                continue  # Not owned by this player

            if star.id == self.player.home_star:
                continue  # Home stars never rebel

            current_garrison = star.stationed_ships.get(self.player_id, 0)
            ships_after = (
                current_garrison
                - ships_leaving[star.id]
                + ships_arriving_immediate[star.id]
            )

            if ships_after < star.base_ru:
                deficit = star.base_ru - ships_after
                ship_word = "ship" if ships_after == 1 else "ships"
                warnings.append(
                    GarrisonWarning(
                        star_id=star.id,
                        star_name=star.name,
                        current_garrison=current_garrison,
                        ships_after_orders=ships_after,
                        required_ru=star.base_ru,
                        deficit=deficit,
                        rebellion_chance=0.5,
                        message=f"Order leaves {star.name} ({star.id}) with {ships_after} {ship_word} (needs {star.base_ru} for {star.base_ru} RU, 50% rebellion risk)",
                    )
                )

        return warnings

    def submit_orders(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
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

    def memory_query(
        self, table: str, filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """Query agent memory.

        Retrieves records from the specified memory table with optional filtering.

        Args:
            table: Table name (battle_log, discovery_log)
            filter_dict: Optional filter criteria

        Returns:
            List of matching records
        """
        logger.info(f"LLM querying memory: table={table}, filter={filter_dict}")

        if table not in self.memory:
            logger.warning(f"LLM attempted to query invalid table: {table}")
            return []

        records = self.memory[table]

        if filter_dict is None:
            logger.info(f"Memory query returned {len(records)} records from {table}")
            return records

        # Simple filtering by key-value match
        filtered = []
        for record in records:
            matches = all(record.get(k) == v for k, v in filter_dict.items())
            if matches:
                filtered.append(record)

        logger.info(
            f"Memory query returned {len(filtered)} filtered records from {table}"
        )
        return filtered


    def get_pending_orders(self) -> Optional[List[Order]]:
        """Get the pending validated orders.

        Returns:
            List of Order objects if orders were validated, None otherwise
        """
        return self.pending_orders

    def execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
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

        # Execute the tool based on name
        try:
            if tool_name == "get_observation":
                result = self.get_observation()

            elif tool_name == "get_ascii_map":
                map_str = self.get_ascii_map(validated_input.view)
                result = {"map": map_str}

            elif tool_name == "query_star":
                result = self.query_star(validated_input.star_ref)

            elif tool_name == "estimate_route":
                result = self.estimate_route(
                    validated_input.from_star, validated_input.to_star
                )

            elif tool_name == "propose_orders":
                # Convert OrderModel list to dict list for internal method
                orders_dict = [
                    {"from": o.from_, "to": o.to, "ships": o.ships}
                    for o in validated_input.draft_orders
                ]
                result = self.propose_orders(orders_dict)

            elif tool_name == "submit_orders":
                # Convert OrderModel list to dict list for internal method
                orders_dict = [
                    {"from": o.from_, "to": o.to, "ships": o.ships}
                    for o in validated_input.orders
                ]
                result = self.submit_orders(orders_dict)

            elif tool_name == "memory_query":
                records = self.memory_query(
                    validated_input.table, validated_input.filter_dict
                )
                result = {"records": records}

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
            r.get("turn") == turn and r.get("star") == star_id
            for r in self.memory["battle_log"]
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
                winner_entity = (
                    attacker_id if winner_role == "attacker" else defender_id
                )
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

            logger.info(
                f"Recorded PvP battle at {star_id} (turn {turn}): {winner} won"
            )

    def _add_discovery_record(self, turn: int, star) -> None:
        """Add discovery record for newly visited stars.

        Args:
            turn: Current turn number
            star: Star object from game.stars
        """
        star_id = star.id

        # Check if already recorded
        existing = any(
            r.get("star") == star_id for r in self.memory["discovery_log"]
        )

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
