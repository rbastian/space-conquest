"""Tests for distance calculations."""

from src.utils import chebyshev_distance


class TestChebyshevDistance:
    """Test Chebyshev distance calculation."""

    def test_distance_same_point(self):
        """Test distance from a point to itself."""
        assert chebyshev_distance(5, 5, 5, 5) == 0

    def test_distance_horizontal(self):
        """Test distance for horizontal movement."""
        assert chebyshev_distance(0, 0, 5, 0) == 5
        assert chebyshev_distance(5, 0, 0, 0) == 5

    def test_distance_vertical(self):
        """Test distance for vertical movement."""
        assert chebyshev_distance(0, 0, 0, 5) == 5
        assert chebyshev_distance(0, 5, 0, 0) == 5

    def test_distance_diagonal(self):
        """Test distance for diagonal movement."""
        assert chebyshev_distance(0, 0, 3, 4) == 4
        assert chebyshev_distance(0, 0, 5, 5) == 5

    def test_distance_negative_coords(self):
        """Test distance with negative coordinates."""
        assert chebyshev_distance(-5, -5, 5, 5) == 10
        assert chebyshev_distance(-3, 0, 0, -4) == 4

    def test_distance_map_corners(self):
        """Test distance between map corners (12x10 grid)."""
        # Bottom-left (0, 0) to top-right (11, 9)
        assert chebyshev_distance(0, 0, 11, 9) == 11

        # Top-left (0, 9) to bottom-right (11, 0)
        assert chebyshev_distance(0, 9, 11, 0) == 11

    def test_distance_home_star_range(self):
        """Test distances within home star placement range."""
        # Home stars should be 0-2 parsecs from corners (Chebyshev)
        # Test corner (0, 0)
        assert chebyshev_distance(0, 0, 0, 0) == 0  # On corner
        assert chebyshev_distance(0, 0, 1, 1) == 1  # 1 parsec away
        assert chebyshev_distance(0, 0, 2, 2) == 2  # 2 parsecs away
        assert chebyshev_distance(0, 0, 2, 0) == 2  # Edge of range

    def test_distance_symmetry(self):
        """Test that distance is symmetric."""
        assert chebyshev_distance(1, 2, 5, 8) == chebyshev_distance(5, 8, 1, 2)
        assert chebyshev_distance(0, 0, 11, 9) == chebyshev_distance(11, 9, 0, 0)
