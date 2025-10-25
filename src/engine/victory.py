"""Phase 3: Victory condition checking.

This module handles:
1. Checking if Player 1 captured Player 2's home star
2. Checking if Player 2 captured Player 1's home star
3. Determining winner (p1, p2, draw, or None)
"""

from ..models.game import Game


def check_victory(game: Game) -> bool:
    """Execute Phase 3: Victory Assessment.

    Check victory conditions after Phase 2 combat:
    1. Check if Player 1 captured Player 2's home star this turn
    2. Check if Player 2 captured Player 1's home star this turn
    3. Victory logic:
       - Both captured opponent homes → game.winner = "draw"
       - Only P1 captured P2 home → game.winner = "p1"
       - Only P2 captured P1 home → game.winner = "p2"
       - Neither captured → game.winner = None (continue)

    Args:
        game: Current game state

    Returns:
        True if game has a winner (including draw), False otherwise
    """
    # Get home star IDs
    p1_home = game.players["p1"].home_star
    p2_home = game.players["p2"].home_star

    # Find the home stars
    p1_home_star = None
    p2_home_star = None

    for star in game.stars:
        if star.id == p1_home:
            p1_home_star = star
        if star.id == p2_home:
            p2_home_star = star

    if p1_home_star is None or p2_home_star is None:
        raise ValueError("Home stars not found in game state")

    # Check who captured whose home
    p1_captured_p2_home = p2_home_star.owner == "p1"  # P1 captured P2's home
    p2_captured_p1_home = p1_home_star.owner == "p2"  # P2 captured P1's home

    # Determine winner
    if p1_captured_p2_home and p2_captured_p1_home:
        # Both captured opponent's home - draw
        game.winner = "draw"
        return True
    elif p2_captured_p1_home:
        # P2 captured P1's home - P2 wins
        game.winner = "p2"
        return True
    elif p1_captured_p2_home:
        # P1 captured P2's home - P1 wins
        game.winner = "p1"
        return True
    else:
        # No victory yet
        game.winner = None
        return False
