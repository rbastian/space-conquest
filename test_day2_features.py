#!/usr/bin/env python3
"""Test script to demonstrate Day 2 TUI features.

This script demonstrates:
1. 4-panel layout (Map, Game State, Reports, Input)
2. Scrollable reports panel
3. Game state updates
4. Combat reports integration
5. Input feedback in reports panel
"""

from src.models.game import Game
from src.models.player import Player
from src.models.star import Star
from src.models.fleet import Fleet
from src.interface.tui_app import SpaceConquestTUI


def create_test_game():
    """Create a test game with combat scenario."""
    # Create stars
    stars = [
        Star(id="A", name="Alpha", x=0, y=0, base_ru=3, owner="p1",
             stationed_ships={"p1": 10}, npc_ships=0),
        Star(id="B", name="Beta", x=3, y=2, base_ru=2, owner="p1",
             stationed_ships={"p1": 5}, npc_ships=0),
        Star(id="C", name="Gamma", x=6, y=5, base_ru=4, owner=None,
             stationed_ships={}, npc_ships=8),
        Star(id="D", name="Delta", x=9, y=7, base_ru=1, owner="p2",
             stationed_ships={"p2": 3}, npc_ships=0),
    ]

    # Create players
    p1 = Player(id="p1", home_star="A")
    p1.visited_stars = {"A", "B", "C"}

    p2 = Player(id="p2", home_star="D")
    p2.visited_stars = {"D", "C"}

    # Create fleets
    fleets = [
        Fleet(id="f1", owner="p1", origin="A", dest="C", ships=5, dist_remaining=1),
    ]

    # Create game
    game = Game(
        seed=12345,
        turn=5,
        stars=stars,
        players={"p1": p1, "p2": p2},
        fleets=fleets,
        p2_model_id="test-model"
    )

    return game


def main():
    """Run the TUI demo."""
    game = create_test_game()

    # Create and run TUI
    app = SpaceConquestTUI(game, "p1")

    print("\n" + "="*70)
    print("DAY 2 TUI FEATURES TEST")
    print("="*70)
    print("\nFeatures to test:")
    print("  1. Four panels: Map, Game State (tables), Reports, Input")
    print("  2. Game State panel now has fixed height (15 lines)")
    print("  3. Reports panel is scrollable and shows feedback")
    print("  4. Type commands and see feedback in Reports panel")
    print("\nCommands to try:")
    print("  - help              (shows help in reports)")
    print("  - move 3 from A to B  (queues order)")
    print("  - list              (shows queued orders)")
    print("  - clear             (clears orders)")
    print("  - done              (submits orders)")
    print("  - quit              (exits)")
    print("\nPress Ctrl+C to exit")
    print("="*70 + "\n")

    app.run(mouse=False)


if __name__ == "__main__":
    main()
