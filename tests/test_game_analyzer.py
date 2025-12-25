"""Tests for the game analyzer module.

Tests comprehensive analysis of strategic gameplay metrics from JSONL logs.
"""

import json
from pathlib import Path

import pytest

from src.analysis.game_analyzer import GameAnalyzer, analyze_multiple_games

# Sample metrics data for testing
SAMPLE_METRICS_EARLY_GAME = {
    "turn": 5,
    "spatial_awareness": {
        "llm_home_coords": (2, 3),
        "opponent_home_coords": (9, 7),
        "llm_home_quadrant": "upper-left",
        "opponent_home_quadrant": "lower-right",
        "opponent_home_discovered": True,
    },
    "expansion": {
        "stars_controlled": 3,
        "new_stars_this_turn": [],
        "avg_distance_from_home": 2.5,
        "nearest_unconquered_distance": 3.0,
        "expansion_pattern": "systematic",
    },
    "resources": {
        "total_production_ru": 12,
        "opponent_production_ru": 10,
        "production_ratio": 1.2,
        "production_advantage": 2,
    },
    "fleets": {
        "total_ships": 50,
        "num_fleets_in_flight": 2,
        "fleet_size_distribution": {"tiny": 0, "small": 1, "medium": 1, "large": 0},
        "largest_fleet_size": 30,
        "largest_fleet_pct_of_total": 60.0,
        "avg_offensive_fleet_size": 25.0,
    },
    "garrison": {
        "home_star_garrison": 10,
        "garrison_pct_of_total": 20.0,
        "nearest_enemy_fleet_distance": 8.0,
        "nearest_enemy_fleet_size": 15,
        "threat_level": "low",
        "garrison_appropriate": True,
    },
    "territory": {
        "stars_in_home_quadrant": 2,
        "stars_in_center_zone": 1,
        "stars_in_opponent_quadrant": 0,
        "territorial_advantage": 0.2,
    },
}

SAMPLE_METRICS_MID_GAME = {
    "turn": 20,
    "spatial_awareness": {
        "llm_home_coords": (2, 3),
        "opponent_home_coords": (9, 7),
        "llm_home_quadrant": "upper-left",
        "opponent_home_quadrant": "lower-right",
        "opponent_home_discovered": True,
    },
    "expansion": {
        "stars_controlled": 8,
        "new_stars_this_turn": [],
        "avg_distance_from_home": 4.2,
        "nearest_unconquered_distance": 2.5,
        "expansion_pattern": "systematic",
    },
    "resources": {
        "total_production_ru": 35,
        "opponent_production_ru": 25,
        "production_ratio": 1.4,
        "production_advantage": 10,
    },
    "fleets": {
        "total_ships": 120,
        "num_fleets_in_flight": 3,
        "fleet_size_distribution": {"tiny": 0, "small": 1, "medium": 1, "large": 1},
        "largest_fleet_size": 55,
        "largest_fleet_pct_of_total": 45.8,
        "avg_offensive_fleet_size": 35.0,
    },
    "garrison": {
        "home_star_garrison": 20,
        "garrison_pct_of_total": 16.7,
        "nearest_enemy_fleet_distance": 5.5,
        "nearest_enemy_fleet_size": 30,
        "threat_level": "medium",
        "garrison_appropriate": True,
    },
    "territory": {
        "stars_in_home_quadrant": 4,
        "stars_in_center_zone": 2,
        "stars_in_opponent_quadrant": 2,
        "territorial_advantage": 0.4,
    },
}

SAMPLE_METRICS_LATE_GAME = {
    "turn": 50,
    "spatial_awareness": {
        "llm_home_coords": (2, 3),
        "opponent_home_coords": (9, 7),
        "llm_home_quadrant": "upper-left",
        "opponent_home_quadrant": "lower-right",
        "opponent_home_discovered": True,
    },
    "expansion": {
        "stars_controlled": 15,
        "new_stars_this_turn": [],
        "avg_distance_from_home": 5.8,
        "nearest_unconquered_distance": 1.0,
        "expansion_pattern": "systematic",
    },
    "resources": {
        "total_production_ru": 65,
        "opponent_production_ru": 30,
        "production_ratio": 2.17,
        "production_advantage": 35,
    },
    "fleets": {
        "total_ships": 280,
        "num_fleets_in_flight": 4,
        "fleet_size_distribution": {"tiny": 0, "small": 0, "medium": 2, "large": 2},
        "largest_fleet_size": 80,
        "largest_fleet_pct_of_total": 28.6,
        "avg_offensive_fleet_size": 55.0,
    },
    "garrison": {
        "home_star_garrison": 35,
        "garrison_pct_of_total": 12.5,
        "nearest_enemy_fleet_distance": 10.0,
        "nearest_enemy_fleet_size": 20,
        "threat_level": "low",
        "garrison_appropriate": True,
    },
    "territory": {
        "stars_in_home_quadrant": 7,
        "stars_in_center_zone": 4,
        "stars_in_opponent_quadrant": 4,
        "territorial_advantage": 0.6,
    },
}


def create_test_log_file(metrics_list: list[dict], temp_dir: Path) -> Path:
    """Create a temporary JSONL log file with sample metrics.

    Args:
        metrics_list: List of metric dictionaries
        temp_dir: Temporary directory path

    Returns:
        Path to created log file
    """
    log_file = temp_dir / "game_test123_strategic.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for metrics in metrics_list:
            f.write(json.dumps(metrics) + "\n")
    return log_file


class TestGameAnalyzer:
    """Test suite for GameAnalyzer class."""

    def test_init_loads_metrics(self, tmp_path):
        """Test that analyzer loads metrics from JSONL file."""
        log_file = create_test_log_file([SAMPLE_METRICS_EARLY_GAME], tmp_path)

        analyzer = GameAnalyzer(str(log_file))

        assert len(analyzer.metrics) == 1
        assert analyzer.metrics[0]["turn"] == 5
        assert analyzer.game_id == "test123"
        assert analyzer.total_turns == 1

    def test_init_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            GameAnalyzer("/nonexistent/path.jsonl")

    def test_init_empty_file(self, tmp_path):
        """Test that ValueError is raised for empty file."""
        log_file = tmp_path / "empty.jsonl"
        log_file.touch()

        with pytest.raises(ValueError, match="empty"):
            GameAnalyzer(str(log_file))

    def test_init_invalid_json(self, tmp_path):
        """Test that ValueError is raised for malformed JSON."""
        log_file = tmp_path / "invalid.jsonl"
        with open(log_file, "w") as f:
            f.write("not json\n")

        with pytest.raises(ValueError, match="Invalid JSON"):
            GameAnalyzer(str(log_file))

    def test_analyze_full_game(self, tmp_path):
        """Test full game analysis with multiple turns."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        # Verify structure
        assert "overall_score" in analysis
        assert "grade" in analysis
        assert "dimension_scores" in analysis
        assert "insights" in analysis
        assert "recommendations" in analysis

        # Verify all dimensions present
        assert "spatial_awareness" in analysis["dimension_scores"]
        assert "expansion" in analysis["dimension_scores"]
        assert "resources" in analysis["dimension_scores"]
        assert "fleets" in analysis["dimension_scores"]
        assert "garrison" in analysis["dimension_scores"]
        assert "territory" in analysis["dimension_scores"]

        # Verify scores are in valid range
        assert 0 <= analysis["overall_score"] <= 100
        for dim_data in analysis["dimension_scores"].values():
            assert 0 <= dim_data["score"] <= 100
            assert "assessment" in dim_data
            assert "details" in dim_data

    def test_spatial_awareness_analysis(self, tmp_path):
        """Test spatial awareness dimension analysis."""
        # Early discovery (turn 5) should score high
        log_file = create_test_log_file([SAMPLE_METRICS_EARLY_GAME], tmp_path)
        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        spatial_score = analysis["dimension_scores"]["spatial_awareness"]["score"]
        assert spatial_score >= 85  # Early discovery should score well

        # Late discovery should score lower
        late_discovery = SAMPLE_METRICS_EARLY_GAME.copy()
        late_discovery["turn"] = 25
        log_file_late = create_test_log_file([late_discovery], tmp_path)
        analyzer_late = GameAnalyzer(str(log_file_late))
        analysis_late = analyzer_late.analyze()

        late_score = analysis_late["dimension_scores"]["spatial_awareness"]["score"]
        assert late_score < spatial_score  # Late discovery should score worse

    def test_expansion_analysis(self, tmp_path):
        """Test expansion strategy analysis."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        expansion = analysis["dimension_scores"]["expansion"]
        assert expansion["score"] > 0
        assert "expansion_rate" in expansion["details"]
        assert "initial_stars" in expansion["details"]
        assert "final_stars" in expansion["details"]

        # Verify expansion rate calculation
        initial = expansion["details"]["initial_stars"]
        final = expansion["details"]["final_stars"]
        assert final >= initial  # Should expand or stay same

    def test_resource_analysis(self, tmp_path):
        """Test resource control analysis."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        resources = analysis["dimension_scores"]["resources"]
        assert resources["score"] > 0

        # Good production ratio should score high
        assert resources["details"]["final_production_ratio"] > 1.0
        assert resources["score"] >= 70  # Should score well with 2.17 ratio

    def test_fleet_concentration_analysis(self, tmp_path):
        """Test fleet concentration analysis."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        fleets = analysis["dimension_scores"]["fleets"]
        assert fleets["score"] > 0
        assert "avg_fleet_size" in fleets["details"]
        assert "final_avg_fleet_size" in fleets["details"]
        assert "avg_large_fleets" in fleets["details"]

        # Large final fleet size should score well
        assert fleets["details"]["final_avg_fleet_size"] >= 50
        assert fleets["score"] >= 60

    def test_garrison_management_analysis(self, tmp_path):
        """Test garrison management analysis."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        garrison = analysis["dimension_scores"]["garrison"]
        assert garrison["score"] > 0
        assert "appropriateness_rate" in garrison["details"]

        # All turns have appropriate garrison
        assert garrison["details"]["appropriateness_rate"] == 1.0
        assert garrison["score"] == 100.0

    def test_territory_control_analysis(self, tmp_path):
        """Test territory control analysis."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        territory = analysis["dimension_scores"]["territory"]
        assert territory["score"] > 0
        assert "final_territorial_advantage" in territory["details"]
        assert "final_center_control" in territory["details"]
        assert "final_opponent_penetration" in territory["details"]

        # Positive advantage should score well
        assert territory["details"]["final_territorial_advantage"] > 0
        assert territory["score"] >= 60

    def test_overall_score_calculation(self, tmp_path):
        """Test overall score calculation."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        # Overall score should be weighted average
        assert 0 <= analysis["overall_score"] <= 100

        # Check that grade matches score
        score = analysis["overall_score"]
        grade = analysis["grade"]
        if score >= 90:
            assert grade == "A"
        elif score >= 80:
            assert grade == "B"
        elif score >= 70:
            assert grade == "C"
        elif score >= 60:
            assert grade == "D"
        else:
            assert grade == "F"

    def test_insights_generation(self, tmp_path):
        """Test insights generation."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        insights = analysis["insights"]
        assert "strengths" in insights
        assert "weaknesses" in insights
        assert isinstance(insights["strengths"], list)
        assert isinstance(insights["weaknesses"], list)
        assert len(insights["strengths"]) > 0
        assert len(insights["weaknesses"]) > 0

    def test_recommendations_generation(self, tmp_path):
        """Test recommendations generation."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        recommendations = analysis["recommendations"]
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 3
        assert len(recommendations) <= 5
        assert all(isinstance(rec, str) for rec in recommendations)

    def test_generate_report(self, tmp_path):
        """Test report generation."""
        metrics_list = [
            SAMPLE_METRICS_EARLY_GAME,
            SAMPLE_METRICS_MID_GAME,
            SAMPLE_METRICS_LATE_GAME,
        ]
        log_file = create_test_log_file(metrics_list, tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        report = analyzer.generate_report()

        # Verify report structure
        assert "STRATEGIC GAMEPLAY ANALYSIS" in report
        assert "Overall Performance" in report
        assert "Dimension Scores" in report
        assert "Key Insights" in report
        assert "Recommendations" in report
        assert "Detailed Metrics Summary" in report

        # Verify game info
        assert "Game: test123" in report
        assert "Duration: 3 turns" in report

    def test_analysis_caching(self, tmp_path):
        """Test that analysis results are cached."""
        log_file = create_test_log_file([SAMPLE_METRICS_EARLY_GAME], tmp_path)

        analyzer = GameAnalyzer(str(log_file))

        # First call
        analysis1 = analyzer.analyze()
        # Second call should return cached result
        analysis2 = analyzer.analyze()

        assert analysis1 is analysis2  # Same object reference


class TestMultiGameAnalysis:
    """Test suite for multi-game analysis."""

    def test_analyze_multiple_games(self, tmp_path):
        """Test analyzing multiple games."""
        # Create multiple game logs
        for i in range(3):
            metrics_list = [
                SAMPLE_METRICS_EARLY_GAME,
                SAMPLE_METRICS_MID_GAME,
                SAMPLE_METRICS_LATE_GAME,
            ]
            log_file = tmp_path / f"game_test{i}_strategic.jsonl"
            with open(log_file, "w", encoding="utf-8") as f:
                for metrics in metrics_list:
                    f.write(json.dumps(metrics) + "\n")

        results = analyze_multiple_games(str(tmp_path))

        assert results["total_games"] == 3
        assert "avg_overall_score" in results
        assert "avg_dimension_scores" in results
        assert "best_game" in results
        assert "worst_game" in results
        assert "common_weaknesses" in results
        assert "score_range" in results

    def test_analyze_no_games(self, tmp_path):
        """Test analyzing directory with no game logs."""
        results = analyze_multiple_games(str(tmp_path))

        assert results["total_games"] == 0
        assert "message" in results

    def test_analyze_nonexistent_directory(self):
        """Test analyzing nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            analyze_multiple_games("/nonexistent/directory")

    def test_analyze_with_invalid_logs(self, tmp_path):
        """Test analyzing with some invalid logs."""
        # Create one valid log
        _log_file1 = create_test_log_file([SAMPLE_METRICS_EARLY_GAME], tmp_path)

        # Create one invalid log
        log_file2 = tmp_path / "game_invalid_strategic.jsonl"
        with open(log_file2, "w") as f:
            f.write("not json\n")

        # Should skip invalid log and analyze valid one
        results = analyze_multiple_games(str(tmp_path))

        assert results["total_games"] == 1

    def test_multi_game_statistics(self, tmp_path):
        """Test statistical calculations across multiple games."""
        # Create games with different scores
        for i, metrics in enumerate([SAMPLE_METRICS_EARLY_GAME, SAMPLE_METRICS_LATE_GAME]):
            log_file = tmp_path / f"game_test{i}_strategic.jsonl"
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")

        results = analyze_multiple_games(str(tmp_path))

        # Verify statistics
        assert results["total_games"] == 2
        assert results["best_game"]["score"] >= results["worst_game"]["score"]
        assert results["score_range"]["spread"] >= 0
        assert results["score_range"]["min"] == results["worst_game"]["score"]
        assert results["score_range"]["max"] == results["best_game"]["score"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_turn_game(self, tmp_path):
        """Test analyzing a game with only one turn."""
        log_file = create_test_log_file([SAMPLE_METRICS_EARLY_GAME], tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        assert analysis["total_turns"] == 1
        assert "overall_score" in analysis

    def test_infinite_production_ratio(self, tmp_path):
        """Test handling infinite production ratio (opponent has 0)."""
        metrics = SAMPLE_METRICS_EARLY_GAME.copy()
        metrics["resources"]["opponent_production_ru"] = 0
        metrics["resources"]["production_ratio"] = float("inf")

        log_file = create_test_log_file([metrics], tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        # Should handle infinity gracefully
        resources = analysis["dimension_scores"]["resources"]
        assert resources["score"] == 100.0  # Max score for overwhelming advantage

    def test_no_fleets_in_flight(self, tmp_path):
        """Test handling game state with no fleets."""
        metrics = SAMPLE_METRICS_EARLY_GAME.copy()
        metrics["fleets"]["num_fleets_in_flight"] = 0
        metrics["fleets"]["avg_offensive_fleet_size"] = 0.0
        metrics["fleets"]["fleet_size_distribution"] = {
            "tiny": 0,
            "small": 0,
            "medium": 0,
            "large": 0,
        }

        log_file = create_test_log_file([metrics], tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        # Should handle zero fleets gracefully
        fleets = analysis["dimension_scores"]["fleets"]
        assert "score" in fleets
        assert fleets["score"] >= 0

    def test_never_discovered_opponent(self, tmp_path):
        """Test game where opponent is never discovered."""
        metrics = SAMPLE_METRICS_LATE_GAME.copy()
        metrics["spatial_awareness"]["opponent_home_discovered"] = False

        log_file = create_test_log_file([metrics], tmp_path)

        analyzer = GameAnalyzer(str(log_file))
        analysis = analyzer.analyze()

        # Should score poorly in spatial awareness
        spatial = analysis["dimension_scores"]["spatial_awareness"]
        assert spatial["score"] < 50
        assert "never" in spatial["details"]["discovery_speed"]
