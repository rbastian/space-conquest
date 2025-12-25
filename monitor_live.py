#!/usr/bin/env python3
"""Live game monitoring from strategic logs.

Monitors a running game by reading the strategic log files being written in real-time.
"""

import argparse
import glob
import json
import time
from pathlib import Path


def find_latest_game_logs() -> list[str]:
    """Find the most recently modified game log files."""
    log_files = glob.glob("logs/game_seed*_strategic.jsonl")
    if not log_files:
        return []

    # Group by seed and get the most recent seed
    by_seed = {}
    for log_file in log_files:
        parts = Path(log_file).stem.split("_")
        seed = parts[1].replace("seed", "")
        mtime = Path(log_file).stat().st_mtime

        if seed not in by_seed:
            by_seed[seed] = []
        by_seed[seed].append((mtime, log_file))

    # Get most recent seed
    if not by_seed:
        return []

    latest_seed = max(by_seed.items(), key=lambda x: max(t for t, _ in x[1]))[0]
    return [f for _, f in by_seed[latest_seed]]


def read_latest_turn(log_file: str) -> dict | None:
    """Read the latest turn data from a log file."""
    try:
        with open(log_file) as f:
            lines = list(f)
            if not lines:
                return None
            return json.loads(lines[-1])
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def display_player_status(player_id: str, data: dict) -> None:
    """Display current status for a player."""
    turn = data.get("turn", "?")

    # Expansion
    exp = data.get("expansion", {})
    stars = exp.get("stars_controlled", 0)
    new_stars = exp.get("new_stars_this_turn", [])

    # Resources
    res = data.get("resources", {})
    production = res.get("total_production_ru", 0)
    production_ratio = res.get("production_ratio", 0)

    # Fleets
    fleets = data.get("fleets", {})
    total_ships = fleets.get("total_ships", 0)
    in_flight = fleets.get("num_fleets_in_flight", 0)

    # Garrison
    garrison = data.get("garrison", {})
    home_garrison = garrison.get("home_star_garrison", 0)
    threat = garrison.get("threat_level", "unknown")

    # Spatial
    spatial = data.get("spatial_awareness", {})
    opp_discovered = spatial.get("opponent_home_discovered", False)

    # Territory
    territory = data.get("territory", {})
    home_quadrant = territory.get("stars_in_home_quadrant", 0)
    center = territory.get("stars_in_center_zone", 0)
    opp_quadrant = territory.get("stars_in_opponent_quadrant", 0)

    print(f"\n{'=' * 60}")
    print(f"  PLAYER {player_id.upper()} - Turn {turn}")
    print(f"{'=' * 60}")

    print("\n📊 Empire:")
    print(f"   Stars controlled: {stars}")
    if new_stars:
        print(f"   New this turn: {', '.join(new_stars)}")
    print(f"   Production: {production} RU/turn (ratio: {production_ratio:.2f}x)")

    print("\n⚔️  Military:")
    print(f"   Total ships: {total_ships}")
    print(f"   Fleets in flight: {in_flight}")
    print(f"   Home garrison: {home_garrison}")

    # Threat indicator
    threat_emoji = {"none": "🟢", "low": "🟡", "medium": "🟠", "high": "🔴", "critical": "🚨"}.get(
        threat, "⚪"
    )
    print(f"   Threat level: {threat_emoji} {threat.upper()}")

    print("\n🗺️  Territory:")
    print(f"   Home quadrant: {home_quadrant} stars")
    print(f"   Center zone: {center} stars")
    print(f"   Opponent quadrant: {opp_quadrant} stars")

    if opp_discovered:
        print("\n🎯 Opponent home: DISCOVERED ✓")
    else:
        print("\n🎯 Opponent home: Not yet found")


def monitor_once(seed: str = None) -> None:
    """Monitor game status once."""
    if seed:
        log_pattern = f"logs/game_seed{seed}_*_strategic.jsonl"
        log_files = glob.glob(log_pattern)
    else:
        log_files = find_latest_game_logs()

    if not log_files:
        print("No game logs found. Start a game first.")
        return

    # Extract seed from filename
    if log_files:
        seed = Path(log_files[0]).stem.split("_")[1].replace("seed", "")
        print(f"\n{'=' * 60}")
        print(f"  MONITORING GAME (Seed: {seed})")
        print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}")

    # Read and display each player
    for log_file in sorted(log_files):
        if "_p1_" in log_file:
            player_id = "p1"
        elif "_p2_" in log_file:
            player_id = "p2"
        else:
            continue

        data = read_latest_turn(log_file)
        if data:
            display_player_status(player_id, data)

    print(f"\n{'=' * 60}\n")


def monitor_continuous(seed: str = None, interval: int = 5) -> None:
    """Monitor game continuously."""
    print("Starting live monitoring (Ctrl+C to stop)...")
    print(f"Refresh interval: {interval} seconds\n")

    try:
        while True:
            # Clear screen
            print("\033[2J\033[H", end="")
            monitor_once(seed)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor a running Space Conquest game via strategic logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor_live.py                    # Monitor most recent game once
  python monitor_live.py --watch            # Continuous monitoring
  python monitor_live.py --watch --interval 10   # Update every 10 seconds
  python monitor_live.py --seed 42          # Monitor specific game by seed
        """,
    )
    parser.add_argument("--seed", type=str, help="Game seed to monitor (default: most recent)")
    parser.add_argument(
        "--watch", action="store_true", help="Watch continuously (refresh automatically)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds for --watch mode (default: 5)",
    )

    args = parser.parse_args()

    if args.watch:
        monitor_continuous(args.seed, args.interval)
    else:
        monitor_once(args.seed)


if __name__ == "__main__":
    main()
