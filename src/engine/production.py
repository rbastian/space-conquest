"""Phase 3b (Rebellions) and Phase 5 (Production).

This module handles rebellions and production as two separate functions:
1. Phase 3b - process_rebellions: Check and resolve rebellions (50% chance if stationed < base_ru)
2. Phase 5 - process_production: Ship production at controlled stars (only for non-rebelling stars)

Key: Rebellions are checked in Phase 3b (after combat, before victory check) so players
see rebellion results BEFORE submitting orders. Production happens in Phase 5 (after orders).
"""

from ..models.game import Game
from ..models.star import Star
from .combat import RebellionEvent, resolve_combat


def _is_home_star(game: Game, star: Star) -> bool:
    """Check if star is a home star for either player.

    Home stars are immune to rebellion and produce a fixed 4 RU per turn
    regardless of their base_ru value.

    Args:
        game: Current game state
        star: Star to check

    Returns:
        True if star is p1 or p2 home star, False otherwise
    """
    home_stars = {p.home_star for p in game.players.values()}
    return star.id in home_stars


def process_rebellions(game: Game) -> tuple[Game, list[RebellionEvent]]:
    """Execute Phase 3b: Rebellions.

    For each player-controlled star:
       - If stationed_ships[owner] < base_ru: 50% rebellion chance (d6 roll of 4-6)
       - On rebellion:
         * Spawn base_ru rebel ships
         * Resolve combat: stationed ships vs rebels
         * If rebels win (or tie):
           - star.owner = None (reverts to NPC)
           - star.npc_ships = surviving_rebel_count
         * If player wins:
           - star.stationed_ships[owner] = surviving_player_count

    Args:
        game: Current game state

    Returns:
        Tuple of (updated game state, list of rebellion events)
    """
    rebellion_events = []

    # Process rebellions for each controlled star
    for star in game.stars:
        event = _check_and_process_rebellion(game, star)
        if event:
            rebellion_events.append(event)

    return game, rebellion_events


def process_production(game: Game, rebelled_star_ids: set[str] | None = None) -> Game:
    """Execute Phase 5: Production.

    For controlled stars that did not rebel this turn:
       - Home stars: +4 ships (always, immune to rebellion)
       - Other stars: +base_ru ships

    Args:
        game: Current game state
        rebelled_star_ids: Set of star IDs that rebelled this turn (no production for them).
                          If None, no stars are excluded from production.

    Returns:
        Updated game state
    """
    if rebelled_star_ids is None:
        rebelled_star_ids = set()

    # Process production for non-rebelling stars
    for star in game.stars:
        if star.id not in rebelled_star_ids:
            _process_star_production(game, star)

    return game


def process_rebellions_and_production(game: Game) -> tuple[Game, list[RebellionEvent]]:
    """Execute Rebellions & Production together (legacy method for backward compatibility).

    This method is kept for tests that expect the old behavior where rebellions
    and production happen together in Phase 5.

    For the main game loop, use process_rebellions() in Phase 3 and
    process_production() in Phase 5 separately.

    Executes in two sequential sub-phases:

    Sub-Phase 5a - Rebellions:
    For each player-controlled star:
       - If stationed_ships[owner] < base_ru: 50% rebellion chance (d6 roll of 4-6)
       - On rebellion:
         * Spawn base_ru rebel ships
         * Resolve combat: stationed ships vs rebels
         * If rebels win (or tie):
           - star.owner = None (reverts to NPC)
           - star.npc_ships = surviving_rebel_count
         * If player wins:
           - star.stationed_ships[owner] = surviving_player_count
       - Track rebelling stars (no production for them)

    Sub-Phase 5b - Production:
    For non-rebelling controlled stars:
       - Home stars: +4 ships (always, immune to rebellion)
       - Other stars: +base_ru ships

    Args:
        game: Current game state

    Returns:
        Tuple of (updated game state, list of rebellion events)
    """
    # Track which stars rebelled (no production for them)
    rebelled_stars = set()

    # Process rebellions
    game, rebellion_events = process_rebellions(game)

    # Track which stars rebelled (no production for them)
    for event in rebellion_events:
        rebelled_stars.add(event.star)

    # Process production for non-rebelling stars
    game = process_production(game, rebelled_stars)

    return game, rebellion_events


def _check_and_process_rebellion(game: Game, star: Star) -> RebellionEvent | None:
    """Check for and process rebellion at a star.

    Home stars are immune to rebellion regardless of garrison strength.

    Args:
        game: Current game state
        star: Star to check for rebellion

    Returns:
        RebellionEvent if rebellion occurred, None otherwise
    """
    # Only player-controlled stars can have rebellions
    if star.owner is None:
        return None

    # Home stars are immune to rebellion
    if _is_home_star(game, star):
        return None  # Home stars never rebel - skip to production

    # Get garrison strength
    garrison = star.stationed_ships.get(star.owner, 0)

    # Check if under-garrisoned
    if garrison >= star.base_ru:
        return None  # Well-garrisoned, no rebellion possible

    # Roll for rebellion (50% = d6 roll of 4-6)
    rebellion_roll = game.rng.randint(1, 6)
    if rebellion_roll < 4:
        return None  # No rebellion

    # Rebellion occurs!
    rebels = star.base_ru
    owner = star.owner
    garrison_before = garrison

    # Resolve combat: garrison vs rebels
    result = resolve_combat(garrison, rebels)

    # Determine outcome and update star state
    if result.winner == "defender":
        # Rebels win - star reverts to NPC
        outcome = "lost"
        star.owner = None
        star.npc_ships = result.defender_survivors
        star.stationed_ships[owner] = 0
        garrison_after = 0
        rebel_survivors = result.defender_survivors
        # Track garrison losses
        game.ships_lost_rebellion[owner] += result.attacker_losses
    elif result.winner == "attacker":
        # Garrison wins
        outcome = "defended"
        star.stationed_ships[owner] = result.attacker_survivors
        garrison_after = result.attacker_survivors
        rebel_survivors = 0
        # Track garrison losses
        game.ships_lost_rebellion[owner] += result.attacker_losses
    else:
        # Tie - mutual destruction, star becomes unowned
        outcome = "lost"
        star.owner = None
        star.npc_ships = 0
        star.stationed_ships[owner] = 0
        garrison_after = 0
        rebel_survivors = 0
        # Track garrison losses (all ships lost in tie)
        game.ships_lost_rebellion[owner] += result.attacker_losses

    # Create rebellion event
    return RebellionEvent(
        star=star.id,
        star_name=star.name,
        owner=owner,
        ru=star.base_ru,
        garrison_before=garrison_before,
        rebel_ships=rebels,
        outcome=outcome,
        garrison_after=garrison_after,
        rebel_survivors=rebel_survivors,
    )


def _process_star_production(game: Game, star: Star) -> None:
    """Process ship production at a controlled star.

    Args:
        game: Current game state
        star: Star to produce ships at
    """
    # Only controlled stars produce
    if star.owner is None:
        return

    owner = star.owner

    # Determine production amount
    # Home stars produce 4, other stars produce base_ru
    if _is_home_star(game, star):
        production = 4
    else:
        production = star.base_ru

    # Add production to stationed ships
    if owner not in star.stationed_ships:
        star.stationed_ships[owner] = 0
    star.stationed_ships[owner] += production

    # Track ships produced
    game.ships_produced[owner] += production
