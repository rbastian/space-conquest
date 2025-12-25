"""Tests for strategic metrics calculator."""

import pytest

from src.analysis.strategic_metrics import calculate_strategic_metrics
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_calculate_strategic_metrics_basic():
    """Test basic strategic metrics calculation."""
    # Create a simple game state
    game = Game(seed=42, turn=5)

    # Create stars in different quadrants
    # Upper-left quadrant (x + y < 11)
    star_a = Star(
        id="A",
        name="Alpha",
        x=2,
        y=3,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    # Lower-right quadrant (x + y >= 11)
    star_b = Star(
        id="B", name="Beta", x=9, y=7, base_ru=2, owner="p1", npc_ships=0, stationed_ships={"p1": 8}
    )
    # Center zone
    star_c = Star(
        id="C",
        name="Gamma",
        x=5,
        y=5,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 15},
    )
    # Neutral star
    star_d = Star(
        id="D", name="Delta", x=6, y=4, base_ru=2, owner=None, npc_ships=5, stationed_ships={}
    )

    game.stars = [star_a, star_b, star_c, star_d]

    # Create players
    player_p1 = Player(id="p1", home_star="B", visited_stars={"B", "C"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "C", "D"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Create some fleets
    fleet1 = Fleet(
        id="p2-001",
        owner="p2",
        ships=20,
        origin="A",
        dest="D",
        dist_remaining=2,
        rationale="attack",
    )
    fleet2 = Fleet(
        id="p2-002",
        owner="p2",
        ships=30,
        origin="C",
        dest="D",
        dist_remaining=1,
        rationale="attack",
    )
    fleet3 = Fleet(
        id="p1-001",
        owner="p1",
        ships=15,
        origin="B",
        dest="C",
        dist_remaining=3,
        rationale="attack",
    )
    game.fleets = [fleet1, fleet2, fleet3]

    # Calculate metrics for p2
    metrics = calculate_strategic_metrics(game, "p2", 5)

    # Verify structure
    assert metrics["turn"] == 5
    assert "spatial_awareness" in metrics
    assert "expansion" in metrics
    assert "resources" in metrics
    assert "fleets" in metrics
    assert "garrison" in metrics
    assert "territory" in metrics

    # Verify spatial awareness
    spatial = metrics["spatial_awareness"]
    assert spatial["llm_home_coords"] == (2, 3)
    assert spatial["opponent_home_coords"] == (9, 7)
    assert spatial["llm_home_quadrant"] == "upper-left"
    assert spatial["opponent_home_quadrant"] == "lower-right"
    assert spatial["opponent_home_discovered"] is False  # p2 hasn't visited B

    # Verify expansion metrics
    expansion = metrics["expansion"]
    assert expansion["stars_controlled"] == 2  # A and C
    assert expansion["avg_distance_from_home"] > 0
    assert expansion["nearest_unconquered_distance"] > 0

    # Verify resource metrics
    resources = metrics["resources"]
    assert resources["total_production_ru"] == 7  # 3 + 4
    assert resources["opponent_production_ru"] == 2  # Just star B
    assert resources["production_ratio"] == 3.5
    assert resources["production_advantage"] == 5

    # Verify fleet metrics
    fleets = metrics["fleets"]
    assert fleets["total_ships"] == 75  # 10 + 15 + 20 + 30
    assert fleets["num_fleets_in_flight"] == 2
    assert fleets["largest_fleet_size"] == 30
    assert fleets["fleet_size_distribution"]["small"] == 1  # 20 ships
    assert fleets["fleet_size_distribution"]["medium"] == 1  # 30 ships

    # Verify garrison metrics
    garrison = metrics["garrison"]
    assert garrison["home_star_garrison"] == 10
    assert garrison["garrison_pct_of_total"] > 0
    assert garrison["threat_level"] in ["none", "low", "medium", "high"]
    assert isinstance(garrison["garrison_appropriate"], bool)


def test_fleet_size_distribution():
    """Test fleet size categorization."""
    game = Game(seed=42, turn=1)

    # Create minimal game state
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 100},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=11,
        y=9,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 100},
    )
    game.stars = [star_a, star_b]

    player_p1 = Player(id="p1", home_star="B", visited_stars={"B"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Create fleets of different sizes
    fleets = [
        Fleet(
            id="p2-001",
            owner="p2",
            ships=5,
            origin="A",
            dest="B",
            dist_remaining=2,
            rationale="attack",
        ),  # tiny
        Fleet(
            id="p2-002",
            owner="p2",
            ships=15,
            origin="A",
            dest="B",
            dist_remaining=2,
            rationale="attack",
        ),  # small
        Fleet(
            id="p2-003",
            owner="p2",
            ships=30,
            origin="A",
            dest="B",
            dist_remaining=2,
            rationale="attack",
        ),  # medium
        Fleet(
            id="p2-004",
            owner="p2",
            ships=60,
            origin="A",
            dest="B",
            dist_remaining=2,
            rationale="attack",
        ),  # large
    ]
    game.fleets = fleets

    metrics = calculate_strategic_metrics(game, "p2", 1)

    dist = metrics["fleets"]["fleet_size_distribution"]
    assert dist["tiny"] == 1
    assert dist["small"] == 1
    assert dist["medium"] == 1
    assert dist["large"] == 1


def test_threat_level_calculation():
    """Test threat level assessment."""
    game = Game(seed=42, turn=10)

    # Create game state with enemy fleet approaching
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 50},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=3,
        y=2,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    game.stars = [star_a, star_b]

    player_p1 = Player(id="p1", home_star="B", visited_stars={"B"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "B"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Large enemy fleet close to home
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=40,
        origin="B",
        dest="A",
        dist_remaining=1,
        rationale="attack",
    )
    game.fleets = [fleet]

    metrics = calculate_strategic_metrics(game, "p2", 10)

    garrison = metrics["garrison"]
    assert garrison["nearest_enemy_fleet_size"] == 40
    assert garrison["threat_level"] in ["medium", "high"]


def test_territory_control():
    """Test territory control metrics."""
    game = Game(seed=42, turn=15)

    # Create stars in different zones
    stars = [
        # p2's home quadrant (upper-left)
        Star(
            id="A",
            name="Alpha",
            x=0,
            y=0,
            base_ru=3,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        Star(
            id="B",
            name="Beta",
            x=2,
            y=2,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        # Center zone
        Star(
            id="C",
            name="Gamma",
            x=5,
            y=5,
            base_ru=4,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        # p1's home quadrant (lower-right)
        Star(
            id="D",
            name="Delta",
            x=11,
            y=9,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 10},
        ),
    ]
    game.stars = stars

    player_p1 = Player(id="p1", home_star="D", visited_stars={"D"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "B", "C"})
    game.players = {"p1": player_p1, "p2": player_p2}
    game.fleets = []

    metrics = calculate_strategic_metrics(game, "p2", 15)

    territory = metrics["territory"]
    assert territory["stars_in_home_quadrant"] == 3  # A, B, and C (C is upper-left with sum=10)
    assert territory["stars_in_center_zone"] == 1  # C (sum=10 is in center zone range 9-12)
    assert territory["stars_in_opponent_quadrant"] == 0
    assert -1.0 <= territory["territorial_advantage"] <= 1.0


def test_no_enemy_fleets():
    """Test metrics when no enemy fleets are visible."""
    game = Game(seed=42, turn=1)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=11,
        y=9,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    game.stars = [star_a, star_b]

    player_p1 = Player(id="p1", home_star="B", visited_stars={"B"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p1": player_p1, "p2": player_p2}
    game.fleets = []  # No fleets

    metrics = calculate_strategic_metrics(game, "p2", 1)

    garrison = metrics["garrison"]
    assert garrison["nearest_enemy_fleet_distance"] is None
    assert garrison["nearest_enemy_fleet_size"] is None
    assert garrison["threat_level"] == "none"


def test_json_serializable():
    """Test that all metrics are JSON-serializable."""
    import json

    game = Game(seed=42, turn=1)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=11,
        y=9,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    game.stars = [star_a, star_b]

    player_p1 = Player(id="p1", home_star="B", visited_stars={"B"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p1": player_p1, "p2": player_p2}
    game.fleets = []

    metrics = calculate_strategic_metrics(game, "p2", 1)

    # Should not raise an exception
    json_str = json.dumps(metrics)
    assert len(json_str) > 0

    # Verify we can round-trip
    parsed = json.loads(json_str)
    assert parsed["turn"] == 1


def test_invalid_player_id():
    """Test error handling for invalid player ID."""
    game = Game(seed=42, turn=1)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    game.stars = [star_a]

    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p2": player_p2}
    game.fleets = []

    with pytest.raises(ValueError, match="Player p3 not found"):
        calculate_strategic_metrics(game, "p3", 1)


def test_production_ratio_zero_division():
    """Test production ratio when opponent has no production."""
    game = Game(seed=42, turn=1)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    game.stars = [star_a]

    player_p1 = Player(id="p1", home_star="A", visited_stars={"A"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A"})
    game.players = {"p1": player_p1, "p2": player_p2}
    game.fleets = []

    metrics = calculate_strategic_metrics(game, "p2", 1)

    resources = metrics["resources"]
    assert resources["opponent_production_ru"] == 0
    # When opponent has 0 production and player has production, ratio should be inf
    assert resources["production_ratio"] == float("inf")


def test_opponent_home_discovery():
    """Test opponent home star discovery tracking."""
    game = Game(seed=42, turn=5)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=11,
        y=9,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    game.stars = [star_a, star_b]

    # p2 has visited opponent's home
    player_p1 = Player(id="p1", home_star="B", visited_stars={"B"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "B"})
    game.players = {"p1": player_p1, "p2": player_p2}
    game.fleets = []

    metrics = calculate_strategic_metrics(game, "p2", 5)

    spatial = metrics["spatial_awareness"]
    assert spatial["opponent_home_discovered"] is True
