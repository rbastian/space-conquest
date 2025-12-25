#!/usr/bin/env python3
"""Watch and display game progress from strategic JSONL logs in real-time."""

import glob
import json
import sys
import time
from pathlib import Path


def find_active_game_logs():
    """Find the most recently updated game log files."""
    log_files = glob.glob("logs/game_seed*_strategic.jsonl")
    if not log_files:
        return None, []

    # Get most recent modification time
    latest_mtime = max(Path(f).stat().st_mtime for f in log_files)

    # Find all logs modified within last 60 seconds (active game)
    active_logs = []
    seed = None
    for log_file in log_files:
        if Path(log_file).stat().st_mtime >= latest_mtime - 60:
            active_logs.append(log_file)
            if not seed:
                seed = Path(log_file).stem.split("_")[1].replace("seed", "")

    return seed, sorted(active_logs)


def tail_jsonl(filepath, num_lines=1):
    """Get the last N lines from a JSONL file."""
    try:
        with open(filepath) as f:
            lines = f.readlines()
            return [json.loads(line) for line in lines[-num_lines:]]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def display_turn(player_id, data, is_new=False):
    """Display turn information for a player."""
    turn = data.get("turn", "?")

    # Expansion
    exp = data.get("expansion", {})
    stars = exp.get("stars_controlled", 0)
    new_stars = exp.get("new_stars_this_turn", [])

    # Resources
    res = data.get("resources", {})
    prod = res.get("total_production_ru", 0)
    ratio = res.get("production_ratio", 0)

    # Fleets
    fleets = data.get("fleets", {})
    total_ships = fleets.get("total_ships", 0)
    in_flight = fleets.get("num_fleets_in_flight", 0)

    # Garrison
    garrison = data.get("garrison", {})
    home_garrison = garrison.get("home_star_garrison", 0)
    threat = garrison.get("threat_level", "unknown")

    # Territory
    territory = data.get("territory", {})
    home_q = territory.get("stars_in_home_quadrant", 0)
    center = territory.get("stars_in_center_zone", 0)
    opp_q = territory.get("stars_in_opponent_quadrant", 0)

    # Spatial
    spatial = data.get("spatial_awareness", {})
    opp_found = spatial.get("opponent_home_discovered", False)

    # Threat emoji
    threat_emoji = {"none": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴", "critical": "🚨"}.get(
        threat, "⚪"
    )

    # New turn indicator
    indicator = "🆕" if is_new else "  "

    print(f"\n{indicator} {player_id.upper()} Turn {turn}")
    print(f"   {'─' * 50}")

    # Compact display
    print(f"   🏛️  {stars} stars", end="")
    if new_stars:
        print(f" (+{', '.join(new_stars)})", end="")
    print(f" | 🏭 {prod} RU/turn ({ratio:.2f}x)")

    print(
        f"   ⚔️  {total_ships} ships | ✈️  {in_flight} fleets | 🛡️  {home_garrison} garrison {threat_emoji}"
    )

    if opp_found:
        print("   🎯 Enemy home FOUND!")

    if opp_q > 0:
        print(f"   🗺️  Territory: {home_q} home | {center} center | {opp_q} enemy ⚠️")

    # Show expansion events
    if new_stars:
        print(f"   🌟 Expanded to: {', '.join(new_stars)}")


def watch_game(refresh_interval=3):
    """Watch game logs and display updates."""
    print("🔍 Scanning for active game...")

    seed, log_files = find_active_game_logs()

    if not log_files:
        print("❌ No active game found. Start a game first:")
        print("   python game.py --mode lvl")
        return

    print(f"✅ Found active game (seed: {seed})")
    print(f"   Watching {len(log_files)} player(s)")
    print(f"   Refresh every {refresh_interval}s (Ctrl+C to stop)\n")

    # Track last turn seen per player
    last_turns = {}

    try:
        while True:
            # Re-check for log files (in case new ones appear)
            _, current_logs = find_active_game_logs()

            has_updates = False

            for log_file in sorted(current_logs):
                # Extract player ID
                if "_p1_" in log_file:
                    player = "p1"
                elif "_p2_" in log_file:
                    player = "p2"
                else:
                    continue

                # Get latest turn
                entries = tail_jsonl(log_file, 1)
                if not entries:
                    continue

                latest = entries[0]
                turn = latest.get("turn", 0)

                # Check if this is a new turn
                is_new = player not in last_turns or last_turns[player] < turn

                if is_new:
                    has_updates = True
                    display_turn(player, latest, is_new=True)
                    last_turns[player] = turn

            if not has_updates:
                # Show spinner to indicate we're still watching
                print(".", end="", flush=True)
            else:
                print()  # New line after updates

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching")


def show_current_status():
    """Show current game status once and exit."""
    seed, log_files = find_active_game_logs()

    if not log_files:
        print("No game logs found")
        sys.exit(1)

    print(f"{'=' * 60}")
    print(f"  GAME STATUS (Seed: {seed})")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 60}")

    for log_file in sorted(log_files):
        if "_p1_" in log_file:
            player = "p1"
        elif "_p2_" in log_file:
            player = "p2"
        else:
            continue

        entries = tail_jsonl(log_file, 1)
        if entries:
            display_turn(player, entries[0])

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Watch Space Conquest game in real-time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python watch_game.py              # Watch with 3s refresh
  python watch_game.py --interval 5 # Watch with 5s refresh
  python watch_game.py --once       # Show current status and exit
        """,
    )
    parser.add_argument(
        "--interval", type=int, default=3, help="Refresh interval in seconds (default: 3)"
    )
    parser.add_argument("--once", action="store_true", help="Show current status once and exit")

    args = parser.parse_args()

    if args.once:
        show_current_status()
    else:
        watch_game(args.interval)
