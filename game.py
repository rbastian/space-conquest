#!/usr/bin/env python3
"""Space Conquest - Main entry point.

A turn-based 4X strategy game where players compete to capture
each other's home stars through fleet management and combat.
"""

import argparse
import logging
import sys

from src.agent.langgraph_player import LangGraphPlayer
from src.engine.map_generator import generate_map
from src.engine.turn_executor import TurnExecutor
from src.interface.display import DisplayManager
from src.interface.human_player import HumanPlayer
from src.models.game import Game
from src.models.order import Order
from src.utils.serialization import load_game, save_game


class GameOrchestrator:
    """Manages turn loop and player coordination."""

    def __init__(self, game: Game, p1_controller, p2_controller, use_tui: bool = False):
        """Initialize game orchestrator.

        Args:
            game: Initial game state
            p1_controller: Controller for player 1 (HumanPlayer or LangGraphPlayer)
            p2_controller: Controller for player 2 (HumanPlayer or LangGraphPlayer)
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
        if isinstance(p2_controller, LangGraphPlayer):
            self.game.p2_model_id = p2_controller.client.model_id

    def run(self) -> Game:
        """Main game loop."""
        # Show welcome message
        if not self.use_tui:
            print("\n" + "=" * 60)
            print("Space Conquest")
            print("=" * 60)
            print("\nGoal: Capture your opponent's home star to win!")
            print("Press Ctrl+C at any time to quit.\n")

            # Only wait for Enter if there's a human player
            has_human = any(isinstance(p, HumanPlayer) for p in self.players.values())
            if has_human:
                input("Press Enter to start the game...")
            else:
                print("Starting AI vs AI game...\n")

        try:
            while not self.game.winner:
                # Pre-turn: movement, combat, rebellions (BEFORE player sees state)
                self._execute_pre_turn_logic()

                if self.game.winner:
                    self._show_victory()
                    break

                # Order collection: players see state and give orders
                orders = self._collect_player_orders()

                # Post-turn: process orders, production
                self._execute_post_turn_logic(orders)

        except KeyboardInterrupt:
            print("\n\nGame interrupted by user. Exiting...")
            sys.exit(0)

        return self.game

    def _execute_pre_turn_logic(self):
        """Execute pre-turn game logic (movement, combat, rebellions, victory check).

        This runs BEFORE players see the game state. After this, turn counter increments.

        Updates:
            - self.last_combat_events
            - self.last_hyperspace_losses
            - self.last_rebellion_events
        """
        try:
            self.game, combat_events, hyperspace_losses, rebellion_events = (
                self.turn_executor.execute_pre_turn_logic(self.game)
            )
            self.last_combat_events = combat_events
            self.last_hyperspace_losses = hyperspace_losses
            self.last_rebellion_events = rebellion_events
        except Exception as e:
            print(f"Error executing pre-turn logic: {e}")
            print("Game cannot continue. Exiting...")
            sys.exit(1)

    def _collect_player_orders(self) -> dict[str, list[Order]]:
        """Collect orders from both players.

        Returns:
            Dictionary mapping player ID to list of orders
        """
        orders = {}
        for pid, controller in self.players.items():
            try:
                orders[pid] = controller.get_orders(self.game)
            except KeyboardInterrupt:
                raise  # Re-raise to be caught by outer try/except
            except Exception as e:
                print(f"Error getting orders from {pid}: {e}")
                orders[pid] = []
        return orders

    def _execute_post_turn_logic(self, orders: dict[str, list[Order]]):
        """Execute post-turn game logic (order processing, production).

        This runs AFTER players submit orders.

        Args:
            orders: Dictionary mapping player ID to list of orders
        """
        try:
            self.game = self.turn_executor.execute_post_turn_logic(self.game, orders)
        except Exception as e:
            print(f"Error executing post-turn logic: {e}")
            print("Game cannot continue. Exiting...")
            sys.exit(1)

    def _show_victory(self) -> None:
        """Display enhanced victory message."""
        # Use the enhanced victory screen with stored events
        self.display.show_enhanced_victory(
            self.game,
            self.last_combat_events,
            self.last_hyperspace_losses,
            self.last_rebellion_events,
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Space Conquest - Turn-based 4X Strategy Game",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                      # Start new game, human vs human (text mode)
  %(prog)s --tui                                # Start with terminal user interface (TUI)
  %(prog)s --tui --mode hvl                     # TUI mode, human vs LLM (AWS Bedrock)
  %(prog)s --mode hvl --provider openai --model gpt-4o  # Human vs OpenAI GPT-4
  %(prog)s --mode hvl --provider ollama --model llama3  # Human vs local Ollama model
  %(prog)s --mode hvh --seed 42                 # Specific seed
  %(prog)s --load savegame.json                 # Load saved game
  %(prog)s --save mygame.json                   # Auto-save after game
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["hvh", "hvl", "lvl"],
        default="hvh",
        help="Game mode: hvh=human vs human, hvl=human vs LLM, lvl=LLM vs LLM (default: hvh)",
    )
    parser.add_argument(
        "--provider",
        choices=["bedrock", "openai", "anthropic", "ollama"],
        default="bedrock",
        help="LLM provider: bedrock=AWS Bedrock, openai=OpenAI API, anthropic=Anthropic API, ollama=local models (default: bedrock)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (provider-specific). Examples: "
        "Bedrock: haiku, sonnet, opus | "
        "OpenAI: gpt-4o, gpt-4o-mini, gpt-3.5-turbo | "
        "Anthropic: claude-3-5-sonnet-20241022, haiku, opus | "
        "Ollama: llama3, mistral, mixtral (default: provider-specific default)",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default=None,
        help="API base URL (for Ollama, default: http://localhost:11434)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for map generation (default: 42)",
    )
    parser.add_argument("--load", type=str, metavar="FILE", help="Load game from JSON file")
    parser.add_argument(
        "--save",
        type=str,
        metavar="FILE",
        help="Save game to JSON file after completion",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and verbose AI reasoning (shows AI's thought process, uses more tokens/costs more)",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Use terminal user interface (TUI) for human players instead of basic text mode",
    )

    args = parser.parse_args()

    # Configure logging to display LLM reasoning and tool use
    # This shows all the LLM's thinking when verbose=True in LangGraphPlayer
    # Use DEBUG level when --debug flag is set, otherwise INFO for cleaner output
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(message)s",  # Show log level with message
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress noisy HTTP request logs from httpx, openai, and httpcore
    # These are moved to DEBUG level - only visible with --debug flag
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

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
        model_display = args.model or f"{args.provider} default"
        print(
            f"Initializing Human vs LLM game ({args.provider} provider, model: {model_display})..."
        )
        if args.tui:
            from src.interface.tui_player import TUIPlayer

            p1 = TUIPlayer("p1")
        else:
            p1 = HumanPlayer("p1")
        try:
            # Try to use real LLM client, fall back to mock if unavailable
            p2 = LangGraphPlayer(
                "p2",
                use_mock=False,
                provider=args.provider,
                model=args.model,
                api_base=args.api_base,
                verbose=args.debug,
            )
            print("LLM player initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize {args.provider} client: {e}")
            print("Falling back to mock LLM player (for testing only)")
            p2 = LangGraphPlayer("p2", use_mock=True, verbose=args.debug)
    else:  # lvl
        model_display = args.model or f"{args.provider} default"
        print(f"Initializing LLM vs LLM game ({args.provider} provider, model: {model_display})...")
        try:
            p1 = LangGraphPlayer(
                "p1",
                use_mock=False,
                provider=args.provider,
                model=args.model,
                api_base=args.api_base,
                verbose=args.debug,
            )
            p2 = LangGraphPlayer(
                "p2",
                use_mock=False,
                provider=args.provider,
                model=args.model,
                api_base=args.api_base,
                verbose=args.debug,
            )
            print("Both LLM players initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize {args.provider} client: {e}")
            print("Falling back to mock LLM players (for testing only)")
            p1 = LangGraphPlayer("p1", use_mock=True, verbose=args.debug)
            p2 = LangGraphPlayer("p2", use_mock=True, verbose=args.debug)

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
