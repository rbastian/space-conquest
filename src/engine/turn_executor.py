"""Main turn execution orchestrator.

This module coordinates the turn phases in the correct order:
1. Fleet Movement (Phase 1)
2. Combat Resolution (Phase 2)
3. Rebellion Resolution (Phase 3)
4. Victory Assessment (Phase 4)
5. Display Rendering & Order Collection (Phase 5) - happens in caller
6. Order Processing (Phase 6)
7. Ship Production (Phase 7)

The turn counter increments AFTER phases 1-4 but BEFORE phase 5 (display/orders),
so that players see the results of movement/combat/rebellions when making decisions.

Architecture:
Each phase is an independent, composable method. Orchestration methods compose
these phases in the correct order. This makes it easy to reorder, test, or modify
individual phases without affecting others.
"""

import logging
from dataclasses import dataclass

from ..models.fleet import Fleet
from ..models.game import Game
from ..models.order import Order
from ..models.star import Star
from ..utils.distance import chebyshev_distance
from .combat import CombatEvent, RebellionEvent, process_combat
from .movement import HyperspaceLoss, process_fleet_movement
from .production import (
    process_production,
    process_rebellions,
    process_rebellions_and_production,
)
from .victory import check_victory

logger = logging.getLogger(__name__)


@dataclass
class PhaseResults:
    """Results from executing pre-display phases (1-4).

    Contains all events that occurred during phases 1-4 so they can be
    displayed to players before they submit orders.
    """

    combat_events: list[CombatEvent]
    hyperspace_losses: list[HyperspaceLoss]
    rebellion_events: list[RebellionEvent]


class TurnExecutor:
    """Orchestrates the turn phases in the correct order.

    Each phase is an independent method that can be tested and modified separately.
    Orchestration methods compose these phases in the correct execution order.
    """

    # =========================================================================
    # INDEPENDENT PHASE METHODS
    # Each method handles ONE phase and returns updated game state + events
    # =========================================================================

    def execute_phase_movement(self, game: Game) -> tuple[Game, list[HyperspaceLoss]]:
        """Execute Phase 1: Fleet Movement.

        All fleets move one step toward their destination. Fleets that have
        traveled their full distance arrive and merge with stationed ships
        or trigger combat.

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game state, hyperspace loss events)
        """
        game, hyperspace_losses = process_fleet_movement(game)

        # Store hyperspace losses in game state for observation
        game.hyperspace_losses_last_turn = [
            {
                "fleet_id": loss.fleet_id,
                "owner": loss.owner,
                "ships": loss.ships,
                "origin": loss.origin,
                "dest": loss.dest,
            }
            for loss in hyperspace_losses
        ]

        return game, hyperspace_losses

    def execute_phase_combat(self, game: Game) -> tuple[Game, list[CombatEvent]]:
        """Execute Phase 2: Combat Resolution.

        Resolve all combats at stars where multiple players have ships.
        Updates star ownership and stationed ships based on combat outcomes.

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game state, combat events)
        """
        game, combat_events = process_combat(game)

        # Store combat events in game state for observation
        # IMPORTANT: Store BEFORE victory check so final turn combats are visible
        game.combats_last_turn = [
            {
                "star_id": event.star_id,
                "star_name": event.star_name,
                "combat_type": event.combat_type,
                "attacker": event.attacker,
                "defender": event.defender,
                "attacker_ships": event.attacker_ships,
                "defender_ships": event.defender_ships,
                "winner": event.winner,
                "attacker_survivors": event.attacker_survivors,
                "defender_survivors": event.defender_survivors,
                "attacker_losses": event.attacker_losses,
                "defender_losses": event.defender_losses,
                "control_before": event.control_before,
                "control_after": event.control_after,
                "simultaneous": event.simultaneous,
            }
            for event in combat_events
        ]

        # Update combat history (keep last 5 turns)
        game.combats_history.append(game.combats_last_turn)
        if len(game.combats_history) > 5:
            game.combats_history = game.combats_history[-5:]

        return game, combat_events

    def execute_phase_rebellions(self, game: Game) -> tuple[Game, list[RebellionEvent]]:
        """Execute Phase 3: Rebellion Resolution.

        Check each player-controlled star for rebellions. Under-garrisoned stars
        have a 50% chance to rebel. Rebellions trigger combat between garrison
        and rebel forces.

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game state, rebellion events)
        """
        game, rebellion_events = process_rebellions(game)

        # Store rebellion events in game state for observation
        game.rebellions_last_turn = [
            {
                "star": event.star,
                "star_name": event.star_name,
                "owner": event.owner,
                "ru": event.ru,
                "garrison_before": event.garrison_before,
                "rebel_ships": event.rebel_ships,
                "outcome": event.outcome,
                "garrison_after": event.garrison_after,
                "rebel_survivors": event.rebel_survivors,
            }
            for event in rebellion_events
        ]

        return game, rebellion_events

    def execute_phase_victory_check(self, game: Game) -> Game:
        """Execute Phase 4: Victory Assessment.

        Check if either player has won by controlling opponent's home star,
        or if a draw condition has been met (e.g., both eliminated).

        Args:
            game: Current game state

        Returns:
            Updated game state (game.winner set if game ended)
        """
        check_victory(game)
        return game

    def execute_phase_orders(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """Execute Phase 6: Order Processing.

        Process player orders to create fleets. Validates orders and deducts
        ships from origin stars. Invalid orders are logged but don't crash.

        Args:
            game: Current game state
            orders: Dictionary mapping player ID to list of orders
                   e.g., {"p1": [Order(...), ...], "p2": [...]}

        Returns:
            Updated game state with new fleets created
        """
        game = self._process_orders(game, orders)
        return game

    def execute_phase_production(self, game: Game) -> Game:
        """Execute Phase 7: Ship Production.

        Produce ships at all controlled stars that did not rebel this turn.
        Home stars produce 4 ships, other stars produce base_ru ships.

        Args:
            game: Current game state

        Returns:
            Updated game state with production added
        """
        # Track which stars rebelled this turn (no production for them)
        rebelled_star_ids = {event["star"] for event in game.rebellions_last_turn}

        game = process_production(game, rebelled_star_ids)
        return game

    # =========================================================================
    # ORCHESTRATION METHODS
    # Compose independent phases in the correct execution order
    # =========================================================================

    def execute_pre_turn_logic(
        self, game: Game
    ) -> tuple[Game, list[CombatEvent], list[HyperspaceLoss], list[RebellionEvent]]:
        """Execute pre-turn game logic: movement, combat, rebellions, victory check.

        This runs BEFORE players see state. After this, turn counter increments.

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game, combat events, hyperspace losses, rebellion events)
            If game.winner is set, the game has ended
        """
        # Movement
        game, hyperspace_losses = self._move_fleets(game)

        # Combat
        game, combat_events = self._resolve_combat(game)

        # Rebellions
        game, rebellion_events = self._process_rebellions(game)

        # Victory check
        game = self._check_victory(game)

        # Increment turn counter
        game.turn += 1

        return game, combat_events, hyperspace_losses, rebellion_events

    def execute_post_turn_logic(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """Execute post-turn game logic: order processing, production.

        This runs AFTER players submit orders.

        Args:
            game: Current game state (with turn already incremented)
            orders: Dictionary mapping player ID to list of orders

        Returns:
            Updated game state
        """
        # Process orders
        game = self._process_orders_wrapper(game, orders)

        # Production
        game = self._process_production_wrapper(game)

        return game

    # =========================================================================
    # PRIVATE HELPER METHODS FOR NEW ORCHESTRATION
    # These delegate to the existing phase methods
    # =========================================================================

    def _move_fleets(self, game: Game) -> tuple[Game, list[HyperspaceLoss]]:
        """Execute fleet movement."""
        return self.execute_phase_movement(game)

    def _resolve_combat(self, game: Game) -> tuple[Game, list[CombatEvent]]:
        """Resolve combat at all stars."""
        return self.execute_phase_combat(game)

    def _process_rebellions(self, game: Game) -> tuple[Game, list[RebellionEvent]]:
        """Process rebellions at under-garrisoned stars."""
        return self.execute_phase_rebellions(game)

    def _check_victory(self, game: Game) -> Game:
        """Check for victory conditions."""
        return self.execute_phase_victory_check(game)

    def _process_orders_wrapper(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """Process player orders."""
        return self.execute_phase_orders(game, orders)

    def _process_production_wrapper(self, game: Game) -> Game:
        """Process ship production."""
        # Track which stars rebelled (no production for them)
        rebelled_star_ids = {event["star"] for event in game.rebellions_last_turn}
        game = process_production(game, rebelled_star_ids)
        return game

    # =========================================================================
    # OLD ORCHESTRATION METHODS (kept for reference)
    # =========================================================================

    def execute_pre_display_phases(self, game: Game) -> tuple[Game, PhaseResults]:
        """Execute phases 1-4 (before display/order collection).

        DEPRECATED: Use execute_pre_turn_logic() instead.

        This orchestration method runs all phases that happen before players
        see the game state and submit orders. After these phases, the turn
        counter is incremented so the display shows the correct turn number.

        Phases executed:
        1. Fleet Movement
        2. Combat Resolution
        3. Rebellion Resolution
        4. Victory Assessment

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game state, phase results)
            Note: If game.winner is set, the game has ended
        """
        # Phase 1: Fleet Movement
        game, hyperspace_losses = self.execute_phase_movement(game)

        # Phase 2: Combat Resolution
        game, combat_events = self.execute_phase_combat(game)

        # Phase 3: Rebellion Resolution
        game, rebellion_events = self.execute_phase_rebellions(game)

        # Phase 4: Victory Assessment
        game = self.execute_phase_victory_check(game)

        # Increment turn counter BEFORE displaying and collecting orders
        # This ensures the display shows the correct turn after phases 1-4 execute
        game.turn += 1

        results = PhaseResults(
            combat_events=combat_events,
            hyperspace_losses=hyperspace_losses,
            rebellion_events=rebellion_events,
        )

        return game, results

    def execute_post_order_phases(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """Execute phases 6-7 (after order collection).

        DEPRECATED: Use execute_post_turn_logic() instead.

        This orchestration method runs all phases that happen after players
        submit orders. These phases prepare the game state for the next turn.

        Phases executed:
        6. Order Processing
        7. Ship Production

        Args:
            game: Current game state (with turn already incremented)
            orders: Dictionary mapping player ID to list of orders
                   e.g., {"p1": [Order(...), ...], "p2": [...]}

        Returns:
            Updated game state
        """
        # Phase 6: Order Processing
        game = self.execute_phase_orders(game, orders)

        # Phase 7: Ship Production
        game = self.execute_phase_production(game)

        return game

    # =========================================================================
    # BACKWARD COMPATIBILITY - DEPRECATED
    # Old numbered phase methods for existing tests
    # =========================================================================

    def execute_phases_1_to_4(
        self, game: Game
    ) -> tuple[Game, list[CombatEvent], list[HyperspaceLoss], list[RebellionEvent]]:
        """DEPRECATED: Use execute_pre_turn_logic() instead."""
        return self.execute_pre_turn_logic(game)

    def execute_phases_6_to_7(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """DEPRECATED: Use execute_post_turn_logic() instead."""
        return self.execute_post_turn_logic(game, orders)

    # Backward compatibility methods (renamed but same behavior)
    def execute_phases_1_to_3(
        self, game: Game
    ) -> tuple[Game, list[CombatEvent], list[HyperspaceLoss]]:
        """Legacy method: Execute phases 1-3 (Movement, Combat, Victory).

        DEPRECATED: This method exists for backward compatibility only.
        Use execute_phases_1_to_4() instead, which also includes rebellions.

        Args:
            game: Current game state

        Returns:
            Tuple of (updated game state, combat events, hyperspace losses)
        """
        game, combat_events, hyperspace_losses, _ = self.execute_phases_1_to_4(game)
        return game, combat_events, hyperspace_losses

    def execute_phases_4_to_5(
        self, game: Game, orders: dict[str, list[Order]]
    ) -> tuple[Game, list[RebellionEvent]]:
        """Legacy method: Execute phases 4-5 (Orders, Rebellions & Production).

        DEPRECATED: This method exists for backward compatibility only.
        It executes rebellions and production together (old Phase 5 behavior).

        For new code, use execute_phases_6_to_7() which only does orders and production,
        since rebellions now happen in Phase 3 (before orders).

        Args:
            game: Current game state (with turn already incremented)
            orders: Dictionary mapping player ID to list of orders

        Returns:
            Tuple of (updated game state, rebellion events)
        """
        # Phase 4: Process Orders
        game = self._process_orders(game, orders)

        # Phase 5: Rebellions & Production (combined for backward compatibility)
        game, rebellion_events = process_rebellions_and_production(game)

        # Store rebellion events in game state for observation
        game.rebellions_last_turn = [
            {
                "star": event.star,
                "star_name": event.star_name,
                "owner": event.owner,
                "ru": event.ru,
                "garrison_before": event.garrison_before,
                "rebel_ships": event.rebel_ships,
                "outcome": event.outcome,
                "garrison_after": event.garrison_after,
                "rebel_survivors": event.rebel_survivors,
            }
            for event in rebellion_events
        ]

        return game, rebellion_events

    def execute_turn(
        self, game: Game, orders: dict[str, list[Order]]
    ) -> tuple[Game, list[CombatEvent], list[HyperspaceLoss], list[RebellionEvent]]:
        """Execute one complete turn (legacy method for backward compatibility).

        BACKWARD COMPATIBILITY: This method wraps the new orchestration methods
        to maintain the old method signature.

        WARNING: This method executes all phases in one go, which means the display
        will show state BEFORE phases 1-4 execute. This is incorrect for the main
        game loop but may be needed for tests that expect the old behavior.

        For the main game loop, use execute_pre_display_phases() followed by
        execute_post_order_phases() with display/order collection in between.

        Args:
            game: Current game state
            orders: Dictionary mapping player ID to list of orders
                   e.g., {"p1": [Order(...), ...], "p2": [...]}

        Returns:
            Tuple of (updated game state, combat events, hyperspace losses, rebellion events)
        """
        # Execute phases 1-4 (Movement, Combat, Rebellions, Victory)
        game, results = self.execute_pre_display_phases(game)

        # Check if game ended
        if game.winner:
            return game, results.combat_events, results.hyperspace_losses, results.rebellion_events

        # Execute phases 6-7 (Orders, Production)
        game = self.execute_post_order_phases(game, orders)

        return game, results.combat_events, results.hyperspace_losses, results.rebellion_events

    # =========================================================================
    # INTERNAL HELPER METHODS
    # Private methods for order processing and validation
    # =========================================================================

    def _process_orders(self, game: Game, orders: dict[str, list[Order]]) -> Game:
        """Process player orders and create fleets with graceful error handling.

        Validates and executes player move orders with hybrid validation:
        - Strict: Over-commitment (total ships > available) rejects entire order set
        - Lenient: Individual order errors skip that order, execute rest
        - No crashes: All errors are logged, not raised

        Args:
            game: Current game state
            orders: Dictionary mapping player ID to list of orders

        Returns:
            Updated game state with new fleets created
        """
        # Clear previous turn's errors
        game.order_errors.clear()

        # Create star lookup dictionary for performance (O(1) instead of O(n))
        star_dict = {star.id: star for star in game.stars}

        for player_id, player_orders in orders.items():
            if not player_orders:
                continue

            errors = self._process_player_orders(game, player_id, player_orders, star_dict)

            if errors:
                # Log errors but don't crash
                for error in errors:
                    logger.warning(f"Player {player_id} order error: {error}")
                # Store errors on game state for display to player
                game.order_errors[player_id] = errors

        return game

    def _process_player_orders(
        self,
        game: Game,
        player_id: str,
        orders: list[Order],
        star_dict: dict[str, Star],
    ) -> list[str]:
        """Process orders for one player with error handling.

        Uses hybrid validation approach:
        1. Check for over-commitment first (strict - rejects entire set)
        2. Process individual orders leniently (skip invalid, execute valid)

        Args:
            game: Current game state
            player_id: ID of player issuing orders
            orders: List of orders from this player
            star_dict: Dictionary mapping star ID to Star object for O(1) lookups

        Returns:
            List of error messages (empty if all succeeded)
        """
        errors = []

        # Step 1: Check for over-commitment (strict)
        over_commitment_error = self._check_over_commitment(game, player_id, orders, star_dict)
        if over_commitment_error:
            errors.append(over_commitment_error)
            return errors  # Reject entire order set

        # Step 2: Execute individual orders (lenient)
        for i, order in enumerate(orders):
            try:
                self._validate_single_order(game, player_id, order, star_dict)
                self._execute_order(game, player_id, order, star_dict)
            except ValueError as e:
                errors.append(
                    f"Order {i} ({order.from_star} -> {order.to_star}, "
                    f"{order.ships} ships): {str(e)}"
                )
                # Continue to next order (skip this one)

        return errors

    def _check_over_commitment(
        self,
        game: Game,
        player_id: str,
        orders: list[Order],
        star_dict: dict[str, Star],
    ) -> str | None:
        """Check if player is trying to send more ships than available from any star.

        Args:
            game: Current game state
            player_id: ID of player issuing orders
            orders: List of all orders from this player
            star_dict: Dictionary mapping star ID to Star object for O(1) lookups

        Returns:
            Error message if over-committed, None if valid
        """
        ships_by_star: dict[str, int] = {}

        for order in orders:
            if order.from_star not in ships_by_star:
                ships_by_star[order.from_star] = 0
            ships_by_star[order.from_star] += order.ships

        for star_id, total_ships in ships_by_star.items():
            # Look up the star (O(1) instead of O(n))
            origin_star = star_dict.get(star_id)

            if origin_star is None:
                # Star doesn't exist - this will be caught in individual validation
                continue

            # Check ownership BEFORE checking ship availability
            if origin_star.owner != player_id:
                return f"You do not control star '{star_id}'"

            # Check available ships
            available = origin_star.stationed_ships.get(player_id, 0)
            if total_ships > available:
                # Build detailed error showing all orders from this star
                orders_from_star = [
                    f"{o.from_star}->{o.to_star} ({o.ships} ships)"
                    for o in orders
                    if o.from_star == star_id
                ]
                return (
                    f"Over-commitment at star {star_id}: "
                    f"Total ordered: {total_ships} ships, Available: {available} ships. "
                    f"Orders from {star_id}: [{', '.join(orders_from_star)}]"
                )

        return None

    def _validate_single_order(
        self, game: Game, player_id: str, order: Order, star_dict: dict[str, Star]
    ) -> None:
        """Validate a single order. Raises ValueError if invalid.

        Args:
            game: Current game state
            player_id: ID of player issuing order
            order: Order to validate
            star_dict: Dictionary mapping star ID to Star object for O(1) lookups

        Raises:
            ValueError: If order is invalid
        """
        # Check ships > 0 (should be caught by Order.__post_init__, but double-check)
        if order.ships <= 0:
            raise ValueError(f"Ship count must be positive, got {order.ships}")

        # Check stars exist (O(1) lookups instead of O(n))
        from_star = star_dict.get(order.from_star)
        to_star = star_dict.get(order.to_star)

        if from_star is None:
            raise ValueError(f"Origin star '{order.from_star}' does not exist")
        if to_star is None:
            raise ValueError(f"Destination star '{order.to_star}' does not exist")

        # Check not same star (should be caught by Order.__post_init__, but double-check)
        if order.from_star == order.to_star:
            raise ValueError("Cannot send fleet from star to itself")

        # Check ownership
        if from_star.owner != player_id:
            raise ValueError(f"You do not control star '{order.from_star}'")

        # Check sufficient ships (after over-commitment already checked)
        available = from_star.stationed_ships.get(player_id, 0)
        if order.ships > available:
            raise ValueError(
                f"Insufficient ships at {order.from_star}: "
                f"requested {order.ships}, available {available}"
            )

    def _execute_order(
        self, game: Game, player_id: str, order: Order, star_dict: dict[str, Star]
    ) -> None:
        """Execute a single validated order.

        Assumes order has already been validated by _validate_single_order.

        Args:
            game: Current game state
            player_id: ID of player issuing order
            order: Order to execute
            star_dict: Dictionary mapping star ID to Star object for O(1) lookups
        """
        # Find origin and destination stars (O(1) lookups instead of O(n))
        origin_star = star_dict[order.from_star]
        dest_star = star_dict[order.to_star]

        # Calculate distance
        distance = chebyshev_distance(origin_star.x, origin_star.y, dest_star.x, dest_star.y)

        # Deduct ships from origin star immediately
        # This ensures ships don't participate in combat after being ordered to depart
        origin_star.stationed_ships[player_id] -= order.ships

        # Create fleet
        fleet_id = f"{player_id}-{game.fleet_counter[player_id]:03d}"
        game.fleet_counter[player_id] += 1

        # IMPORTANT: Phase 1 (Fleet Movement) runs BEFORE Phase 4 (Orders Processing),
        # so fleets created this turn won't move until next turn's Phase 1.
        # To ensure correct arrival timing, we set dist_remaining = distance (not distance - 1).
        # The fleet will move for the first time in the NEXT turn's Phase 1.
        #
        # Example timeline for distance=1:
        # - Turn 0 Phase 1: (fleet doesn't exist yet)
        # - Turn 0 Phase 4: Fleet created with dist_remaining=1
        # - Turn 1 Phase 1: Fleet moves, dist_remaining 1→0, arrives
        # - Display at Turn 1 start shows: Turn 1 + 1 - 1 = "Arrives Turn 1" (correct!)
        fleet = Fleet(
            id=fleet_id,
            owner=player_id,
            ships=order.ships,
            origin=order.from_star,
            dest=order.to_star,
            dist_remaining=distance,
        )

        game.fleets.append(fleet)
