"""Game configuration constants from specification."""

# Grid dimensions
GRID_X = 12
GRID_Y = 10

# Star configuration
NUM_STARS = 18
HOME_RU = 4
NPC_RU_RANGE = (1, 3)  # Base RU for NPC stars

# Probabilities
HYPERSPACE_LOSS_PROB = 0.02  # 2% per turn
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
