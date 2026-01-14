"""Decision-making process logger for AI agents.

This module provides JSONL logging for agent decision-making processes.
Each turn's complete decision trail (tool calls, calculations, orders) is written
as a single JSON line to enable analysis of agent reasoning and behavior.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class DecisionLogger:
    """Logs agent decision-making process to JSONL files.

    Each game gets its own log file where each turn's decision process is written
    as a JSON line. This format enables easy streaming analysis and parsing.
    """

    # Maximum length for truncating long strings
    MAX_STRING_LENGTH = 1000

    def __init__(self, game_id: str, output_dir: str = "logs"):
        """Initialize logger for a specific game.

        Args:
            game_id: Unique identifier for the game (e.g., "seed12345_p2_turn1")
            output_dir: Directory to write log files (default: "logs")
        """
        self.game_id = game_id
        self.output_dir = Path(output_dir)

        # Create logs directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set up file path: {output_dir}/game_{game_id}_decisions.jsonl
        self.log_path = self.output_dir / f"game_{game_id}_decisions.jsonl"

        # Open file in append mode to support resuming games
        try:
            self.file_handle = open(self.log_path, "a", encoding="utf-8")
        except OSError as e:
            raise OSError(f"Failed to open log file {self.log_path}: {e}") from e

        # Current turn data being accumulated
        self.current_turn_data: dict[str, Any] | None = None
        self.turn_start_time: float | None = None

    def start_turn(self, turn: int, game_stage: str | None = None) -> None:
        """Start logging a new turn.

        Args:
            turn: Turn number
            game_stage: Current game stage ("early", "mid", "late"), optional
        """
        self.current_turn_data = {
            "turn": turn,
            "timestamp": datetime.now().isoformat(),
            "game_stage": game_stage,
            "tool_calls": [],
            "calculations_performed": {
                "distance": False,
                "hyperspace_risk": False,
                "combat_outcome": False,
                "fleet_timing": False,
            },
            "orders_submitted": [],
            "token_usage": None,
        }
        self.turn_start_time = time.time()

    def log_tool_call(
        self, tool_name: str, tool_input: str | dict, tool_output: str, success: bool = True
    ) -> None:
        """Log a tool call made during the turn.

        Args:
            tool_name: Name of the tool called
            tool_input: Input to the tool (code string or dict)
            tool_output: Output from the tool
            success: Whether the tool call succeeded
        """
        if self.current_turn_data is None:
            return

        # Truncate long strings
        if isinstance(tool_input, str):
            input_truncated = self._truncate(tool_input)
        else:
            input_truncated = tool_input

        output_truncated = self._truncate(str(tool_output))

        # Detect what type of calculation was performed (for python_repl)
        if tool_name == "python_repl":
            # Extract code from dict or use string directly
            code = tool_input.get("code") if isinstance(tool_input, dict) else tool_input
            if isinstance(code, str):
                self._detect_calculations(code)

        tool_call_entry = {
            "sequence": len(self.current_turn_data["tool_calls"]) + 1,
            "tool": tool_name,
            "input": input_truncated,
            "output": output_truncated,
            "success": success,
        }

        self.current_turn_data["tool_calls"].append(tool_call_entry)

    def log_orders(self, orders: list[dict]) -> None:
        """Log the final orders submitted for the turn.

        Args:
            orders: List of order dictionaries with from, to, ships, rationale
        """
        if self.current_turn_data is None:
            return

        self.current_turn_data["orders_submitted"] = orders

    def log_token_usage(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        """Log token usage for the turn.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            total_tokens: Total tokens used
        """
        if self.current_turn_data is None:
            return

        self.current_turn_data["token_usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    def end_turn(self) -> None:
        """Finish logging the current turn and write to file."""
        if self.current_turn_data is None:
            return

        # Calculate thinking time
        if self.turn_start_time is not None:
            thinking_time = time.time() - self.turn_start_time
            self.current_turn_data["thinking_time_seconds"] = round(thinking_time, 2)

        try:
            # Write as compact JSON (no extra whitespace)
            json_line = json.dumps(self.current_turn_data, separators=(",", ":"))
            self.file_handle.write(json_line + "\n")
            # Flush to ensure data is written immediately
            self.file_handle.flush()
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid decision data format: {e}") from e
        except OSError as e:
            raise OSError(f"Failed to write to log file: {e}") from e
        finally:
            # Reset for next turn
            self.current_turn_data = None
            self.turn_start_time = None

    def _truncate(self, text: str) -> str:
        """Truncate long strings to maximum length.

        Args:
            text: String to truncate

        Returns:
            Truncated string with ellipsis if needed
        """
        if len(text) <= self.MAX_STRING_LENGTH:
            return text
        return text[: self.MAX_STRING_LENGTH] + "... [truncated]"

    def _detect_calculations(self, code: str) -> None:
        """Detect what types of calculations are present in Python code.

        Args:
            code: Python code string to analyze
        """
        if self.current_turn_data is None:
            return

        code_lower = code.lower()
        calculations = self.current_turn_data["calculations_performed"]

        # Detect distance calculations
        if any(
            keyword in code_lower
            for keyword in ["distance", "max(abs(", "abs(x", "abs(y", "chebyshev"]
        ):
            calculations["distance"] = True  # type: ignore[index]

        # Detect hyperspace risk calculations
        if any(
            keyword in code_lower
            for keyword in ["hyperspace", "log2", "survival", "0.02 *", "risk"]
        ):
            calculations["hyperspace_risk"] = True  # type: ignore[index]

        # Detect combat outcome calculations
        if any(
            keyword in code_lower
            for keyword in ["combat", "attackers", "defenders", "ceil", "survivors"]
        ):
            calculations["combat_outcome"] = True  # type: ignore[index]

        # Detect fleet timing calculations
        if any(
            keyword in code_lower
            for keyword in [
                "arrival",
                "eta",
                "game_turn +",
                "turns_until",
                "reinforce",
                "timing",
            ]
        ):
            calculations["fleet_timing"] = True  # type: ignore[index]

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
