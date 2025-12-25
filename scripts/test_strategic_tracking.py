#!/usr/bin/env python3
"""Test script to verify strategic tracking system works end-to-end.

This script:
1. Runs a short game with the LLM player
2. Verifies strategic metrics are logged to JSONL
3. Analyzes the game logs
4. Displays the analysis report
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.langgraph_player import LangGraphPlayer  # noqa: E402
from src.analysis.game_analyzer import GameAnalyzer  # noqa: E402
from src.engine.map_generator import generate_map  # noqa: E402
from src.engine.turn_executor import TurnExecutor  # noqa: E402


class SimpleOpponentPlayer:
    """Minimal opponent that just passes turns - for quick testing."""

    def __init__(self, player_id: str):
        self.player_id = player_id

    def get_orders(self, game):
        """Return empty orders (pass turn)."""
        return []


def run_test_game(seed: int = 42, max_turns: int = 5):
    """Run a short test game with strategic tracking.

    Args:
        seed: Random seed for map generation
        max_turns: Maximum turns to run

    Returns:
        tuple: (game, log_file_path)
    """
    print("=" * 80)
    print("STRATEGIC TRACKING SYSTEM TEST")
    print("=" * 80)
    print(f"\nSeed: {seed}")
    print(f"Max Turns: {max_turns}")
    print("\nPlayer 1: Simple (passes all turns)")
    print("Player 2: LLM Agent (with strategic tracking)")
    print()

    # Generate map
    print("1. Generating map...")
    game = generate_map(seed)
    print(f"   ✓ Map generated with {len(game.stars)} stars")

    # Create players
    print("\n2. Initializing players...")
    p1 = SimpleOpponentPlayer("p1")
    print("   ✓ Simple opponent created")

    try:
        p2 = LangGraphPlayer("p2", use_mock=True, model="sonnet", verbose=False)
        print("   ✓ LLM player created (mock mode)")
    except Exception as e:
        print(f"   ✗ Failed to create LLM player: {e}")
        return None, None

    # Game loop
    print("\n3. Running game...")
    turn_executor = TurnExecutor()

    for turn_num in range(max_turns):
        if game.winner:
            break

        print(f"   - Turn {game.turn}...", end=" ")

        # Get orders
        p1_orders = p1.get_orders(game)
        try:
            p2_orders = p2.get_orders(game)
        except Exception as e:
            print(f"\n   ✗ Error getting LLM orders: {e}")
            p2_orders = []

        # Execute turn
        try:
            game, _, _, _ = turn_executor.execute_turn(game, {"p1": p1_orders, "p2": p2_orders})
            print("✓")
        except Exception as e:
            print(f"\n   ✗ Error executing turn: {e}")
            break

    # Close LLM player to flush logs
    print("\n4. Closing LLM player and flushing logs...")
    try:
        p2.close()
        print("   ✓ Logs flushed")
    except Exception as e:
        print(f"   ✗ Error closing player: {e}")

    # Find the log file
    log_file = Path("logs") / f"game_seed{seed}_turn1_strategic.jsonl"
    print(f"\n5. Checking for log file: {log_file}")

    if log_file.exists():
        print("   ✓ Log file exists")
        return game, log_file
    else:
        print("   ✗ Log file not found")
        print("\n   Available log files:")
        logs_dir = Path("logs")
        if logs_dir.exists():
            for f in logs_dir.glob("*.jsonl"):
                print(f"      - {f.name}")
        else:
            print("      (logs directory doesn't exist)")
        return game, None


def verify_log_file(log_file: Path):
    """Verify the log file contents.

    Args:
        log_file: Path to JSONL log file

    Returns:
        bool: True if valid, False otherwise
    """
    print("\n6. Verifying log file contents...")

    try:
        with open(log_file) as f:
            lines = f.readlines()

        if not lines:
            print("   ✗ Log file is empty")
            return False

        print(f"   ✓ Log file has {len(lines)} turn(s)")

        # Parse each line
        for i, line in enumerate(lines, 1):
            try:
                metrics = json.loads(line)

                # Check for required keys
                required_keys = [
                    "turn",
                    "spatial_awareness",
                    "expansion",
                    "resources",
                    "fleets",
                    "garrison",
                    "territory",
                ]

                missing_keys = [key for key in required_keys if key not in metrics]
                if missing_keys:
                    print(f"   ✗ Turn {i}: Missing keys: {missing_keys}")
                    return False

                print(
                    f"   ✓ Turn {metrics['turn']}: All metrics present "
                    f"(stars={metrics['expansion']['stars_controlled']}, "
                    f"ships={metrics['fleets']['total_ships']})"
                )

            except json.JSONDecodeError as e:
                print(f"   ✗ Turn {i}: Invalid JSON: {e}")
                return False

        return True

    except Exception as e:
        print(f"   ✗ Error reading log file: {e}")
        return False


def analyze_game(log_file: Path):
    """Analyze the game and display report.

    Args:
        log_file: Path to JSONL log file
    """
    print("\n7. Analyzing game...")

    try:
        analyzer = GameAnalyzer(str(log_file))
        print("   ✓ Analyzer initialized")

        print("\n8. Generating analysis report...")
        analysis = analyzer.analyze()
        print("   ✓ Analysis complete")

        print("\n" + "=" * 80)
        print("ANALYSIS REPORT")
        print("=" * 80)

        # Generate and display report
        report = analyzer.generate_report()
        print(report)

        return analysis

    except Exception as e:
        print(f"   ✗ Error analyzing game: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run the end-to-end test."""
    print("\nStarting strategic tracking system test...\n")

    # Run test game
    game, log_file = run_test_game(seed=42, max_turns=5)

    if game is None:
        print("\n❌ TEST FAILED: Could not run game")
        return 1

    if log_file is None:
        print("\n❌ TEST FAILED: Log file not created")
        return 1

    # Verify log file
    if not verify_log_file(log_file):
        print("\n❌ TEST FAILED: Log file verification failed")
        return 1

    # Analyze game
    analysis = analyze_game(log_file)

    if analysis is None:
        print("\n❌ TEST FAILED: Analysis failed")
        return 1

    # Success
    print("\n" + "=" * 80)
    print("✅ TEST PASSED: Strategic tracking system working correctly!")
    print("=" * 80)
    print("\nThe system successfully:")
    print("  1. ✓ Generated a game map")
    print("  2. ✓ Initialized LLM player with tracking")
    print("  3. ✓ Ran multiple game turns")
    print("  4. ✓ Logged strategic metrics to JSONL")
    print("  5. ✓ Verified log file format")
    print("  6. ✓ Analyzed gameplay metrics")
    print("  7. ✓ Generated analysis report")
    print(f"\nLog file: {log_file}")
    print(f"Overall score: {analysis['overall_score']:.1f}/100")
    print(f"Grade: {analysis['grade']}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
