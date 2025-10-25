"""Tests for game state serialization."""

import tempfile
from pathlib import Path

import pytest

from src.engine.map_generator import generate_map
from src.models.fleet import Fleet
from src.utils.serialization import load_game, save_game


def test_save_and_load_game():
    """Test that a game can be saved and loaded correctly."""
    # Generate a game
    game = generate_map(seed=42)

    # Modify game state slightly
    game.turn = 5
    game.fleets.append(
        Fleet(id="p1-001", owner="p1", ships=10, origin="A", dest="B", dist_remaining=3)
    )

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_game.json"
        save_game(game, str(filepath))

        # Load back
        loaded_game = load_game(str(filepath))

        # Verify basic attributes
        assert loaded_game.seed == game.seed
        assert loaded_game.turn == game.turn
        assert loaded_game.winner == game.winner
        assert len(loaded_game.stars) == len(game.stars)
        assert len(loaded_game.fleets) == len(game.fleets)
        assert len(loaded_game.players) == len(game.players)


def test_save_preserves_star_data():
    """Test that star data is preserved correctly."""
    game = generate_map(seed=123)

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_stars.json"
        save_game(game, str(filepath))
        loaded_game = load_game(str(filepath))

        # Check each star
        for orig_star, loaded_star in zip(game.stars, loaded_game.stars):
            assert orig_star.id == loaded_star.id
            assert orig_star.name == loaded_star.name
            assert orig_star.x == loaded_star.x
            assert orig_star.y == loaded_star.y
            assert orig_star.base_ru == loaded_star.base_ru
            assert orig_star.owner == loaded_star.owner
            assert orig_star.npc_ships == loaded_star.npc_ships
            assert orig_star.stationed_ships == loaded_star.stationed_ships


def test_save_preserves_fleet_data():
    """Test that fleet data is preserved correctly."""
    game = generate_map(seed=456)
    game.fleets.append(
        Fleet(id="p1-001", owner="p1", ships=5, origin="A", dest="C", dist_remaining=2)
    )
    game.fleets.append(
        Fleet(id="p2-001", owner="p2", ships=3, origin="B", dest="D", dist_remaining=4)
    )

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_fleets.json"
        save_game(game, str(filepath))
        loaded_game = load_game(str(filepath))

        # Check fleets
        assert len(loaded_game.fleets) == 2
        for orig_fleet, loaded_fleet in zip(game.fleets, loaded_game.fleets):
            assert orig_fleet.id == loaded_fleet.id
            assert orig_fleet.owner == loaded_fleet.owner
            assert orig_fleet.ships == loaded_fleet.ships
            assert orig_fleet.origin == loaded_fleet.origin
            assert orig_fleet.dest == loaded_fleet.dest
            assert orig_fleet.dist_remaining == loaded_fleet.dist_remaining


def test_save_preserves_player_fog_of_war():
    """Test that player fog-of-war data is preserved."""
    game = generate_map(seed=789)

    # Update player visited stars
    game.players["p1"].visited_stars.add("C")

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_fog.json"
        save_game(game, str(filepath))
        loaded_game = load_game(str(filepath))

        # Check player knowledge
        assert (
            loaded_game.players["p1"].visited_stars == game.players["p1"].visited_stars
        )


def test_save_preserves_rng_state():
    """Test that RNG state is preserved for determinism."""
    game = generate_map(seed=999)

    # Generate some random numbers to advance RNG state
    game.rng.randint(1, 100)
    game.rng.randint(1, 100)

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "test_rng.json"
        save_game(game, str(filepath))
        loaded_game = load_game(str(filepath))

        # Generate same random numbers from both RNGs
        orig_nums = [game.rng.randint(1, 100) for _ in range(10)]
        loaded_nums = [loaded_game.rng.randint(1, 100) for _ in range(10)]

        # Should match exactly
        assert orig_nums == loaded_nums


def test_load_nonexistent_file():
    """Test that loading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_game("nonexistent_file_xyz.json")
