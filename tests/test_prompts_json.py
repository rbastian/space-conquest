"""Tests for JSON-formatted prompts."""

import json

from src.agent.prompts_json import format_game_state_prompt_json
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_npc_star_categorization_with_npc_ships():
    """Test that stars with owner=None and npc_ships>0 are categorized as NPC stars."""
    game = Game(seed=42, turn=1)

    # Create stars with various states
    star_npc = Star(
        id="A",
        name="NPC Star",
        x=2,
        y=2,
        base_ru=3,
        owner=None,
        npc_ships=5,
        stationed_ships={},
    )
    star_home = Star(
        id="B",
        name="Home",
        x=0,
        y=0,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    game.stars = [star_npc, star_home]

    # Create player with visited stars
    game.players = {
        "p1": Player(id="p1", home_star="B", visited_stars={"A", "B"}),
        "p2": Player(id="p2", home_star="C"),
    }

    # Generate prompt
    prompt = format_game_state_prompt_json(game, "p1")

    # Parse JSON from prompt
    json_start = prompt.index("{")
    json_end = prompt.rindex("}") + 1
    game_state = json.loads(prompt[json_start:json_end])

    # Verify NPC star is included
    npc_stars = game_state["neutral_territory"]["npc_stars"]
    assert len(npc_stars) == 1
    assert npc_stars[0]["id"] == "A"
    assert npc_stars[0]["name"] == "NPC Star"
    assert npc_stars[0]["estimated_defenders"] == 3  # Based on base_ru


def test_npc_star_categorization_after_combat_tie():
    """Test that stars with owner=None and npc_ships=0 (after tie) are still categorized as NPC stars."""
    game = Game(seed=42, turn=1)

    # Create star after combat tie: owner=None, npc_ships=0, no stationed ships
    star_empty = Star(
        id="A",
        name="Empty Star",
        x=2,
        y=2,
        base_ru=3,
        owner=None,
        npc_ships=0,  # After combat tie
        stationed_ships={},
    )
    star_home = Star(
        id="B",
        name="Home",
        x=0,
        y=0,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    game.stars = [star_empty, star_home]

    # Create player with visited stars
    game.players = {
        "p1": Player(id="p1", home_star="B", visited_stars={"A", "B"}),
        "p2": Player(id="p2", home_star="C"),
    }

    # Generate prompt
    prompt = format_game_state_prompt_json(game, "p1")

    # Parse JSON from prompt
    json_start = prompt.index("{")
    json_end = prompt.rindex("}") + 1
    game_state = json.loads(prompt[json_start:json_end])

    # Verify empty star is still included in NPC stars
    npc_stars = game_state["neutral_territory"]["npc_stars"]
    assert len(npc_stars) == 1
    assert npc_stars[0]["id"] == "A"
    assert npc_stars[0]["name"] == "Empty Star"
    # After tie, it's uncontrolled but still shown to player


def test_npc_star_not_shown_if_unvisited():
    """Test that NPC stars are only shown if visited."""
    game = Game(seed=42, turn=1)

    # Create NPC star that hasn't been visited
    star_npc = Star(
        id="A",
        name="Unvisited NPC",
        x=2,
        y=2,
        base_ru=3,
        owner=None,
        npc_ships=5,
        stationed_ships={},
    )
    star_home = Star(
        id="B",
        name="Home",
        x=0,
        y=0,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    game.stars = [star_npc, star_home]

    # Create player who hasn't visited star A
    game.players = {
        "p1": Player(id="p1", home_star="B", visited_stars={"B"}),
        "p2": Player(id="p2", home_star="C"),
    }

    # Generate prompt
    prompt = format_game_state_prompt_json(game, "p1")

    # Parse JSON from prompt
    json_start = prompt.index("{")
    json_end = prompt.rindex("}") + 1
    game_state = json.loads(prompt[json_start:json_end])

    # Verify NPC star is NOT in npc_stars (it's in unknown_stars)
    npc_stars = game_state["neutral_territory"]["npc_stars"]
    assert len(npc_stars) == 0

    # Verify it's in unknown stars instead
    unknown_stars = game_state["neutral_territory"]["unexplored_stars"]
    assert len(unknown_stars) == 1
    assert unknown_stars[0]["id"] == "A"


def test_star_coordinates_and_quadrant_in_json():
    """Test that all stars in JSON output include coordinates and quadrant fields."""
    game = Game(seed=42, turn=1)

    # Create stars in different quadrants
    star_nw = Star(
        id="A",
        name="Northwest Star",
        x=2,
        y=2,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_ne = Star(
        id="B",
        name="Northeast Star",
        x=8,
        y=2,
        base_ru=2,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 5},
    )
    star_sw = Star(
        id="C",
        name="Southwest Star",
        x=2,
        y=7,
        base_ru=2,
        owner=None,
        npc_ships=3,
        stationed_ships={},
    )
    star_se = Star(
        id="D",
        name="Southeast Star",
        x=8,
        y=7,
        base_ru=1,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    game.stars = [star_nw, star_ne, star_sw, star_se]

    # Create players with visited stars
    game.players = {
        "p1": Player(id="p1", home_star="A", visited_stars={"A", "B", "C"}),
        "p2": Player(id="p2", home_star="B", visited_stars={"B"}),
    }

    # Generate prompt
    prompt = format_game_state_prompt_json(game, "p1")

    # Parse JSON from prompt
    json_start = prompt.index("{")
    json_end = prompt.rindex("}") + 1
    game_state = json.loads(prompt[json_start:json_end])

    # Check controlled stars (star A - Northwest)
    controlled = game_state["my_empire"]["controlled_stars"]
    assert len(controlled) == 1
    assert controlled[0]["id"] == "A"
    assert "coordinates" in controlled[0]
    assert controlled[0]["coordinates"]["x"] == 2
    assert controlled[0]["coordinates"]["y"] == 2
    assert controlled[0]["quadrant"] == "Northwest"

    # Check enemy stars (star B - Northeast)
    enemy = game_state["opponent"]["visible_stars"]
    assert len(enemy) == 1
    assert enemy[0]["id"] == "B"
    assert "coordinates" in enemy[0]
    assert enemy[0]["coordinates"]["x"] == 8
    assert enemy[0]["coordinates"]["y"] == 2
    assert enemy[0]["quadrant"] == "Northeast"

    # Check NPC stars (star C - Southwest)
    npc = game_state["neutral_territory"]["npc_stars"]
    assert len(npc) == 1
    assert npc[0]["id"] == "C"
    assert "coordinates" in npc[0]
    assert npc[0]["coordinates"]["x"] == 2
    assert npc[0]["coordinates"]["y"] == 7
    assert npc[0]["quadrant"] == "Southwest"

    # Check unknown stars (star D - Southeast, not visited)
    unknown = game_state["neutral_territory"]["unexplored_stars"]
    assert len(unknown) == 1
    assert unknown[0]["id"] == "D"
    assert "coordinates" in unknown[0]
    assert unknown[0]["coordinates"]["x"] == 8
    assert unknown[0]["coordinates"]["y"] == 7
    assert unknown[0]["quadrant"] == "Southeast"

    # Check spatial awareness (home star)
    your_home = game_state["map_awareness"]["your_home"]
    assert "coordinates" in your_home
    assert your_home["coordinates"]["x"] == 2
    assert your_home["coordinates"]["y"] == 2
    assert your_home["quadrant"] == "Northwest"
