"""Phase 1: Fleet movement and hyperspace loss.

This module handles:
1. Hyperspace loss (n log n scaling - longer journeys are riskier)
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
from ..utils.constants import calculate_hyperspace_per_turn_risk
from ..utils.distance import chebyshev_distance


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


@dataclass
class FleetArrival:
    """Record of a fleet arrival.

    Attributes:
        fleet_id: ID of arrived fleet
        owner: Owner of fleet
        ships: Number of ships that arrived
        origin: Origin star ID
        dest: Destination star ID
        distance: Total distance traveled
    """

    fleet_id: str
    owner: str
    ships: int
    origin: str
    dest: str
    distance: int


def process_fleet_movement(game: Game) -> tuple[Game, list[HyperspaceLoss], list[FleetArrival]]:
    """Execute Phase 1: Fleet Movement.

    1. Apply n log n hyperspace loss to each fleet in transit:
       - Calculate total journey distance from origin to destination
       - Determine per-turn risk using n log n scaling: risk = k × d × log(d)
       - Roll random float [0,1) against per-turn risk
       - If roll < risk: entire fleet is destroyed
       - Otherwise: fleet continues with all ships intact
    2. Decrement dist_remaining for surviving fleets
    3. Process arrivals (dist_remaining == 0):
       - Add arriving fleet ships to star.stationed_ships[owner]
       - Reveal star RU to arriving player (update known_ru)

    Note: Ships are already deducted from origin stars in Phase 4 when fleets
    are created, so no departure processing is needed here.

    Args:
        game: Current game state

    Returns:
        Tuple of (updated game state with fleets moved and arrivals processed,
                 list of hyperspace losses, list of fleet arrivals)
    """
    surviving_fleets = []
    arriving_fleets = []
    hyperspace_losses = []
    fleet_arrivals = []

    # Process each fleet
    for fleet in game.fleets:
        # Calculate total journey distance for n log n risk calculation
        origin_star = next((s for s in game.stars if s.id == fleet.origin), None)
        dest_star = next((s for s in game.stars if s.id == fleet.dest), None)

        if origin_star and dest_star:
            total_distance = chebyshev_distance(
                origin_star.x, origin_star.y, dest_star.x, dest_star.y
            )
        else:
            # Fallback: estimate from dist_remaining (shouldn't happen)
            total_distance = fleet.dist_remaining

        # Get per-turn risk using n log n scaling
        per_turn_risk = calculate_hyperspace_per_turn_risk(total_distance)

        # Roll against per-turn probability
        roll = game.rng.random()  # Random float [0, 1)
        if roll < per_turn_risk:
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
            # Track hyperspace losses
            game.ships_lost_hyperspace[fleet.owner] += fleet.ships
            continue

        # Decrement distance
        fleet.dist_remaining -= 1

        # Check if fleet is arriving
        if fleet.dist_remaining == 0:
            arriving_fleets.append(fleet)
        else:
            surviving_fleets.append(fleet)

    # Process arrivals and calculate distances
    for fleet in arriving_fleets:
        # Calculate distance using star positions
        origin_star = next((s for s in game.stars if s.id == fleet.origin), None)
        dest_star = next((s for s in game.stars if s.id == fleet.dest), None)

        if origin_star and dest_star:
            distance = chebyshev_distance(origin_star.x, origin_star.y, dest_star.x, dest_star.y)
        else:
            distance = 0  # Fallback if stars not found

        # Record arrival
        fleet_arrivals.append(
            FleetArrival(
                fleet_id=fleet.id,
                owner=fleet.owner,
                ships=fleet.ships,
                origin=fleet.origin,
                dest=fleet.dest,
                distance=distance,
            )
        )

        # Process the arrival (add ships to star)
        _process_fleet_arrival(game, fleet)

    # Update game state
    game.fleets = surviving_fleets

    return game, hyperspace_losses, fleet_arrivals


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
