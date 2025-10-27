"""Test to reproduce the fleet arrival bug reported by user.

Bug scenario:
- Fleet created Turn 2, dist_remaining = 1
- At START of Turn 3: display shows "Arrives Turn 3"
- After Turn 3 Phase 1: fleet should arrive
- User reports: fleet did NOT arrive

This test will verify that fleets DO arrive when they should.
"""

from src.engine.turn_executor import TurnExecutor
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


def test_fleet_arrives_turn_3_after_creation_turn_2():
    """Reproduce exact scenario from bug report.

    Turn 0: Game starts
    Turn 1: Game runs (no orders)
    Turn 2: Create fleet with dist_remaining=1, counter increments to 3
    Turn 3 START: Fleet shows "Arrives Turn 3" (3 + 1 - 1 = 3)
    Turn 3 Phase 1: Fleet should arrive
    """
    game = Game(seed=42, turn=0)

    # Create two stars distance=1 apart
    star_c = Star(
        id="C",
        name="Centauri",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_n = Star(
        id="N",
        name="Nemesis",
        x=1,
        y=0,  # Distance = 1
        base_ru=2,
        owner=None,
        npc_ships=5,  # Add NPCs
        stationed_ships={},
    )
    # Add p2 home star to avoid victory
    star_z = Star(
        id="Z",
        name="Zeta",
        x=9,
        y=9,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_c, star_n, star_z]
    game.players = {
        "p1": Player(id="p1", home_star="C"),
        "p2": Player(id="p2", home_star="Z"),
    }

    executor = TurnExecutor()

    # Turn 0: No orders
    print(f"\n=== Turn {game.turn} START ===")
    print(f"Fleets: {len(game.fleets)}")
    game, _, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})
    print(f"=== After Turn 0 execution: turn={game.turn} ===")

    # Turn 1: No orders
    print(f"\n=== Turn {game.turn} START ===")
    print(f"Fleets: {len(game.fleets)}")
    game, _, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})
    print(f"=== After Turn 1 execution: turn={game.turn} ===")

    # Turn 2: Submit fleet order
    print(f"\n=== Turn {game.turn} START ===")
    print(f"Fleets: {len(game.fleets)}")
    print(f"Star N ships before: {star_n.stationed_ships}")

    orders = {"p1": [Order(from_star="C", to_star="N", ships=4)], "p2": []}
    game, _, _, _ = executor.execute_turn(game, orders)

    print(f"=== After Turn 2 execution: turn={game.turn} ===")
    print(f"Fleets: {len(game.fleets)}")
    if game.fleets:
        print(f"Fleet[0]: dist_remaining={game.fleets[0].dist_remaining}")

        # This is the state the user sees at START of Turn 3 (after phases 1-3 of turn 3 complete)
        # Display formula (after fix): arrival_turn = game.turn + fleet.dist_remaining
        arrival_turn = game.turn + game.fleets[0].dist_remaining
        print(f"Display shows: 'Arrives Turn {arrival_turn}'")
        print(f"Expected: Turn 4 (fleet will arrive in Phase 1 of turn 4)")

    # Turn 3: No orders - fleet should arrive during Phase 1
    print(f"\n=== Turn {game.turn} START (BEFORE Phase 1) ===")
    print(f"Fleets: {len(game.fleets)}")
    if game.fleets:
        print(f"Fleet[0]: dist_remaining={game.fleets[0].dist_remaining}")
    print(f"Star N ships before Phase 1: {star_n.stationed_ships}")

    game, _, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

    print(f"\n=== After Turn 3 execution (AFTER Phase 1): turn={game.turn} ===")
    print(f"Fleets: {len(game.fleets)}")
    print(f"Star N ships after: {star_n.stationed_ships}")

    # Verify fleet arrived
    assert len(game.fleets) == 0, f"Fleet should have arrived, but {len(game.fleets)} fleets remain"

    # Verify ships arrived (some may be lost in combat with NPCs)
    # Fleet had 4 ships, NPCs had 5, so p1 might lose
    # But at least the fleet should have been removed from hyperspace
    print(f"\nFleet successfully arrived! Star N final state: {star_n.stationed_ships}")


def test_multiple_fleets_same_turn():
    """Test multiple fleets arriving on the same turn to ensure all arrive."""
    game = Game(seed=42, turn=0)

    # Create three stars in a line, distance=1 apart
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=1,
        y=0,  # Distance = 1 from A
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 20},
    )
    star_c = Star(
        id="C",
        name="Centauri",
        x=2,
        y=0,  # Distance = 1 from B, 2 from A
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    # Add p2 home star
    star_z = Star(
        id="Z",
        name="Zeta",
        x=9,
        y=9,
        base_ru=3,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c, star_z]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="Z"),
    }

    executor = TurnExecutor()

    # Turn 0: Send two fleets to C (one from A, one from B)
    # Fleet from A: dist=2, will arrive Turn 2
    # Fleet from B: dist=1, will arrive Turn 1
    orders = {
        "p1": [
            Order(from_star="A", to_star="C", ships=5),
            Order(from_star="B", to_star="C", ships=3),
        ],
        "p2": [],
    }
    game, _, _, _ = executor.execute_turn(game, orders)

    # After Turn 0 → Turn 1
    assert game.turn == 1
    assert len(game.fleets) == 2
    print(f"\nAfter Turn 0: {len(game.fleets)} fleets")
    for fleet in game.fleets:
        print(f"  {fleet.id}: dist_remaining={fleet.dist_remaining}")

    # Turn 1: Fleet from B should arrive (dist=1)
    game, _, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

    # After Turn 1 → Turn 2
    assert game.turn == 2
    print(f"\nAfter Turn 1: {len(game.fleets)} fleets remaining")
    for fleet in game.fleets:
        print(f"  {fleet.id}: dist_remaining={fleet.dist_remaining}")

    # Only fleet from A should remain
    assert len(game.fleets) == 1, f"Expected 1 fleet, got {len(game.fleets)}"
    assert game.fleets[0].origin == "A"

    # Turn 2: Fleet from A should arrive (dist=2, now at 0)
    game, _, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

    # After Turn 2 → Turn 3
    assert game.turn == 3
    print(f"\nAfter Turn 2: {len(game.fleets)} fleets remaining")

    # All fleets should have arrived
    assert len(game.fleets) == 0, f"Expected 0 fleets, got {len(game.fleets)}"
    print("\nAll fleets arrived successfully!")
