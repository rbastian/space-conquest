"""Fleet data model for ships in hyperspace transit."""

from dataclasses import dataclass


@dataclass
class Fleet:
    """Represents ships in hyperspace transit.

    Fleets are created when players send ships from one star to another.
    They travel through hyperspace and arrive after a number of turns equal
    to the Chebyshev distance between stars.
    """

    id: str  # Unique identifier (e.g., "p1-003")
    owner: str  # "p1" or "p2"
    ships: int  # Ship count
    origin: str  # Origin star ID
    dest: str  # Destination star ID
    dist_remaining: int  # Turns until arrival

    def __post_init__(self):
        """Validate fleet data after initialization."""
        if self.owner not in ("p1", "p2"):
            raise ValueError(f"Invalid owner: {self.owner} (must be 'p1' or 'p2')")
        if self.ships <= 0:
            raise ValueError(f"Invalid ships: {self.ships} (must be > 0)")
        if self.dist_remaining < 0:
            raise ValueError(
                f"Invalid dist_remaining: {self.dist_remaining} (must be >= 0)"
            )
