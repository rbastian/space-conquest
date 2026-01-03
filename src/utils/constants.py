"""Game configuration constants from specification."""

import math

# Grid dimensions
GRID_X = 12
GRID_Y = 10

# Star configuration
NUM_STARS = 18
HOME_RU = 4
NPC_RU_RANGE = (1, 3)  # Base RU for NPC stars

# Probabilities
HYPERSPACE_LOSS_BASE = 0.02  # Base constant for n log n formula (2%)
HYPERSPACE_LOSS_PROB = HYPERSPACE_LOSS_BASE  # Kept for backward compatibility
REBELLION_PROB = 0.5  # 50% if under-garrisoned (d6 roll of 4-6)

# Map generation
HOME_DISTANCE_RANGE = (
    0,
    3,
)  # Chebyshev distance from corners (gives 6-11 parsec separation)

# Movement
MOVE_RATE = 1  # Parsecs per turn

# Testing
RNG_SEED_DEFAULT = 42  # Default seed for testing


def calculate_hyperspace_cumulative_risk(distance: int) -> float:
    """Calculate cumulative hyperspace loss probability for a journey.

    Uses n log n scaling: risk = k × distance × log(distance)
    where k = HYPERSPACE_LOSS_BASE (0.02 or 2%)

    This makes longer journeys disproportionately riskier, incentivizing
    waypoint stops and strategic route planning.

    Args:
        distance: Journey distance in turns

    Returns:
        Cumulative probability of fleet loss (0.0 to 1.0)

    Examples:
        - 1 turn: 0% (log(1) = 0, special case)
        - 4 turns: ~11%
        - 8 turns: ~33%
        - 12 turns: ~50%
    """
    if distance <= 0:
        return 0.0

    # Special case: distance 1 has minimal risk (use base rate)
    if distance == 1:
        return HYPERSPACE_LOSS_BASE

    # n log n formula: k × distance × log_2(distance)
    cumulative_risk = HYPERSPACE_LOSS_BASE * distance * math.log2(distance)

    # Cap at 99% (never certain destruction)
    return min(cumulative_risk, 0.99)


def calculate_hyperspace_per_turn_risk(distance: int) -> float:
    """Calculate per-turn hyperspace loss probability for a journey.

    Converts cumulative n log n risk into per-turn probability assuming
    independent rolls each turn in transit.

    If cumulative risk is R and distance is d:
    R = 1 - (1-p)^d, so p = 1 - (1-R)^(1/d)

    Args:
        distance: Journey distance in turns

    Returns:
        Per-turn probability of fleet loss (0.0 to 1.0)
    """
    if distance <= 0:
        return 0.0

    cumulative_risk = calculate_hyperspace_cumulative_risk(distance)

    # Convert cumulative to per-turn: p = 1 - (1-R)^(1/d)
    per_turn_risk = 1.0 - (1.0 - cumulative_risk) ** (1.0 / distance)

    return per_turn_risk
