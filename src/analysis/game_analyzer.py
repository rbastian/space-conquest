"""Comprehensive post-game analysis tool for strategic gameplay metrics.

This module analyzes JSONL log files produced by the strategic logger and generates
detailed reports with actionable insights for improving LLM gameplay performance.
"""

import json
from pathlib import Path


class GameAnalyzer:
    """Analyzes strategic gameplay metrics from JSONL logs.

    Provides comprehensive analysis across six strategic dimensions:
    - Spatial Awareness: Discovery and positioning relative to opponent
    - Expansion Strategy: Territory growth patterns and efficiency
    - Resource Control: Production capacity and economic performance
    - Fleet Concentration: Fleet size distribution and offensive capability
    - Garrison Management: Home defense and threat response
    - Territory Control: Quadrant dominance and strategic positioning
    """

    def __init__(self, log_file_path: str):
        """Load metrics from a strategic log file.

        Args:
            log_file_path: Path to JSONL log file

        Raises:
            FileNotFoundError: If log file doesn't exist
            ValueError: If log file is empty or malformed
        """
        self.log_file_path = Path(log_file_path)

        if not self.log_file_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_file_path}")

        # Load all metrics from JSONL file
        self.metrics = []
        with open(self.log_file_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    metric = json.loads(line)
                    self.metrics.append(metric)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}") from e

        if not self.metrics:
            raise ValueError(f"Log file is empty: {log_file_path}")

        # Extract game metadata
        self.game_id = self.log_file_path.stem.replace("game_", "").replace("_strategic", "")
        self.total_turns = len(self.metrics)
        self.first_turn = self.metrics[0].get("turn", 1)
        self.last_turn = self.metrics[-1].get("turn", self.total_turns)

        # Cache analysis results
        self._analysis_cache = None

    def analyze(self) -> dict:
        """Perform comprehensive analysis of gameplay.

        Returns:
            Dictionary with analysis results:
            - overall_score: 0-100 overall performance score
            - dimension_scores: Individual dimension scores and assessments
            - insights: Strengths, weaknesses, key findings
            - recommendations: Actionable improvement suggestions
            - metrics_summary: Statistical summaries of key metrics
        """
        if self._analysis_cache is not None:
            return self._analysis_cache

        # Analyze each dimension
        spatial_analysis = self._analyze_spatial_awareness()
        expansion_analysis = self._analyze_expansion()
        resource_analysis = self._analyze_resources()
        fleet_analysis = self._analyze_fleets()
        garrison_analysis = self._analyze_garrison()
        territory_analysis = self._analyze_territory()

        # Calculate overall score
        dimension_scores = {
            "spatial_awareness": spatial_analysis["score"],
            "expansion": expansion_analysis["score"],
            "resources": resource_analysis["score"],
            "fleets": fleet_analysis["score"],
            "garrison": garrison_analysis["score"],
            "territory": territory_analysis["score"],
        }

        overall_score = self._calculate_overall_score(dimension_scores)

        # Generate insights and recommendations
        recommendations = self._generate_recommendations(
            {
                "spatial": spatial_analysis,
                "expansion": expansion_analysis,
                "resources": resource_analysis,
                "fleets": fleet_analysis,
                "garrison": garrison_analysis,
                "territory": territory_analysis,
            }
        )

        # Compile results
        self._analysis_cache = {
            "game_id": self.game_id,
            "total_turns": self.total_turns,
            "overall_score": overall_score,
            "grade": self._score_to_grade(overall_score),
            "dimension_scores": {
                "spatial_awareness": {
                    "score": spatial_analysis["score"],
                    "assessment": spatial_analysis["assessment"],
                    "details": spatial_analysis,
                },
                "expansion": {
                    "score": expansion_analysis["score"],
                    "assessment": expansion_analysis["assessment"],
                    "details": expansion_analysis,
                },
                "resources": {
                    "score": resource_analysis["score"],
                    "assessment": resource_analysis["assessment"],
                    "details": resource_analysis,
                },
                "fleets": {
                    "score": fleet_analysis["score"],
                    "assessment": fleet_analysis["assessment"],
                    "details": fleet_analysis,
                },
                "garrison": {
                    "score": garrison_analysis["score"],
                    "assessment": garrison_analysis["assessment"],
                    "details": garrison_analysis,
                },
                "territory": {
                    "score": territory_analysis["score"],
                    "assessment": territory_analysis["assessment"],
                    "details": territory_analysis,
                },
            },
            "insights": self._generate_insights(dimension_scores),
            "recommendations": recommendations,
        }

        return self._analysis_cache

    def generate_report(self) -> str:
        """Generate human-readable report.

        Returns:
            Formatted text report with comprehensive analysis
        """
        analysis = self.analyze()

        lines = [
            "=" * 70,
            "STRATEGIC GAMEPLAY ANALYSIS",
            "=" * 70,
            f"Game: {analysis['game_id']}",
            f"Duration: {analysis['total_turns']} turns (Turn {self.first_turn} - {self.last_turn})",
            "",
            "--- Overall Performance ---",
            f"Score: {analysis['overall_score']:.1f}/100",
            f"Grade: {analysis['grade']}",
            "",
            "--- Dimension Scores ---",
        ]

        # Add dimension scores
        for dim_name, dim_data in analysis["dimension_scores"].items():
            display_name = dim_name.replace("_", " ").title()
            score = dim_data["score"]
            assessment = dim_data["assessment"]
            lines.append(f"{display_name}: {score:.1f}/100 - {assessment}")

        # Add insights
        lines.extend(
            [
                "",
                "--- Key Insights ---",
                "",
                "Strengths:",
            ]
        )
        for strength in analysis["insights"]["strengths"]:
            lines.append(f"  - {strength}")

        lines.append("")
        lines.append("Weaknesses:")
        for weakness in analysis["insights"]["weaknesses"]:
            lines.append(f"  - {weakness}")

        # Add recommendations
        lines.extend(
            [
                "",
                "--- Recommendations ---",
            ]
        )
        for i, rec in enumerate(analysis["recommendations"], 1):
            lines.append(f"{i}. {rec}")

        # Add detailed metrics summary
        lines.extend(
            [
                "",
                "--- Detailed Metrics Summary ---",
                "",
            ]
        )

        for dim_name, dim_data in analysis["dimension_scores"].items():
            display_name = dim_name.replace("_", " ").title()
            details = dim_data["details"]

            lines.append(f"{display_name}:")
            for key, value in details.items():
                if key not in ["score", "assessment"]:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def _analyze_spatial_awareness(self) -> dict:
        """Analyze spatial awareness and opponent discovery.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        # Check if opponent home was discovered
        opponent_discovered = False
        discovery_turn = None

        for i, metric in enumerate(self.metrics):
            spatial = metric.get("spatial_awareness", {})
            if spatial.get("opponent_home_discovered"):
                opponent_discovered = True
                discovery_turn = metric.get("turn", i + 1)
                break

        # Score based on discovery timing
        score = 0.0

        if opponent_discovered:
            # Earlier discovery is better
            if discovery_turn <= 5:
                score = 100.0
            elif discovery_turn <= 10:
                score = 85.0
            elif discovery_turn <= 20:
                score = 70.0
            elif discovery_turn <= 30:
                score = 55.0
            else:
                score = 40.0
        else:
            # Didn't discover opponent - poor spatial awareness
            score = 20.0

        # Assessment
        if score >= 85:
            assessment = "Excellent - Early opponent discovery"
        elif score >= 70:
            assessment = "Good - Timely opponent discovery"
        elif score >= 55:
            assessment = "Adequate - Slow opponent discovery"
        else:
            assessment = "Poor - Late or no opponent discovery"

        return {
            "score": score,
            "assessment": assessment,
            "opponent_discovered": opponent_discovered,
            "discovery_turn": discovery_turn,
            "discovery_speed": "early"
            if discovery_turn and discovery_turn <= 10
            else "late"
            if discovery_turn
            else "never",
        }

    def _analyze_expansion(self) -> dict:
        """Analyze expansion strategy and efficiency.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        if not self.metrics:
            return {"score": 0.0, "assessment": "No data"}

        # Track expansion rate
        stars_over_time = []
        for metric in self.metrics:
            expansion = metric.get("expansion", {})
            stars = expansion.get("stars_controlled", 0)
            stars_over_time.append(stars)

        # Calculate expansion rate
        if len(stars_over_time) > 1:
            initial_stars = stars_over_time[0]
            final_stars = stars_over_time[-1]
            expansion_rate = (final_stars - initial_stars) / len(stars_over_time)
        else:
            expansion_rate = 0.0

        # Average distance from home (measures if expansion is systematic)
        avg_distances = []
        for metric in self.metrics:
            expansion = metric.get("expansion", {})
            dist = expansion.get("avg_distance_from_home", 0)
            if dist > 0:
                avg_distances.append(dist)

        avg_distance = sum(avg_distances) / len(avg_distances) if avg_distances else 0.0

        # Score based on expansion rate and pattern
        score = 0.0

        # Rate component (0-60 points)
        if expansion_rate >= 0.5:
            score += 60.0
        elif expansion_rate >= 0.3:
            score += 45.0
        elif expansion_rate >= 0.2:
            score += 30.0
        else:
            score += 15.0

        # Pattern component (0-40 points)
        # Systematic expansion (growing distance from home) is better
        if avg_distance >= 3.0 and avg_distance <= 7.0:
            score += 40.0  # Good balance
        elif avg_distance >= 2.0:
            score += 25.0  # Okay
        else:
            score += 10.0  # Too conservative

        # Assessment
        if score >= 85:
            assessment = "Excellent - Rapid and systematic expansion"
        elif score >= 70:
            assessment = "Good - Effective expansion strategy"
        elif score >= 55:
            assessment = "Adequate - Moderate expansion"
        else:
            assessment = "Poor - Slow or inefficient expansion"

        return {
            "score": score,
            "assessment": assessment,
            "expansion_rate": round(expansion_rate, 3),
            "initial_stars": stars_over_time[0] if stars_over_time else 0,
            "final_stars": stars_over_time[-1] if stars_over_time else 0,
            "avg_distance_from_home": round(avg_distance, 2),
        }

    def _analyze_resources(self) -> dict:
        """Analyze resource control and economic performance.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        if not self.metrics:
            return {"score": 0.0, "assessment": "No data"}

        # Track production over time
        production_ratios = []
        production_advantages = []

        for metric in self.metrics:
            resources = metric.get("resources", {})
            ratio = resources.get("production_ratio", 0.0)
            advantage = resources.get("production_advantage", 0)

            # Handle infinite ratio (opponent has 0 production)
            if ratio == float("inf"):
                ratio = 10.0  # Cap at 10x for scoring

            production_ratios.append(ratio)
            production_advantages.append(advantage)

        # Calculate trends
        avg_ratio = sum(production_ratios) / len(production_ratios) if production_ratios else 0.0
        final_ratio = production_ratios[-1] if production_ratios else 0.0
        final_advantage = production_advantages[-1] if production_advantages else 0

        # Check if ratio is improving over time
        if len(production_ratios) >= 10:
            early_ratio = sum(production_ratios[:5]) / 5
            late_ratio = sum(production_ratios[-5:]) / 5
            ratio_trend = "improving" if late_ratio > early_ratio else "declining"
        else:
            ratio_trend = "stable"

        # Score based on production ratio
        score = 0.0

        if final_ratio >= 2.0:
            score = 100.0
        elif final_ratio >= 1.5:
            score = 85.0
        elif final_ratio >= 1.2:
            score = 70.0
        elif final_ratio >= 1.0:
            score = 55.0
        elif final_ratio >= 0.8:
            score = 40.0
        else:
            score = 20.0

        # Bonus for improving trend
        if ratio_trend == "improving" and score < 100:
            score += 10.0

        score = min(score, 100.0)

        # Assessment
        if score >= 85:
            assessment = "Excellent - Strong production advantage"
        elif score >= 70:
            assessment = "Good - Favorable economic position"
        elif score >= 55:
            assessment = "Adequate - Competitive production"
        else:
            assessment = "Poor - Production disadvantage"

        return {
            "score": score,
            "assessment": assessment,
            "avg_production_ratio": round(avg_ratio, 2),
            "final_production_ratio": round(final_ratio, 2),
            "final_production_advantage": final_advantage,
            "ratio_trend": ratio_trend,
        }

    def _analyze_fleets(self) -> dict:
        """Analyze fleet concentration and offensive capability.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        if not self.metrics:
            return {"score": 0.0, "assessment": "No data"}

        # Track fleet metrics over time
        large_fleet_counts = []
        avg_fleet_sizes = []

        for metric in self.metrics:
            fleets = metric.get("fleets", {})
            distribution = fleets.get("fleet_size_distribution", {})
            avg_size = fleets.get("avg_offensive_fleet_size", 0.0)

            # Count large fleets (50+ ships)
            large_fleets = distribution.get("large", 0)
            large_fleet_counts.append(large_fleets)
            avg_fleet_sizes.append(avg_size)

        # Calculate metrics
        avg_large_fleets = (
            sum(large_fleet_counts) / len(large_fleet_counts) if large_fleet_counts else 0.0
        )
        avg_fleet_size = sum(avg_fleet_sizes) / len(avg_fleet_sizes) if avg_fleet_sizes else 0.0
        final_avg_size = avg_fleet_sizes[-1] if avg_fleet_sizes else 0.0

        # Check if fleet sizes are growing
        if len(avg_fleet_sizes) >= 10:
            early_size = sum(avg_fleet_sizes[:5]) / 5
            late_size = sum(avg_fleet_sizes[-5:]) / 5
            size_trend = "growing" if late_size > early_size * 1.2 else "stable"
        else:
            size_trend = "stable"

        # Score based on fleet concentration
        score = 0.0

        # Average fleet size (0-60 points)
        if final_avg_size >= 50:
            score += 60.0
        elif final_avg_size >= 30:
            score += 45.0
        elif final_avg_size >= 20:
            score += 30.0
        else:
            score += 15.0

        # Large fleet presence (0-40 points)
        if avg_large_fleets >= 2.0:
            score += 40.0
        elif avg_large_fleets >= 1.0:
            score += 30.0
        elif avg_large_fleets >= 0.5:
            score += 20.0
        else:
            score += 10.0

        # Assessment
        if score >= 85:
            assessment = "Excellent - Strong fleet concentration"
        elif score >= 70:
            assessment = "Good - Effective fleet sizes"
        elif score >= 55:
            assessment = "Adequate - Moderate fleet strength"
        else:
            assessment = "Poor - Weak or scattered fleets"

        return {
            "score": score,
            "assessment": assessment,
            "avg_fleet_size": round(avg_fleet_size, 1),
            "final_avg_fleet_size": round(final_avg_size, 1),
            "avg_large_fleets": round(avg_large_fleets, 1),
            "fleet_size_trend": size_trend,
        }

    def _analyze_garrison(self) -> dict:
        """Analyze garrison management and threat response.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        if not self.metrics:
            return {"score": 0.0, "assessment": "No data"}

        # Track garrison appropriateness
        appropriate_count = 0
        total_count = 0
        garrison_percentages = []
        threat_levels_seen = {"none": 0, "low": 0, "medium": 0, "high": 0}

        for metric in self.metrics:
            garrison = metric.get("garrison", {})
            appropriate = garrison.get("garrison_appropriate", False)
            garrison_pct = garrison.get("garrison_pct_of_total", 0.0)
            threat = garrison.get("threat_level", "none")

            if appropriate:
                appropriate_count += 1
            total_count += 1

            garrison_percentages.append(garrison_pct)
            threat_levels_seen[threat] = threat_levels_seen.get(threat, 0) + 1

        # Calculate appropriateness rate
        appropriateness_rate = appropriate_count / total_count if total_count > 0 else 0.0
        avg_garrison_pct = (
            sum(garrison_percentages) / len(garrison_percentages) if garrison_percentages else 0.0
        )

        # Score based on appropriateness
        score = appropriateness_rate * 100.0

        # Assessment
        if score >= 85:
            assessment = "Excellent - Consistently appropriate garrison"
        elif score >= 70:
            assessment = "Good - Usually appropriate garrison"
        elif score >= 55:
            assessment = "Adequate - Sometimes appropriate garrison"
        else:
            assessment = "Poor - Often inappropriate garrison"

        return {
            "score": score,
            "assessment": assessment,
            "appropriateness_rate": round(appropriateness_rate, 2),
            "avg_garrison_pct": round(avg_garrison_pct, 1),
            "threat_levels_encountered": dict(threat_levels_seen),
        }

    def _analyze_territory(self) -> dict:
        """Analyze territory control and strategic positioning.

        Returns:
            Dictionary with score, assessment, and detailed metrics
        """
        if not self.metrics:
            return {"score": 0.0, "assessment": "No data"}

        # Track territorial metrics
        territorial_advantages = []
        center_control = []
        opponent_penetration = []

        for metric in self.metrics:
            territory = metric.get("territory", {})
            advantage = territory.get("territorial_advantage", 0.0)
            center = territory.get("stars_in_center_zone", 0)
            opponent_quad = territory.get("stars_in_opponent_quadrant", 0)

            territorial_advantages.append(advantage)
            center_control.append(center)
            opponent_penetration.append(opponent_quad)

        # Calculate metrics
        avg_advantage = (
            sum(territorial_advantages) / len(territorial_advantages)
            if territorial_advantages
            else 0.0
        )
        final_advantage = territorial_advantages[-1] if territorial_advantages else 0.0
        final_center = center_control[-1] if center_control else 0
        final_penetration = opponent_penetration[-1] if opponent_penetration else 0

        # Check if advantage is improving
        if len(territorial_advantages) >= 10:
            early_advantage = sum(territorial_advantages[:5]) / 5
            late_advantage = sum(territorial_advantages[-5:]) / 5
            advantage_trend = "improving" if late_advantage > early_advantage else "declining"
        else:
            advantage_trend = "stable"

        # Score based on territorial advantage
        score = 0.0

        # Territorial advantage (-1 to 1) converted to 0-100
        # Map: -1 -> 0, 0 -> 50, 1 -> 100
        advantage_score = (final_advantage + 1.0) * 50.0
        score = advantage_score

        # Bonus for center control
        if final_center >= 3:
            score += 10.0
        elif final_center >= 1:
            score += 5.0

        # Bonus for opponent penetration
        if final_penetration >= 3:
            score += 10.0
        elif final_penetration >= 1:
            score += 5.0

        score = min(score, 100.0)
        score = max(score, 0.0)

        # Assessment
        if score >= 85:
            assessment = "Excellent - Dominant territorial position"
        elif score >= 70:
            assessment = "Good - Favorable territorial control"
        elif score >= 55:
            assessment = "Adequate - Competitive territory"
        else:
            assessment = "Poor - Weak territorial position"

        return {
            "score": score,
            "assessment": assessment,
            "avg_territorial_advantage": round(avg_advantage, 2),
            "final_territorial_advantage": round(final_advantage, 2),
            "final_center_control": final_center,
            "final_opponent_penetration": final_penetration,
            "advantage_trend": advantage_trend,
        }

    def _calculate_overall_score(self, dimension_scores: dict[str, float]) -> float:
        """Calculate weighted overall score from dimension scores.

        Args:
            dimension_scores: Dictionary mapping dimension names to scores

        Returns:
            Overall score (0-100)
        """
        # Weight each dimension based on strategic importance
        weights = {
            "spatial_awareness": 0.15,  # Important early game
            "expansion": 0.20,  # Critical for winning
            "resources": 0.25,  # Most important long-term
            "fleets": 0.20,  # Critical for offense
            "garrison": 0.10,  # Important but not primary
            "territory": 0.10,  # Secondary to production
        }

        total_score = 0.0
        for dimension, score in dimension_scores.items():
            weight = weights.get(dimension, 0.1)
            total_score += score * weight

        return round(total_score, 1)

    def _score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade.

        Args:
            score: Score (0-100)

        Returns:
            Letter grade (A/B/C/D/F)
        """
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_insights(self, dimension_scores: dict[str, float]) -> dict:
        """Generate insights about strengths and weaknesses.

        Args:
            dimension_scores: Dictionary mapping dimension names to scores

        Returns:
            Dictionary with 'strengths' and 'weaknesses' lists
        """
        # Sort dimensions by score
        sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)

        # Top 2 are strengths, bottom 2 are weaknesses
        strengths = []
        weaknesses = []

        for dim_name, score in sorted_dims[:2]:
            if score >= 70:
                display_name = dim_name.replace("_", " ").title()
                strengths.append(f"{display_name} ({score:.1f}/100)")

        for dim_name, score in sorted_dims[-2:]:
            if score < 70:
                display_name = dim_name.replace("_", " ").title()
                weaknesses.append(f"{display_name} ({score:.1f}/100)")

        # Ensure we have at least something
        if not strengths:
            strengths.append("All dimensions need improvement")
        if not weaknesses:
            weaknesses.append("All dimensions performing well")

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
        }

    def _generate_recommendations(self, analyses: dict) -> list[str]:
        """Generate actionable recommendations based on analysis.

        Args:
            analyses: Dictionary containing all dimension analyses

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Spatial awareness recommendations
        spatial = analyses["spatial"]
        if spatial["score"] < 70:
            if not spatial["opponent_discovered"]:
                recommendations.append(
                    "PRIORITY: Implement early scouting strategy to discover opponent home star within first 10 turns. "
                    "Send small scout fleets (5-10 ships) to unexplored quadrants immediately."
                )
            elif spatial["discovery_turn"] and spatial["discovery_turn"] > 15:
                recommendations.append(
                    "Improve early-game exploration by sending scouts to all quadrants by turn 5. "
                    "Faster opponent discovery enables more effective strategic planning."
                )

        # Expansion recommendations
        expansion = analyses["expansion"]
        if expansion["score"] < 70:
            if expansion["expansion_rate"] < 0.3:
                recommendations.append(
                    "Increase expansion rate by conquering 1 new star every 2-3 turns. "
                    "Prioritize nearby unconquered stars with higher RU production values."
                )
            if expansion["avg_distance_from_home"] < 3.0:
                recommendations.append(
                    "Expand more aggressively beyond home territory. "
                    "Target stars 3-5 units away to control more strategic space."
                )

        # Resource recommendations
        resources = analyses["resources"]
        if resources["score"] < 70:
            if resources["final_production_ratio"] < 1.0:
                recommendations.append(
                    "CRITICAL: Reverse production disadvantage by prioritizing conquest of high-RU stars. "
                    "Target stars with 3+ RU production and maintain offensive pressure."
                )
            if resources["ratio_trend"] == "declining":
                recommendations.append(
                    "Production ratio is declining - opponent is outpacing your expansion. "
                    "Increase conquest rate and defend conquered territories more effectively."
                )

        # Fleet recommendations
        fleets = analyses["fleets"]
        if fleets["score"] < 70:
            if fleets["final_avg_fleet_size"] < 30:
                recommendations.append(
                    "Concentrate forces into larger fleets (30-50 ships minimum). "
                    "Stop sending small fleets - merge forces at staging points before attacking."
                )
            if fleets["avg_large_fleets"] < 1.0:
                recommendations.append(
                    "Build and maintain at least 1-2 large offensive fleets (50+ ships). "
                    "Large fleets are essential for conquering defended stars and maintaining offensive pressure."
                )

        # Garrison recommendations
        garrison = analyses["garrison"]
        if garrison["score"] < 70:
            if garrison["appropriateness_rate"] < 0.7:
                recommendations.append(
                    "Improve garrison management by matching defense to threat level. "
                    "Low threat: 5% garrison, Medium: 15-20%, High: 25-30% of total forces."
                )

        # Territory recommendations
        territory = analyses["territory"]
        if territory["score"] < 70:
            if territory["final_territorial_advantage"] < 0:
                recommendations.append(
                    "Improve territorial position by pushing toward center and opponent quadrant. "
                    "Center control provides strategic advantage and denies opponent expansion routes."
                )
            if territory["final_opponent_penetration"] == 0:
                recommendations.append(
                    "Penetrate opponent's home quadrant to pressure their economy and force defensive responses. "
                    "Target stars in opponent territory to gain territorial advantage."
                )

        # If doing well, give advanced recommendations
        overall_score = self._calculate_overall_score(
            {k: v["score"] for k, v in analyses.items() if isinstance(v, dict) and "score" in v}
        )

        if overall_score >= 80 and len(recommendations) < 2:
            recommendations.append(
                "Advanced: Focus on economic efficiency - maximize ships per RU by "
                "maintaining high offensive pressure while minimizing unnecessary garrison."
            )
            recommendations.append(
                "Advanced: Optimize fleet timing - coordinate multiple fleets to arrive simultaneously "
                "at strategic targets for overwhelming force concentration."
            )

        # Ensure we have at least 3 recommendations
        if len(recommendations) < 3:
            recommendations.append(
                "Continue current strategy - performance is strong across most dimensions. "
                "Focus on consistency and avoiding strategic errors."
            )

        return recommendations[:5]  # Limit to top 5 recommendations


def analyze_multiple_games(log_dir: str = "logs") -> dict:
    """Analyze all games in a directory.

    Args:
        log_dir: Directory containing JSONL log files

    Returns:
        Aggregated analysis across all games with statistics:
        - total_games: Number of games analyzed
        - avg_scores: Average scores per dimension
        - best_game: Game with highest overall score
        - worst_game: Game with lowest overall score
        - common_weaknesses: Most common weak dimensions
        - improvement_trends: Trends across games (if played chronologically)
    """
    log_path = Path(log_dir)

    if not log_path.exists():
        raise FileNotFoundError(f"Log directory not found: {log_dir}")

    # Find all strategic log files
    log_files = list(log_path.glob("game_*_strategic.jsonl"))

    if not log_files:
        return {
            "total_games": 0,
            "message": f"No strategic log files found in {log_dir}",
        }

    # Analyze each game
    game_analyses = []
    for log_file in log_files:
        try:
            analyzer = GameAnalyzer(str(log_file))
            analysis = analyzer.analyze()
            game_analyses.append(
                {
                    "game_id": analysis["game_id"],
                    "file": str(log_file),
                    "overall_score": analysis["overall_score"],
                    "grade": analysis["grade"],
                    "dimension_scores": {
                        k: v["score"] for k, v in analysis["dimension_scores"].items()
                    },
                }
            )
        except Exception as e:
            # Skip files that can't be analyzed
            print(f"Warning: Could not analyze {log_file}: {e}")
            continue

    if not game_analyses:
        return {
            "total_games": 0,
            "message": "No games could be successfully analyzed",
        }

    # Calculate aggregate statistics
    total_games = len(game_analyses)

    # Average scores per dimension
    dimension_names = list(game_analyses[0]["dimension_scores"].keys())
    avg_scores = {}
    for dim in dimension_names:
        scores = [g["dimension_scores"][dim] for g in game_analyses]
        avg_scores[dim] = round(sum(scores) / len(scores), 1)

    # Overall average
    overall_scores = [g["overall_score"] for g in game_analyses]
    avg_overall = round(sum(overall_scores) / len(overall_scores), 1)

    # Best and worst games
    best_game = max(game_analyses, key=lambda g: g["overall_score"])
    worst_game = min(game_analyses, key=lambda g: g["overall_score"])

    # Find common weaknesses (dimensions with avg score < 70)
    common_weaknesses = [
        dim.replace("_", " ").title() for dim, score in avg_scores.items() if score < 70
    ]

    return {
        "total_games": total_games,
        "avg_overall_score": avg_overall,
        "avg_dimension_scores": avg_scores,
        "best_game": {
            "game_id": best_game["game_id"],
            "score": best_game["overall_score"],
            "grade": best_game["grade"],
        },
        "worst_game": {
            "game_id": worst_game["game_id"],
            "score": worst_game["overall_score"],
            "grade": worst_game["grade"],
        },
        "common_weaknesses": common_weaknesses
        if common_weaknesses
        else ["None - all dimensions strong"],
        "score_range": {
            "min": worst_game["overall_score"],
            "max": best_game["overall_score"],
            "spread": round(best_game["overall_score"] - worst_game["overall_score"], 1),
        },
    }
