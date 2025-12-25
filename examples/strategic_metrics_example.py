"""Example usage of strategic metrics calculator.

This script demonstrates how to calculate and analyze strategic metrics
for LLM gameplay analysis.
"""

import json

from src.analysis import calculate_strategic_metrics
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def create_example_game() -> Game:
    """Create an example game state for demonstration."""
    game = Game(seed=42, turn=10)

    # Create stars in various positions
    stars = [
        # p2's home and nearby stars (upper-left quadrant)
        Star(
            id="A",
            name="Alpha",
            x=1,
            y=2,
            base_ru=3,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 25},
        ),
        Star(
            id="B",
            name="Beta",
            x=3,
            y=3,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        # Center zone stars
        Star(
            id="C",
            name="Gamma",
            x=5,
            y=5,
            base_ru=4,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 15},
        ),
        Star(
            id="D", name="Delta", x=6, y=4, base_ru=2, owner=None, npc_ships=5, stationed_ships={}
        ),
        # p1's home and nearby stars (lower-right quadrant)
        Star(
            id="E",
            name="Epsilon",
            x=10,
            y=8,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 30},
        ),
        Star(
            id="F",
            name="Zeta",
            x=9,
            y=7,
            base_ru=2,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 12},
        ),
    ]
    game.stars = stars

    # Create players
    player_p1 = Player(id="p1", home_star="E", visited_stars={"E", "F", "D"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "B", "C", "D"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Create fleets
    fleets = [
        # p2's offensive fleets
        Fleet(
            id="p2-001",
            owner="p2",
            ships=20,
            origin="A",
            dest="D",
            dist_remaining=2,
            rationale="attack",
        ),
        Fleet(
            id="p2-002",
            owner="p2",
            ships=35,
            origin="C",
            dest="D",
            dist_remaining=1,
            rationale="attack",
        ),
        # p1's fleet approaching p2's territory
        Fleet(
            id="p1-001",
            owner="p1",
            ships=25,
            origin="F",
            dest="C",
            dist_remaining=3,
            rationale="attack",
        ),
    ]
    game.fleets = fleets

    return game


def main():
    """Run the example."""
    print("Strategic Metrics Calculator - Example Usage\n")
    print("=" * 60)

    # Create example game
    game = create_example_game()

    # Calculate metrics for p2 (LLM player)
    metrics = calculate_strategic_metrics(game, "p2", game.turn)

    # Display metrics in a human-readable format
    print(f"\nTurn: {metrics['turn']}")
    print("\n1. SPATIAL AWARENESS")
    print("-" * 60)
    spatial = metrics["spatial_awareness"]
    print(f"   LLM Home: {spatial['llm_home_coords']} ({spatial['llm_home_quadrant']})")
    print(
        f"   Opponent Home: {spatial['opponent_home_coords']} ({spatial['opponent_home_quadrant']})"
    )
    print(f"   Opponent Home Discovered: {spatial['opponent_home_discovered']}")

    print("\n2. EXPANSION")
    print("-" * 60)
    expansion = metrics["expansion"]
    print(f"   Stars Controlled: {expansion['stars_controlled']}")
    print(f"   Avg Distance from Home: {expansion['avg_distance_from_home']}")
    print(f"   Nearest Unconquered: {expansion['nearest_unconquered_distance']} units away")
    print(f"   Expansion Pattern: {expansion['expansion_pattern']}")

    print("\n3. RESOURCES")
    print("-" * 60)
    resources = metrics["resources"]
    print(f"   Total Production: {resources['total_production_ru']} RU/turn")
    print(f"   Opponent Production: {resources['opponent_production_ru']} RU/turn")
    print(f"   Production Ratio: {resources['production_ratio']:.2f}")
    print(f"   Production Advantage: {resources['production_advantage']:+d} RU/turn")

    print("\n4. FLEETS")
    print("-" * 60)
    fleets = metrics["fleets"]
    print(f"   Total Ships: {fleets['total_ships']}")
    print(f"   Fleets in Flight: {fleets['num_fleets_in_flight']}")
    print("   Fleet Size Distribution:")
    for size, count in fleets["fleet_size_distribution"].items():
        print(f"      {size.capitalize()}: {count}")
    print(
        f"   Largest Fleet: {fleets['largest_fleet_size']} ships ({fleets['largest_fleet_pct_of_total']:.1f}%)"
    )
    print(f"   Avg Offensive Fleet Size: {fleets['avg_offensive_fleet_size']:.1f}")

    print("\n5. GARRISON")
    print("-" * 60)
    garrison = metrics["garrison"]
    print(
        f"   Home Garrison: {garrison['home_star_garrison']} ships ({garrison['garrison_pct_of_total']:.1f}%)"
    )
    if garrison["nearest_enemy_fleet_distance"]:
        print(
            f"   Nearest Enemy Fleet: {garrison['nearest_enemy_fleet_size']} ships, "
            f"{garrison['nearest_enemy_fleet_distance']:.1f} units away"
        )
    else:
        print("   Nearest Enemy Fleet: None visible")
    print(f"   Threat Level: {garrison['threat_level']}")
    print(f"   Garrison Appropriate: {garrison['garrison_appropriate']}")

    print("\n6. TERRITORY")
    print("-" * 60)
    territory = metrics["territory"]
    print(f"   Stars in Home Quadrant: {territory['stars_in_home_quadrant']}")
    print(f"   Stars in Center Zone: {territory['stars_in_center_zone']}")
    print(f"   Stars in Opponent Quadrant: {territory['stars_in_opponent_quadrant']}")
    print(f"   Territorial Advantage: {territory['territorial_advantage']:+.2f}")

    print("\n" + "=" * 60)
    print("\nJSON Output (for JSONL logging):")
    print("-" * 60)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
