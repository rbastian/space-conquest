"""Game stage determination for strategic decision-making.

This module provides heuristics to determine the current game stage
(early, mid, late) based on opponent contact and home star knowledge.
"""

from src.models.game import Game


def calculate_game_stage(game: Game, player_id: str) -> str:
    """Determine current game stage based on opponent contact and home star knowledge.

    Game stages:
    - EARLY: No enemy contact (no enemy fleets exist)
    - MID: Enemy contact made, but home stars not located
    - LATE: Home stars known (mine threatened or opponent's discovered)

    Args:
        game: Current game state
        player_id: The player ID to calculate stage for ("p1" or "p2")

    Returns:
        One of: "early", "mid", "late"
    """
    opponent_id = "p1" if player_id == "p2" else "p2"

    # Find my home star
    my_home = None
    for star in game.stars:
        if star.owner == player_id and star.base_ru == 4:
            my_home = star
            break

    # Check if any VISIBLE enemy fleets exist (respect fog of war)
    # A fleet is visible if its destination or origin star has been visited
    player = game.players.get(player_id)
    if not player:
        return "early"

    enemy_fleets_visible = any(
        fleet.owner == opponent_id
        and (fleet.dest in player.visited_stars or fleet.origin in player.visited_stars)
        for fleet in game.fleets
    )

    if not enemy_fleets_visible:
        # No enemy contact yet
        return "early"

    # Check if opponent home is known (discovered via fog of war)
    opponent = game.players.get(opponent_id)
    opponent_home_known = False
    if player and opponent:
        opponent_home_known = opponent.home_star in player.visited_stars

    # Check if my home is threatened (enemy fleet within 4 turns)
    # Only consider VISIBLE enemy fleets (respect fog of war)
    my_home_threatened = False
    if my_home:
        # Create star lookup dict
        star_lookup = {star.id: star for star in game.stars}

        for fleet in game.fleets:
            if fleet.owner == opponent_id:
                # Only consider visible fleets
                if (
                    fleet.dest not in player.visited_stars
                    and fleet.origin not in player.visited_stars
                ):
                    continue

                # Look up destination star
                dest_star = star_lookup.get(fleet.dest)
                if dest_star:
                    dest_distance = max(abs(dest_star.x - my_home.x), abs(dest_star.y - my_home.y))
                    if dest_distance <= 4:
                        my_home_threatened = True
                        break

    # Determine stage
    if opponent_home_known or my_home_threatened:
        return "late"
    else:
        return "mid"
