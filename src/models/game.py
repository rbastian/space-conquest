"""Game state container."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..utils import GameRNG
from .fleet import Fleet
from .player import Player
from .star import Star


@dataclass
class Game:
    """Main game state container.

    The Game class holds all game state including stars, fleets, players,
    and the RNG for deterministic gameplay. All game logic operates on
    this state.
    """

    seed: int  # RNG seed
    turn: int  # Current turn number
    stars: List[Star] = field(default_factory=list)  # All stars
    fleets: List[Fleet] = field(default_factory=list)  # All fleets
    players: Dict[str, Player] = field(default_factory=dict)  # "p1" and "p2"
    rng: Optional[GameRNG] = None  # Seeded RNG instance
    winner: Optional[str] = None  # "p1", "p2", "draw", or None
    turn_history: List[Dict] = field(
        default_factory=list
    )  # Event log for replay (format: [{"turn": N, "events": [...]}])
    fleet_counter: Dict[str, int] = field(
        default_factory=lambda: {"p1": 0, "p2": 0}
    )  # Fleet ID generation
    order_errors: Dict[str, List[str]] = field(
        default_factory=dict
    )  # Player ID -> list of order error messages
    rebellions_last_turn: List[Dict] = field(
        default_factory=list
    )  # Rebellion events from previous turn
    combats_last_turn: List[Dict] = field(
        default_factory=list
    )  # Combat events from previous turn
    combats_history: List[List[Dict]] = field(
        default_factory=list
    )  # Combat history: list of combat lists from last 5 turns (oldest to newest)
    hyperspace_losses_last_turn: List[Dict] = field(
        default_factory=list
    )  # Hyperspace loss events from previous turn
    rebellion_explanation_shown: Dict[str, bool] = field(
        default_factory=lambda: {"p1": False, "p2": False}
    )  # Track if rebellion explanation has been shown to each player
    p2_model_id: Optional[str] = None  # Model ID for p2 (for display name generation)
    agent_memory: Dict[str, Dict[str, List[Dict]]] = field(
        default_factory=dict
    )  # Agent memory persistence (per player)

    def __post_init__(self):
        """Initialize RNG if not provided."""
        if self.rng is None:
            self.rng = GameRNG(self.seed)
        if self.turn < 0:
            raise ValueError(f"Invalid turn: {self.turn} (must be >= 0)")
        if self.winner not in (None, "p1", "p2", "draw"):
            raise ValueError(
                f"Invalid winner: {self.winner} (must be None, 'p1', 'p2', or 'draw')"
            )
