"""Seedable RNG wrapper for deterministic gameplay."""

import random


class GameRNG:
    """Wrapper around Python's random.Random for deterministic game behavior.

    All randomness in the game should go through this class to ensure
    deterministic behavior when using the same seed.
    """

    def __init__(self, seed: int):
        """Initialize RNG with given seed.

        Args:
            seed: Integer seed for deterministic randomness
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        """Return random integer in range [a, b], inclusive.

        Args:
            a: Lower bound (inclusive)
            b: Upper bound (inclusive)

        Returns:
            Random integer between a and b
        """
        return self.rng.randint(a, b)

    def choice(self, seq):
        """Choose random element from non-empty sequence.

        Args:
            seq: Sequence to choose from

        Returns:
            Random element from sequence
        """
        return self.rng.choice(seq)

    def shuffle(self, seq):
        """Shuffle sequence in place.

        Args:
            seq: Sequence to shuffle
        """
        self.rng.shuffle(seq)

    def random(self) -> float:
        """Return random float in [0.0, 1.0).

        Returns:
            Random float between 0.0 and 1.0
        """
        return self.rng.random()

    def get_state(self):
        """Get the current state of the RNG for serialization.

        Returns:
            RNG state tuple that can be used with set_state
        """
        return self.rng.getstate()

    def set_state(self, state):
        """Set the state of the RNG for deserialization.

        Args:
            state: RNG state tuple from get_state
        """
        self.rng.setstate(state)
