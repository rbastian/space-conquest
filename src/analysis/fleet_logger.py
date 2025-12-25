"""Fleet movement logger with rationale tracking.

Logs detailed fleet information including strategic rationale to enable
real-time monitoring of fleet movements.
"""

import json
from pathlib import Path
from typing import Any


class FleetLogger:
    """Logs fleet movements with rationale to JSONL files."""

    def __init__(self, output_dir: str = "logs"):
        """Initialize fleet logger.

        Args:
            output_dir: Directory to write log files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.log_files: dict[str, Any] = {}

    def log_turn(self, game, player_id: str, turn: int) -> None:
        """Log fleet status for a player's turn.

        Args:
            game: Current game state
            player_id: Player ID (p1 or p2)
            turn: Current turn number
        """
        # Get log file handle
        log_file = self._get_log_file(game.seed, player_id)

        # Extract fleet information
        my_fleets = [f for f in game.fleets if f.owner == player_id]

        fleet_data = []
        for fleet in my_fleets:
            # Get star names
            origin_star = next((s for s in game.stars if s.id == fleet.origin), None)
            dest_star = next((s for s in game.stars if s.id == fleet.dest), None)

            fleet_data.append(
                {
                    "fleet_id": fleet.id,
                    "ships": fleet.ships,
                    "origin_id": fleet.origin,
                    "origin_name": origin_star.name if origin_star else fleet.origin,
                    "dest_id": fleet.dest,
                    "dest_name": dest_star.name if dest_star else fleet.dest,
                    "turns_remaining": fleet.dist_remaining,
                    "rationale": fleet.rationale,
                }
            )

        # Create log entry
        log_entry = {
            "turn": turn,
            "player": player_id,
            "timestamp": self._get_timestamp(),
            "fleets": fleet_data,
            "fleet_count": len(fleet_data),
        }

        # Write to file
        log_file.write(json.dumps(log_entry) + "\n")
        log_file.flush()

    def _get_log_file(self, seed: int, player_id: str):
        """Get or create log file handle for a player."""
        key = f"{seed}_{player_id}"

        if key not in self.log_files:
            filename = f"game_seed{seed}_{player_id}_fleets.jsonl"
            filepath = self.output_dir / filename
            self.log_files[key] = open(filepath, "a")

        return self.log_files[key]

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    def close(self) -> None:
        """Close all open log files."""
        for f in self.log_files.values():
            f.close()
        self.log_files.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
