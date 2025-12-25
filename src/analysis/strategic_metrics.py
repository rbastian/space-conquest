"""Strategic metrics calculator for analyzing LLM gameplay.

This module provides comprehensive strategic analysis across multiple dimensions:
- Spatial awareness (home star locations, quadrants)
- Expansion strategy (conquest patterns, territory growth)
- Resource control (production capacity, economic advantage)
- Fleet concentration (fleet sizes, distribution)
- Garrison management (home defense, threat assessment)
- Territory control (quadrant dominance, territorial advantage)
"""

from ..models.game import Game
from ..models.star import Star


def calculate_strategic_metrics(game: Game, player_id: str, turn: int) -> dict:
    """Calculate strategic gameplay metrics for a player at a specific turn.

    Args:
        game: The game state
        player_id: The player to analyze (typically "p2" for LLM)
        turn: Current turn number

    Returns:
        Dictionary containing strategic metrics across multiple dimensions:
        - spatial_awareness: Home star locations and quadrants
        - expansion: Territory growth and expansion patterns
        - resources: Production capacity and economic metrics
        - fleets: Fleet sizes, distribution, and concentration
        - garrison: Home defense and threat assessment
        - territory: Quadrant control and territorial advantage
    """
    player = game.players.get(player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found in game")

    opponent_id = _get_opponent_id(player_id)

    # Calculate all metric categories
    spatial_metrics = _calculate_spatial_awareness(game, player_id, opponent_id)
    expansion_metrics = _calculate_expansion_metrics(game, player_id, spatial_metrics)
    resource_metrics = _calculate_resource_metrics(game, player_id, opponent_id)
    fleet_metrics = _calculate_fleet_metrics(game, player_id)
    garrison_metrics = _calculate_garrison_metrics(game, player_id, opponent_id, spatial_metrics)
    territory_metrics = _calculate_territory_metrics(game, player_id, opponent_id, spatial_metrics)

    return {
        "turn": turn,
        "spatial_awareness": spatial_metrics,
        "expansion": expansion_metrics,
        "resources": resource_metrics,
        "fleets": fleet_metrics,
        "garrison": garrison_metrics,
        "territory": territory_metrics,
    }


def _calculate_spatial_awareness(game: Game, player_id: str, opponent_id: str) -> dict:
    """Calculate spatial awareness metrics.

    Analyzes home star locations, quadrants, and whether the opponent's
    home has been discovered.
    """
    player = game.players[player_id]
    opponent = game.players[opponent_id]

    # Get home star coordinates
    llm_home = _get_star_by_id(game, player.home_star)
    opponent_home = _get_star_by_id(game, opponent.home_star)

    llm_home_coords = (llm_home.x, llm_home.y)
    opponent_home_coords = (opponent_home.x, opponent_home.y)

    # Determine quadrants
    llm_quadrant = _determine_quadrant(llm_home.x, llm_home.y)
    opponent_quadrant = _determine_quadrant(opponent_home.x, opponent_home.y)

    # Check if opponent's home has been discovered
    opponent_home_discovered = opponent.home_star in player.visited_stars

    return {
        "llm_home_coords": llm_home_coords,
        "opponent_home_coords": opponent_home_coords,
        "llm_home_quadrant": llm_quadrant,
        "opponent_home_quadrant": opponent_quadrant,
        "opponent_home_discovered": opponent_home_discovered,
    }


def _calculate_expansion_metrics(game: Game, player_id: str, spatial_metrics: dict) -> dict:
    """Calculate expansion strategy metrics.

    Analyzes territory growth, expansion patterns, and strategic positioning.
    """
    player_stars = _get_player_stars(game, player_id)
    stars_controlled = len(player_stars)

    # Calculate average distance from home
    home_coords = spatial_metrics["llm_home_coords"]
    if stars_controlled > 0:
        total_distance = sum(
            _calculate_distance(home_coords[0], home_coords[1], star.x, star.y)
            for star in player_stars
        )
        avg_distance_from_home = round(total_distance / stars_controlled, 2)
    else:
        avg_distance_from_home = 0.0

    # Find nearest unconquered star
    unconquered_stars = [s for s in game.stars if s.owner != player_id]
    if unconquered_stars:
        nearest_unconquered_distance = min(
            _calculate_distance(home_coords[0], home_coords[1], star.x, star.y)
            for star in unconquered_stars
        )
    else:
        nearest_unconquered_distance = 0.0

    # Determine expansion pattern (systematic vs random)
    # Systematic: new conquests tend to be near existing territory
    # For now, we'll use a simple heuristic based on average distance
    # In future, could compare to previous turn data
    expansion_pattern = "systematic" if avg_distance_from_home < 5.0 else "random"

    # New stars this turn - would need previous turn data
    # For now, return empty list (can be enhanced with turn history)
    new_stars_this_turn = []

    return {
        "stars_controlled": stars_controlled,
        "new_stars_this_turn": new_stars_this_turn,
        "avg_distance_from_home": avg_distance_from_home,
        "nearest_unconquered_distance": round(nearest_unconquered_distance, 2),
        "expansion_pattern": expansion_pattern,
    }


def _calculate_resource_metrics(game: Game, player_id: str, opponent_id: str) -> dict:
    """Calculate resource control metrics.

    Analyzes production capacity and economic advantage.
    """
    player_stars = _get_player_stars(game, player_id)
    opponent_stars = _get_player_stars(game, opponent_id)

    total_production_ru = sum(star.base_ru for star in player_stars)
    opponent_production_ru = sum(star.base_ru for star in opponent_stars)

    # Calculate production ratio (avoid division by zero)
    if opponent_production_ru > 0:
        production_ratio = round(total_production_ru / opponent_production_ru, 2)
    else:
        production_ratio = float("inf") if total_production_ru > 0 else 0.0

    production_advantage = total_production_ru - opponent_production_ru

    return {
        "total_production_ru": total_production_ru,
        "opponent_production_ru": opponent_production_ru,
        "production_ratio": production_ratio,
        "production_advantage": production_advantage,
    }


def _calculate_fleet_metrics(game: Game, player_id: str) -> dict:
    """Calculate fleet concentration metrics.

    Analyzes fleet sizes, distribution, and concentration patterns.
    """
    player_stars = _get_player_stars(game, player_id)
    player_fleets = [f for f in game.fleets if f.owner == player_id]

    # Calculate total ships
    ships_in_stars = sum(star.stationed_ships.get(player_id, 0) for star in player_stars)
    ships_in_fleets = sum(fleet.ships for fleet in player_fleets)
    total_ships = ships_in_stars + ships_in_fleets

    num_fleets_in_flight = len(player_fleets)

    # Fleet size distribution
    fleet_size_distribution = {
        "tiny": 0,  # 1-9 ships
        "small": 0,  # 10-24 ships
        "medium": 0,  # 25-49 ships
        "large": 0,  # 50+ ships
    }

    for fleet in player_fleets:
        if fleet.ships < 10:
            fleet_size_distribution["tiny"] += 1
        elif fleet.ships < 25:
            fleet_size_distribution["small"] += 1
        elif fleet.ships < 50:
            fleet_size_distribution["medium"] += 1
        else:
            fleet_size_distribution["large"] += 1

    # Largest fleet
    largest_fleet_size = max((f.ships for f in player_fleets), default=0)
    largest_fleet_pct_of_total = (
        round(largest_fleet_size / total_ships * 100, 2) if total_ships > 0 else 0.0
    )

    # Average offensive fleet size
    avg_offensive_fleet_size = (
        round(ships_in_fleets / num_fleets_in_flight, 2) if num_fleets_in_flight > 0 else 0.0
    )

    return {
        "total_ships": total_ships,
        "num_fleets_in_flight": num_fleets_in_flight,
        "fleet_size_distribution": fleet_size_distribution,
        "largest_fleet_size": largest_fleet_size,
        "largest_fleet_pct_of_total": largest_fleet_pct_of_total,
        "avg_offensive_fleet_size": avg_offensive_fleet_size,
    }


def _calculate_garrison_metrics(
    game: Game, player_id: str, opponent_id: str, spatial_metrics: dict
) -> dict:
    """Calculate garrison management metrics.

    Analyzes home defense, threat assessment, and garrison appropriateness.
    """
    player = game.players[player_id]
    home_star = _get_star_by_id(game, player.home_star)
    home_star_garrison = home_star.stationed_ships.get(player_id, 0)

    # Calculate total ships for percentage
    player_stars = _get_player_stars(game, player_id)
    player_fleets = [f for f in game.fleets if f.owner == player_id]
    total_ships = sum(star.stationed_ships.get(player_id, 0) for star in player_stars)
    total_ships += sum(fleet.ships for fleet in player_fleets)

    garrison_pct_of_total = (
        round(home_star_garrison / total_ships * 100, 2) if total_ships > 0 else 0.0
    )

    # Find nearest enemy fleet
    opponent_fleets = [f for f in game.fleets if f.owner == opponent_id]
    home_coords = spatial_metrics["llm_home_coords"]

    nearest_enemy_fleet_distance = None
    nearest_enemy_fleet_size = None

    if opponent_fleets:
        # Calculate distance to each enemy fleet's destination
        fleet_distances = []
        for fleet in opponent_fleets:
            dest_star = _get_star_by_id(game, fleet.dest)
            distance = _calculate_distance(home_coords[0], home_coords[1], dest_star.x, dest_star.y)
            # Adjust for time to arrival
            effective_distance = distance + fleet.dist_remaining
            fleet_distances.append((effective_distance, fleet.ships))

        if fleet_distances:
            nearest_enemy_fleet_distance, nearest_enemy_fleet_size = min(
                fleet_distances, key=lambda x: x[0]
            )
            nearest_enemy_fleet_distance = round(nearest_enemy_fleet_distance, 2)

    # Calculate threat level
    threat_level = _calculate_threat_level(nearest_enemy_fleet_distance, nearest_enemy_fleet_size)

    # Determine if garrison is appropriate
    garrison_appropriate = _is_garrison_appropriate(home_star_garrison, threat_level, total_ships)

    return {
        "home_star_garrison": home_star_garrison,
        "garrison_pct_of_total": garrison_pct_of_total,
        "nearest_enemy_fleet_distance": nearest_enemy_fleet_distance,
        "nearest_enemy_fleet_size": nearest_enemy_fleet_size,
        "threat_level": threat_level,
        "garrison_appropriate": garrison_appropriate,
    }


def _calculate_territory_metrics(
    game: Game, player_id: str, opponent_id: str, spatial_metrics: dict
) -> dict:
    """Calculate territory control metrics.

    Analyzes quadrant control and territorial dominance.
    """
    player_stars = _get_player_stars(game, player_id)
    opponent_stars = _get_player_stars(game, opponent_id)

    llm_quadrant = spatial_metrics["llm_home_quadrant"]
    opponent_quadrant = spatial_metrics["opponent_home_quadrant"]

    # Count stars in each zone
    stars_in_home_quadrant = sum(
        1 for star in player_stars if _determine_quadrant(star.x, star.y) == llm_quadrant
    )

    stars_in_center_zone = sum(1 for star in player_stars if _is_center_zone(star.x, star.y))

    stars_in_opponent_quadrant = sum(
        1 for star in player_stars if _determine_quadrant(star.x, star.y) == opponent_quadrant
    )

    # Calculate territorial advantage
    # Score based on: home quadrant control, center control, opponent quadrant penetration
    player_score = (
        stars_in_home_quadrant * 1.0  # Home territory is baseline
        + stars_in_center_zone * 1.5  # Center is more valuable
        + stars_in_opponent_quadrant * 2.0  # Opponent territory is most valuable
    )

    # Calculate opponent's score
    opp_stars_in_home_quadrant = sum(
        1 for star in opponent_stars if _determine_quadrant(star.x, star.y) == opponent_quadrant
    )
    opp_stars_in_center_zone = sum(1 for star in opponent_stars if _is_center_zone(star.x, star.y))
    opp_stars_in_player_quadrant = sum(
        1 for star in opponent_stars if _determine_quadrant(star.x, star.y) == llm_quadrant
    )

    opponent_score = (
        opp_stars_in_home_quadrant * 1.0
        + opp_stars_in_center_zone * 1.5
        + opp_stars_in_player_quadrant * 2.0
    )

    # Normalize to [-1, 1] range
    total_score = player_score + opponent_score
    if total_score > 0:
        territorial_advantage = round((player_score - opponent_score) / total_score, 2)
    else:
        territorial_advantage = 0.0

    return {
        "stars_in_home_quadrant": stars_in_home_quadrant,
        "stars_in_center_zone": stars_in_center_zone,
        "stars_in_opponent_quadrant": stars_in_opponent_quadrant,
        "territorial_advantage": territorial_advantage,
    }


# Helper functions


def _calculate_distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Calculate Chebyshev distance between two points.

    Chebyshev distance is the maximum of the absolute differences
    of their coordinates, commonly used in grid-based games.

    Args:
        x1, y1: Coordinates of first point
        x2, y2: Coordinates of second point

    Returns:
        Chebyshev distance as a float
    """
    return float(max(abs(x2 - x1), abs(y2 - y1)))


def _get_player_stars(game: Game, player_id: str) -> list[Star]:
    """Get all stars owned by a player.

    Args:
        game: The game state
        player_id: The player ID

    Returns:
        List of Star objects owned by the player
    """
    return [star for star in game.stars if star.owner == player_id]


def _get_opponent_id(player_id: str) -> str:
    """Get the opponent's player ID.

    Args:
        player_id: The current player ID ("p1" or "p2")

    Returns:
        The opponent's player ID
    """
    return "p1" if player_id == "p2" else "p2"


def _get_star_by_id(game: Game, star_id: str) -> Star:
    """Get a star by its ID.

    Args:
        game: The game state
        star_id: The star ID

    Returns:
        The Star object

    Raises:
        ValueError: If star not found
    """
    for star in game.stars:
        if star.id == star_id:
            return star
    raise ValueError(f"Star {star_id} not found")


def _determine_quadrant(x: int, y: int) -> str:
    """Determine which quadrant a coordinate is in.

    The map is divided into two diagonal quadrants:
    - upper-left: coordinates where x + y < map_center
    - lower-right: coordinates where x + y >= map_center

    Args:
        x: X coordinate (0-11)
        y: Y coordinate (0-9)

    Returns:
        "upper-left" or "lower-right"
    """
    # Map is 12x10, so center is approximately at (6, 5)
    # Sum of coordinates: upper-left has lower sums, lower-right has higher sums
    return "upper-left" if x + y < 11 else "lower-right"


def _is_center_zone(x: int, y: int) -> bool:
    """Check if coordinates are in the center zone.

    The center zone is the middle region between the two diagonal quadrants,
    roughly where x + y is close to the map center.

    Args:
        x: X coordinate (0-11)
        y: Y coordinate (0-9)

    Returns:
        True if in center zone, False otherwise
    """
    # Center zone is roughly where 9 <= x + y <= 12
    coord_sum = x + y
    return 9 <= coord_sum <= 12


def _calculate_threat_level(distance: float | None, fleet_size: int | None) -> str:
    """Determine threat level based on enemy fleet proximity and size.

    Args:
        distance: Distance to nearest enemy fleet (None if no enemy fleets)
        fleet_size: Size of nearest enemy fleet (None if no enemy fleets)

    Returns:
        "none", "low", "medium", or "high"
    """
    if distance is None or fleet_size is None:
        return "none"

    # Threat assessment based on distance and fleet size
    if distance > 8:
        return "low"
    elif distance > 5:
        return "medium" if fleet_size > 20 else "low"
    elif distance > 3:
        return "high" if fleet_size > 30 else "medium"
    else:
        return "high"


def _is_garrison_appropriate(garrison: int, threat_level: str, total_ships: int) -> bool:
    """Determine if garrison size is appropriate for the threat level.

    Args:
        garrison: Number of ships stationed at home
        threat_level: Current threat level ("none", "low", "medium", "high")
        total_ships: Total number of ships owned by player

    Returns:
        True if garrison is appropriate, False otherwise
    """
    if total_ships == 0:
        return True  # No ships to garrison

    garrison_pct = garrison / total_ships

    # Expected garrison percentages by threat level
    thresholds = {
        "none": 0.05,  # 5% minimum for home defense
        "low": 0.10,  # 10% for low threat
        "medium": 0.20,  # 20% for medium threat
        "high": 0.30,  # 30% for high threat
    }

    expected_pct = thresholds.get(threat_level, 0.05)

    # Allow 10% margin of error
    return garrison_pct >= (expected_pct - 0.10)
