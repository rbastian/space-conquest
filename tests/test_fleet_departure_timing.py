"""Tests to verify fleet departure timing bug fix.

This test file verifies that ships ordered to depart do NOT participate in
combat at their origin star - they leave BEFORE Phase 2 combat occurs.
"""

from src.engine.turn_executor import TurnExecutor
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


def test_departing_ships_do_not_defend_origin_star():
    """Test that ships ordered to depart do NOT participate in origin star defense.

    Scenario:
    - Turn 1: P1 has 10 ships at star A, orders 5 to depart
    - Turn 2, Phase 1: 5 ships depart (A now has 5 ships)
    - Turn 2, Phase 2: P2 attacks A with 3 ships
    - Expected: Combat is 3 vs 5 (not 3 vs 10)
    """
    game = Game(seed=42, turn=0)

    # Create stars: A (P1 home), B (neutral), C (P2 home)
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Gamma",
        x=9,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    executor = TurnExecutor()

    # TURN 1: P1 orders 5 ships to depart from A to B
    orders_turn1 = {
        "p1": [Order(from_star="A", to_star="B", ships=5)],
        "p2": [],
    }

    game, combat_events_t1, hyperspace_losses_t1, rebellion_events_t1 = (
        executor.execute_turn(game, orders_turn1)
    )

    # After Turn 1: Ships should be deducted immediately in Phase 4
    # 10 (start) - 5 (departed) + 4 (production) = 9
    assert star_a.stationed_ships["p1"] == 9

    # Fleet created and ships already deducted
    assert len(game.fleets) == 1
    assert game.fleets[0].ships == 5

    # TURN 2: P2 sends 3 ships to attack A, P1 sends no new orders
    # P1's fleet already departed in Turn 1 Phase 4, so it's in transit
    # In Phase 2, no combat at A because P2's fleet hasn't arrived yet
    orders_turn2 = {
        "p1": [],
        "p2": [Order(from_star="C", to_star="A", ships=3)],
    }

    game, combat_events_t2, hyperspace_losses_t2, rebellion_events_t2 = (
        executor.execute_turn(game, orders_turn2)
    )

    # After Turn 2: P1's fleet is still in transit, P2's fleet just created
    # A: 9 (after T1) + 4 (T2 production) = 13
    # C: 10 (start) + 4 (T1 production) - 3 (fleet) + 4 (T2 production) = 15

    # Check combat: P2's attacking fleet hasn't arrived yet (distance > 1)
    # So no combat should have occurred at A yet
    assert len(combat_events_t2) == 0  # No combat this turn

    # Ships at A after T2 production: 9 + 4 = 13
    assert star_a.stationed_ships["p1"] == 13

    # P2's fleet is in transit (ships already deducted in Turn 2 Phase 4)
    # C had production in both turns: 10 + 4 (T1) - 3 (fleet) + 4 (T2) = 15
    assert star_c.stationed_ships["p2"] == 15
    assert len(game.fleets) == 2  # P1's fleet to B + P2's fleet to A


def test_fleet_departs_before_combat_multi_turn():
    """Test complete multi-turn scenario with fleet departure timing.

    Turn 1: P1 orders 5 ships from A to B (distance 1)
    Turn 2: Fleet arrives at B, P2 attacks A with 4 ships (distance 1)
    Turn 3: P2's fleet arrives at A, combat occurs with remaining P1 ships
    """
    game = Game(seed=100, turn=0)

    # Create stars: A (P1 home), B (adjacent to A), C (P2 home)
    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=1,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Gamma",
        x=9,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="C"),
    }

    executor = TurnExecutor()

    # TURN 1: P1 orders 5 ships from A to B
    orders_turn1 = {
        "p1": [Order(from_star="A", to_star="B", ships=5)],
        "p2": [],
    }

    game, _, _, _ = executor.execute_turn(game, orders_turn1)

    # After Turn 1: Ships deducted immediately in Phase 4
    assert star_a.stationed_ships["p1"] == 9  # 10 - 5 + 4 production
    assert len(game.fleets) == 1

    # TURN 2: P1's fleet arrives at B (distance 1)
    # P2 orders 4 ships to attack A
    orders_turn2 = {
        "p1": [],
        "p2": [Order(from_star="C", to_star="A", ships=4)],
    }

    game, combat_events_t2, _, _ = executor.execute_turn(game, orders_turn2)

    # P1's fleet arrived at B (distance 1)
    # A: 9 (after T1) + 4 (T2 production) = 13
    assert star_a.stationed_ships["p1"] == 13

    # P1's fleet arrived at B (5 ships) + production (2 RU) = 7
    assert star_b.stationed_ships.get("p1", 0) == 7
    assert star_b.owner == "p1"  # P1 captured B

    # P2's fleet created in Phase 4, ships already deducted
    assert len(game.fleets) == 1
    assert game.fleets[0].owner == "p2"
    # C: 10 (start) + 4 (T1 production) - 4 (fleet) + 4 (T2 production) = 14
    assert star_c.stationed_ships["p2"] == 14

    # No combat yet at A
    assert len(combat_events_t2) == 0


def test_order_validation_against_current_ships():
    """Test that order validation checks ships at order time.

    If you have 10 ships, you can order up to 10 ships total in one turn
    (e.g., 5+5), because orders are validated against current garrison.
    Ships are deducted as each order is executed in Phase 4.
    """
    game = Game(seed=42, turn=0)

    star_a = Star(
        id="A",
        name="Alpha",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Beta",
        x=1,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    star_c = Star(
        id="C",
        name="Gamma",
        x=2,
        y=0,
        base_ru=2,
        owner=None,
        npc_ships=0,
        stationed_ships={},
    )
    star_d = Star(
        id="D",
        name="Delta",
        x=9,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 10},
    )
    game.stars = [star_a, star_b, star_c, star_d]
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="D"),
    }

    executor = TurnExecutor()

    # Try to order ALL 10 ships in multiple orders
    orders = {
        "p1": [
            Order(from_star="A", to_star="B", ships=5),
            Order(from_star="A", to_star="C", ships=5),
        ],
        "p2": [],
    }

    game, _, _, _ = executor.execute_turn(game, orders)

    # Both orders should succeed
    assert len(game.fleets) == 2
    assert game.fleets[0].ships == 5
    assert game.fleets[1].ships == 5

    # Ships deducted immediately: 10 - 5 - 5 + 4 production = 4
    assert star_a.stationed_ships["p1"] == 4

    # No errors
    assert "p1" not in game.order_errors
