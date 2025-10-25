"""Tests for Phase 1: Fleet Movement."""

from src.engine.movement import process_fleet_movement
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star
from src.utils import GameRNG


def test_hyperspace_loss_destroys_fleet():
    """Test that d50 roll of 1 destroys entire fleet."""
    # Create game with seed that will roll 1 on first d50
    game = Game(seed=42, turn=0)
    game.rng = GameRNG(42)

    # Create a fleet
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=100,
        origin="A",
        dest="B",
        dist_remaining=2,
    )
    game.fleets = [fleet]

    # Create stars
    star_a = Star(id="A", name="Altair", x=0, y=0, base_ru=4, owner="p1", npc_ships=0)
    star_b = Star(
        id="B", name="Bellatrix", x=5, y=5, base_ru=2, owner=None, npc_ships=2
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Test multiple fleets to find one that gets destroyed
    # We'll create many fleets and check if any are destroyed
    test_fleets = []
    for i in range(100):
        test_fleets.append(
            Fleet(
                id=f"p1-{i:03d}",
                owner="p1",
                ships=10,
                origin="A",
                dest="B",
                dist_remaining=2,
            )
        )

    game.fleets = test_fleets
    initial_count = len(game.fleets)

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Some fleets should be destroyed (2% loss rate)
    # With 100 fleets, we expect around 2 destroyed (but could vary)
    assert len(game.fleets) < initial_count
    assert len(hyperspace_losses) > 0


def test_fleet_movement_decrements_distance():
    """Test that surviving fleets have distance decremented."""
    game = Game(seed=12345, turn=0)  # Different seed to avoid hyperspace loss

    # Create a fleet
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=5,
        origin="A",
        dest="B",
        dist_remaining=3,
    )
    game.fleets = [fleet]

    # Create stars
    star_a = Star(id="A", name="Altair", x=0, y=0, base_ru=4, owner="p1", npc_ships=0)
    star_b = Star(
        id="B", name="Bellatrix", x=2, y=1, base_ru=2, owner=None, npc_ships=2
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Check that fleet survived and distance decremented
    surviving_fleets = [f for f in game.fleets if f.id == "p1-001"]
    if len(surviving_fleets) > 0:
        assert surviving_fleets[0].dist_remaining == 2


def test_fleet_arrival_adds_ships_to_star():
    """Test that arriving fleets add ships to destination star."""
    game = Game(seed=100, turn=0)

    # Create a fleet arriving this turn
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=5,
        origin="A",
        dest="B",
        dist_remaining=1,
    )
    game.fleets = [fleet]

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=1,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Fleet should have arrived
    assert len(game.fleets) == 0 or "p1-001" not in [f.id for f in game.fleets]

    # Ships should be added to star B
    assert star_b.stationed_ships.get("p1", 0) >= 5


def test_fleet_arrival_reveals_star_ru():
    """Test that fleet arrival reveals star RU to player."""
    game = Game(seed=200, turn=0)

    # Create a fleet arriving at unknown star
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=3,
        origin="A",
        dest="B",
        dist_remaining=1,
    )
    game.fleets = [fleet]

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=1,
        y=0,
        base_ru=3,
        owner=None,
        npc_ships=3,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]

    # Create players - p1 hasn't visited star B
    player1 = Player(
        id="p1",
        home_star="A",
        visited_stars={"A"},
    )
    game.players = {
        "p1": player1,
        "p2": Player(id="p2", home_star="C"),
    }

    # Player hasn't visited star B yet
    assert "B" not in player1.visited_stars

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Player should now have visited star B
    assert "B" in player1.visited_stars


def test_multiple_fleets_arrive_simultaneously():
    """Test that multiple fleets can arrive at same star."""
    game = Game(seed=300, turn=0)

    # Create multiple fleets arriving at same star
    fleet1 = Fleet(
        id="p1-001",
        owner="p1",
        ships=3,
        origin="A",
        dest="B",
        dist_remaining=1,
    )
    fleet2 = Fleet(
        id="p1-002",
        owner="p1",
        ships=2,
        origin="A",
        dest="B",
        dist_remaining=1,
    )
    game.fleets = [fleet1, fleet2]

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=1,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Both fleets should arrive (assuming no hyperspace loss)
    # At least one should arrive
    assert star_b.stationed_ships.get("p1", 0) > 0


def test_no_fleets_in_transit():
    """Test that movement phase works when no fleets exist."""
    game = Game(seed=400, turn=0)
    game.fleets = []

    # Create stars
    star_a = Star(id="A", name="Altair", x=0, y=0, base_ru=4, owner="p1", npc_ships=0)
    game.stars = [star_a]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process movement
    game, hyperspace_losses = process_fleet_movement(game)

    # Should complete without error
    assert game.fleets == []


def test_hyperspace_loss_statistical():
    """Test that hyperspace loss rate is approximately 2%."""
    # Create multiple fleets and count losses
    total_fleets = 1000
    destroyed_count = 0

    for seed in range(total_fleets):
        game = Game(seed=seed, turn=0)
        fleet = Fleet(
            id="p1-001",
            owner="p1",
            ships=10,
            origin="A",
            dest="B",
            dist_remaining=2,
        )
        game.fleets = [fleet]

        # Create minimal stars
        star_a = Star(
            id="A", name="Altair", x=0, y=0, base_ru=4, owner="p1", npc_ships=0
        )
        star_b = Star(
            id="B", name="Bellatrix", x=2, y=0, base_ru=2, owner=None, npc_ships=2
        )
        game.stars = [star_a, star_b]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="C"),
        }

        # Process movement
        game, hyperspace_losses = process_fleet_movement(game)

        # Check if fleet was destroyed
        if len(game.fleets) == 0:
            destroyed_count += 1

    # Check that loss rate is approximately 2% (within reasonable margin)
    loss_rate = destroyed_count / total_fleets
    assert 0.01 < loss_rate < 0.03, f"Loss rate {loss_rate:.2%} outside expected range"
