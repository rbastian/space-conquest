#!/usr/bin/env python3
"""Create a test game with fleets for monitoring."""

from src.engine.turn_executor import TurnExecutor
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star
from src.utils.rng import GameRNG
from src.utils.serialization import save_game


def main():
    # Create a game mid-way through with interesting state
    stars = [
        # P1's empire (upper left)
        Star(
            id="A",
            name="Alpha",
            x=0,
            y=0,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 25},
        ),
        Star(
            id="B",
            name="Beta",
            x=2,
            y=1,
            base_ru=2,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 8},
        ),
        Star(
            id="C",
            name="Gamma",
            x=1,
            y=3,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 5},
        ),
        # P2's empire (lower right)
        Star(
            id="X",
            name="Xeno",
            x=11,
            y=9,
            base_ru=4,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 30},
        ),
        Star(
            id="Y",
            name="Yara",
            x=9,
            y=8,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 6},
        ),
        Star(
            id="Z",
            name="Zeta",
            x=10,
            y=7,
            base_ru=3,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 12},
        ),
        # Neutral zone
        Star(
            id="M", name="Midway", x=5, y=5, base_ru=2, owner=None, npc_ships=3, stationed_ships={}
        ),
        Star(
            id="N", name="Nexus", x=6, y=6, base_ru=3, owner=None, npc_ships=4, stationed_ships={}
        ),
    ]

    p1 = Player(id="p1", home_star="A")
    p1.visited_stars = {"A", "B", "C", "M", "Y", "Z"}  # P1 has scouted some enemy territory

    p2 = Player(id="p2", home_star="X")
    p2.visited_stars = {"X", "Y", "Z", "N", "B"}  # P2 has scouted P1's Beta

    game = Game(
        seed=42,
        turn=5,  # Mid-game
        stars=stars,
        players={"p1": p1, "p2": p2},
        fleets=[],
        rng=GameRNG(42),
    )

    # P1 submits orders with strategic rationale
    orders_p1 = [
        Order(from_star="A", to_star="M", ships=15, rationale="expand"),  # Expand into neutral
        Order(from_star="B", to_star="Y", ships=6, rationale="attack"),  # Attack enemy
        Order(from_star="C", to_star="B", ships=2, rationale="reinforce"),  # Reinforce own star
    ]

    # P2 submits counter-orders
    orders_p2 = [
        Order(from_star="X", to_star="M", ships=20, rationale="attack"),  # Race for neutral
        Order(from_star="Z", to_star="Y", ships=8, rationale="reinforce"),  # Defend
    ]

    # Execute orders to create fleets
    executor = TurnExecutor()
    game = executor.execute_phase_orders(game, {"p1": orders_p1, "p2": orders_p2})

    # Simulate one turn of movement
    game, _ = executor.execute_phase_movement(game)
    game.turn += 1

    # Add a combat event for demonstration
    game.combats_last_turn = [
        {
            "star_id": "B",
            "star_name": "Beta",
            "combat_type": "pvp",
            "attacker": "p2",
            "defender": "p1",
            "attacker_ships": 10,
            "defender_ships": 8,
            "winner": "defender",
            "attacker_survivors": 0,
            "defender_survivors": 2,
            "attacker_losses": 10,
            "defender_losses": 6,
            "control_before": "p1",
            "control_after": "p1",
            "simultaneous": False,
        }
    ]

    # Save the game
    save_game(game, "test_game.json")
    print("✅ Test game created: state/test_game.json")
    print(f"   Turn: {game.turn}")
    print(f"   P1 fleets: {len([f for f in game.fleets if f.owner == 'p1'])}")
    print(f"   P2 fleets: {len([f for f in game.fleets if f.owner == 'p2'])}")
    print("\nTo monitor this game, run:")
    print("   python monitor_game.py state/test_game.json")


if __name__ == "__main__":
    main()
