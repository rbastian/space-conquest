"""Tests for ASCII map renderer."""

from src.interface.renderer import MapRenderer
from src.models.player import Player
from src.models.star import Star


def test_render_empty_grid():
    """Test rendering with no stars."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A")

    map_str = renderer.render(player, [])

    # Should be 10 lines (rows)
    lines = map_str.split("\n")
    assert len(lines) == 10

    # Each line should be 35 chars (12 cells * 2 chars + 11 spaces)
    for line in lines:
        assert line == ".. .. .. .. .. .. .. .. .. .. .. .."


def test_render_single_unknown_star():
    """Test rendering a star with unknown RU."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A")

    star = Star(
        id="B",
        name="Bellatrix",
        x=5,
        y=3,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={"p1": 0, "p2": 0},
    )

    map_str = renderer.render(player, [star])
    lines = map_str.split("\n")

    # Check that row 3 has the star at position 5
    row_3 = lines[3]
    cells = row_3.split(" ")
    assert cells[5] == "?B"


def test_render_known_star():
    """Test rendering a star with known RU."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A", visited_stars={"A", "C"})

    star = Star(
        id="C",
        name="Capella",
        x=2,
        y=1,
        base_ru=3,
        owner=None,
        npc_ships=3,
        stationed_ships={"p1": 0, "p2": 0},
    )

    map_str = renderer.render(player, [star])
    lines = map_str.split("\n")

    # Check that row 1 has the star at position 2 with RU
    row_1 = lines[1]
    cells = row_1.split(" ")
    assert cells[2] == "3C"


def test_render_controlled_star():
    """Test rendering a player-controlled star."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A", visited_stars={"A"})

    star = Star(
        id="A",
        name="Altair",
        x=1,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 4, "p2": 0},
    )

    map_str = renderer.render(player, [star])
    lines = map_str.split("\n")

    # Check that row 0 has the star at position 1 with @ marker
    row_0 = lines[0]
    cells = row_0.split(" ")
    assert cells[1] == "@A"


def test_render_opponent_star():
    """Test rendering opponent-controlled star."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A", visited_stars={"A", "B"})

    star = Star(
        id="B",
        name="Bellatrix",
        x=10,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p1": 0, "p2": 4},
    )

    map_str = renderer.render(player, [star])
    lines = map_str.split("\n")

    # Check that row 9 has the star at position 10 with ! marker
    row_9 = lines[9]
    cells = row_9.split(" ")
    assert cells[10] == "!B"


def test_render_multiple_stars():
    """Test rendering multiple stars."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A", visited_stars={"A", "B"})

    stars = [
        Star(
            id="A",
            name="Altair",
            x=0,
            y=0,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 4, "p2": 0},
        ),
        Star(
            id="B",
            name="Bellatrix",
            x=11,
            y=9,
            base_ru=2,
            owner=None,
            npc_ships=2,
            stationed_ships={"p1": 0, "p2": 0},
        ),
    ]

    map_str = renderer.render(player, stars)
    lines = map_str.split("\n")

    # Check both stars
    cells_0 = lines[0].split(" ")
    cells_9 = lines[9].split(" ")
    assert cells_0[0] == "@A"
    assert cells_9[11] == "2B"


def test_render_with_coords():
    """Test rendering with coordinate labels."""
    renderer = MapRenderer()
    player = Player(id="p1", home_star="A")

    map_str = renderer.render_with_coords(player, [])
    lines = map_str.split("\n")

    # Should have header + 10 rows
    assert len(lines) == 11

    # Header should have column numbers
    header = lines[0]
    assert " 0" in header
    assert "11" in header

    # Rows should have row numbers
    for i, line in enumerate(lines[1:]):
        assert line.startswith(f"{i:2d} ")
