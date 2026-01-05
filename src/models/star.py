"""Star system data model."""

from dataclasses import dataclass, field
from enum import Enum


class Quadrant(Enum):
    """Map quadrant enumeration."""

    NORTHWEST = "Northwest"
    NORTHEAST = "Northeast"
    SOUTHWEST = "Southwest"
    SOUTHEAST = "Southeast"


@dataclass
class Star:
    """Represents a star system on the map.

    Stars are the main strategic locations in the game. They can be controlled
    by players or remain as NPC (neutral) systems. Stars produce ships based
    on their resource units (RU) value.
    """

    id: str  # Unique identifier (e.g., "A", "B", "C")
    name: str  # Human-readable name (generated from seed)
    x: int  # X coordinate (0-11)
    y: int  # Y coordinate (0-9)
    base_ru: int  # Resource units (1-4)
    owner: str | None  # "p1", "p2", or None (NPC)
    npc_ships: int  # NPC defender count (initialized to base_ru for NPC stars)
    quadrant: Quadrant | None = None  # Map quadrant (auto-computed if not provided)
    stationed_ships: dict[str, int] = field(default_factory=dict)  # {"p1": 5, "p2": 0}

    def __post_init__(self):
        """Validate star data after initialization."""
        if not (0 <= self.x < 12):
            raise ValueError(f"Invalid x coordinate: {self.x} (must be 0-11)")
        if not (0 <= self.y < 10):
            raise ValueError(f"Invalid y coordinate: {self.y} (must be 0-9)")
        if not (1 <= self.base_ru <= 4):
            raise ValueError(f"Invalid base_ru: {self.base_ru} (must be 1-4)")
        if self.owner not in (None, "p1", "p2"):
            raise ValueError(f"Invalid owner: {self.owner} (must be None, 'p1', or 'p2')")
        if self.npc_ships < 0:
            raise ValueError(f"Invalid npc_ships: {self.npc_ships} (must be >= 0)")

        # Auto-compute quadrant from coordinates if not provided
        if self.quadrant is None:
            if self.x <= 5 and self.y <= 4:
                object.__setattr__(self, "quadrant", Quadrant.NORTHWEST)
            elif self.x >= 6 and self.y <= 4:
                object.__setattr__(self, "quadrant", Quadrant.NORTHEAST)
            elif self.x <= 5 and self.y >= 5:
                object.__setattr__(self, "quadrant", Quadrant.SOUTHWEST)
            else:  # x >= 6 and y >= 5
                object.__setattr__(self, "quadrant", Quadrant.SOUTHEAST)
