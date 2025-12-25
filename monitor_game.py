#!/usr/bin/env python3
"""Game monitoring script - watch any Space Conquest game in progress.

Usage:
    python monitor_game.py <game_save_file>
    python monitor_game.py state/my_game.json

This script displays:
- Current game status (turn, winner)
- Player statistics (ships, stars, production)
- Fleet movements with rationale
- Recent combat events
- Strategic insights
"""

import argparse
import json
import sys

from src.agent.prompts_json import format_game_state_prompt_json
from src.utils.serialization import load_game


def display_header(title: str) -> None:
    """Display a formatted section header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


def display_game_status(game) -> None:
    """Display overall game status."""
    display_header("GAME STATUS")
    print(f"Turn: {game.turn}")
    print(f"Seed: {game.seed}")

    if game.winner:
        print(f"\n🏆 Winner: {game.winner}")
    else:
        print("\n⚔️  Game in progress")


def display_player_stats(game, player_id: str) -> None:
    """Display statistics for a player."""
    player = game.players[player_id]

    # Count stars
    stars_controlled = sum(1 for star in game.stars if star.owner == player_id)

    # Count ships
    stationed_ships = sum(
        star.stationed_ships.get(player_id, 0) for star in game.stars if star.owner == player_id
    )
    ships_in_transit = sum(fleet.ships for fleet in game.fleets if fleet.owner == player_id)
    total_ships = stationed_ships + ships_in_transit

    # Calculate production
    total_production = sum(star.base_ru for star in game.stars if star.owner == player_id)

    display_header(f"PLAYER {player_id.upper()} STATISTICS")
    print(f"Home star: {player.home_star}")
    print(f"Stars controlled: {stars_controlled}")
    print(f"Stars visited: {len(player.visited_stars)}")
    print(f"\nShips stationed: {stationed_ships}")
    print(f"Ships in transit: {ships_in_transit}")
    print(f"Total ships: {total_ships}")
    print(f"\nProduction (RU/turn): {total_production}")


def display_fleets(game, player_id: str) -> None:
    """Display fleet movements with rationale."""
    fleets = [f for f in game.fleets if f.owner == player_id]

    display_header(f"PLAYER {player_id.upper()} FLEETS IN TRANSIT")

    if not fleets:
        print("No fleets in transit")
        return

    print(f"\n{len(fleets)} fleet(s) in transit:\n")

    for fleet in sorted(fleets, key=lambda f: f.dist_remaining):
        # Get star names
        origin_star = next((s for s in game.stars if s.id == fleet.origin), None)
        dest_star = next((s for s in game.stars if s.id == fleet.dest), None)

        origin_name = origin_star.name if origin_star else fleet.origin
        dest_name = dest_star.name if dest_star else fleet.dest

        print(f"Fleet {fleet.id}:")
        print(f"  Route: {origin_name} ({fleet.origin}) → {dest_name} ({fleet.dest})")
        print(f"  Ships: {fleet.ships}")
        print(f"  Arrival: {fleet.dist_remaining} turn(s)")

        if fleet.rationale:
            # Add emoji based on rationale
            emoji_map = {
                "attack": "⚔️",
                "reinforce": "🛡️",
                "expand": "🌟",
                "probe": "🔭",
                "retreat": "↩️",
                "consolidate": "🔄",
            }
            emoji = emoji_map.get(fleet.rationale, "📋")
            print(f"  Rationale: {emoji} {fleet.rationale.upper()}")
        else:
            print("  Rationale: None")

        print()


def display_combat_events(game, player_id: str) -> None:
    """Display recent combat events involving this player."""
    if not game.combats_last_turn:
        return

    player = game.players[player_id]
    relevant_combats = [
        c
        for c in game.combats_last_turn
        if (c.get("attacker") == player_id or c.get("defender") == player_id)
        and c.get("star_id") in player.visited_stars
    ]

    if not relevant_combats:
        return

    display_header("RECENT COMBAT EVENTS")

    for combat in relevant_combats:
        star_name = combat.get("star_name", "Unknown")
        combat_type = combat.get("combat_type", "unknown")

        if combat_type != "pvp":
            continue

        attacker = combat.get("attacker")
        defender = combat.get("defender")
        winner = combat.get("winner")

        you_were = "attacker" if attacker == player_id else "defender"
        your_ships = (
            combat.get("attacker_ships") if you_were == "attacker" else combat.get("defender_ships")
        )
        enemy_ships = (
            combat.get("defender_ships") if you_were == "attacker" else combat.get("attacker_ships")
        )

        if winner == "attacker" and attacker == player_id:
            outcome = "✅ VICTORY"
        elif winner == "defender" and defender == player_id:
            outcome = "✅ VICTORY"
        elif winner:
            outcome = "❌ DEFEAT"
        else:
            outcome = "⚔️ TIE"

        print(f"\nBattle at {star_name}:")
        print(f"  You were: {you_were}")
        print(f"  Your ships: {your_ships}")
        print(f"  Enemy ships: {enemy_ships}")
        print(f"  Outcome: {outcome}")
        print(
            f"  Survivors: {combat.get('attacker_survivors' if attacker == player_id else 'defender_survivors', 0)}"
        )


def display_json_prompt_excerpt(game, player_id: str) -> None:
    """Display a relevant excerpt from the JSON prompt."""
    display_header("JSON PROMPT EXCERPT (What the LLM sees)")

    json_prompt = format_game_state_prompt_json(game, player_id)
    prompt_data = json.loads(json_prompt)

    # Show fleets if any
    my_fleets = prompt_data.get("fleets_in_transit", {}).get("my_fleets", [])
    if my_fleets:
        print("\nFleets in transit JSON:")
        print(json.dumps({"my_fleets": my_fleets}, indent=2))

    # Show spatial awareness
    spatial = prompt_data.get("my_empire", {}).get("spatial_awareness", {})
    opponent_discovered = spatial.get("opponent_home_discovered", False)

    print(f"\nOpponent home discovered: {opponent_discovered}")

    if opponent_discovered:
        opp_home = spatial.get("opponent_home", {})
        print(f"Opponent home: {opp_home.get('name')} ({opp_home.get('id')})")
        print(f"Location: {opp_home.get('location')}")
        print(f"🎯 {opp_home.get('victory_objective', 'CAPTURE TO WIN')}")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor a Space Conquest game in progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor_game.py state/my_game.json
  python monitor_game.py /path/to/game.json
        """,
    )
    parser.add_argument("game_file", help="Path to game save file (.json)")
    parser.add_argument(
        "--player",
        choices=["p1", "p2", "both"],
        default="both",
        help="Which player(s) to show (default: both)",
    )
    parser.add_argument("--json", action="store_true", help="Include JSON prompt excerpts")

    args = parser.parse_args()

    # Load game
    try:
        game = load_game(args.game_file)
    except FileNotFoundError:
        print(f"Error: Game file not found: {args.game_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading game: {e}", file=sys.stderr)
        sys.exit(1)

    # Display game status
    display_game_status(game)

    # Determine which players to show
    players_to_show = ["p1", "p2"] if args.player == "both" else [args.player]

    for player_id in players_to_show:
        display_player_stats(game, player_id)
        display_fleets(game, player_id)
        display_combat_events(game, player_id)

        if args.json:
            display_json_prompt_excerpt(game, player_id)

    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
