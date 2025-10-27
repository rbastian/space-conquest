"""Test that the display shows an arrow indicator for fleets arriving this turn."""

from io import StringIO
import sys

from src.interface.display import DisplayManager
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_fleet_arriving_this_turn_shows_arrow():
    """Test that a fleet arriving THIS turn shows '→' indicator."""
    game = Game(seed=42, turn=3)

    # Create stars
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
        x=5,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]

    # Create player
    player = Player(id="p1", home_star="A")
    game.players = {"p1": player}

    # Create fleet that will arrive THIS turn
    # At Turn 3 with dist_remaining=1: arrival_turn = 3 + 1 - 1 = 3 (this turn!)
    fleet_arriving = Fleet(
        id="p1-001",
        owner="p1",
        ships=5,
        origin="A",
        dest="B",
        dist_remaining=1,
    )

    # Create fleet that will arrive NEXT turn
    # At Turn 3 with dist_remaining=2: arrival_turn = 3 + 2 - 1 = 4 (next turn)
    fleet_next_turn = Fleet(
        id="p1-002",
        owner="p1",
        ships=3,
        origin="A",
        dest="B",
        dist_remaining=2,
    )

    game.fleets = [fleet_arriving, fleet_next_turn]

    # Capture display output
    display = DisplayManager()
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        display._show_fleets_in_transit(player, game)
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    print("\n=== Display Output ===")
    print(output)

    # Verify output contains the arrow indicator for arriving fleet
    assert "Turn 3 →" in output, "Fleet arriving this turn should show arrow indicator"
    assert "Turn 4" in output, "Fleet arriving next turn should NOT show arrow"
    assert "Turn 4 →" not in output, "Only arriving fleets should have arrow"

    # Verify both fleets are shown
    assert "p1-001" in output
    assert "p1-002" in output

    print("✓ Display correctly indicates fleet arriving this turn with '→'")


def test_fleet_arriving_future_turn_no_arrow():
    """Test that fleets arriving in FUTURE turns don't show arrow."""
    game = Game(seed=42, turn=1)

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
        x=5,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star_a, star_b]

    player = Player(id="p1", home_star="A")
    game.players = {"p1": player}

    # Fleet arriving Turn 5 (far in future)
    # At Turn 1 with dist_remaining=5: arrival_turn = 1 + 5 - 1 = 5
    fleet = Fleet(
        id="p1-001",
        owner="p1",
        ships=5,
        origin="A",
        dest="B",
        dist_remaining=5,
    )
    game.fleets = [fleet]

    display = DisplayManager()
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        display._show_fleets_in_transit(player, game)
        output = captured_output.getvalue()
    finally:
        sys.stdout = old_stdout

    print("\n=== Display Output ===")
    print(output)

    # Verify NO arrow for future arrival
    assert "Turn 5" in output, "Should show arrival turn"
    assert "→" not in output, "Should NOT show arrow for future arrival"

    print("✓ Display correctly shows no arrow for future arrivals")
