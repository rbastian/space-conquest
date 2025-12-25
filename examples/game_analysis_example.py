#!/usr/bin/env python3
"""Example demonstrating comprehensive game analysis capabilities.

This script shows how to:
1. Load and analyze a single game log
2. Generate detailed reports
3. Extract specific metrics for custom analysis
4. Analyze multiple games for trends
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.game_analyzer import GameAnalyzer, analyze_multiple_games


def analyze_single_game_example():
    """Example: Analyze a single game and extract insights."""
    print("=" * 70)
    print("EXAMPLE 1: Single Game Analysis")
    print("=" * 70)
    print()

    # Load and analyze a game
    log_file = "examples/sample_game_log.jsonl"
    analyzer = GameAnalyzer(log_file)

    # Get full analysis results
    analysis = analyzer.analyze()

    print(f"Game ID: {analysis['game_id']}")
    print(f"Overall Score: {analysis['overall_score']:.1f}/100")
    print(f"Grade: {analysis['grade']}")
    print()

    # Extract specific dimension details
    print("Spatial Awareness Details:")
    spatial = analysis["dimension_scores"]["spatial_awareness"]
    print(f"  Score: {spatial['score']:.1f}/100")
    print(f"  Assessment: {spatial['assessment']}")
    print(f"  Opponent discovered: {spatial['details']['opponent_discovered']}")
    print(f"  Discovery turn: {spatial['details']['discovery_turn']}")
    print()

    # Print recommendations
    print("Top Recommendations:")
    for i, rec in enumerate(analysis["recommendations"][:3], 1):
        print(f"  {i}. {rec}")
    print()


def generate_report_example():
    """Example: Generate human-readable report."""
    print("=" * 70)
    print("EXAMPLE 2: Generate Full Report")
    print("=" * 70)
    print()

    log_file = "examples/sample_game_log.jsonl"
    analyzer = GameAnalyzer(log_file)

    # Generate and print full report
    report = analyzer.generate_report()
    print(report)
    print()


def custom_analysis_example():
    """Example: Extract raw metrics for custom analysis."""
    print("=" * 70)
    print("EXAMPLE 3: Custom Metric Extraction")
    print("=" * 70)
    print()

    log_file = "examples/sample_game_log.jsonl"
    analyzer = GameAnalyzer(log_file)

    # Access raw metrics data
    print(f"Total turns logged: {len(analyzer.metrics)}")
    print()

    # Analyze production growth over time
    print("Production Growth Over Time:")
    for i, metric in enumerate(analyzer.metrics, 1):
        resources = metric["resources"]
        print(
            f"  Turn {metric['turn']:2d}: "
            f"{resources['total_production_ru']:3d} RU/turn "
            f"(ratio: {resources['production_ratio']:.2f})"
        )
    print()

    # Analyze fleet concentration trend
    print("Fleet Size Trend:")
    for i, metric in enumerate(analyzer.metrics, 1):
        fleets = metric["fleets"]
        avg_size = fleets["avg_offensive_fleet_size"]
        num_large = fleets["fleet_size_distribution"]["large"]
        print(
            f"  Turn {metric['turn']:2d}: "
            f"Avg size: {avg_size:5.1f} ships, "
            f"Large fleets: {num_large}"
        )
    print()


def multi_game_analysis_example():
    """Example: Analyze multiple games for trends."""
    print("=" * 70)
    print("EXAMPLE 4: Multi-Game Analysis")
    print("=" * 70)
    print()

    try:
        # Analyze all games in logs directory
        results = analyze_multiple_games("logs")

        print(f"Games analyzed: {results['total_games']}")
        print(f"Average overall score: {results['avg_overall_score']:.1f}/100")
        print()

        print("Average Dimension Scores:")
        for dim, score in results["avg_dimension_scores"].items():
            display_name = dim.replace("_", " ").title()
            print(f"  {display_name}: {score:.1f}/100")
        print()

        print("Best Game:")
        best = results["best_game"]
        print(f"  ID: {best['game_id']}")
        print(f"  Score: {best['score']:.1f}/100 (Grade: {best['grade']})")
        print()

        print("Worst Game:")
        worst = results["worst_game"]
        print(f"  ID: {worst['game_id']}")
        print(f"  Score: {worst['score']:.1f}/100 (Grade: {worst['grade']})")
        print()

        print("Common Weaknesses:")
        for weakness in results["common_weaknesses"]:
            print(f"  - {weakness}")
        print()

    except FileNotFoundError as e:
        print(f"Note: {e}")
        print("Run some games first to generate log files.")
        print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("GAME ANALYSIS TOOL - COMPREHENSIVE EXAMPLES")
    print("=" * 70)
    print()

    try:
        # Example 1: Single game analysis
        analyze_single_game_example()

        # Example 2: Full report generation
        # Commented out to keep output concise - uncomment to see full report
        # generate_report_example()

        # Example 3: Custom metric extraction
        custom_analysis_example()

        # Example 4: Multi-game analysis
        multi_game_analysis_example()

        print("=" * 70)
        print("Examples complete!")
        print("=" * 70)
        print()

        print("Next Steps:")
        print("1. Analyze your own games:")
        print("   uv run scripts/analyze_game.py logs/game_YOUR_ID_strategic.jsonl")
        print()
        print("2. Analyze all games:")
        print("   uv run scripts/analyze_game.py --all logs")
        print()
        print("3. Integrate into your workflow:")
        print("   - Run analyzer after each game to get immediate feedback")
        print("   - Track dimension scores over time to measure improvement")
        print("   - Use recommendations to tune LLM prompts and strategies")
        print()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure sample_game_log.jsonl exists in examples/ directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
