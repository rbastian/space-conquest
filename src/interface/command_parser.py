"""Natural language command parser for human players.

This module parses natural language commands like "move 5 ships from A to B"
into Order objects that can be executed by the game engine.
"""

import re
from enum import Enum
from typing import List, Optional

from ..models.order import Order


class ErrorType(Enum):
    """Classification of order input errors."""
    UNKNOWN_COMMAND = "unknown_command"
    SYNTAX_ERROR = "syntax_error"
    VALIDATION_ERROR = "validation_error"


class OrderParseError(Exception):
    """Raised when order parsing fails with classification."""

    def __init__(self, error_type: ErrorType, message: str):
        """Initialize parse error.

        Args:
            error_type: Classification of the error
            message: Human-readable error message
        """
        self.error_type = error_type
        self.message = message
        super().__init__(message)


class CommandParser:
    """Parse natural language commands into Orders."""

    def parse(self, command: str) -> Optional[Order]:
        """Parse a command string into an Order.

        Supported formats:
        - "move <num> ships from <star> to <star>"
        - "send <num> from <star> to <star>"
        - "move <num> from <star> to <star>"
        - "attack <star> with <num> from <star>"
        - "<num> from <star> to <star>"

        Special commands (return None):
        - "pass" (no moves)
        - "done" (end turn)
        - "help"
        - "status"

        Args:
            command: Command string to parse

        Returns:
            Order object if parsed successfully, None for special commands

        Raises:
            ValueError: If command format is invalid
        """
        # Normalize: lowercase and strip whitespace
        cmd = command.strip().lower()

        # Check for special commands (these are handled by HumanPlayer)
        # Return None for commands that shouldn't be parsed as orders
        if cmd in ("pass", "done", "end", "list", "ls", "clear", "reset"):
            return None  # Signal special command (not an order)

        if cmd in ("help", "h", "?"):
            raise ValueError("HELP")  # Special signal for help

        if cmd in ("status", "st"):
            raise ValueError("STATUS")  # Special signal for status

        if cmd in ("quit", "exit", "q"):
            raise ValueError("QUIT")  # Special signal for quit

        # Try different patterns
        order = (
            self._parse_move_pattern(cmd)
            or self._parse_attack_pattern(cmd)
            or self._parse_simple_pattern(cmd)
        )

        if order is None:
            # Determine if this is unknown command or syntax error
            first_word = cmd.split()[0] if cmd.split() else ""

            # Check if first word looks like it could be a command attempt
            known_commands = ["move", "done", "list", "clear", "help", "status", "quit",
                            "end", "ls", "reset", "h", "st", "exit", "q", "pass"]

            # If first word is not recognized at all, it's unknown command
            if first_word not in known_commands and not first_word.isdigit():
                raise OrderParseError(
                    ErrorType.UNKNOWN_COMMAND,
                    f"Unknown command: '{first_word}'"
                )
            else:
                # Otherwise it's a syntax error (recognized pattern but invalid format)
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    "Syntax error: invalid command format\nCorrect format: move <ships> from <star> to <star>"
                )

        return order

    def _parse_move_pattern(self, cmd: str) -> Optional[Order]:
        """Parse 'move <num> ships from <star> to <star>' pattern.

        Args:
            cmd: Normalized command string

        Returns:
            Order if pattern matches, None otherwise

        Raises:
            OrderParseError: If pattern looks like move command but has syntax error
        """
        # Check if command starts with 'move'
        if not cmd.startswith("move"):
            return None

        # Pattern: move <num> (ships)? from <star> to <star>
        pattern = r"move\s+(\d+)\s+(?:ships?\s+)?from\s+(\w+)\s+to\s+(\w+)"
        match = re.match(pattern, cmd)

        if match:
            ships = int(match.group(1))
            # Check for zero or negative ships before creating Order
            if ships <= 0:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid ship count: must be positive (got {ships})"
                )
            from_star = match.group(2).upper()
            to_star = match.group(3).upper()
            return Order(from_star=from_star, to_star=to_star, ships=ships)

        # Pattern didn't match - provide specific syntax error
        # Split command to diagnose issue
        parts = cmd.split()

        if len(parts) < 2:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: invalid command format\nCorrect format: move <ships> from <star> to <star>"
            )

        # Check if second part is a number
        ship_part = parts[1]

        # Try to parse as integer
        try:
            ship_count = int(ship_part)
        except ValueError:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                f"Invalid ship count: '{ship_part}' is not a number"
            )

        if ship_count <= 0:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                f"Invalid ship count: must be positive (got {ship_count})"
            )

        # Check for 'from' keyword
        if 'from' not in parts:
            # Check for common typos
            if 'form' in parts:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    "Syntax error: did you mean 'from'? Got 'form'\nCorrect format: move <ships> from <star> to <star>"
                )
            else:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    "Syntax error: expected 'from' after ship count\nCorrect format: move <ships> from <star> to <star>"
                )

        # Check for 'to' keyword
        if 'to' not in parts:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: expected 'to' after origin star\nCorrect format: move <ships> from <star> to <star>"
            )

        # Get indices
        from_idx = parts.index('from')
        to_idx = parts.index('to')

        # Check for missing star after 'from'
        if from_idx + 1 >= len(parts) or parts[from_idx + 1] == 'to':
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: missing origin star ID after 'from'\nCorrect format: move <ships> from <star> to <star>"
            )

        # Check for missing star after 'to'
        if to_idx + 1 >= len(parts):
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: missing destination star ID after 'to'\nCorrect format: move <ships> from <star> to <star>"
            )

        # If we got here, there's some other syntax issue
        raise OrderParseError(
            ErrorType.SYNTAX_ERROR,
            "Syntax error: invalid command format\nCorrect format: move <ships> from <star> to <star>"
        )

    def _parse_attack_pattern(self, cmd: str) -> Optional[Order]:
        """Parse 'attack <star> with <num> from <star>' pattern.

        Args:
            cmd: Normalized command string

        Returns:
            Order if pattern matches, None otherwise
        """
        # Pattern: attack <star> with <num> (ships)? from <star>
        pattern = r"attack\s+(\w+)\s+with\s+(\d+)\s+(?:ships?\s+)?from\s+(\w+)"
        match = re.match(pattern, cmd)

        if match:
            to_star = match.group(1).upper()
            ships = int(match.group(2))
            from_star = match.group(3).upper()
            return Order(from_star=from_star, to_star=to_star, ships=ships)

        return None

    def _parse_simple_pattern(self, cmd: str) -> Optional[Order]:
        """Parse '<num> from <star> to <star>' pattern.

        Args:
            cmd: Normalized command string

        Returns:
            Order if pattern matches, None otherwise

        Raises:
            OrderParseError: If pattern looks like simple order but has syntax error
        """
        # Check if command starts with a number
        parts = cmd.split()
        if not parts or not parts[0].isdigit():
            return None

        # Pattern: <num> (ships)? from <star> to <star>
        pattern = r"(\d+)\s+(?:ships?\s+)?from\s+(\w+)\s+to\s+(\w+)"
        match = re.match(pattern, cmd)

        if match:
            ships = int(match.group(1))
            # Check for zero or negative ships before creating Order
            if ships <= 0:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid ship count: must be positive (got {ships})"
                )
            from_star = match.group(2).upper()
            to_star = match.group(3).upper()
            return Order(from_star=from_star, to_star=to_star, ships=ships)

        # Pattern didn't match - provide specific syntax error
        try:
            ship_count = int(parts[0])
        except ValueError:
            # This shouldn't happen since we check isdigit() above
            # but keep for safety
            return None

        if ship_count <= 0:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                f"Invalid ship count: must be positive (got {ship_count})"
            )

        # Similar diagnostic logic as move pattern
        if 'from' not in parts:
            if 'form' in parts:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    "Syntax error: did you mean 'from'? Got 'form'\nCorrect format: <ships> from <star> to <star>"
                )
            else:
                raise OrderParseError(
                    ErrorType.SYNTAX_ERROR,
                    "Syntax error: expected 'from' after ship count\nCorrect format: <ships> from <star> to <star>"
                )

        if 'to' not in parts:
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: expected 'to' after origin star\nCorrect format: <ships> from <star> to <star>"
            )

        from_idx = parts.index('from')
        to_idx = parts.index('to')

        if from_idx + 1 >= len(parts) or parts[from_idx + 1] == 'to':
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: missing origin star ID after 'from'\nCorrect format: <ships> from <star> to <star>"
            )

        if to_idx + 1 >= len(parts):
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                "Syntax error: missing destination star ID after 'to'\nCorrect format: <ships> from <star> to <star>"
            )

        raise OrderParseError(
            ErrorType.SYNTAX_ERROR,
            "Syntax error: invalid command format\nCorrect format: <ships> from <star> to <star>"
        )

    def parse_multiple(self, command: str) -> List[Order]:
        """Parse multiple orders from a single command string.

        Orders can be separated by semicolons, commas, or 'and'.

        Args:
            command: Command string potentially containing multiple orders

        Returns:
            List of Order objects

        Raises:
            ValueError: If any command is invalid
        """
        # Split by separators
        separators = [";", ",", " and ", " & "]
        parts = [command]

        for sep in separators:
            new_parts = []
            for part in parts:
                new_parts.extend(part.split(sep))
            parts = new_parts

        # Parse each part
        orders = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            order = self.parse(part)
            if order is not None:
                orders.append(order)

        return orders
