"""Tests for independent phase execution in TurnExecutor.

These tests verify that the new phase architecture allows independent
testing and composition of individual phases.
"""

from src.engine.turn_executor import PhaseResults, TurnExecutor
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


def create_test_game():
    """Create a basic test game."""
    game = Game(seed=42, turn=0)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Beta",
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


def test_phase_movement_independent():
    """Test that phase 1 (movement) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    # Add a fleet to the game
    from src.models.fleet import Fleet

    game.fleets.append(
        Fleet(
            id="p1-001",
            owner="p1",
            ships=5,
            origin="A",
            dest="B",
            dist_remaining=2,
            rationale="attack",
        )
    )

    # Execute movement phase only
    game, hyperspace_losses, fleet_arrivals = executor.execute_phase_movement(game)

    # Fleet should have moved
    assert len(game.fleets) == 1
    assert game.fleets[0].dist_remaining == 1
    assert len(hyperspace_losses) == 0
    assert len(fleet_arrivals) == 0  # No arrivals yet


def test_phase_combat_independent():
    """Test that phase 2 (combat) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    # Set up a combat scenario - P1 attacks P2's home
    game.stars[1].stationed_ships["p1"] = 5  # P1 has 5 ships at star B
    game.stars[1].stationed_ships["p2"] = 10  # P2 has 10 ships at star B

    # Execute combat phase only
    game, combat_events = executor.execute_phase_combat(game)

    # Combat should have occurred
    assert len(combat_events) == 1
    assert combat_events[0].star_id == "B"
    assert len(game.combats_last_turn) == 1


def test_phase_rebellions_independent():
    """Test that phase 3 (rebellions) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    # Create an under-garrisoned non-home star
    star_c = Star(
        id="C",
        name="Gamma",
        x=5,
        y=5,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 2},  # Under-garrisoned (2 < 4)
    )
    game.stars.append(star_c)

    # Execute rebellion phase only (multiple times to trigger rebellion)
    # Note: This is probabilistic, so we run it multiple times
    rebellion_occurred = False
    for _ in range(20):  # Try 20 times, should get at least one rebellion
        game_copy = Game(seed=game.seed + _, turn=0)
        game_copy.stars = [s for s in game.stars]
        game_copy.players = game.players

        game_copy, rebellion_events = executor.execute_phase_rebellions(game_copy)

        if len(rebellion_events) > 0:
            rebellion_occurred = True
            assert rebellion_events[0].star == "C"
            break

    # With 20 tries, probability of failure is (0.5)^20 ≈ 0.0001%
    assert rebellion_occurred, "No rebellion occurred in 20 attempts (extremely unlikely)"


def test_phase_victory_check_independent():
    """Test that phase 4 (victory check) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    # Set up victory condition - P1 controls P2's home
    game.stars[1].owner = "p1"

    # Execute victory check phase only
    game = executor.execute_phase_victory_check(game)

    # Victory should be detected
    assert game.winner == "p1"


def test_phase_orders_independent():
    """Test that phase 6 (order processing) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    # Execute order processing phase only
    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}
    game = executor.execute_phase_orders(game, orders)

    # Fleet should be created
    assert len(game.fleets) == 1
    assert game.fleets[0].owner == "p1"
    assert game.fleets[0].ships == 5


def test_phase_production_independent():
    """Test that phase 7 (production) can be executed independently."""
    game = create_test_game()
    executor = TurnExecutor()

    initial_ships = game.stars[0].stationed_ships["p1"]

    # Execute production phase only
    game = executor.execute_phase_production(game)

    # Home star should produce 4 ships
    assert game.stars[0].stationed_ships["p1"] == initial_ships + 4


def test_orchestration_pre_display_phases():
    """Test that the pre-display orchestration method composes phases correctly."""
    game = create_test_game()
    executor = TurnExecutor()

    # Add a fleet for movement
    from src.models.fleet import Fleet

    game.fleets.append(
        Fleet(
            id="p1-001",
            owner="p1",
            ships=5,
            origin="A",
            dest="B",
            dist_remaining=1,
            rationale="attack",
        )
    )

    initial_turn = game.turn

    # Execute pre-display phases (1-4)
    game, results = executor.execute_pre_display_phases(game)

    # Check that results are returned correctly
    assert isinstance(results, PhaseResults)
    assert isinstance(results.combat_events, list)
    assert isinstance(results.hyperspace_losses, list)
    assert isinstance(results.rebellion_events, list)

    # Turn should be incremented
    assert game.turn == initial_turn + 1

    # Fleet should have arrived (movement phase executed)
    assert len(game.fleets) == 0  # Fleet removed after arrival


def test_orchestration_post_order_phases():
    """Test that the post-order orchestration method composes phases correctly."""
    game = create_test_game()
    executor = TurnExecutor()

    initial_ships = game.stars[0].stationed_ships["p1"]

    # Execute post-order phases (6-7)
    orders = {"p1": [Order(from_star="A", to_star="B", ships=3)], "p2": []}
    game = executor.execute_post_order_phases(game, orders)

    # Fleet should be created (order processing executed)
    assert len(game.fleets) == 1
    assert game.fleets[0].ships == 3

    # Production should have occurred (production phase executed)
    # Initial - 3 (sent) + 4 (production) = initial + 1
    assert game.stars[0].stationed_ships["p1"] == initial_ships - 3 + 4


def test_backward_compatibility_execute_phases_1_to_4():
    """Test that old method name still works."""
    game = create_test_game()
    executor = TurnExecutor()

    # Old method should still work
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_phases_1_to_4(game)

    assert isinstance(combat_events, list)
    assert isinstance(hyperspace_losses, list)
    assert isinstance(rebellion_events, list)
    assert game.turn == 1  # Turn incremented


def test_backward_compatibility_execute_phases_6_to_7():
    """Test that old method name still works."""
    game = create_test_game()
    executor = TurnExecutor()

    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}

    # Old method should still work
    game = executor.execute_phases_6_to_7(game, orders)

    assert len(game.fleets) == 1
    assert game.fleets[0].ships == 5


def test_backward_compatibility_execute_turn():
    """Test that old execute_turn method still works."""
    game = create_test_game()
    executor = TurnExecutor()

    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}

    # Old method should still work
    game, combat_events, hyperspace_losses, rebellion_events = executor.execute_turn(game, orders)

    assert game.turn == 1
    assert len(game.fleets) == 1
    assert isinstance(combat_events, list)
    assert isinstance(hyperspace_losses, list)
    assert isinstance(rebellion_events, list)
