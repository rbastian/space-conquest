"""Strategic gameplay metrics logger.

This module provides JSONL logging for strategic metrics calculated during gameplay.
Each turn's metrics are written as a single JSON line to enable easy parsing and analysis.
"""

import json
from pathlib import Path


class StrategicLogger:
    """Logs strategic gameplay metrics to JSONL files.

    Each game gets its own log file where metrics from each turn are written
    as JSON lines. This format enables easy streaming analysis and parsing.
    """

    def __init__(self, game_id: str, output_dir: str = "logs"):
        """Initialize logger for a specific game.

        Args:
            game_id: Unique identifier for the game
            output_dir: Directory to write log files (default: "logs")
        """
        self.game_id = game_id
        self.output_dir = Path(output_dir)

        # Create logs directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up file path: {output_dir}/game_{game_id}_strategic.jsonl
        self.log_path = self.output_dir / f"game_{game_id}_strategic.jsonl"

        # Open file in append mode to support resuming games
        try:
            self.file_handle = open(self.log_path, "a", encoding="utf-8")
        except OSError as e:
            raise OSError(f"Failed to open log file {self.log_path}: {e}") from e

    def log_turn(self, metrics: dict) -> None:
        """Log strategic metrics for a turn.

        Writes metrics as a single line JSON object. Flushes after each write
        to ensure data is persisted even if the program crashes.

        Args:
            metrics: Dictionary returned by calculate_strategic_metrics()
        """
        try:
            # Write as compact JSON (no extra whitespace)
            json_line = json.dumps(metrics, separators=(",", ":"))
            self.file_handle.write(json_line + "\n")
            # Flush to ensure data is written immediately
            self.file_handle.flush()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid metrics format: {e}") from e
        except OSError as e:
            raise OSError(f"Failed to write to log file: {e}") from e

    def close(self) -> None:
        """Close the log file.

        Should be called when the game is complete to properly close resources.
        Safe to call multiple times.
        """
        if hasattr(self, "file_handle") and self.file_handle and not self.file_handle.closed:
            try:
                self.file_handle.close()
            except OSError:
                # Ignore errors on close
                pass

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager protocol."""
        self.close()
        return False
