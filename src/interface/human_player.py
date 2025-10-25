"""Human player controller for CLI interaction.

This module provides the HumanPlayer class which handles getting orders
from human players via command-line interface.
"""

from typing import List

from ..engine.combat import CombatEvent, RebellionEvent
from ..engine.movement import HyperspaceLoss
from ..models.game import Game
from ..models.order import Order
from .command_parser import CommandParser, OrderParseError, ErrorType
from .display import DisplayManager
from .renderer import MapRenderer


class HumanPlayer:
    """Human player controller class.

    Handles CLI interaction for human players, including displaying
    the map, getting orders, and showing game state.
    """

    def __init__(self, player_id: str):
        """Initialize human player controller.

        Args:
            player_id: Player ID ("p1" or "p2")
        """
        self.player_id = player_id
        self.renderer = MapRenderer()
        self.display = DisplayManager()
        self.parser = CommandParser()

    def _format_error_message(self, error_type: ErrorType, message: str) -> str:
        """Format error message with emoji and optional help.

        Args:
            error_type: Classification of the error
            message: Error message content

        Returns:
            Formatted error message string
        """
        # All errors start with ❌ emoji
        formatted = f"❌ {message}"

        # Only Unknown Command errors show help hint
        if error_type == ErrorType.UNKNOWN_COMMAND:
            formatted += "\n\nAvailable commands: move, done, list, clear, help, status, quit"
            formatted += "\nExample: move 5 ships from A to B"

        return formatted

    def _dict_to_combat_event(self, d: dict) -> CombatEvent:
        """Convert dictionary to CombatEvent object.

        Args:
            d: Dictionary containing combat event data

        Returns:
            CombatEvent object
        """
        return CombatEvent(
            star_id=d["star_id"],
            star_name=d["star_name"],
            combat_type=d["combat_type"],
            attacker=d["attacker"],
            defender=d["defender"],
            attacker_ships=d["attacker_ships"],
            defender_ships=d["defender_ships"],
            winner=d.get("winner"),
            attacker_survivors=d["attacker_survivors"],
            defender_survivors=d["defender_survivors"],
            attacker_losses=d["attacker_losses"],
            defender_losses=d["defender_losses"],
            control_before=d.get("control_before"),
            control_after=d.get("control_after"),
            simultaneous=d.get("simultaneous", False),
        )

    def _dict_to_hyperspace_loss(self, d: dict) -> HyperspaceLoss:
        """Convert dictionary to HyperspaceLoss object.

        Args:
            d: Dictionary containing hyperspace loss data

        Returns:
            HyperspaceLoss object
        """
        return HyperspaceLoss(
            fleet_id=d["fleet_id"],
            owner=d["owner"],
            ships=d["ships"],
            origin=d["origin"],
            dest=d["dest"],
        )

    def _dict_to_rebellion_event(self, d: dict) -> RebellionEvent:
        """Convert dictionary to RebellionEvent object.

        Args:
            d: Dictionary containing rebellion event data

        Returns:
            RebellionEvent object
        """
        return RebellionEvent(
            star=d["star"],
            star_name=d["star_name"],
            owner=d["owner"],
            ru=d["ru"],
            garrison_before=d["garrison_before"],
            rebel_ships=d["rebel_ships"],
            outcome=d["outcome"],
            garrison_after=d["garrison_after"],
            rebel_survivors=d["rebel_survivors"],
        )

    def get_orders(self, game: Game) -> List[Order]:
        """Get orders from human player via CLI with continuous input flow.

        Displays the current game state and prompts the player for orders.
        Uses continuous input loop where players can queue multiple orders
        without interruption. Validates orders immediately before queuing.

        Args:
            game: Current game state

        Returns:
            List of Order objects (may be empty if player passes)
        """
        player = game.players[self.player_id]

        # Clear screen for clean display (optional)
        print("\n" * 2)

        # Show turn summary with reports from last turn
        # Convert dictionaries to typed objects for display
        combat_events = None
        if hasattr(game, "combats_last_turn") and game.combats_last_turn:
            # Convert dictionaries to CombatEvent objects
            combat_events = [
                self._dict_to_combat_event(d) for d in game.combats_last_turn
            ]

        hyperspace_losses = None
        if hasattr(game, "hyperspace_losses_last_turn") and game.hyperspace_losses_last_turn:
            # Convert dictionaries to HyperspaceLoss objects, filter for this player
            all_losses = [
                self._dict_to_hyperspace_loss(d) for d in game.hyperspace_losses_last_turn
            ]
            hyperspace_losses = [
                loss for loss in all_losses if loss.owner == self.player_id
            ]

        rebellion_events = None
        if hasattr(game, "rebellions_last_turn") and game.rebellions_last_turn:
            # Convert dictionaries to RebellionEvent objects
            rebellion_events = [
                self._dict_to_rebellion_event(d) for d in game.rebellions_last_turn
            ]

        self.display.show_turn_summary(
            player, game, combat_events, hyperspace_losses, rebellion_events
        )

        # Show map
        print("Map:")
        map_str = self.renderer.render_with_coords(player, game.stars)
        print(map_str)
        print()

        # Get orders with continuous input
        print("Enter orders (type 'done' to submit, 'help' for commands):")
        print()

        orders = self._get_orders_continuous(game, player)

        return orders

    def _get_orders_continuous(self, game: Game, player) -> List[Order]:
        """Continuous order input loop with command support.

        Supports:
        - move X from A to B: Queue an order
        - done: Submit all queued orders
        - list: Show queued orders
        - clear: Clear all queued orders
        - help: Show help

        Args:
            game: Current game state
            player: Player object

        Returns:
            List of validated orders
        """
        orders = []
        commitment_tracker = {}  # Track ships committed per star

        while True:
            try:
                # Prompt for command with turn number
                command = input(f"[Turn {game.turn}] [{self.player_id}] > ").strip()

                # Empty input - ignore and re-prompt
                if not command:
                    continue

                # Parse command
                cmd_lower = command.lower()

                # Handle 'done' command
                if cmd_lower in ("done", "end"):
                    count = len(orders)
                    if count == 0:
                        print("Submitting 0 orders (passing turn)...")
                    else:
                        print(f"Submitting {count} order{'s' if count != 1 else ''}...")
                    break

                # Handle 'list' command
                if cmd_lower in ("list", "ls"):
                    self._show_queued_orders(orders)
                    continue

                # Handle 'clear' command
                if cmd_lower in ("clear", "reset"):
                    count = len(orders)
                    orders.clear()
                    commitment_tracker.clear()
                    if count == 0:
                        print("No orders to clear")
                    else:
                        print(f"Cleared {count} order{'s' if count != 1 else ''}")
                    continue

                # Handle 'help' command
                if cmd_lower in ("help", "h", "?"):
                    self._show_continuous_help()
                    continue

                # Handle 'status' command
                if cmd_lower in ("status", "st"):
                    self.display.show_turn_summary(player, game)
                    print("Map:")
                    print(self.renderer.render_with_coords(player, game.stars))
                    print()
                    continue

                # Handle 'quit' command
                if cmd_lower in ("quit", "exit", "q"):
                    print("\nExiting game. Thanks for playing!")
                    raise SystemExit(0)

                # Try to parse as order
                try:
                    order = self.parser.parse(command)

                    if order is None:
                        # Parser returned None for unrecognized command
                        # This shouldn't happen now with OrderParseError, but keep as fallback
                        print(self._format_error_message(
                            ErrorType.UNKNOWN_COMMAND,
                            f"Unknown command: '{cmd_lower.split()[0] if cmd_lower.split() else cmd_lower}'"
                        ))
                        continue

                    # Pre-validate order before queuing
                    error = self._validate_order_pre_queue(
                        game, player, order, commitment_tracker
                    )

                    if error:
                        # Validation error - no help hint
                        print(self._format_error_message(ErrorType.VALIDATION_ERROR, error))
                        continue

                    # Order is valid - queue it
                    orders.append(order)

                    # Update commitment tracker
                    if order.from_star not in commitment_tracker:
                        commitment_tracker[order.from_star] = 0
                    commitment_tracker[order.from_star] += order.ships

                    # Show success feedback
                    self._show_order_queued(order, orders, commitment_tracker)

                except OrderParseError as e:
                    # Parser raised classified error
                    print(self._format_error_message(e.error_type, e.message))

                except ValueError as e:
                    # Unexpected ValueError (fallback - shouldn't happen)
                    print(self._format_error_message(ErrorType.SYNTAX_ERROR, str(e)))

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'done' to submit queued orders.")
                continue

            except Exception as e:
                # Truly unexpected error
                print(f"❌ Unexpected error: {e}")

        return orders

    def _validate_order_pre_queue(
        self, game: Game, player, order: Order, commitment_tracker: dict
    ) -> str:
        """Validate order before queuing (pre-validation).

        Checks:
        - Ship count > 0
        - Stars exist
        - Not same star
        - Player owns origin star
        - Sufficient ships (accounting for already queued orders)

        Args:
            game: Current game state
            player: Player object
            order: Order to validate
            commitment_tracker: Dict tracking ships committed per star

        Returns:
            Error message if invalid, empty string if valid
        """
        # Check ships > 0
        if order.ships <= 0:
            return f"Invalid ship count: must be positive (got {order.ships})"

        # Check stars exist
        from_star = None
        to_star = None
        for star in game.stars:
            if star.id == order.from_star:
                from_star = star
            if star.id == order.to_star:
                to_star = star

        if from_star is None and to_star is None:
            return f"Stars '{order.from_star}' and '{order.to_star}' do not exist"
        if from_star is None:
            return f"Origin star '{order.from_star}' does not exist"
        if to_star is None:
            return f"Destination star '{order.to_star}' does not exist"

        # Check not same star
        if order.from_star == order.to_star:
            return f"Cannot send fleet from {order.from_star} to itself"

        # Check ownership
        if from_star.owner != player.id:
            return f"You do not control star '{order.from_star}'"

        # Check sufficient ships (accounting for already committed ships)
        available = from_star.stationed_ships.get(player.id, 0)
        already_committed = commitment_tracker.get(order.from_star, 0)
        remaining = available - already_committed

        if order.ships > remaining:
            return (
                f"Insufficient ships at {order.from_star}\n"
                f"Requested: {order.ships}, Available: {available}, "
                f"Already committed: {already_committed}, Remaining: {remaining}"
            )

        return ""  # Valid

    def _show_order_queued(
        self, order: Order, orders: List[Order], commitment_tracker: dict
    ) -> None:
        """Show feedback after order is queued.

        Args:
            order: Order that was just queued
            orders: All queued orders
            commitment_tracker: Dict tracking ships committed per star
        """
        # Show success message
        print(
            f"✓ Order queued: {order.ships} ships from {order.from_star} to {order.to_star}"
        )

        # Show summary line
        order_count = len(orders)
        committed_stars = sorted(commitment_tracker.keys())
        committed_str = ", ".join(
            f"{star}({commitment_tracker[star]})" for star in committed_stars
        )
        print(f"  Orders: {order_count} | Committed: {committed_str}")

    def _show_queued_orders(self, orders: List[Order]) -> None:
        """Show all queued orders.

        Args:
            orders: List of queued orders
        """
        if not orders:
            print("No orders queued")
            return

        print("Queued orders:")
        for i, order in enumerate(orders, 1):
            print(
                f"  {i}. Move {order.ships} ships: {order.from_star} → {order.to_star}"
            )

    def _show_continuous_help(self) -> None:
        """Show help for continuous input mode."""
        print("\n=== Space Conquest - Command Help ===\n")
        print("Core commands:")
        print("  move <ships> from <star> to <star>  - Queue an order")
        print(
            "  done                                 - Submit all queued orders and end turn"
        )
        print("  list                                 - Show all queued orders")
        print("  clear                                - Remove all queued orders")
        print("  help                                 - Show this help message")
        print()
        print("Other commands:")
        print("  status                               - Show current game state")
        print("  quit                                 - Exit the game")
        print()
        print("Examples:")
        print("  move 5 ships from A to B")
        print("  move 10 from C to D")
        print("  done")
        print()
        print("Note: You can enter multiple orders before typing 'done'")
        print("      Empty input is ignored (just re-prompts)")
        print()

    def show_turn_result(self, game: Game) -> None:
        """Show the result of the turn after execution.

        Args:
            game: Game state after turn execution
        """
        player = game.players[self.player_id]

        print(f"\n{'=' * 60}")
        print(f"Turn {game.turn - 1} Complete")
        print(f"{'=' * 60}\n")

        # Show updated state
        self.display.show_turn_summary(player, game)

        # Check for victory
        if game.winner:
            self.display.show_victory(game)

        # Wait for player to continue
        input("Press Enter to continue...")
