#!/usr/bin/env python3
"""Space Conquest - Main entry point.

A turn-based 4X strategy game where players compete to capture
each other's home stars through fleet management and combat.
"""

import argparse
import logging
import sys

from src.agent.llm_player import LLMPlayer
from src.engine.map_generator import generate_map
from src.engine.turn_executor import TurnExecutor
from src.interface.display import DisplayManager
from src.interface.human_player import HumanPlayer
from src.models.game import Game
from src.utils.serialization import load_game, save_game


class GameOrchestrator:
    """Manages turn loop and player coordination."""

    def __init__(self, game: Game, p1_controller, p2_controller, use_tui: bool = False):
        """Initialize game orchestrator.

        Args:
            game: Initial game state
            p1_controller: Controller for player 1 (HumanPlayer or LLMPlayer)
            p2_controller: Controller for player 2 (HumanPlayer or LLMPlayer)
            use_tui: If True, skip welcome message (TUI shows its own)
        """
        self.game = game
        self.players = {"p1": p1_controller, "p2": p2_controller}
        self.turn_executor = TurnExecutor()
        self.display = DisplayManager()
        self.use_tui = use_tui
        self.last_combat_events = []
        self.last_hyperspace_losses = []
        self.last_rebellion_events = []

        # Extract and store p2 model ID for display name generation
        if isinstance(p2_controller, LLMPlayer):
            self.game.p2_model_id = p2_controller.client.model_id

    def run(self) -> Game:
        """Main game loop.

        Executes turns until victory condition is met.

        Returns:
            Final game state with winner set
        """
        if not self.use_tui:
            print("\n" + "=" * 60)
            print("Space Conquest")
            print("=" * 60)
            print("\nGoal: Capture your opponent's home star to win!")
            print("Press Ctrl+C at any time to quit.\n")
            input("Press Enter to start the game...")

        try:
            while not self.game.winner:
                # Get orders from both players - each sees only their perspective (fog-of-war)
                orders = {}
                for pid, controller in self.players.items():
                    # Get orders from this player
                    try:
                        orders[pid] = controller.get_orders(self.game)
                    except KeyboardInterrupt:
                        print("\nGame interrupted. Exiting...")
                        sys.exit(0)
                    except Exception as e:
                        print(f"Error getting orders from {pid}: {e}")
                        orders[pid] = []

                # Execute turn
                try:
                    self.game, combat_events, hyperspace_losses, rebellion_events = (
                        self.turn_executor.execute_turn(self.game, orders)
                    )
                    # Store events for display at start of next turn
                    self.last_combat_events = combat_events
                    self.last_hyperspace_losses = hyperspace_losses
                    self.last_rebellion_events = rebellion_events
                except Exception as e:
                    print(f"Error executing turn: {e}")
                    print("Game cannot continue. Exiting...")
                    sys.exit(1)

                # Check for victory
                if self.game.winner:
                    self._show_victory(
                        combat_events, hyperspace_losses, rebellion_events
                    )
                    break

        except KeyboardInterrupt:
            print("\n\nGame interrupted by user. Exiting...")
            sys.exit(0)

        return self.game

    def _show_victory(self, combat_events, hyperspace_losses, rebellion_events) -> None:
        """Display enhanced victory message.

        Args:
            combat_events: Combat events from the final turn
            hyperspace_losses: Hyperspace losses from the final turn
            rebellion_events: Rebellion events from the final turn
        """
        # Use the enhanced victory screen
        self.display.show_enhanced_victory(
            self.game, combat_events, hyperspace_losses, rebellion_events
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Space Conquest - Turn-based 4X Strategy Game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Start new game, human vs human (text mode)
  %(prog)s --tui                  # Start with terminal user interface (TUI)
  %(prog)s --tui --mode hvl       # TUI mode, human vs LLM
  %(prog)s --mode hvh --seed 42   # Specific seed
  %(prog)s --load savegame.json   # Load saved game
  %(prog)s --save mygame.json     # Auto-save after game
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["hvh", "hvl", "lvl"],
        default="hvh",
        help="Game mode: hvh=human vs human, hvl=human vs LLM, lvl=LLM vs LLM (default: hvh)",
    )
    parser.add_argument(
        "--model",
        choices=["haiku", "haiku45", "sonnet", "opus"],
        default="haiku",
        help="LLM model for AI player: haiku=fast/cheap, haiku45=Claude 4.5, sonnet=balanced, opus=most capable (default: haiku)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for map generation (default: 42)",
    )
    parser.add_argument(
        "--load", type=str, metavar="FILE", help="Load game from JSON file"
    )
    parser.add_argument(
        "--save",
        type=str,
        metavar="FILE",
        help="Save game to JSON file after completion",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (shows verbose LLM tool calls and iterations)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Use terminal user interface (TUI) for human players instead of basic text mode",
    )

    args = parser.parse_args()

    # Configure logging to display LLM reasoning and tool use
    # This shows all the LLM's thinking when verbose=True in LLMPlayer
    # Use DEBUG level when --debug flag is set, otherwise INFO for cleaner output
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(message)s",  # Show log level with message
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Initialize game
    if args.load:
        print(f"Loading game from {args.load}...")
        try:
            game = load_game(args.load)
            print(f"Game loaded successfully (Turn {game.turn}, Seed {game.seed})")
        except FileNotFoundError:
            print(f"Error: File {args.load} not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading game: {e}")
            sys.exit(1)
    else:
        print(f"Generating new map with seed {args.seed}...")
        game = generate_map(args.seed)
        print("Map generated successfully!")

    # Check if TUI mode is requested with unsupported game mode
    if args.tui and args.mode == "lvl":
        print("Error: --tui flag does not work with --mode lvl (LLM vs LLM)")
        print("TUI mode requires at least one human player")
        sys.exit(1)

    # Create player controllers
    if args.mode == "hvh":
        if args.tui:
            from src.interface.tui_player import TUIPlayer
            p1 = TUIPlayer("p1")
            p2 = TUIPlayer("p2")
        else:
            p1 = HumanPlayer("p1")
            p2 = HumanPlayer("p2")
    elif args.mode == "hvl":
        print(f"Initializing Human vs LLM game (using {args.model})...")
        if args.tui:
            from src.interface.tui_player import TUIPlayer
            p1 = TUIPlayer("p1")
        else:
            p1 = HumanPlayer("p1")
        try:
            # Try to use real Bedrock client, fall back to mock if unavailable
            p2 = LLMPlayer("p2", use_mock=False, model=args.model, verbose=args.debug)
            print("LLM player initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize Bedrock client: {e}")
            print("Falling back to mock LLM player (for testing only)")
            p2 = LLMPlayer("p2", use_mock=True, verbose=args.debug)
    else:  # lvl
        print(f"Initializing LLM vs LLM game (both using {args.model})...")
        try:
            p1 = LLMPlayer("p1", use_mock=False, model=args.model, verbose=args.debug)
            p2 = LLMPlayer("p2", use_mock=False, model=args.model, verbose=args.debug)
            print("Both LLM players initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize Bedrock client: {e}")
            print("Falling back to mock LLM players (for testing only)")
            p1 = LLMPlayer("p1", use_mock=True, verbose=args.debug)
            p2 = LLMPlayer("p2", use_mock=True, verbose=args.debug)

    # Run game
    orchestrator = GameOrchestrator(game, p1, p2, use_tui=args.tui)
    final_game = orchestrator.run()

    # Save if requested
    if args.save:
        print(f"\nSaving game to {args.save}...")
        try:
            save_game(final_game, args.save)
            print("Game saved successfully!")
        except Exception as e:
            print(f"Error saving game: {e}")


if __name__ == "__main__":
    main()
