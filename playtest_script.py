#!/usr/bin/env python3
"""Playtesting script for observing LLM agent behavior.

This script automates Player 1's actions with simple defensive behavior
to focus on evaluating Player 2 (LLM agent) strategic decision-making.
"""

import sys
import logging
from typing import List

from src.agent.llm_player import LLMPlayer
from src.engine.map_generator import generate_map
from src.engine.turn_executor import TurnExecutor
from src.interface.display import DisplayManager
from src.models.game import Game
from src.models.order import Order
from src.utils.distance import chebyshev_distance


class PlaytestPlayer:
    """Simple automated player for playtesting - plays conservatively."""

    def __init__(self, player_id: str):
        self.player_id = player_id
        self.display = DisplayManager()

    def get_orders(self, game: Game) -> List[Order]:
        """Get automated orders for playtesting.

        Simple strategy: Scout nearby, expand conservatively, defend home.
        """
        player = game.players[self.player_id]
        orders = []

        # Get home star
        home_star_id = game.players[self.player_id].home_star
        home_star = next((s for s in game.stars if s.id == home_star_id), None)

        if not home_star:
            return []

        available_ships = home_star.stationed_ships.get(self.player_id, 0)

        # Keep minimum 4 ships at home
        if available_ships <= 4:
            print(
                f"[P1 AUTO] Turn {game.turn}: Passing (only {available_ships} ships at home)"
            )
            return []

        # Scout or expand on early turns
        if game.turn <= 5:
            # Find nearest unknown star
            nearest = None
            min_dist = 999
            for star in game.stars:
                if star.owner is None:  # Unknown or NPC
                    dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
                    if dist < min_dist and dist <= 6:
                        min_dist = dist
                        nearest = star

            if nearest and available_ships > 5:
                # Send 1 scout
                orders.append(
                    Order(from_star=home_star.id, to_star=nearest.id, ships=1)
                )
                print(
                    f"[P1 AUTO] Turn {game.turn}: Scouting {nearest.name} ({min_dist} distance)"
                )

        # Later turns: expand to known NPC stars
        elif available_ships > 8:
            # Find nearest NPC star we can capture
            for star in game.stars:
                if star.owner == "npc" and star.id in player.visited_stars:
                    dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
                    if dist <= 5:
                        ru = star.base_ru
                        ships_needed = max(4, ru + 2)
                        if available_ships - ships_needed >= 4:
                            orders.append(
                                Order(
                                    from_star=home_star.id,
                                    to_star=star.id,
                                    ships=ships_needed,
                                )
                            )
                            print(
                                f"[P1 AUTO] Turn {game.turn}: Expanding to {star.name} ({ru} RU, {dist} distance)"
                            )
                            break

        if not orders:
            print(f"[P1 AUTO] Turn {game.turn}: Passing (no good targets)")

        return orders


def run_playtest(seed: int, max_turns: int = 25):
    """Run a playtesting game.

    Args:
        seed: Random seed for map generation
        max_turns: Maximum turns before ending game
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    print("\n" + "=" * 80)
    print("SPACE CONQUEST - LLM AGENT PLAYTEST")
    print("=" * 80)
    print(f"\nSeed: {seed}")
    print(f"Max Turns: {max_turns}")
    print("\nPlayer 1: Automated (Simple Conservative Strategy)")
    print("Player 2: LLM Agent (Enhanced Strategic Guidance)")
    print("\n" + "=" * 80)

    # Generate map
    print(f"\nGenerating map with seed {seed}...")
    game = generate_map(seed)
    print("Map generated successfully!")

    # Create players
    p1 = PlaytestPlayer("p1")

    print("\nInitializing LLM player (Sonnet model)...")
    try:
        p2 = LLMPlayer("p2", use_mock=False, model="sonnet", verbose=True)
        print("LLM player initialized successfully!")
    except Exception as e:
        print(f"Warning: Could not initialize Bedrock client: {e}")
        print("Cannot proceed without LLM player. Exiting...")
        return

    # Game loop
    turn_executor = TurnExecutor()
    display = DisplayManager()
    last_combat_events = []
    last_hyperspace_losses = []

    print("\nStarting game...\n")

    while not game.winner and game.turn <= max_turns:
        print(f"\n{'=' * 80}")
        print(f"TURN {game.turn}")
        print(f"{'=' * 80}\n")

        # Show current state summary
        # Calculate totals from all stars
        p1_total = sum(star.stationed_ships.get("p1", 0) for star in game.stars)
        p2_total = sum(star.stationed_ships.get("p2", 0) for star in game.stars)
        p1_production = sum(star.base_ru for star in game.stars if star.owner == "p1")
        p2_production = sum(star.base_ru for star in game.stars if star.owner == "p2")

        print(
            f"P1: {p1_total} ships, {p1_production} RU/turn | P2: {p2_total} ships, {p2_production} RU/turn"
        )
        print()

        # Get orders from both players - show fog-of-war filtered events per player
        # P1's turn
        try:
            # Display P1's filtered combat reports (fog-of-war)
            if last_combat_events:
                display.display_combat_results(last_combat_events, game, player_id="p1")

            # Display P1's hyperspace losses
            if last_hyperspace_losses:
                p1_losses = [
                    loss for loss in last_hyperspace_losses if loss.owner == "p1"
                ]
                if p1_losses:
                    display.display_hyperspace_losses(p1_losses)

            p1_orders = p1.get_orders(game)
        except Exception as e:
            print(f"Error getting P1 orders: {e}")
            p1_orders = []

        # P2's turn
        try:
            print("\n--- Player 2 (LLM) Turn ---")

            # Display P2's filtered combat reports (fog-of-war)
            if last_combat_events:
                display.display_combat_results(last_combat_events, game, player_id="p2")

            # Display P2's hyperspace losses
            if last_hyperspace_losses:
                p2_losses = [
                    loss for loss in last_hyperspace_losses if loss.owner == "p2"
                ]
                if p2_losses:
                    display.display_hyperspace_losses(p2_losses)

            p2_orders = p2.get_orders(game)
            print(f"[P2 LLM] Submitted {len(p2_orders)} order(s)")
            for order in p2_orders:
                star_from = next(
                    (s for s in game.stars if s.id == order.from_star), None
                )
                star_to = next((s for s in game.stars if s.id == order.to_star), None)
                if star_from and star_to:
                    print(
                        f"  - {order.ships} ships: {star_from.name} -> {star_to.name}"
                    )
        except Exception as e:
            print(f"Error getting P2 orders: {e}")
            p2_orders = []

        # Execute turn
        try:
            game, combat_events, hyperspace_losses, rebellion_events = (
                turn_executor.execute_turn(game, {"p1": p1_orders, "p2": p2_orders})
            )
            last_combat_events = combat_events
            last_hyperspace_losses = hyperspace_losses
        except Exception as e:
            print(f"Error executing turn: {e}")
            break

        # Check for victory
        if game.winner:
            print(f"\n{'=' * 80}")
            print("GAME OVER")
            print(f"{'=' * 80}\n")
            if game.winner == "draw":
                print("Result: DRAW (simultaneous home capture)")
            else:
                print(f"Winner: {game.winner}")
            print(f"Final Turn: {game.turn}")
            break

    # Game ended
    if not game.winner and game.turn > max_turns:
        print(f"\n{'=' * 80}")
        print(f"GAME ENDED - Max turns ({max_turns}) reached")
        print(f"{'=' * 80}\n")
        print("Result: No winner (time limit)")

    print("\nPlaytest complete!")
    return game


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Playtest LLM agent behavior")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--max-turns", type=int, default=25, help="Maximum turns (default: 25)"
    )

    args = parser.parse_args()

    try:
        run_playtest(args.seed, args.max_turns)
    except KeyboardInterrupt:
        print("\n\nPlaytest interrupted. Exiting...")
        sys.exit(0)
