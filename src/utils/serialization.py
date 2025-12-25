"""Game state serialization to/from JSON.

This module provides functions to save and load game state to JSON files,
enabling game persistence and replay functionality.
"""

import json
from pathlib import Path
from typing import Any

from ..models.fleet import Fleet
from ..models.game import Game
from ..models.player import Player
from ..models.star import Star
from ..utils.rng import GameRNG


def save_game(game: Game, filepath: str) -> None:
    """Save game state to JSON file.

    Args:
        game: Game state to save
        filepath: Path to save file (will be created in /state directory if relative)

    Example:
        save_game(game, "my_game.json")  # Saves to state/my_game.json
        save_game(game, "/absolute/path/game.json")  # Saves to absolute path
    """
    # Convert to absolute path if relative
    path = Path(filepath)
    if not path.is_absolute():
        # Create state directory if it doesn't exist
        state_dir = Path(__file__).parent.parent.parent / "state"
        state_dir.mkdir(exist_ok=True)
        path = state_dir / filepath

    # Serialize game state
    game_dict = _serialize_game(game)

    # Write to file
    with open(path, "w") as f:
        json.dump(game_dict, f, indent=2)


def load_game(filepath: str) -> Game:
    """Load game state from JSON file.

    Args:
        filepath: Path to saved game file

    Returns:
        Loaded Game object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid or malformed

    Example:
        game = load_game("my_game.json")  # Loads from state/my_game.json
        game = load_game("/absolute/path/game.json")  # Loads from absolute path
    """
    # Convert to absolute path if relative
    path = Path(filepath)
    if not path.is_absolute():
        state_dir = Path(__file__).parent.parent.parent / "state"
        path = state_dir / filepath

    # Read from file
    with open(path) as f:
        game_dict = json.load(f)

    # Deserialize game state
    return _deserialize_game(game_dict)


def _serialize_game(game: Game) -> dict[str, Any]:
    """Convert Game object to JSON-compatible dictionary.

    Args:
        game: Game to serialize

    Returns:
        Dictionary representation of game state
    """
    return {
        "seed": game.seed,
        "turn": game.turn,
        "stars": [_serialize_star(s) for s in game.stars],
        "fleets": [_serialize_fleet(f) for f in game.fleets],
        "players": {pid: _serialize_player(p) for pid, p in game.players.items()},
        "winner": game.winner,
        "turn_history": game.turn_history,
        "fleet_counter": game.fleet_counter,
        "rng_state": game.rng.get_state(),  # Save RNG state for determinism
    }


def _deserialize_game(data: dict[str, Any]) -> Game:
    """Reconstruct Game object from dictionary.

    Args:
        data: Dictionary representation of game state

    Returns:
        Reconstructed Game object
    """
    # Create RNG and restore state
    rng = GameRNG(data["seed"])
    if "rng_state" in data:
        # Convert RNG state from JSON (lists) back to tuples
        state = data["rng_state"]
        # The RNG state is a tuple with version, inner state tuple, and gauss_next
        if isinstance(state, list):
            # Convert list to tuple, and inner list to tuple
            state = (state[0], tuple(state[1]), state[2])
        rng.set_state(state)

    # Create game object
    game = Game(
        seed=data["seed"],
        turn=data["turn"],
        stars=[_deserialize_star(s) for s in data["stars"]],
        fleets=[_deserialize_fleet(f) for f in data["fleets"]],
        players={pid: _deserialize_player(p) for pid, p in data["players"].items()},
        rng=rng,
        winner=data.get("winner"),
        turn_history=data.get("turn_history", []),
        fleet_counter=data.get("fleet_counter", {"p1": 0, "p2": 0}),
    )

    return game


def _serialize_star(star: Star) -> dict[str, Any]:
    """Convert Star to dictionary."""
    return {
        "id": star.id,
        "name": star.name,
        "x": star.x,
        "y": star.y,
        "base_ru": star.base_ru,
        "owner": star.owner,
        "npc_ships": star.npc_ships,
        "stationed_ships": star.stationed_ships,
    }


def _deserialize_star(data: dict[str, Any]) -> Star:
    """Reconstruct Star from dictionary."""
    return Star(
        id=data["id"],
        name=data["name"],
        x=data["x"],
        y=data["y"],
        base_ru=data["base_ru"],
        owner=data.get("owner"),
        npc_ships=data.get("npc_ships", 0),
        stationed_ships=data.get("stationed_ships", {}),
    )


def _serialize_fleet(fleet: Fleet) -> dict[str, Any]:
    """Convert Fleet to dictionary."""
    return {
        "id": fleet.id,
        "owner": fleet.owner,
        "ships": fleet.ships,
        "origin": fleet.origin,
        "dest": fleet.dest,
        "dist_remaining": fleet.dist_remaining,
        "rationale": fleet.rationale,
    }


def _deserialize_fleet(data: dict[str, Any]) -> Fleet:
    """Reconstruct Fleet from dictionary."""
    return Fleet(
        id=data["id"],
        owner=data["owner"],
        ships=data["ships"],
        origin=data["origin"],
        dest=data["dest"],
        dist_remaining=data["dist_remaining"],
        rationale=data.get("rationale", "unknown"),  # Default for legacy saves
    )


def _serialize_player(player: Player) -> dict[str, Any]:
    """Convert Player to dictionary."""
    return {
        "id": player.id,
        "home_star": player.home_star,
        "visited_stars": list(player.visited_stars),
        "fleets": [_serialize_fleet(f) for f in player.fleets],
    }


def _deserialize_player(data: dict[str, Any]) -> Player:
    """Reconstruct Player from dictionary."""
    return Player(
        id=data["id"],
        home_star=data["home_star"],
        visited_stars=set(data.get("visited_stars", [])),
        fleets=[_deserialize_fleet(f) for f in data.get("fleets", [])],
    )
