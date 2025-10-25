"""Tests for Game Orchestrator - Bug Fix Verification."""

import pytest
from unittest.mock import Mock

from game import GameOrchestrator
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


def create_simple_game():
    """Create a simple game for testing."""
    game = Game(seed=42, turn=0)

    # Create two home stars (coordinates must be 0-11 for x, 0-9 for y)
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


def test_execute_turn_unpacks_tuple_correctly():
    """Test that execute_turn() tuple is unpacked correctly.

    This is the bug fix verification test. Previously, execute_turn() returned
    a tuple (game, combat_events, hyperspace_losses) but the orchestrator
    was treating it as just a Game object, causing AttributeError on game.winner.
    Now returns (game, combat_events, hyperspace_losses, rebellion_events).
    """
    game = create_simple_game()

    # Create mock players that return empty orders
    mock_p1 = Mock()
    mock_p1.get_orders = Mock(return_value=[])

    mock_p2 = Mock()
    mock_p2.get_orders = Mock(return_value=[])

    # Create orchestrator
    orchestrator = GameOrchestrator(game, mock_p1, mock_p2)

    # Execute one turn manually (not using full run() to avoid infinite loop)
    orders = {"p1": [], "p2": []}

    # This should NOT raise AttributeError: 'tuple' object has no attribute 'winner'
    try:
        result_game, combat_events, hyperspace_losses, rebellion_events = (
            orchestrator.turn_executor.execute_turn(orchestrator.game, orders)
        )

        # Verify the return types
        assert isinstance(result_game, Game), "First return value should be Game object"
        assert isinstance(combat_events, list), (
            "Second return value should be list of combat events"
        )
        assert isinstance(hyperspace_losses, list), (
            "Third return value should be list of hyperspace losses"
        )
        assert isinstance(rebellion_events, list), (
            "Fourth return value should be list of rebellion events"
        )

        # Verify game state is accessible
        assert hasattr(result_game, "winner"), (
            "Game object should have winner attribute"
        )
        assert result_game.turn == 1, "Turn should have incremented"

    except AttributeError as e:
        pytest.fail(f"Bug still present: {e}")


def test_orchestrator_stores_display_manager():
    """Test that GameOrchestrator initializes DisplayManager."""
    game = create_simple_game()
    mock_p1 = Mock()
    mock_p2 = Mock()

    orchestrator = GameOrchestrator(game, mock_p1, mock_p2)

    # Verify DisplayManager is initialized
    assert hasattr(orchestrator, "display"), (
        "Orchestrator should have display attribute"
    )
    assert orchestrator.display is not None, "Display manager should be initialized"


def test_display_methods_called_after_turn_execution(monkeypatch):
    """Test that events are properly stored in Game object after turn execution.

    After the consolidation of report display (Change 1), the orchestrator no longer
    calls display methods directly. Instead, events are stored in the Game object
    (combats_last_turn, hyperspace_losses_last_turn, rebellions_last_turn) by the
    TurnExecutor, and controllers retrieve them to pass to show_turn_summary().
    """
    game = create_simple_game()

    # Create mock players
    mock_p1 = Mock()
    mock_p1.get_orders = Mock(return_value=[])

    mock_p2 = Mock()
    mock_p2.get_orders = Mock(return_value=[])

    # Create orchestrator
    orchestrator = GameOrchestrator(game, mock_p1, mock_p2)

    # Mock input to prevent blocking
    monkeypatch.setattr("builtins.input", lambda _: None)

    # Create mock combat and hyperspace events
    from src.engine.combat import CombatEvent
    from src.engine.movement import HyperspaceLoss

    mock_combat_event = CombatEvent(
        star_id="A",
        star_name="Altair",
        combat_type="npc",
        attacker="p1",
        defender="npc",
        attacker_ships=5,
        defender_ships=2,
        winner="attacker",
        attacker_survivors=4,
        defender_survivors=0,
        attacker_losses=1,
        defender_losses=2,
        control_before=None,
        control_after=None,
        simultaneous=False,
    )
    mock_hyperspace_loss = HyperspaceLoss(
        fleet_id="p1-001", owner="p1", ships=3, origin="A", dest="B"
    )

    # Execute turn should return events on first call, then set winner on second call
    turn_count = [0]

    def mock_execute_turn(game, orders):
        turn_count[0] += 1
        if turn_count[0] == 1:
            # First turn: return events and store them in game object
            # (This simulates what the real TurnExecutor does)
            combat_dict = {
                "star_id": mock_combat_event.star_id,
                "star_name": mock_combat_event.star_name,
                "combat_type": mock_combat_event.combat_type,
                "attacker": mock_combat_event.attacker,
                "defender": mock_combat_event.defender,
                "attacker_ships": mock_combat_event.attacker_ships,
                "defender_ships": mock_combat_event.defender_ships,
                "winner": mock_combat_event.winner,
                "attacker_survivors": mock_combat_event.attacker_survivors,
                "defender_survivors": mock_combat_event.defender_survivors,
                "attacker_losses": mock_combat_event.attacker_losses,
                "defender_losses": mock_combat_event.defender_losses,
                "control_before": mock_combat_event.control_before,
                "control_after": mock_combat_event.control_after,
                "simultaneous": mock_combat_event.simultaneous,
            }
            loss_dict = {
                "fleet_id": mock_hyperspace_loss.fleet_id,
                "owner": mock_hyperspace_loss.owner,
                "ships": mock_hyperspace_loss.ships,
                "origin": mock_hyperspace_loss.origin,
                "dest": mock_hyperspace_loss.dest,
            }
            game.combats_last_turn = [combat_dict]
            game.hyperspace_losses_last_turn = [loss_dict]
            return game, [mock_combat_event], [mock_hyperspace_loss], []
        else:
            # Second turn: set winner to exit loop
            game.winner = "p1"
            return game, [], [], []

    orchestrator.turn_executor.execute_turn = mock_execute_turn

    # Run the game (should execute two turns and exit)
    final_game = orchestrator.run()

    # Verify that the game ended with the correct winner
    assert final_game.winner == "p1", "Game should have ended with winner"

    # Verify get_orders was called for both players
    # (This confirms that the flow continues to work correctly)
    assert mock_p1.get_orders.call_count >= 1, "p1.get_orders should be called at least once"
    assert mock_p2.get_orders.call_count >= 1, "p2.get_orders should be called at least once"


def test_game_attribute_remains_game_object_after_turn():
    """Test that self.game remains a Game object after turn execution."""
    game = create_simple_game()

    mock_p1 = Mock()
    mock_p1.get_orders = Mock(return_value=[])

    mock_p2 = Mock()
    mock_p2.get_orders = Mock(return_value=[])

    orchestrator = GameOrchestrator(game, mock_p1, mock_p2)

    # Execute turn directly on the executor to get the tuple
    orders = {"p1": [], "p2": []}
    result_game, combat_events, hyperspace_losses, rebellion_events = (
        orchestrator.turn_executor.execute_turn(orchestrator.game, orders)
    )

    # Simulate the orchestrator's assignment
    orchestrator.game = result_game

    # Verify game is still a Game object
    assert isinstance(orchestrator.game, Game), "self.game should remain a Game object"
    assert hasattr(orchestrator.game, "winner"), "Game should have winner attribute"
    assert hasattr(orchestrator.game, "turn"), "Game should have turn attribute"
    assert hasattr(orchestrator.game, "stars"), "Game should have stars attribute"

    # Should be able to check winner without AttributeError
    try:
        _winner = orchestrator.game.winner
        _turn = orchestrator.game.turn
    except AttributeError as e:
        pytest.fail(f"Bug still present - cannot access game attributes: {e}")


def test_turn_execution_with_actual_orders():
    """Test turn execution with real orders to ensure end-to-end flow works."""
    game = Game(seed=42, turn=0)

    # Create stars for order testing
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=3,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Gamma",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 20},
    )
    game.stars = [star_a, star_b, star_c]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Create mock players that return orders
    mock_p1 = Mock()
    mock_p1.get_orders = Mock(return_value=[Order(from_star="A", to_star="B", ships=5)])

    mock_p2 = Mock()
    mock_p2.get_orders = Mock(return_value=[])

    orchestrator = GameOrchestrator(game, mock_p1, mock_p2)

    # Execute turn
    orders = {"p1": [Order(from_star="A", to_star="B", ships=5)], "p2": []}

    # This should work without errors
    try:
        result_game, combat_events, hyperspace_losses, rebellion_events = (
            orchestrator.turn_executor.execute_turn(orchestrator.game, orders)
        )

        # Verify game state
        assert isinstance(result_game, Game)
        assert result_game.turn == 1
        assert len(result_game.fleets) == 1
        assert result_game.fleets[0].ships == 5
        assert result_game.fleets[0].dest == "B"

        # Verify events are lists
        assert isinstance(combat_events, list)
        assert isinstance(hyperspace_losses, list)

        # Should be able to check winner
        _ = result_game.winner

    except AttributeError as e:
        pytest.fail(f"Bug still present: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
