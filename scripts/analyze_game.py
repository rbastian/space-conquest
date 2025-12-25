#!/usr/bin/env python3
"""Command-line tool for analyzing LLM gameplay.

Usage:
    uv run scripts/analyze_game.py <log_file>
    uv run scripts/analyze_game.py --all [log_dir]

Examples:
    # Analyze a single game
    uv run scripts/analyze_game.py logs/game_abc123_strategic.jsonl

    # Analyze all games in logs directory
    uv run scripts/analyze_game.py --all

    # Analyze all games in a specific directory
    uv run scripts/analyze_game.py --all /path/to/logs
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.game_analyzer import GameAnalyzer, analyze_multiple_games


def print_usage():
    """Print usage information."""
    print(__doc__)


def main():
    """Main entry point for the CLI tool."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Check for --all flag
    if sys.argv[1] == "--all":
        # Multi-game analysis
        log_dir = sys.argv[2] if len(sys.argv) > 2 else "logs"

        try:
            results = analyze_multiple_games(log_dir)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Print multi-game summary
        print("=" * 70)
        print("MULTI-GAME ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Total Games Analyzed: {results.get('total_games', 0)}")

        if results.get("total_games", 0) == 0:
            print(f"\n{results.get('message', 'No games found')}")
            sys.exit(0)

        print(f"\nOverall Average Score: {results['avg_overall_score']:.1f}/100")

        print("\n--- Average Dimension Scores ---")
        for dim, score in results["avg_dimension_scores"].items():
            display_name = dim.replace("_", " ").title()
            print(f"{display_name}: {score:.1f}/100")

        print("\n--- Best Game ---")
        print(f"Game ID: {results['best_game']['game_id']}")
        print(
            f"Score: {results['best_game']['score']:.1f}/100 (Grade: {results['best_game']['grade']})"
        )

        print("\n--- Worst Game ---")
        print(f"Game ID: {results['worst_game']['game_id']}")
        print(
            f"Score: {results['worst_game']['score']:.1f}/100 (Grade: {results['worst_game']['grade']})"
        )

        print("\n--- Score Distribution ---")
        print(f"Range: {results['score_range']['min']:.1f} - {results['score_range']['max']:.1f}")
        print(f"Spread: {results['score_range']['spread']:.1f} points")

        print("\n--- Common Weaknesses ---")
        for weakness in results["common_weaknesses"]:
            print(f"  - {weakness}")

        print("=" * 70)

    elif sys.argv[1] in ["-h", "--help"]:
        print_usage()
        sys.exit(0)

    else:
        # Single game analysis
        log_file = sys.argv[1]

        try:
            analyzer = GameAnalyzer(log_file)
            report = analyzer.generate_report()
            print(report)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
