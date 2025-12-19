"""TUI-based player controller for Space Conquest."""

import sys

from ..models.game import Game
from ..models.order import Order
from .tui_app import SpaceConquestTUI


class TUIPlayer:
    """Player controller using the terminal user interface (TUI)."""

    def __init__(self, player_id: str):
        """Initialize TUI player.

        Args:
            player_id: Player ID ("p1" or "p2")
        """
        self.player_id = player_id

    def get_orders(self, game: Game) -> list[Order]:
        """Get orders from player using TUI.

        Args:
            game: Current game state

        Returns:
            List of orders submitted by the player

        Raises:
            KeyboardInterrupt: If player chooses to quit the game
        """
        # Create and run TUI app for this turn
        app = SpaceConquestTUI(game, self.player_id)

        try:
            orders = app.run(mouse=False)
        except Exception:
            # If the app was closed unexpectedly, treat as quit
            print("\nGame interrupted. Exiting...")
            sys.exit(0)

        # If orders is None, user quit via quit command
        if orders is None:
            print("\nGame interrupted by user. Exiting...")
            sys.exit(0)

        return orders if orders else []
