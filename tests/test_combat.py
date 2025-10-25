"""Tests for Phase 2: Combat Resolution."""

import math


from src.engine.combat import process_combat, resolve_combat
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_resolve_combat_attacker_wins():
    """Test combat where attacker has more ships."""
    result = resolve_combat(attacker_ships=10, defender_ships=4)

    assert result.winner == "attacker"
    assert result.attacker_losses == math.ceil(4 / 2)  # 2
    assert result.defender_losses == 4
    assert result.attacker_survivors == 8
    assert result.defender_survivors == 0


def test_resolve_combat_defender_wins():
    """Test combat where defender has more ships."""
    result = resolve_combat(attacker_ships=3, defender_ships=10)

    assert result.winner == "defender"
    assert result.attacker_losses == 3
    assert result.defender_losses == math.ceil(3 / 2)  # 2
    assert result.attacker_survivors == 0
    assert result.defender_survivors == 8


def test_resolve_combat_tie():
    """Test combat where both sides have equal ships."""
    result = resolve_combat(attacker_ships=5, defender_ships=5)

    assert result.winner is None
    assert result.attacker_losses == 5
    assert result.defender_losses == 5
    assert result.attacker_survivors == 0
    assert result.defender_survivors == 0


def test_resolve_combat_odd_numbers():
    """Test combat with odd number of ships (ceil function)."""
    # 5 vs 3: attacker wins, loses ceil(3/2) = 2
    result = resolve_combat(attacker_ships=5, defender_ships=3)
    assert result.winner == "attacker"
    assert result.attacker_losses == 2
    assert result.attacker_survivors == 3


def test_npc_combat_player_wins():
    """Test player defeating NPC defenders."""
    game = Game(seed=42, turn=0)

    # Create NPC star with defenders
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=3,
        stationed_ships={"p1": 5},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # P1 should win, NPC eliminated, P1 takes control
    assert star.npc_ships == 0
    assert star.owner == "p1"  # P1 takes control after defeating NPC
    assert star.stationed_ships["p1"] == 3  # 5 - ceil(3/2) = 5 - 2 = 3


def test_npc_combat_npc_wins():
    """Test NPC defenders defeating player attackers."""
    game = Game(seed=42, turn=0)

    # Create NPC star with strong defenders
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=10,
        stationed_ships={"p1": 3},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # NPC should win, P1 eliminated
    assert star.npc_ships == 8  # 10 - ceil(3/2) = 10 - 2 = 8
    assert star.owner is None
    assert star.stationed_ships["p1"] == 0


def test_npc_combat_multiple_players():
    """Test multiple players arriving at NPC star simultaneously.

    NEW SPEC: PvP combat first, then winner vs NPC.
    """
    game = Game(seed=42, turn=0)

    # Create NPC star with both players attacking
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=4,
        stationed_ships={"p1": 3, "p2": 3},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # NEW SPEC: PvP first
    # P1 (3) vs P2 (3) → Tie, both eliminated
    # No winner to fight NPC
    # Result: NPC retains control with 4 ships
    assert star.npc_ships == 4  # NPC untouched (no one left to fight)
    assert star.stationed_ships["p1"] == 0  # Eliminated in PvP tie
    assert star.stationed_ships["p2"] == 0  # Eliminated in PvP tie
    assert star.owner is None  # Star remains NPC-controlled


def test_player_vs_player_combat():
    """Test player vs player combat after NPC eliminated."""
    game = Game(seed=42, turn=0)

    # Create star with two players (no NPC)
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={"p1": 7, "p2": 4},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # P1 should win
    assert star.owner == "p1"
    assert star.stationed_ships["p1"] == 5  # 7 - ceil(4/2) = 7 - 2 = 5
    assert star.stationed_ships["p2"] == 0


def test_player_vs_player_tie():
    """Test player vs player combat ending in tie."""
    game = Game(seed=42, turn=0)

    # Create star with equal forces
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={"p1": 5, "p2": 5},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # Both eliminated
    assert star.stationed_ships["p1"] == 0
    assert star.stationed_ships["p2"] == 0
    # Owner should be None for unowned star
    assert star.owner is None


def test_no_combat_single_player():
    """Test no combat when only one player present."""
    game = Game(seed=42, turn=0)

    # Create star with only one player
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={"p1": 5},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # P1 takes control without combat
    assert star.owner == "p1"
    assert star.stationed_ships["p1"] == 5


def test_no_combat_empty_star():
    """Test no combat when star is empty."""
    game = Game(seed=42, turn=0)

    # Create empty star
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # No change
    assert star.owner is None
    assert star.npc_ships == 0


def test_sequential_combat_npc_then_player():
    """Test simultaneous arrival at NPC star with unequal forces.

    NEW SPEC: PvP combat first, then winner vs NPC.
    """
    game = Game(seed=42, turn=0)

    # Create star: NPC defenders, both players attacking
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={"p1": 5, "p2": 3},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # NEW SPEC: PvP first
    # First: P1 (5) vs P2 (3) → P1 wins
    # P1 losses: ceil(3/2) = 2, survivors = 5 - 2 = 3
    #
    # Then: P1 (3) vs NPC (2) → P1 wins
    # P1 losses: ceil(2/2) = 1, survivors = 3 - 1 = 2
    assert star.owner == "p1"
    assert star.stationed_ships["p1"] == 2
    assert star.stationed_ships["p2"] == 0
    assert star.npc_ships == 0


def test_combat_at_multiple_stars():
    """Test combat resolution at multiple stars simultaneously."""
    game = Game(seed=42, turn=0)

    # Create multiple stars with combat
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=3,
        stationed_ships={"p1": 5},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={"p1": 4, "p2": 6},
    )
    game.stars = [star_a, star_b]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="C"),
        "p2": Player(id="p2", home_star="D"),
    }

    # Process combat
    game = process_combat(game)

    # Star A: P1 (5) defeats NPC (3) -> P1 has 3 survivors, takes control
    assert star_a.owner == "p1"
    assert star_a.stationed_ships["p1"] == 3

    # Star B: P2 (6) defeats P1 (4) -> P2 has 4 survivors, takes control
    assert star_b.owner == "p2"
    assert star_b.stationed_ships["p2"] == 4
    assert star_b.stationed_ships["p1"] == 0


def test_player_controlled_star_attacked():
    """Test existing player control contested by opponent."""
    game = Game(seed=42, turn=0)

    # Create star controlled by P1, attacked by P2
    star = Star(
        id="A",
        name="Altair",
        x=5,
        y=5,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 4, "p2": 7},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="B"),
        "p2": Player(id="p2", home_star="C"),
    }

    # Process combat
    game = process_combat(game)

    # P2 should win and take control
    assert star.owner == "p2"
    assert star.stationed_ships["p2"] == 5  # 7 - ceil(4/2) = 7 - 2 = 5
    assert star.stationed_ships["p1"] == 0
