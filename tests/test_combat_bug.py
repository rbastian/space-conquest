"""Test case to reproduce the bug where p1 fleet doesn't participate in NPC combat."""

import random

from src.engine.combat import process_combat
from src.engine.movement import process_fleet_movement
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_simultaneous_arrival_at_npc_star_both_fleets_participate():
    """
    Test spec-compliant behavior: Two players send fleets to same NPC star.
    PvP combat occurs first, then winner vs NPC.

    Setup:
    - Star J: NPC, 2 defenders (weakened from previous battle)
    - P1 fleet: 3 ships arriving at J
    - P2 fleet: 4 ships arriving at J

    Expected Sequence (NEW SPEC):
    - Phase 1 (PvP): 3 vs 4 → P2 wins with 2 survivors (loses ceil(3/2) = 2)
    - Phase 2 (NPC): 2 vs 2 → Tie, mutual destruction
    - Result: J becomes NPC-controlled with 0 ships

    Old Behavior (BUG):
    - Combined attack: 7 ships vs 2 NPC
    - Attackers win, lose ceil(2/2) = 1 ship → 6 survivors
    - P1 gets 3, P2 gets 3
    - Then PvP: 3 vs 3 = tie, mutual destruction
    - Result: J unowned, 0 ships
    """
    # Create game with fixed seed
    game = Game(
        turn=11,
        seed=42,
        rng=random.Random(42),
        stars=[],
        fleets=[],
        players={},
        fleet_counter={"p1": 15, "p2": 10},
    )

    # Create star J (NPC, 2 defenders - weakened)
    star_j = Star(
        id="J",
        name="Jabbah",
        x=6,
        y=6,
        base_ru=3,
        owner=None,  # NPC
        npc_ships=2,  # Weakened from previous battle
        stationed_ships={},
    )
    game.stars.append(star_j)

    # Create players
    game.players["p1"] = Player(
        id="p1",
        home_star="C",
        visited_stars=set(),
    )
    game.players["p2"] = Player(
        id="p2",
        home_star="P",
        visited_stars=set(),
    )

    # Create fleets arriving at J
    fleet_p1 = Fleet(
        id="p1-013",
        owner="p1",
        ships=3,
        origin="O",
        dest="J",
        dist_remaining=1,  # Will arrive this turn
        rationale="attack",
    )

    fleet_p2 = Fleet(
        id="p2-005",
        owner="p2",
        ships=4,
        origin="K",
        dest="J",
        dist_remaining=1,  # Will arrive this turn
        rationale="attack",
    )

    game.fleets = [fleet_p1, fleet_p2]

    # Phase 1: Fleet Movement (both fleets arrive)
    game, hyperspace_losses, fleet_arrivals = process_fleet_movement(game)

    # Verify both fleets arrived
    assert len(game.fleets) == 0, "Both fleets should have arrived"
    assert len(hyperspace_losses) == 0, "No hyperspace losses expected"

    # Verify both players have ships at J
    assert star_j.stationed_ships.get("p1", 0) == 3, "P1 should have 3 ships at J"
    assert star_j.stationed_ships.get("p2", 0) == 4, "P2 should have 4 ships at J"

    # Phase 2: Combat Resolution
    game, combat_events = process_combat(game)

    # Verify combat events
    print("\n=== Combat Events ===")
    for i, event in enumerate(combat_events):
        print(f"Event {i + 1}: {event.combat_type} at {event.star_name}")
        print(f"  Attacker: {event.attacker} ({event.attacker_ships} ships)")
        print(f"  Defender: {event.defender} ({event.defender_ships} ships)")
        print(f"  Winner: {event.winner}")
        print(
            f"  Survivors: Attacker={event.attacker_survivors}, Defender={event.defender_survivors}"
        )
        print(f"  Control: {event.control_before} → {event.control_after}")

    # Should have 2 combat events: PvP combat first, then NPC combat
    assert len(combat_events) == 2, f"Expected 2 combat events, got {len(combat_events)}"

    # Event 1: PvP combat (3 vs 4 → P2 wins)
    pvp_combat = combat_events[0]
    assert pvp_combat.combat_type == "pvp"
    assert pvp_combat.attacker in ["p1", "p2"]
    assert pvp_combat.defender in ["p1", "p2"]
    # P1 has 3 ships, P2 has 4 ships → P2 should win
    # Winner loses ceil(3/2) = 2 ships → 4 - 2 = 2 survivors
    # The PvP resolution determines attacker/defender roles, but result is deterministic
    assert pvp_combat.winner in ["attacker", "defender"]  # Higher count wins
    # Verify the winner has 2 survivors (4 - ceil(3/2) = 2)
    winner_survivors = (
        pvp_combat.attacker_survivors
        if pvp_combat.winner == "attacker"
        else pvp_combat.defender_survivors
    )
    loser_survivors = (
        pvp_combat.defender_survivors
        if pvp_combat.winner == "attacker"
        else pvp_combat.attacker_survivors
    )
    assert winner_survivors == 2
    assert loser_survivors == 0

    # Event 2: NPC combat (2 vs 2 tie)
    npc_combat = combat_events[1]
    assert npc_combat.combat_type == "npc"
    assert npc_combat.attacker in ["p1", "p2"]  # Winner from PvP
    assert npc_combat.defender == "npc"
    assert npc_combat.attacker_ships == 2  # P2's survivors from PvP
    assert npc_combat.defender_ships == 2  # NPC garrison
    assert npc_combat.winner is None, "Should be a tie (mutual destruction)"
    assert npc_combat.attacker_survivors == 0
    assert npc_combat.defender_survivors == 0

    # Final state: J should be NPC-controlled with 0 ships
    # (NPC tie means star becomes/stays NPC-controlled)
    assert star_j.owner is None, f"J should be NPC (owner=None), got {star_j.owner}"
    assert star_j.stationed_ships.get("p1", 0) == 0
    assert star_j.stationed_ships.get("p2", 0) == 0
    assert star_j.npc_ships == 0  # NPC lost all ships in tie


if __name__ == "__main__":
    # Run the test
    test_simultaneous_arrival_at_npc_star_both_fleets_participate()
    print("\n✅ Test passed!")
