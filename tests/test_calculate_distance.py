"""Tests for calculate_distance tool."""

import pytest

from src.agent.tools import AgentTools
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star
from src.utils.rng import GameRNG


@pytest.fixture
def test_game():
    """Create a test game with known star positions."""
    stars = [
        # Star A at (0, 0)
        Star(
            id="A",
            name="Alpha",
            x=0,
            y=0,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 10},
        ),
        # Star B at (3, 0) - 3 turns away horizontally
        Star(
            id="B",
            name="Beta",
            x=3,
            y=0,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 5},
        ),
        # Star C at (0, 4) - 4 turns away vertically
        Star(
            id="C", name="Gamma", x=0, y=4, base_ru=3, owner=None, npc_ships=3, stationed_ships={}
        ),
        # Star D at (5, 5) - 5 turns away diagonally (Chebyshev max(5,5) = 5)
        Star(
            id="D", name="Delta", x=5, y=5, base_ru=2, owner=None, npc_ships=2, stationed_ships={}
        ),
    ]

    p1 = Player(id="p1", home_star="A")
    p2 = Player(id="p2", home_star="B")

    game = Game(
        seed=42,
        turn=10,
        stars=stars,
        players={"p1": p1, "p2": p2},
        fleets=[],
        rng=GameRNG(42),
    )

    return game


def test_calculate_distance_horizontal(test_game):
    """Test distance calculation for horizontal movement."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("A", "B")

    assert result["from_star"] == "A"
    assert result["from_star_name"] == "Alpha"
    assert result["to_star"] == "B"
    assert result["to_star_name"] == "Beta"
    assert result["distance_turns"] == 3
    assert result["current_turn"] == 10
    assert result["arrival_turn"] == 13  # turn 10 + 3
    # 3 turns: 1 - (0.98)^3 = 0.0588 = 5.88%
    assert abs(result["hyperspace_loss_probability"] - 0.0588) < 0.001


def test_calculate_distance_vertical(test_game):
    """Test distance calculation for vertical movement."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("A", "C")

    assert result["from_star"] == "A"
    assert result["to_star"] == "C"
    assert result["distance_turns"] == 4
    assert result["current_turn"] == 10
    assert result["arrival_turn"] == 14  # turn 10 + 4


def test_calculate_distance_diagonal(test_game):
    """Test distance calculation for diagonal movement (Chebyshev)."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("A", "D")

    assert result["from_star"] == "A"
    assert result["to_star"] == "D"
    assert result["distance_turns"] == 5  # max(5, 5) = 5
    assert result["current_turn"] == 10
    assert result["arrival_turn"] == 15  # turn 10 + 5


def test_calculate_distance_same_star(test_game):
    """Test distance calculation for same star (should be 0)."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("A", "A")

    assert result["distance_turns"] == 0
    assert result["current_turn"] == 10
    assert result["arrival_turn"] == 10  # turn 10 + 0
    assert result["hyperspace_loss_probability"] == 0.0  # No travel, no loss


def test_calculate_distance_reverse_direction(test_game):
    """Test distance calculation is symmetric (A->B == B->A)."""
    tools = AgentTools(test_game, player_id="p1")

    forward = tools.calculate_distance("A", "B")
    reverse = tools.calculate_distance("B", "A")

    assert forward["distance_turns"] == reverse["distance_turns"]
    assert forward["distance_turns"] == 3


def test_calculate_distance_lowercase_ids(test_game):
    """Test that lowercase star IDs are automatically uppercased."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("a", "b")

    assert result["from_star"] == "A"
    assert result["to_star"] == "B"
    assert result["distance_turns"] == 3


def test_calculate_distance_numeric_indices(test_game):
    """Test that numeric indices work (0 = A, 1 = B, etc.)."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.calculate_distance("0", "1")  # A to B

    assert result["from_star"] == "A"
    assert result["to_star"] == "B"
    assert result["distance_turns"] == 3


def test_calculate_distance_invalid_from_star(test_game):
    """Test error handling for invalid from_star."""
    tools = AgentTools(test_game, player_id="p1")

    with pytest.raises(ValueError, match="Invalid from_star"):
        tools.calculate_distance("Z", "B")


def test_calculate_distance_invalid_to_star(test_game):
    """Test error handling for invalid to_star."""
    tools = AgentTools(test_game, player_id="p1")

    with pytest.raises(ValueError, match="Invalid to_star"):
        tools.calculate_distance("A", "Z")


def test_calculate_distance_via_execute_tool(test_game):
    """Test calculate_distance via the execute_tool interface."""
    tools = AgentTools(test_game, player_id="p1")

    result = tools.execute_tool("calculate_distance", {"from": "A", "to": "B"})

    assert result["from_star"] == "A"
    assert result["to_star"] == "B"
    assert result["distance_turns"] == 3
    assert result["current_turn"] == 10
    assert result["arrival_turn"] == 13


def test_calculate_distance_tool_registry():
    """Test that calculate_distance is properly registered."""
    from src.agent.tool_models import TOOL_DEFINITIONS, TOOL_REGISTRY

    assert "calculate_distance" in TOOL_REGISTRY
    assert TOOL_REGISTRY["calculate_distance"]["input_model"].__name__ == "CalculateDistanceInput"
    assert TOOL_REGISTRY["calculate_distance"]["output_model"].__name__ == "CalculateDistanceOutput"

    # Check it appears in TOOL_DEFINITIONS for LLM
    tool_names = [tool["name"] for tool in TOOL_DEFINITIONS]
    assert "calculate_distance" in tool_names


def test_calculate_distance_works_regardless_of_fog_of_war(test_game):
    """Test that calculate_distance works for stars not yet visited (fog-of-war)."""
    tools = AgentTools(test_game, player_id="p1")

    # Player p1 hasn't visited star D
    assert "D" not in test_game.players["p1"].visited_stars

    # Should still work
    result = tools.calculate_distance("A", "D")

    assert result["from_star"] == "A"
    assert result["to_star"] == "D"
    assert result["distance_turns"] == 5


def test_calculate_distance_different_turn_numbers(test_game):
    """Test that arrival_turn updates based on current game turn."""
    tools = AgentTools(test_game, player_id="p1")

    # Turn 10
    result1 = tools.calculate_distance("A", "B")
    assert result1["current_turn"] == 10
    assert result1["distance_turns"] == 3
    assert result1["arrival_turn"] == 13

    # Advance to turn 20
    test_game.turn = 20
    result2 = tools.calculate_distance("A", "B")
    assert result2["current_turn"] == 20
    assert result2["distance_turns"] == 3  # distance unchanged
    assert result2["arrival_turn"] == 23  # but arrival advances


def test_calculate_distance_hyperspace_loss_probability(test_game):
    """Test hyperspace loss probability calculation."""
    tools = AgentTools(test_game, player_id="p1")

    # 0 turns: 0% loss
    result0 = tools.calculate_distance("A", "A")
    assert result0["hyperspace_loss_probability"] == 0.0

    # 3 turns: 1 - (0.98)^3 = 5.88%
    result3 = tools.calculate_distance("A", "B")
    assert abs(result3["hyperspace_loss_probability"] - 0.0588) < 0.001

    # 5 turns: 1 - (0.98)^5 = 9.61%
    result5 = tools.calculate_distance("A", "D")
    assert abs(result5["hyperspace_loss_probability"] - 0.0961) < 0.001

    # Test that longer distances have higher loss probability
    assert result5["hyperspace_loss_probability"] > result3["hyperspace_loss_probability"]
    assert result3["hyperspace_loss_probability"] > result0["hyperspace_loss_probability"]
