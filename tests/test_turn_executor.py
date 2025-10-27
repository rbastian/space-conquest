"""Tests for Turn Executor - Full Turn Integration."""

from src.engine.turn_executor import TurnExecutor
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


def create_basic_game(seed=42):
    """Create a basic game with both home stars for testing."""
    game = Game(seed=seed, turn=0)

    # Create both home stars
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
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    return game


def test_execute_turn_increments_turn_counter():
    """Test that turn counter increments after execution."""
    game = create_basic_game()

    executor = TurnExecutor()
    orders = {"p1": [], "p2": []}

    # Execute turn
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Turn should increment
    assert game.turn == 1


def test_execute_turn_processes_orders():
    """Test that orders create fleets."""
    game = Game(seed=42, turn=0)

    # Create two stars
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
        x=3,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()
    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}

    # Execute turn
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Fleet should be created
    assert len(game.fleets) == 1
    assert game.fleets[0].owner == "p1"
    assert game.fleets[0].ships == 5
    assert game.fleets[0].dest == "B"
    assert game.fleets[0].dist_remaining == 3  # Manhattan distance


def test_execute_turn_deducts_ships():
    """Test that orders deduct ships from origin immediately in Phase 4."""
    game = Game(seed=42, turn=0)

    # Create star
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
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()
    orders = {"p1": [Order(from_star="A", to_star="B", ships=3)], "p2": []}

    # Execute turn
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Ships should be deducted immediately in Phase 4
    # 10 (start) - 3 (fleet) + 4 (home production) = 11
    # The 3 ships are already in the fleet, not at the star
    assert star_a.stationed_ships["p1"] == 11

    # Fleet should be created with ships already deducted
    assert len(game.fleets) == 1
    assert game.fleets[0].owner == "p1"
    assert game.fleets[0].ships == 3
    assert game.fleets[0].origin == "A"
    assert game.fleets[0].dest == "B"


def test_execute_turn_validates_orders():
    """Test that invalid orders are logged but don't crash."""
    game = Game(seed=42, turn=0)

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 5},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=1,
        y=1,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 4},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Try to send to non-existent star
    orders = {"p1": [Order(from_star="A", to_star="C", ships=5)], "p2": []}

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Should have error logged
    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1
    assert "does not exist" in game.order_errors["p1"][0]

    # No fleet should be created
    assert len(game.fleets) == 0

    # Ships should not be deducted (but production adds 4 more)
    assert star_a.stationed_ships["p1"] == 9  # 5 + 4 production


def test_execute_turn_victory_stops_processing():
    """Test that victory stops further turn processing."""
    game = Game(seed=42, turn=0)

    # Set up victory condition - P1 controls P2's home
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
        x=11,
        y=9,
        base_ru=4,
        owner="p1",  # P1 captured P2's home
        npc_ships=0,
        stationed_ships={"p1": 5},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()
    orders = {"p1": [], "p2": []}

    # Execute turn
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Game should have winner
    # Note: Turn counter increments even on victory (phases 1-3 executed)
    # This is correct behavior - the turn DID happen before victory was detected
    assert game.winner == "p1"
    assert game.turn == 1  # Turn increments because phases 1-3 executed


def test_multiple_orders_from_same_star():
    """Test multiple orders from same star."""
    game = Game(seed=42, turn=0)

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=2,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Capella",
        x=0,
        y=3,
        base_ru=1,
        owner=None,
        npc_ships=1,
        stationed_ships={},
    )
    star_d = Star(
        id="D",
        name="Deneb",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c, star_d]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="D"),
    }

    executor = TurnExecutor()
    orders = {
        "p1": [
            Order(from_star="A", to_star="B", ships=5),
            Order(from_star="A", to_star="C", ships=3),
        ],
        "p2": [],
    }

    # Execute turn
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Both fleets should be created
    assert len(game.fleets) == 2
    # Ships deducted immediately in Phase 4
    # 20 (start) - 5 (fleet1) - 3 (fleet2) + 4 (production) = 16
    assert star_a.stationed_ships["p1"] == 16


def test_full_turn_cycle():
    """Test complete turn with all phases."""
    game = Game(seed=100, turn=0)

    # Create complex scenario
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
        x=2,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Turn 1: Send fleet to B
    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    assert game.turn == 1
    assert len(game.fleets) == 1

    # Turn 2: Fleet arrives and fights NPC
    orders = {"p1": [], "p2": []}
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    assert game.turn == 2
    # Fleet should arrive and fight NPC (assuming survival)
    # P1 (5) vs NPC (2) -> P1 wins with 4 survivors


def test_order_from_uncontrolled_star():
    """Test graceful handling of order from uncontrolled star."""
    game = Game(seed=42, turn=0)

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
        x=2,
        y=0,
        base_ru=2,
        owner="p2",  # Controlled by P2
        npc_ships=0,
        stationed_ships={"p2": 5},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # P1 tries to order from P2's star
    orders = {"p1": [Order(from_star="B", to_star="A", ships=3)], "p2": []}

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Should have error logged (ownership check catches this)
    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1
    assert "do not control" in game.order_errors["p1"][0].lower()

    # No fleet should be created
    assert len(game.fleets) == 0


def test_order_to_nonexistent_star():
    """Test graceful handling of order to nonexistent star."""
    game = Game(seed=42, turn=0)

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
        y=1,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Order to nonexistent star
    orders = {"p1": [Order(from_star="A", to_star="Z", ships=5)], "p2": []}

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Should have error logged
    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1
    assert "does not exist" in game.order_errors["p1"][0]

    # No fleet should be created
    assert len(game.fleets) == 0


def test_fleet_id_generation():
    """Test that fleet IDs are generated correctly."""
    game = Game(seed=42, turn=0)

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
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
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Create multiple fleets
    orders = {
        "p1": [
            Order(from_star="A", to_star="B", ships=3),
            Order(from_star="A", to_star="B", ships=2),
        ],
        "p2": [],
    }
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Check fleet IDs
    assert game.fleets[0].id == "p1-000"
    assert game.fleets[1].id == "p1-001"
    assert game.fleet_counter["p1"] == 2


def test_both_players_submit_orders():
    """Test both players submitting orders."""
    game = Game(seed=42, turn=0)

    # Create stars for both players
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
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    star_c = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b, star_c]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Both players send fleets
    orders = {
        "p1": [Order(from_star="A", to_star="C", ships=5)],
        "p2": [Order(from_star="B", to_star="C", ships=6)],
    }
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Both fleets should be created
    assert len(game.fleets) == 2
    p1_fleet = [f for f in game.fleets if f.owner == "p1"][0]
    p2_fleet = [f for f in game.fleets if f.owner == "p2"][0]
    assert p1_fleet.dest == "C"
    assert p2_fleet.dest == "C"


def test_multiple_orders_exceed_ships():
    """Test that multiple orders from same star cannot exceed available ships (over-commitment)."""
    game = Game(seed=42, turn=0)

    # Create home stars and a captured star (C) where we'll test the validation
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
        base_ru=1,
        owner=None,
        npc_ships=1,
        stationed_ships={},
    )
    # Star C is NOT a home star, so it gets base_ru production (1)
    # Initial: 4 ships, After production: 4 + 1 = 5 ships
    star_c = Star(
        id="C",
        name="Capella",
        x=2,
        y=0,
        base_ru=1,
        owner="p1",  # Controlled by p1 but not home star
        npc_ships=0,
        stationed_ships={"p1": 4},
    )
    star_d = Star(
        id="D",
        name="Deneb",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c, star_d]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="D"),
    }

    executor = TurnExecutor()

    # Try to send 7 ships total from star C
    # Star C has 4 ships. Orders are processed in Phase 4 (before production in Phase 5)
    # So we have 4 ships available when orders are processed
    # Ordering 7 ships should be rejected (over-commitment)
    orders = {
        "p1": [
            Order(from_star="C", to_star="A", ships=4),
            Order(from_star="C", to_star="B", ships=3),
        ],
        "p2": [],
    }

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Should have over-commitment error logged
    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1
    assert "Over-commitment at star C" in game.order_errors["p1"][0]
    assert "Total ordered: 7 ships, Available: 4 ships" in game.order_errors["p1"][0]
    assert "Orders from C:" in game.order_errors["p1"][0]

    # No fleets should be created (entire order set rejected)
    assert len(game.fleets) == 0

    # Ships should not be deducted from star C, and production happens at end
    assert star_c.stationed_ships["p1"] == 5  # 4 initial + 1 production (Phase 5)


def test_partial_order_execution():
    """Test lenient execution: skip invalid orders, execute valid ones."""
    game = Game(seed=42, turn=0)

    # Create stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=2,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Capella",
        x=0,
        y=3,
        base_ru=1,
        owner=None,
        npc_ships=1,
        stationed_ships={},
    )
    star_d = Star(
        id="D",
        name="Deneb",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c, star_d]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="D"),
    }

    executor = TurnExecutor()

    # Mix of valid and invalid orders
    orders = {
        "p1": [
            Order(from_star="A", to_star="B", ships=5),  # Valid
            Order(from_star="A", to_star="Z", ships=3),  # Invalid (nonexistent dest)
            Order(from_star="A", to_star="C", ships=4),  # Valid
        ],
        "p2": [],
    }

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # Should have one error logged
    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1
    assert "does not exist" in game.order_errors["p1"][0]
    assert "Order 1" in game.order_errors["p1"][0]  # Second order (0-indexed)

    # Two valid fleets should be created
    assert len(game.fleets) == 2
    assert game.fleets[0].dest == "B"
    assert game.fleets[0].ships == 5
    assert game.fleets[1].dest == "C"
    assert game.fleets[1].ships == 4

    # Ships deducted immediately for valid orders
    # 20 (start) - 5 (fleet1) - 4 (fleet2) + 4 (production) = 15
    # The invalid order (3 ships to Z) was skipped, so those ships not deducted
    assert star_a.stationed_ships["p1"] == 15


def test_no_crash_on_multiple_error_types():
    """Test that multiple different error types are all handled gracefully."""
    game = Game(seed=42, turn=0)

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
        x=2,
        y=0,
        base_ru=2,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 5},
    )
    star_c = Star(
        id="C",
        name="Capella",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    executor = TurnExecutor()

    # Various error types that should all be caught gracefully
    valid_orders = [
        Order(from_star="A", to_star="Z", ships=3),  # Nonexistent destination
        Order(
            from_star="B", to_star="A", ships=2
        ),  # Not owned (will trigger over-commitment)
    ]
    test_orders = {"p1": valid_orders, "p2": []}

    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, test_orders
    )

    # Should have error (ownership check catches the "not owned" order first)
    assert "p1" in game.order_errors
    assert "do not control" in game.order_errors["p1"][0].lower()

    # No fleets should be created
    assert len(game.fleets) == 0


def test_empty_order_list():
    """Test that empty order lists are handled gracefully."""
    game = create_basic_game()
    executor = TurnExecutor()

    orders = {"p1": [], "p2": []}

    # Should not crash
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(
        game, orders
    )

    # No errors
    assert "p1" not in game.order_errors
    assert "p2" not in game.order_errors

    # No fleets created
    assert len(game.fleets) == 0


def test_order_errors_cleared_between_turns():
    """Test that order errors don't accumulate across turns."""
    game = Game(seed=42, turn=0)

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
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    executor = TurnExecutor()

    # Turn 1: Invalid order
    orders = {"p1": [Order(from_star="A", to_star="Z", ships=5)], "p2": []}
    game, _, _, _ = executor.execute_turn(game, orders)

    assert "p1" in game.order_errors
    assert len(game.order_errors["p1"]) == 1

    # Turn 2: Valid order (errors should be cleared)
    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}
    game, _, _, _ = executor.execute_turn(game, orders)

    # No errors this turn, so p1 should not be in order_errors
    assert "p1" not in game.order_errors

    # Fleet should have been created successfully
    assert len(game.fleets) == 1
