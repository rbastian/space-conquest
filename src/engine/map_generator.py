"""Star map generation logic with balanced quadrant distribution."""

from typing import List, Tuple

from ..models import Game, Player, Star
from ..utils import (
    GRID_X,
    GRID_Y,
    HOME_DISTANCE_RANGE,
    HOME_RU,
    NUM_STARS,
    GameRNG,
    chebyshev_distance,
)

# Fixed star ID to name mapping (deterministic)
STAR_ID_TO_NAME = {
    "A": "Altair",
    "B": "Bellatrix",
    "C": "Capella",
    "D": "Deneb",
    "E": "Epsilon Eridani",
    "F": "Fomalhaut",
    "G": "Gamma Crucis",
    "H": "Hadar",
    "I": "Izar",
    "J": "Jabbah",
    "K": "Kappa Phoenicis",
    "L": "Lesath",
    "M": "Mintaka",
    "N": "Naos",
    "O": "Ophiuchi",
    "P": "Polaris",
}

# Quadrant definitions for balanced star distribution
# 12x10 board divided into four 6x5 quadrants
QUADRANTS = {
    "Q1": {  # Northwest - P1 home region
        "x_range": (0, 5),
        "y_range": (0, 4),
        "npc_count": 4,
        "ru_values": [1, 2, 2, 3],  # 8 RU total
    },
    "Q2": {  # Northeast - Neutral
        "x_range": (6, 11),
        "y_range": (0, 4),
        "npc_count": 3,
        "ru_values": [1, 2, 3],  # 6 RU total
    },
    "Q3": {  # Southwest - Neutral
        "x_range": (0, 5),
        "y_range": (5, 9),
        "npc_count": 3,
        "ru_values": [1, 2, 3],  # 6 RU total
    },
    "Q4": {  # Southeast - P2 home region
        "x_range": (6, 11),
        "y_range": (5, 9),
        "npc_count": 4,
        "ru_values": [1, 2, 2, 3],  # 8 RU total
    },
}


def generate_map(seed: int) -> Game:
    """Generate a balanced game map with quadrant-based star distribution.

    Algorithm:
    1. Place 2 home stars (0-3 parsecs from corners, using Chebyshev distance)
    2. Place 14 NPC stars using balanced quadrant distribution:
       - Q1 (NW): 4 NPC stars with RU {1,2,2,3} = 8 RU
       - Q2 (NE): 3 NPC stars with RU {1,2,3} = 6 RU
       - Q3 (SW): 3 NPC stars with RU {1,2,3} = 6 RU
       - Q4 (SE): 4 NPC stars with RU {1,2,2,3} = 8 RU
    3. Shuffle star IDs (A-P) and assign to stars in generation order
    4. Assign star names deterministically based on star ID
    5. Initialize NPC ships = base_ru for each NPC star
    6. Create initial player objects with fog-of-war

    Args:
        seed: RNG seed for deterministic map generation

    Returns:
        Game object with initialized map and players
    """
    rng = GameRNG(seed)

    # Track occupied cells to avoid collisions
    occupied_cells: set[Tuple[int, int]] = set()

    # Place home stars (0-3 parsecs from corners)
    p1_home = _place_home_star_in_corner(rng, corner=(0, 0), max_dist=3, occupied_cells=occupied_cells)
    occupied_cells.add(p1_home)

    p2_home = _place_home_star_in_corner(rng, corner=(GRID_X - 1, GRID_Y - 1), max_dist=3, occupied_cells=occupied_cells)
    occupied_cells.add(p2_home)

    # Generate NPC stars by quadrant with balanced RU distribution
    npc_stars: list[dict] = []
    for quad_name in ["Q1", "Q2", "Q3", "Q4"]:  # Deterministic order
        quad_config = QUADRANTS[quad_name]

        # Shuffle RU values for this quadrant
        ru_values = quad_config["ru_values"].copy()
        rng.shuffle(ru_values)

        # Place stars in this quadrant
        for ru_value in ru_values:
            position = _find_random_cell_in_quadrant(
                rng,
                quad_config["x_range"],
                quad_config["y_range"],
                occupied_cells,
            )
            occupied_cells.add(position)
            npc_stars.append({"position": position, "ru": ru_value})

    # Shuffle star IDs for random assignment
    star_ids = list("ABCDEFGHIJKLMNOP")
    rng.shuffle(star_ids)

    # Create stars list
    stars: List[Star] = []

    # Add p1 home star (first star in generation order)
    p1_star_id = star_ids[0]
    stars.append(
        Star(
            id=p1_star_id,
            name=STAR_ID_TO_NAME[p1_star_id],
            x=p1_home[0],
            y=p1_home[1],
            base_ru=HOME_RU,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": HOME_RU, "p2": 0},
        )
    )

    # Add p2 home star (second star in generation order)
    p2_star_id = star_ids[1]
    stars.append(
        Star(
            id=p2_star_id,
            name=STAR_ID_TO_NAME[p2_star_id],
            x=p2_home[0],
            y=p2_home[1],
            base_ru=HOME_RU,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p1": 0, "p2": HOME_RU},
        )
    )

    # Add NPC stars (14 stars)
    for i, npc_data in enumerate(npc_stars):
        star_id = star_ids[i + 2]  # Offset by 2 for home stars
        stars.append(
            Star(
                id=star_id,
                name=STAR_ID_TO_NAME[star_id],
                x=npc_data["position"][0],
                y=npc_data["position"][1],
                base_ru=npc_data["ru"],
                owner=None,
                npc_ships=npc_data["ru"],
                stationed_ships={"p1": 0, "p2": 0},
            )
        )

    # Create players with initial fog-of-war
    p1 = Player(
        id="p1",
        home_star=p1_star_id,
        visited_stars={p1_star_id},  # Home star is visited
        fleets=[],
    )

    p2 = Player(
        id="p2",
        home_star=p2_star_id,
        visited_stars={p2_star_id},  # Home star is visited
        fleets=[],
    )

    # Create game object
    game = Game(
        seed=seed,
        turn=0,
        stars=stars,
        fleets=[],
        players={"p1": p1, "p2": p2},
        rng=rng,
        winner=None,
        turn_history=[],
        fleet_counter={"p1": 0, "p2": 0},
    )

    return game


def _place_home_star_in_corner(
    rng: GameRNG,
    corner: Tuple[int, int],
    max_dist: int,
    occupied_cells: set[Tuple[int, int]],
) -> Tuple[int, int]:
    """Place a home star within max_dist of corner.

    Args:
        rng: Random number generator
        corner: Corner coordinates (x, y)
        max_dist: Maximum Chebyshev distance from corner
        occupied_cells: Set of already occupied cells

    Returns:
        Tuple of (x, y) coordinates for home star

    Raises:
        RuntimeError: If no valid position found
    """
    corner_x, corner_y = corner

    # Generate all valid cells within max_dist
    valid_cells = []
    for x in range(GRID_X):
        for y in range(GRID_Y):
            chebyshev_dist = max(abs(x - corner_x), abs(y - corner_y))
            if chebyshev_dist <= max_dist and (x, y) not in occupied_cells:
                valid_cells.append((x, y))

    if not valid_cells:
        raise RuntimeError(
            f"Could not find unoccupied cell within {max_dist} parsecs of corner {corner}"
        )

    return rng.choice(valid_cells)


def _find_random_cell_in_quadrant(
    rng: GameRNG,
    x_range: Tuple[int, int],
    y_range: Tuple[int, int],
    occupied: set[Tuple[int, int]],
) -> Tuple[int, int]:
    """Find random unoccupied cell in quadrant.

    Args:
        rng: Random number generator
        x_range: Tuple of (x_min, x_max) inclusive range
        y_range: Tuple of (y_min, y_max) inclusive range
        occupied: Set of occupied cells

    Returns:
        Tuple of (x, y) coordinates

    Raises:
        RuntimeError: If no unoccupied cell found after max attempts
    """
    x_min, x_max = x_range
    y_min, y_max = y_range

    attempts = 0
    max_attempts = 100

    while attempts < max_attempts:
        x = rng.randint(x_min, x_max)
        y = rng.randint(y_min, y_max)

        if (x, y) not in occupied:
            return (x, y)

        attempts += 1

    raise RuntimeError(
        f"Could not find unoccupied cell in quadrant "
        f"x[{x_min},{x_max}] y[{y_min},{y_max}] after {max_attempts} attempts"
    )
