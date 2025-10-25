"""Star system data model."""

from dataclasses import dataclass, field
from typing import Dict, Optional


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
    owner: Optional[str]  # "p1", "p2", or None (NPC)
    npc_ships: int  # NPC defender count (initialized to base_ru for NPC stars)
    stationed_ships: Dict[str, int] = field(default_factory=dict)  # {"p1": 5, "p2": 0}

    def __post_init__(self):
        """Validate star data after initialization."""
        if not (0 <= self.x < 12):
            raise ValueError(f"Invalid x coordinate: {self.x} (must be 0-11)")
        if not (0 <= self.y < 10):
            raise ValueError(f"Invalid y coordinate: {self.y} (must be 0-9)")
        if not (1 <= self.base_ru <= 4):
            raise ValueError(f"Invalid base_ru: {self.base_ru} (must be 1-4)")
        if self.owner not in (None, "p1", "p2"):
            raise ValueError(
                f"Invalid owner: {self.owner} (must be None, 'p1', or 'p2')"
            )
        if self.npc_ships < 0:
            raise ValueError(f"Invalid npc_ships: {self.npc_ships} (must be >= 0)")
