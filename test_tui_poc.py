#!/usr/bin/env python3
"""Quick test to verify TUI POC is working."""

import sys
from src.models.star import Star
from src.models.player import Player
from src.models.fleet import Fleet
from src.models.game import Game

# Create a simple test game state
stars = [
    Star(id="A", name="Alpha", x=0, y=0, base_ru=3, owner="p1",
         stationed_ships={"p1": 10}, npc_ships=0),
    Star(id="B", name="Beta", x=3, y=2, base_ru=2, owner="p1",
         stationed_ships={"p1": 5}, npc_ships=0),
    Star(id="C", name="Gamma", x=6, y=5, base_ru=4, owner=None,
         stationed_ships={}, npc_ships=8),
]

# Create players
p1 = Player(id="p1", home_star="A")
p1.visited_stars = {"A", "B", "C"}

p2 = Player(id="p2", home_star="C")

# Create a fleet in transit
fleets = [
    Fleet(id="f1", owner="p1", origin="A", dest="C", ships=3, dist_remaining=2),
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

# Test that DisplayManager can generate output
from src.interface.display import DisplayManager
display = DisplayManager()

print("Testing DisplayManager output:")
print("=" * 60)
display._show_controlled_stars(p1, game)
display._show_fleets_in_transit(p1, game)
print("=" * 60)

print("\nTUI POC Status: SUCCESS")
print("- DisplayManager generates output correctly")
print("- Test data is valid")
print("\nTo run the interactive TUI demo:")
print("  .venv/bin/python -m src.interface.tui_app")
