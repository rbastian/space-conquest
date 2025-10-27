"""Main turn execution orchestrator.

This module coordinates the 5 turn phases:
1. Fleet Movement
2. Combat Resolution
3. Victory Assessment
4. Orders Processing
5. Rebellions & Production
"""

import logging
from typing import Dict, List, Optional

from ..models.fleet import Fleet
from ..models.game import Game
from ..models.order import Order
from ..models.star import Star
from ..utils.distance import chebyshev_distance
from .combat import CombatEvent, RebellionEvent, process_combat
from .movement import HyperspaceLoss, process_fleet_movement
from .production import process_rebellions_and_production
from .victory import check_victory

logger = logging.getLogger(__name__)


class TurnExecutor:
    """Orchestrates the 5 turn phases."""

    def execute_turn(
        self, game: Game, orders: Dict[str, List[Order]]
    ) -> tuple[Game, List[CombatEvent], List[HyperspaceLoss], List[RebellionEvent]]:
        """Execute one complete turn.

        Args:
            game: Current game state
            orders: Dictionary mapping player ID to list of orders
                   e.g., {"p1": [Order(...), ...], "p2": [...]}

        Returns:
            Tuple of (updated game state, combat events, hyperspace losses, rebellion events)
        """
        # Phase 1: Fleet Movement
        game, hyperspace_losses = process_fleet_movement(game)

        # Store hyperspace losses in game state for observation
        # Convert HyperspaceLoss objects to dictionaries for storage
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

        # Phase 2: Combat Resolution
        game, combat_events = process_combat(game)

        # Store combat events in game state for observation
        # IMPORTANT: Store BEFORE victory check so final turn combats are visible
        # Convert CombatEvent objects to dictionaries for storage
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
        # Append current turn's combats to history
        game.combats_history.append(game.combats_last_turn)

        # Keep only last 5 turns (trim from front if needed)
        if len(game.combats_history) > 5:
            game.combats_history = game.combats_history[-5:]

        # Phase 3: Victory Assessment
        if check_victory(game):
            # Game has ended - don't process remaining phases
            # But combat events are already stored for final observations
            return game, combat_events, hyperspace_losses, []

        # Phase 4: Process Orders
        game = self._process_orders(game, orders)

        # Phase 5: Rebellions & Production
        game, rebellion_events = process_rebellions_and_production(game)

        # Store rebellion events in game state for observation
        # Convert RebellionEvent objects to dictionaries for storage
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

        # Increment turn counter
        game.turn += 1

        return game, combat_events, hyperspace_losses, rebellion_events

    def _process_orders(self, game: Game, orders: Dict[str, List[Order]]) -> Game:
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

            errors = self._process_player_orders(
                game, player_id, player_orders, star_dict
            )

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
        orders: List[Order],
        star_dict: Dict[str, Star],
    ) -> List[str]:
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
        over_commitment_error = self._check_over_commitment(
            game, player_id, orders, star_dict
        )
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
                    f"Order {i} ({order.from_star} -> {order.to_star}, {order.ships} ships): {str(e)}"
                )
                # Continue to next order (skip this one)

        return errors

    def _check_over_commitment(
        self,
        game: Game,
        player_id: str,
        orders: List[Order],
        star_dict: Dict[str, Star],
    ) -> Optional[str]:
        """Check if player is trying to send more ships than available from any star.

        Args:
            game: Current game state
            player_id: ID of player issuing orders
            orders: List of all orders from this player
            star_dict: Dictionary mapping star ID to Star object for O(1) lookups

        Returns:
            Error message if over-committed, None if valid
        """
        ships_by_star: Dict[str, int] = {}

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
        self, game: Game, player_id: str, order: Order, star_dict: Dict[str, Star]
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
                f"Insufficient ships at {order.from_star}: requested {order.ships}, available {available}"
            )

    def _execute_order(
        self, game: Game, player_id: str, order: Order, star_dict: Dict[str, Star]
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
        distance = chebyshev_distance(
            origin_star.x, origin_star.y, dest_star.x, dest_star.y
        )

        # Deduct ships from origin star immediately
        # This ensures ships don't participate in combat after being ordered to depart
        origin_star.stationed_ships[player_id] -= order.ships

        # Create fleet
        fleet_id = f"{player_id}-{game.fleet_counter[player_id]:03d}"
        game.fleet_counter[player_id] += 1

        fleet = Fleet(
            id=fleet_id,
            owner=player_id,
            ships=order.ships,
            origin=order.from_star,
            dest=order.to_star,
            dist_remaining=distance,
        )

        game.fleets.append(fleet)
