"""Distance calculations for the game map."""


def chebyshev_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    """Calculate Chebyshev distance between two points.

    Chebyshev distance is the maximum absolute difference of coordinates.
    Also known as chessboard or L∞ distance. In game terms, this represents
    the number of turns needed to travel between stars, where diagonal
    movement costs the same as orthogonal movement.

    Args:
        x1: X coordinate of first point
        y1: Y coordinate of first point
        x2: X coordinate of second point
        y2: Y coordinate of second point

    Returns:
        Chebyshev distance between the two points

    Examples:
        >>> chebyshev_distance(0, 0, 3, 3)
        3  # Diagonal is same cost as orthogonal
        >>> chebyshev_distance(0, 0, 5, 0)
        5  # Horizontal movement unchanged
    """
    return max(abs(x2 - x1), abs(y2 - y1))
