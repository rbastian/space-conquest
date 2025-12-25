"""Order data model for player commands."""

from dataclasses import dataclass


@dataclass
class Order:
    """Represents a movement order submitted by a player.

    Orders are submitted by players at the end of each turn to specify
    how they want to move their ships. Orders are validated and executed
    in Phase 5 of turn processing.
    """

    from_star: str  # Origin star ID
    to_star: str  # Destination star ID
    ships: int  # Number of ships to move (must be > 0)
    rationale: str | None = None  # Strategic purpose (attack, reinforce, expand, etc.)

    def __post_init__(self):
        """Validate order data after initialization."""
        if self.ships <= 0:
            raise ValueError(f"Invalid ships: {self.ships} (must be > 0)")
        if not self.from_star:
            raise ValueError("from_star cannot be empty")
        if not self.to_star:
            raise ValueError("to_star cannot be empty")
        if self.from_star == self.to_star:
            raise ValueError(f"Cannot move ships from star to itself: {self.from_star}")
