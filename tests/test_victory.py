"""Tests for Phase 3: Victory Condition Checking."""

import pytest

from src.engine.victory import check_victory
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_p1_wins_by_capturing_p2_home():
    """Test P1 victory by capturing P2's home star."""
    game = Game(seed=42, turn=0)

    # Create home stars
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

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory
    has_winner = check_victory(game)

    assert has_winner is True
    assert game.winner == "p1"


def test_p2_wins_by_capturing_p1_home():
    """Test P2 victory by capturing P1's home star."""
    game = Game(seed=42, turn=0)

    # Create home stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p2",  # P2 captured P1's home
        npc_ships=0,
        stationed_ships={"p2": 5},
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

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory
    has_winner = check_victory(game)

    assert has_winner is True
    assert game.winner == "p2"


def test_draw_both_capture_homes():
    """Test draw when both players capture opponent's home."""
    game = Game(seed=42, turn=0)

    # Create home stars - both captured by opponent
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p2",  # P2 captured P1's home
        npc_ships=0,
        stationed_ships={"p2": 5},
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

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory
    has_winner = check_victory(game)

    assert has_winner is True
    assert game.winner == "draw"


def test_no_victory_both_control_own_homes():
    """Test no victory when both players still control their homes."""
    game = Game(seed=42, turn=0)

    # Create home stars - each player controls their own
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

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory
    has_winner = check_victory(game)

    assert has_winner is False
    assert game.winner is None


def test_no_victory_home_npc_controlled():
    """Test no victory when home is NPC-controlled (not captured by opponent)."""
    game = Game(seed=42, turn=0)

    # Create home stars - one is NPC (liberated but not captured)
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner=None,  # NPC-controlled (not captured by P2)
        npc_ships=5,
        stationed_ships={},
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

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory
    has_winner = check_victory(game)

    assert has_winner is False
    assert game.winner is None


def test_victory_with_other_stars_on_map():
    """Test victory works correctly with multiple stars on map."""
    game = Game(seed=42, turn=0)

    # Create home stars and some NPC stars
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
    star_c = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 3},
    )
    star_d = Star(
        id="D",
        name="Deneb",
        x=3,
        y=3,
        base_ru=1,
        owner=None,
        npc_ships=1,
        stationed_ships={},
    )
    game.stars = [star_a, star_b, star_c, star_d]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory - P1 should win by capturing B
    has_winner = check_victory(game)

    assert has_winner is True
    assert game.winner == "p1"


def test_victory_home_star_not_found_error():
    """Test error handling when home star not found."""
    game = Game(seed=42, turn=0)

    # Create star that isn't a home star
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
    game.stars = [star_a]

    # Create players with home stars that don't exist
    game.players = {
        "p1": Player(id="p1", home_star="X"),
        "p2": Player(id="p2", home_star="Y"),
    }

    # Check victory should raise error
    with pytest.raises(ValueError, match="Home stars not found"):
        check_victory(game)


def test_victory_empty_star_control():
    """Test victory when home has no ships but is controlled."""
    game = Game(seed=42, turn=0)

    # P1 captured P2's home but has no ships there
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
        owner="p1",  # P1 owns it
        npc_ships=0,
        stationed_ships={"p1": 0},  # But no ships stationed
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Check victory - P1 should still win (ownership matters, not ship count)
    has_winner = check_victory(game)

    assert has_winner is True
    assert game.winner == "p1"
