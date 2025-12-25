"""Example usage of strategic logging during gameplay.

This script demonstrates how strategic metrics are automatically logged
during LLM gameplay and how to read the JSONL logs afterward.
"""

import json
from pathlib import Path

from src.agent.langgraph_player import LangGraphPlayer
from src.models.game import Game


def run_game_with_logging(num_turns: int = 5) -> str:
    """Run a game and return the log file path.

    Args:
        num_turns: Number of turns to play

    Returns:
        Path to the generated log file
    """
    print("Strategic Logging Example")
    print("=" * 60)
    print(f"\nRunning game for {num_turns} turns with strategic logging enabled...\n")

    # Create a game with a fixed seed for reproducibility
    game = Game(seed=42, turn=1)

    # Initialize game with minimal setup for testing
    from src.models.player import Player
    from src.models.star import Star

    # Create minimal game state
    stars = [
        Star(
            id="A",
            name="Alpha",
            x=1,
            y=2,
            base_ru=3,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        Star(
            id="E",
            name="Epsilon",
            x=10,
            y=8,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 10},
        ),
    ]
    game.stars = stars

    player_p1 = Player(id="p1", home_star="E", visited_stars={"E"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Create LLM player (using mock client for example)
    # Strategic logging is always-on, no flags needed
    llm_player = LangGraphPlayer(player_id="p2", use_mock=True)

    # Play the game (simplified - just log metrics each turn)
    for turn in range(num_turns):
        print(f"Turn {turn + 1}...")
        game.turn = turn + 1

        # Manually trigger metric logging (in real game, this happens in get_orders)
        llm_player._log_strategic_metrics(game)

    # Clean up
    llm_player.close()

    # Return log file path
    if llm_player.strategic_logger:
        log_path = str(llm_player.strategic_logger.log_path)
        print(f"\nLog written to: {log_path}\n")
        return log_path
    else:
        print("\nNo logs were written (logger not initialized)\n")
        return ""


def read_and_display_logs(log_path: str) -> None:
    """Read and display strategic logs in a human-readable format.

    Args:
        log_path: Path to the JSONL log file
    """
    if not log_path or not Path(log_path).exists():
        print("Log file not found")
        return

    print("=" * 60)
    print("STRATEGIC METRICS LOG")
    print("=" * 60)

    with open(log_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Parse JSON line
            metrics = json.loads(line)

            print(f"\nTurn {metrics['turn']}")
            print("-" * 60)

            # Display key metrics
            spatial = metrics["spatial_awareness"]
            expansion = metrics["expansion"]
            resources = metrics["resources"]
            garrison = metrics["garrison"]

            print(f"  Stars Controlled: {expansion['stars_controlled']}")
            print(f"  Total Ships: {metrics['fleets']['total_ships']}")
            print(f"  Production: {resources['total_production_ru']} RU/turn")
            print(f"  Production Ratio: {resources['production_ratio']:.2f}")
            print(f"  Home Garrison: {garrison['home_star_garrison']} ships")
            print(f"  Threat Level: {garrison['threat_level']}")
            print(f"  Opponent Home Discovered: {spatial['opponent_home_discovered']}")

            # Display territorial advantage
            territory = metrics["territory"]
            print(f"  Territorial Advantage: {territory['territorial_advantage']:+.2f}")

    print("\n" + "=" * 60)
    print(f"\nTotal turns logged: {line_num}")


def display_json_format(log_path: str, num_lines: int = 1) -> None:
    """Display raw JSON format for the first few lines.

    Args:
        log_path: Path to the JSONL log file
        num_lines: Number of lines to display
    """
    if not log_path or not Path(log_path).exists():
        return

    print("\n" + "=" * 60)
    print(f"RAW JSONL FORMAT (first {num_lines} line(s))")
    print("=" * 60)

    with open(log_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= num_lines:
                break

            # Parse and pretty-print
            metrics = json.loads(line)
            print(json.dumps(metrics, indent=2))

            if i < num_lines - 1:
                print("\n" + "-" * 60 + "\n")


def main():
    """Run the example."""
    # Run a game with logging
    log_path = run_game_with_logging(num_turns=5)

    if log_path:
        # Display metrics in readable format
        read_and_display_logs(log_path)

        # Show raw JSON format
        display_json_format(log_path, num_lines=1)

        print("\n" + "=" * 60)
        print("ANALYSIS TIPS")
        print("=" * 60)
        print("""
The JSONL format enables easy analysis:

1. Stream processing: Read line-by-line without loading entire file
2. jq queries: Use jq for filtering and analysis
   Example: jq '.resources.production_ratio' game_*_strategic.jsonl
3. Pandas analysis: Load into DataFrame for statistical analysis
   df = pd.read_json('game_*_strategic.jsonl', lines=True)
4. Time series: Track metric evolution over turns
5. Comparison: Compare strategies across different games
        """)


if __name__ == "__main__":
    main()
