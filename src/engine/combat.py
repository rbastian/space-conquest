"""Phase 2: Combat resolution.

This module handles:
1. Merging arriving fleets with stationed ships
2. NPC combat (if star is NPC-owned and has attackers)
3. Player vs player combat (if multiple players at same star)
4. Star ownership updates
"""

import math
from dataclasses import dataclass
from typing import List, Optional

from ..models.game import Game
from ..models.star import Star


@dataclass
class CombatResult:
    """Result of a combat resolution.

    Attributes:
        winner: "attacker", "defender", or None (for tie)
        attacker_losses: Number of ships lost by attacker
        defender_losses: Number of ships lost by defender
        attacker_survivors: Number of ships remaining for attacker
        defender_survivors: Number of ships remaining for defender
    """

    winner: Optional[str]
    attacker_losses: int
    defender_losses: int
    attacker_survivors: int
    defender_survivors: int


@dataclass
class CombatEvent:
    """Record of a combat that occurred.

    Attributes:
        star_id: ID of star where combat occurred
        star_name: Name of star where combat occurred
        combat_type: "npc" or "pvp"
        attacker: "p1", "p2", or "combined" (for NPC combat)
        defender: "p1", "p2", or "npc"
        attacker_ships: Initial attacker ship count
        defender_ships: Initial defender ship count
        winner: "attacker", "defender", or None (tie)
        attacker_survivors: Surviving attacker ships
        defender_survivors: Surviving defender ships
        attacker_losses: Attacker casualties
        defender_losses: Defender casualties
        control_before: Star owner before combat ("p1", "p2", or None for NPC/uncontrolled)
        control_after: Star owner after combat ("p1", "p2", or None)
        simultaneous: Flag for simultaneous arrival at uncontrolled star (both players arrive same turn)
    """

    star_id: str
    star_name: str
    combat_type: str
    attacker: str
    defender: str
    attacker_ships: int
    defender_ships: int
    winner: Optional[str]
    attacker_survivors: int
    defender_survivors: int
    attacker_losses: int
    defender_losses: int
    control_before: Optional[str]
    control_after: Optional[str]
    simultaneous: bool = False


@dataclass
class RebellionEvent:
    """Record of a rebellion that occurred.

    Attributes:
        star: Star ID where rebellion occurred
        star_name: Human-readable star name
        owner: Player who owned the star ("p1" or "p2")
        ru: Star's RU value
        garrison_before: Player's ships before rebellion
        rebel_ships: Rebel forces spawned (= RU)
        outcome: "lost" or "defended"
        garrison_after: Player's surviving ships
        rebel_survivors: Remaining rebel forces
    """

    star: str
    star_name: str
    owner: str
    ru: int
    garrison_before: int
    rebel_ships: int
    outcome: str
    garrison_after: int
    rebel_survivors: int


def resolve_combat(attacker_ships: int, defender_ships: int) -> CombatResult:
    """Resolve combat between two forces.

    Combat rules:
    - attacker_ships > defender_ships: attacker wins, loses ceil(defender/2)
    - attacker_ships < defender_ships: defender wins, loses ceil(attacker/2)
    - attacker_ships == defender_ships: tie, both eliminated

    Args:
        attacker_ships: Number of attacking ships
        defender_ships: Number of defending ships

    Returns:
        CombatResult with winner and casualties
    """
    if attacker_ships > defender_ships:
        # Attacker wins
        attacker_losses = math.ceil(defender_ships / 2)
        defender_losses = defender_ships
        return CombatResult(
            winner="attacker",
            attacker_losses=attacker_losses,
            defender_losses=defender_losses,
            attacker_survivors=attacker_ships - attacker_losses,
            defender_survivors=0,
        )
    elif defender_ships > attacker_ships:
        # Defender wins
        defender_losses = math.ceil(attacker_ships / 2)
        attacker_losses = attacker_ships
        return CombatResult(
            winner="defender",
            attacker_losses=attacker_losses,
            defender_losses=defender_losses,
            attacker_survivors=0,
            defender_survivors=defender_ships - defender_losses,
        )
    else:
        # Tie - mutual destruction
        return CombatResult(
            winner=None,
            attacker_losses=attacker_ships,
            defender_losses=defender_ships,
            attacker_survivors=0,
            defender_survivors=0,
        )


def process_combat(game: Game) -> tuple[Game, List[CombatEvent]]:
    """Execute Phase 2: Combat Resolution.

    For each star with potential combat:
    1. If star is NPC-owned and has attackers:
       - Combine all attacking forces (both players if present)
       - Resolve attackers vs NPC defenders
       - NPC loses: star becomes unowned, attackers redistribute
       - Attackers lose: NPC retains control
    2. If multiple players have ships at star (after NPC combat):
       - Resolve player-vs-player combat
       - Higher ship count wins
       - Loser eliminated completely
       - Winner loses ceil(loser/2) ships
       - Tie: mutual destruction (both eliminated)
       - Winner gains star control

    Args:
        game: Current game state

    Returns:
        Tuple of (updated game state with combat resolved, list of combat events)
    """
    combat_events = []
    for star in game.stars:
        events = _resolve_star_combat(game, star)
        combat_events.extend(events)

    return game, combat_events


def _resolve_star_combat(game: Game, star: Star) -> List[CombatEvent]:
    """Resolve all combat at a single star.

    Combat sequence depends on the situation:
    1. Both players at NPC star: PvP first, then winner vs NPC
    2. Single player at NPC star: Player vs NPC
    3. Both players at non-NPC star: PvP combat

    Args:
        game: Current game state
        star: Star where combat is being resolved

    Returns:
        List of combat events that occurred at this star
    """
    events = []

    # Check for simultaneous arrival at NPC star (special case)
    p1_ships = star.stationed_ships.get("p1", 0)
    p2_ships = star.stationed_ships.get("p2", 0)
    is_npc_star = star.owner is None and star.npc_ships > 0
    both_players_present = p1_ships > 0 and p2_ships > 0

    if is_npc_star and both_players_present:
        # Special case: Both players arrive at NPC star
        # Sequence: PvP first, then winner vs NPC

        # 1. PvP combat between the two players
        pvp_event = _resolve_player_combat(game, star)
        if pvp_event:
            events.append(pvp_event)

        # 2. Winner vs NPC combat (only if there's a winner with ships)
        # If PvP was a tie, star becomes uncontrolled and no NPC combat occurs
        if pvp_event and pvp_event.winner is not None:
            # One player won and has survivors - fight the NPC
            npc_event = _resolve_npc_combat(game, star)
            if npc_event:
                events.append(npc_event)
        elif pvp_event and pvp_event.winner is None:
            # PvP tie - star becomes uncontrolled, NPC ships remain
            star.owner = None
            star.stationed_ships["p1"] = 0
            star.stationed_ships["p2"] = 0
            # npc_ships stays as-is (no NPC combat occurred)
    else:
        # Standard sequence: NPC combat first (if applicable), then PvP
        if is_npc_star:
            event = _resolve_npc_combat(game, star)
            if event:
                events.append(event)

        # Then, handle player vs player combat if applicable
        event = _resolve_player_combat(game, star)
        if event:
            events.append(event)

    return events


def _resolve_npc_combat(game: Game, star: Star) -> Optional[CombatEvent]:
    """Resolve combat between NPC defenders and player attackers.

    Args:
        game: Current game state
        star: NPC-owned star with potential attackers

    Returns:
        CombatEvent if combat occurred, None otherwise
    """
    # Count total attacking forces
    p1_ships = star.stationed_ships.get("p1", 0)
    p2_ships = star.stationed_ships.get("p2", 0)
    total_attackers = p1_ships + p2_ships

    # No attackers - nothing to do
    if total_attackers == 0:
        return None

    # Record initial state
    initial_attackers = total_attackers
    initial_defenders = star.npc_ships
    control_before = star.owner  # Should be None for NPC stars

    # Resolve combat: attackers vs NPC
    result = resolve_combat(total_attackers, star.npc_ships)

    # Determine attacker label
    if p1_ships > 0 and p2_ships > 0:
        attacker_label = "combined"
    elif p1_ships > 0:
        attacker_label = "p1"
    else:
        attacker_label = "p2"

    if result.winner == "attacker":
        # Attackers win - NPC eliminated
        star.npc_ships = 0

        # Distribute survivors proportionally
        if total_attackers > 0:
            p1_proportion = p1_ships / total_attackers
            p2_proportion = p2_ships / total_attackers

            # Assign survivors proportionally (rounding down, excess goes to p1)
            p1_survivors = int(result.attacker_survivors * p1_proportion)
            p2_survivors = int(result.attacker_survivors * p2_proportion)

            # Give any remainder to p1
            remainder = result.attacker_survivors - (p1_survivors + p2_survivors)
            p1_survivors += remainder

            star.stationed_ships["p1"] = p1_survivors
            star.stationed_ships["p2"] = p2_survivors

        # Determine ownership after NPC combat
        # If only one player has survivors, they gain control
        # If both players have survivors, star becomes unowned (PvP will decide)
        p1_final = star.stationed_ships.get("p1", 0)
        p2_final = star.stationed_ships.get("p2", 0)
        if p1_final > 0 and p2_final == 0:
            star.owner = "p1"
        elif p2_final > 0 and p1_final == 0:
            star.owner = "p2"
        else:
            star.owner = None  # Star becomes unowned (no survivors or both have survivors)
    else:
        # Attackers lose or tie - star remains/becomes NPC-controlled
        star.npc_ships = result.defender_survivors
        star.stationed_ships["p1"] = 0
        star.stationed_ships["p2"] = 0
        star.owner = None  # Star is NPC-controlled

    control_after = star.owner

    # Create combat event
    return CombatEvent(
        star_id=star.id,
        star_name=star.name,
        combat_type="npc",
        attacker=attacker_label,
        defender="npc",
        attacker_ships=initial_attackers,
        defender_ships=initial_defenders,
        winner=result.winner,
        attacker_survivors=result.attacker_survivors,
        defender_survivors=result.defender_survivors,
        attacker_losses=result.attacker_losses,
        defender_losses=result.defender_losses,
        control_before=control_before,
        control_after=control_after,
        simultaneous=False,
    )


def _resolve_player_combat(game: Game, star: Star) -> Optional[CombatEvent]:
    """Resolve combat between two players at a star.

    Only called after NPC combat (if any) has been resolved.

    Args:
        game: Current game state
        star: Star with potential player vs player combat

    Returns:
        CombatEvent if combat occurred, None otherwise
    """
    p1_ships = star.stationed_ships.get("p1", 0)
    p2_ships = star.stationed_ships.get("p2", 0)

    # No combat if only one player or neither present
    if p1_ships == 0 or p2_ships == 0:
        # Update ownership based on who has ships
        if p1_ships > 0:
            star.owner = "p1"
        elif p2_ships > 0:
            star.owner = "p2"
        # If neither, star remains as-is (could be unowned or keep old owner)
        return None

    # Record initial state
    initial_p1 = p1_ships
    initial_p2 = p2_ships
    control_before = star.owner

    # Check for simultaneous arrival (both arrive at uncontrolled star)
    simultaneous = control_before is None and p1_ships > 0 and p2_ships > 0

    # Determine attacker and defender roles based on who controlled the star before
    # The attacker is whoever DIDN'T control the star (i.e., the arriving fleet)
    # The defender is whoever DID control the star (i.e., the garrison)
    # Special case: simultaneous arrival -> alphabetically first player is attacker
    if simultaneous:
        # Both arrived at uncontrolled star - p1 is attacker by convention
        attacker_id = "p1"
        defender_id = "p2"
        attacker_ships = initial_p1
        defender_ships = initial_p2
    elif control_before == "p1":
        # p1 controlled before, so p2 is attacker
        attacker_id = "p2"
        defender_id = "p1"
        attacker_ships = initial_p2
        defender_ships = initial_p1
    elif control_before == "p2":
        # p2 controlled before, so p1 is attacker
        attacker_id = "p1"
        defender_id = "p2"
        attacker_ships = initial_p1
        defender_ships = initial_p2
    else:
        # control_before is None but not simultaneous (shouldn't happen after NPC combat)
        # Default to p1 as attacker
        attacker_id = "p1"
        defender_id = "p2"
        attacker_ships = initial_p1
        defender_ships = initial_p2

    # Resolve combat with correct attacker/defender roles
    result = resolve_combat(attacker_ships, defender_ships)

    # Update star based on winner
    if result.winner == "attacker":
        # Attacker wins
        star.stationed_ships[attacker_id] = result.attacker_survivors
        star.stationed_ships[defender_id] = 0
        star.owner = attacker_id
    elif result.winner == "defender":
        # Defender wins
        star.stationed_ships[attacker_id] = 0
        star.stationed_ships[defender_id] = result.defender_survivors
        star.owner = defender_id
    else:
        # Tie - mutual destruction
        star.stationed_ships["p1"] = 0
        star.stationed_ships["p2"] = 0
        # Star ownership becomes unowned after mutual destruction
        star.owner = None

    control_after = star.owner

    # Create combat event with correct attacker/defender roles
    return CombatEvent(
        star_id=star.id,
        star_name=star.name,
        combat_type="pvp",
        attacker=attacker_id,
        defender=defender_id,
        attacker_ships=attacker_ships,
        defender_ships=defender_ships,
        winner=result.winner,
        attacker_survivors=result.attacker_survivors,
        defender_survivors=result.defender_survivors,
        attacker_losses=result.attacker_losses,
        defender_losses=result.defender_losses,
        control_before=control_before,
        control_after=control_after,
        simultaneous=simultaneous,
    )
