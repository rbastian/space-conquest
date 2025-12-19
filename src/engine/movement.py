"""Phase 1: Fleet movement and hyperspace loss.

This module handles:
1. Hyperspace loss (2% chance per fleet per turn)
2. Fleet movement (decrement dist_remaining)
3. Fleet arrivals (dist_remaining == 0)
4. Fog-of-war reveal (star RU reveal to arriving player)

Note: Ships are deducted from origin stars in Phase 4 when fleets are created,
NOT in Phase 1. This ensures ships don't participate in combat at their origin
after being ordered to depart.
"""

from dataclasses import dataclass

from ..models.fleet import Fleet
from ..models.game import Game


@dataclass
class HyperspaceLoss:
    """Record of a fleet lost in hyperspace.

    Attributes:
        fleet_id: ID of lost fleet
        owner: Owner of lost fleet
        ships: Number of ships in lost fleet
        origin: Origin star ID
        dest: Destination star ID
    """

    fleet_id: str
    owner: str
    ships: int
    origin: str
    dest: str


def process_fleet_movement(game: Game) -> tuple[Game, list[HyperspaceLoss]]:
    """Execute Phase 1: Fleet Movement.

    1. Apply 2% hyperspace loss to each fleet in transit:
       - Roll d50 for each fleet (once per fleet, not per ship)
       - On roll of 1: entire fleet is destroyed
       - On roll of 2-50: fleet continues with all ships intact
    2. Decrement dist_remaining for surviving fleets
    3. Process arrivals (dist_remaining == 0):
       - Add arriving fleet ships to star.stationed_ships[owner]
       - Reveal star RU to arriving player (update known_ru)

    Note: Ships are already deducted from origin stars in Phase 4 when fleets
    are created, so no departure processing is needed here.

    Args:
        game: Current game state

    Returns:
        Tuple of (updated game state with fleets moved and arrivals processed, list of hyperspace losses)
    """
    surviving_fleets = []
    arriving_fleets = []
    hyperspace_losses = []

    # Process each fleet
    for fleet in game.fleets:
        # Apply hyperspace loss (2% = d50 roll of 1)
        roll = game.rng.randint(1, 50)
        if roll == 1:
            # Fleet is destroyed - record the loss
            hyperspace_losses.append(
                HyperspaceLoss(
                    fleet_id=fleet.id,
                    owner=fleet.owner,
                    ships=fleet.ships,
                    origin=fleet.origin,
                    dest=fleet.dest,
                )
            )
            continue

        # Decrement distance
        fleet.dist_remaining -= 1

        # Check if fleet is arriving
        if fleet.dist_remaining == 0:
            arriving_fleets.append(fleet)
        else:
            surviving_fleets.append(fleet)

    # Process arrivals
    for fleet in arriving_fleets:
        _process_fleet_arrival(game, fleet)

    # Update game state
    game.fleets = surviving_fleets

    return game, hyperspace_losses


def _process_fleet_arrival(game: Game, fleet: Fleet) -> None:
    """Process a single fleet arrival.

    1. Find destination star
    2. Add ships to star.stationed_ships[owner]
    3. Mark star as visited by arriving player

    Args:
        game: Current game state
        fleet: Fleet that is arriving
    """
    # Find destination star
    dest_star = None
    for star in game.stars:
        if star.id == fleet.dest:
            dest_star = star
            break

    if dest_star is None:
        raise ValueError(f"Fleet {fleet.id} destination star {fleet.dest} not found")

    # Add ships to stationed_ships
    if fleet.owner not in dest_star.stationed_ships:
        dest_star.stationed_ships[fleet.owner] = 0
    dest_star.stationed_ships[fleet.owner] += fleet.ships

    # Mark star as visited by arriving player
    player = game.players[fleet.owner]
    player.visited_stars.add(fleet.dest)
