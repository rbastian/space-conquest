"""Player data model with fog-of-war knowledge."""

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class Player:
    """Player state with fog-of-war knowledge.

    Each player maintains their own view of the game state through visited_stars.
    Once a star is visited, the player has real-time intelligence on its current
    state (RU and ownership) by checking the actual star data.
    """

    id: str  # "p1" or "p2"
    home_star: str  # Home star ID
    visited_stars: Set[str] = field(
        default_factory=set
    )  # Stars visited by fleet arrivals
    fleets: List = field(
        default_factory=list
    )  # Player's fleets in transit (Fleet objects)

    def __post_init__(self):
        """Validate player data after initialization."""
        if self.id not in ("p1", "p2"):
            raise ValueError(f"Invalid player id: {self.id} (must be 'p1' or 'p2')")
        if not self.home_star:
            raise ValueError("home_star cannot be empty")
