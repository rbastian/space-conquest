"""Tests for fog-of-war symmetry in combat displays.

Verifies that both human and LLM players see only the combats they participated in.
"""

import pytest
from io import StringIO
import sys

from src.interface.display import DisplayManager
from src.engine.combat import CombatEvent
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def create_test_game():
    """Create a minimal game for testing."""
    game = Game(seed=42, turn=1)
    game.stars = [
        Star(
            id="A",
            name="Alpha",
            x=0,
            y=0,
            base_ru=2,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 5},
        ),
        Star(
            id="B",
            name="Beta",
            x=5,
            y=5,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 5},
        ),
        Star(
            id="C",
            name="Gamma",
            x=10,
            y=9,
            base_ru=2,
            owner=None,
            npc_ships=3,
            stationed_ships={},
        ),
    ]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }
    return game


def test_player_participated_in_npc_combat():
    """Test fog-of-war filter for NPC combat."""
    display = DisplayManager()

    # p1 attacks NPC
    event_p1_npc = CombatEvent(
        star_id="C",
        star_name="Gamma",
        combat_type="npc",
        attacker="p1",
        defender="npc",
        attacker_ships=5,
        defender_ships=3,
        winner="attacker",
        attacker_survivors=4,
        defender_survivors=0,
        attacker_losses=1,
        defender_losses=3,
        control_before=None,
        control_after=None,
        simultaneous=False,
    )

    # p1 should see it (they attacked)
    assert display._player_participated_in_combat(event_p1_npc, "p1") is True

    # p2 should NOT see it (they didn't participate)
    assert display._player_participated_in_combat(event_p1_npc, "p2") is False


def test_player_participated_in_combined_npc_combat():
    """Test fog-of-war filter for combined NPC combat."""
    display = DisplayManager()

    # Both players attack NPC together
    event_combined = CombatEvent(
        star_id="C",
        star_name="Gamma",
        combat_type="npc",
        attacker="combined",
        defender="npc",
        attacker_ships=10,
        defender_ships=5,
        winner="attacker",
        attacker_survivors=8,
        defender_survivors=0,
        attacker_losses=2,
        defender_losses=5,
        control_before=None,
        control_after=None,
        simultaneous=False,
    )

    # Both players should see it (combined attack)
    assert display._player_participated_in_combat(event_combined, "p1") is True
    assert display._player_participated_in_combat(event_combined, "p2") is True


def test_player_participated_in_pvp_combat():
    """Test fog-of-war filter for PvP combat."""
    display = DisplayManager()

    # p1 attacks p2
    event_pvp = CombatEvent(
        star_id="B",
        star_name="Beta",
        combat_type="pvp",
        attacker="p1",
        defender="p2",
        attacker_ships=10,
        defender_ships=5,
        winner="attacker",
        attacker_survivors=7,
        defender_survivors=0,
        attacker_losses=3,
        defender_losses=5,
        control_before="p2",
        control_after="p1",
        simultaneous=False,
    )

    # Both p1 (attacker) and p2 (defender) should see it
    assert display._player_participated_in_combat(event_pvp, "p1") is True
    assert display._player_participated_in_combat(event_pvp, "p2") is True


def test_display_combat_filters_for_player():
    """Test that display_combat_results filters events based on player_id."""
    game = create_test_game()
    display = DisplayManager()

    # Create multiple combat events
    events = [
        # p1 attacks NPC at C
        CombatEvent(
            star_id="C",
            star_name="Gamma",
            combat_type="npc",
            attacker="p1",
            defender="npc",
            attacker_ships=5,
            defender_ships=3,
            winner="attacker",
            attacker_survivors=4,
            defender_survivors=0,
            attacker_losses=1,
            defender_losses=3,
            control_before=None,
            control_after=None,
            simultaneous=False,
        ),
        # p2 attacks NPC at D (hypothetical)
        CombatEvent(
            star_id="D",
            star_name="Delta",
            combat_type="npc",
            attacker="p2",
            defender="npc",
            attacker_ships=8,
            defender_ships=4,
            winner="attacker",
            attacker_survivors=6,
            defender_survivors=0,
            attacker_losses=2,
            defender_losses=4,
            control_before=None,
            control_after=None,
            simultaneous=False,
        ),
    ]

    # Capture stdout to verify filtering
    old_stdout = sys.stdout

    # Test p1's view (should only see their combat)
    sys.stdout = StringIO()
    display.display_combat_results(events, game, player_id="p1")
    p1_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # p1 should see their combat at Gamma but not p2's combat at Delta
    assert "Gamma" in p1_output
    assert "Delta" not in p1_output

    # Test p2's view (should only see their combat)
    sys.stdout = StringIO()
    display.display_combat_results(events, game, player_id="p2")
    p2_output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    # p2 should see their combat at Delta but not p1's combat at Gamma
    assert "Delta" in p2_output
    assert "Gamma" not in p2_output


def test_display_combat_shows_all_without_player_id():
    """Test that display_combat_results shows all events when player_id is None (victory screen)."""
    game = create_test_game()
    display = DisplayManager()

    events = [
        CombatEvent(
            star_id="C",
            star_name="Gamma",
            combat_type="npc",
            attacker="p1",
            defender="npc",
            attacker_ships=5,
            defender_ships=3,
            winner="attacker",
            attacker_survivors=4,
            defender_survivors=0,
            attacker_losses=1,
            defender_losses=3,
            control_before=None,
            control_after=None,
            simultaneous=False,
        ),
        CombatEvent(
            star_id="D",
            star_name="Delta",
            combat_type="npc",
            attacker="p2",
            defender="npc",
            attacker_ships=8,
            defender_ships=4,
            winner="attacker",
            attacker_survivors=6,
            defender_survivors=0,
            attacker_losses=2,
            defender_losses=4,
            control_before=None,
            control_after=None,
            simultaneous=False,
        ),
    ]

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # No player_id = omniscient view (victory screen mode)
    display.display_combat_results(events, game, player_id=None)
    output = sys.stdout.getvalue()

    sys.stdout = old_stdout

    # Should see both combats
    assert "Gamma" in output
    assert "Delta" in output


def test_no_output_when_player_sees_no_combats():
    """Test that no combat report is printed when player didn't participate in any combats."""
    game = create_test_game()
    display = DisplayManager()

    # Only p1 has combats
    events = [
        CombatEvent(
            star_id="C",
            star_name="Gamma",
            combat_type="npc",
            attacker="p1",
            defender="npc",
            attacker_ships=5,
            defender_ships=3,
            winner="attacker",
            attacker_survivors=4,
            defender_survivors=0,
            attacker_losses=1,
            defender_losses=3,
            control_before=None,
            control_after=None,
            simultaneous=False,
        ),
    ]

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    # p2 should see nothing (didn't participate)
    display.display_combat_results(events, game, player_id="p2")
    p2_output = sys.stdout.getvalue()

    sys.stdout = old_stdout

    # Should be empty (no combat reports header)
    assert "Combat Reports" not in p2_output
    assert "Gamma" not in p2_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
