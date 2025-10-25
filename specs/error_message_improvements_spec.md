# Order Submission Error Message Improvements - Implementation Specification

**Version:** 1.0
**Date:** 2025-10-21
**Status:** Approved for Implementation

## Overview

This specification defines improvements to error messages during order submission in the human player interface. The goal is to provide clearer, more contextual error feedback that helps players quickly understand and correct issues without overwhelming them with redundant help text.

## Design Principles

1. **Visual Clarity**: Use ❌ emoji instead of "Error:" text for immediate recognition
2. **Contextual Specificity**: Provide detailed error messages with relevant values and context
3. **Smart Help**: Only show help hints for unknown commands, not syntax/validation errors
4. **No Redundancy**: Remove "Try again or type 'help'" message from all error paths
5. **Error Hierarchy**: Distinguish between Unknown Command, Syntax Error, and Validation Error

---

## Section 1: Error Message Templates

### 1.1 Unknown Command Errors

**When to Use**: User enters a command word that doesn't match any known command or order pattern.

**Template**:
```
❌ Unknown command: '{command_word}'

Available commands: move, done, list, clear, help, status, quit
Example: move 5 ships from A to B
```

**Variables**:
- `{command_word}`: The first word of the command (lowercased)

**Examples**:
```
Input: "attack A"
Output:
❌ Unknown command: 'attack'

Available commands: move, done, list, clear, help, status, quit
Example: move 5 ships from A to B
```

```
Input: "send 5 from A to B"
Output:
❌ Unknown command: 'send'

Available commands: move, done, list, clear, help, status, quit
Example: move 5 ships from A to B
```

---

### 1.2 Syntax Error - Invalid Ship Count

**When to Use**: Ship count is not a valid number, is zero, or is negative.

**Template for Non-Numeric**:
```
❌ Invalid ship count: '{ship_input}' is not a number
```

**Template for Zero/Negative**:
```
❌ Invalid ship count: must be positive (got {ship_count})
```

**Variables**:
- `{ship_input}`: The text that was parsed as ship count
- `{ship_count}`: The numeric value if parsed (for zero/negative case)

**Examples**:
```
Input: "move abc from A to B"
Output:
❌ Invalid ship count: 'abc' is not a number
```

```
Input: "move 0 from A to B"
Output:
❌ Invalid ship count: must be positive (got 0)
```

```
Input: "move -5 from A to B"
Output:
❌ Invalid ship count: must be positive (got -5)
```

---

### 1.3 Syntax Error - Missing or Wrong Keywords

**When to Use**: Missing 'from' or 'to' keywords, or typos in those keywords.

**Template for Missing FROM**:
```
❌ Syntax error: expected 'from' after ship count
Correct format: move <ships> from <star> to <star>
```

**Template for Missing TO**:
```
❌ Syntax error: expected 'to' after origin star
Correct format: move <ships> from <star> to <star>
```

**Template for Typo Detection** (optional enhancement):
```
❌ Syntax error: did you mean 'from'? Got '{typo}'
Correct format: move <ships> from <star> to <star>
```

**Examples**:
```
Input: "move 5 ships A to B"
Output:
❌ Syntax error: expected 'from' after ship count
Correct format: move <ships> from <star> to <star>
```

```
Input: "move 5 from A B"
Output:
❌ Syntax error: expected 'to' after origin star
Correct format: move <ships> from <star> to <star>
```

```
Input: "move 5 form A to B"
Output:
❌ Syntax error: did you mean 'from'? Got 'form'
Correct format: move <ships> from <star> to <star>
```

---

### 1.4 Syntax Error - Missing Star IDs

**When to Use**: Star ID is missing after 'from' or 'to' keyword.

**Template for Missing Origin**:
```
❌ Syntax error: missing origin star ID after 'from'
Correct format: move <ships> from <star> to <star>
```

**Template for Missing Destination**:
```
❌ Syntax error: missing destination star ID after 'to'
Correct format: move <ships> from <star> to <star>
```

**Examples**:
```
Input: "move 5 from to B"
Output:
❌ Syntax error: missing origin star ID after 'from'
Correct format: move <ships> from <star> to <star>
```

```
Input: "move 5 from A to"
Output:
❌ Syntax error: missing destination star ID after 'to'
Correct format: move <ships> from <star> to <star>
```

---

### 1.5 Syntax Error - Wrong Number of Arguments

**When to Use**: Command has too many or too few tokens.

**Template**:
```
❌ Syntax error: invalid command format
Correct format: move <ships> from <star> to <star>
```

**Example**:
```
Input: "move 5 from"
Output:
❌ Syntax error: invalid command format
Correct format: move <ships> from <star> to <star>
```

---

### 1.6 Validation Error - Stars Don't Exist

**When to Use**: Star ID is syntactically valid but doesn't exist in the game.

**Template for Missing Origin**:
```
❌ Origin star '{star_id}' does not exist
```

**Template for Missing Destination**:
```
❌ Destination star '{star_id}' does not exist
```

**Template for Both Missing** (unlikely but possible):
```
❌ Stars '{origin_id}' and '{dest_id}' do not exist
```

**Variables**:
- `{star_id}`: The star ID that doesn't exist
- `{origin_id}`, `{dest_id}`: Both star IDs if both don't exist

**Examples**:
```
Input: "move 5 from Z to B"
Output:
❌ Origin star 'Z' does not exist
```

```
Input: "move 5 from A to Z"
Output:
❌ Destination star 'Z' does not exist
```

---

### 1.7 Validation Error - Same Star

**When to Use**: Origin and destination are the same star.

**Template**:
```
❌ Cannot send fleet from {star_id} to itself
```

**Variables**:
- `{star_id}`: The star ID

**Example**:
```
Input: "move 5 from A to A"
Output:
❌ Cannot send fleet from A to itself
```

---

### 1.8 Validation Error - Don't Control Origin

**When to Use**: Player doesn't own the origin star.

**Template**:
```
❌ You do not control star '{star_id}'
```

**Variables**:
- `{star_id}`: The origin star ID

**Example**:
```
Input: "move 5 from E to B" (where E is enemy-controlled)
Output:
❌ You do not control star 'E'
```

---

### 1.9 Validation Error - Insufficient Ships

**When to Use**: Not enough ships at origin star (accounting for already queued orders).

**Template**:
```
❌ Insufficient ships at {star_id}
Requested: {requested}, Available: {available}, Already committed: {committed}, Remaining: {remaining}
```

**Variables**:
- `{star_id}`: Origin star ID
- `{requested}`: Ships requested in current order
- `{available}`: Total ships at star
- `{committed}`: Ships already committed in queued orders
- `{remaining}`: Ships still available (available - committed)

**Example**:
```
Input: "move 50 from A to B" (where A has 30 ships, 10 already committed)
Output:
❌ Insufficient ships at A
Requested: 50, Available: 30, Already committed: 10, Remaining: 20
```

---

## Section 2: Error Classification Logic

### 2.1 Error Classification Flow

```
Command Input
    |
    v
Is command empty? → Yes → Ignore (silent re-prompt)
    |
    No
    v
Is recognized special command? (done, list, clear, help, status, quit)
    |
    v Yes → Execute special command
    |
    No
    v
Try to parse as order
    |
    v
Does first word match any pattern? (move, attack, or digit)
    |
    v No → ERROR TYPE: Unknown Command
    |
    v Yes
    |
Parse ship count
    |
    v
Is valid positive integer?
    |
    v No → ERROR TYPE: Syntax Error (Invalid Ship Count)
    |
    v Yes
    |
Check for 'from' keyword
    |
    v
Exists?
    |
    v No → ERROR TYPE: Syntax Error (Missing FROM)
    |
    v Yes
    |
Parse origin star ID
    |
    v
Exists in command?
    |
    v No → ERROR TYPE: Syntax Error (Missing Origin Star)
    |
    v Yes
    |
Check for 'to' keyword
    |
    v
Exists?
    |
    v No → ERROR TYPE: Syntax Error (Missing TO)
    |
    v Yes
    |
Parse destination star ID
    |
    v
Exists in command?
    |
    v No → ERROR TYPE: Syntax Error (Missing Destination Star)
    |
    v Yes
    |
Order syntax is valid - Create Order object
    |
    v
Validate order against game state
    |
    v
Origin star exists? → No → ERROR TYPE: Validation Error (Origin Not Exist)
Destination star exists? → No → ERROR TYPE: Validation Error (Dest Not Exist)
Origin == Destination? → Yes → ERROR TYPE: Validation Error (Same Star)
Player owns origin? → No → ERROR TYPE: Validation Error (Not Controlled)
Sufficient ships? → No → ERROR TYPE: Validation Error (Insufficient Ships)
    |
    v
All validations pass → SUCCESS → Queue order
```

### 2.2 Error Type Definitions

**Unknown Command Error**:
- **Trigger**: First word doesn't match: move, done, list, clear, help, status, quit, or a digit
- **Show Help**: YES
- **Parser Behavior**: Return None and signal unknown command

**Syntax Error**:
- **Trigger**: Command structure invalid (missing keywords, invalid numbers, wrong format)
- **Show Help**: NO
- **Parser Behavior**: Raise ValueError with specific error message

**Validation Error**:
- **Trigger**: Command syntax correct but violates game rules
- **Show Help**: NO
- **Validator Behavior**: Return error string from validation function

---

## Section 3: Code Structure Changes

### 3.1 New Error Handling System

**New Enum Class**: `ErrorType` (add to command_parser.py)
```python
from enum import Enum

class ErrorType(Enum):
    """Classification of order input errors."""
    UNKNOWN_COMMAND = "unknown_command"
    SYNTAX_ERROR = "syntax_error"
    VALIDATION_ERROR = "validation_error"
```

**New Exception Class**: `OrderParseError` (add to command_parser.py)
```python
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
```

**New Function**: `_format_error_message()` (add to human_player.py)
```python
def _format_error_message(self, error_type: ErrorType, message: str) -> str:
    """Format error message with emoji and optional help.

    Args:
        error_type: Classification of the error
        message: Error message content

    Returns:
        Formatted error message string
    """
    # All errors start with ❌ emoji
    formatted = f"❌ {message}"

    # Only Unknown Command errors show help hint
    if error_type == ErrorType.UNKNOWN_COMMAND:
        formatted += "\n\nAvailable commands: move, done, list, clear, help, status, quit"
        formatted += "\nExample: move 5 ships from A to B"

    return formatted
```

### 3.2 Modified Functions

**CommandParser.parse()** - Enhanced error classification:
- Replace generic ValueError with OrderParseError
- Classify errors as UNKNOWN_COMMAND or SYNTAX_ERROR
- Provide specific error messages for each scenario

**HumanPlayer._get_orders_continuous()** - Updated error handling:
- Catch OrderParseError instead of ValueError
- Use _format_error_message() to display errors
- Remove redundant "Try again or type 'help'" message

**HumanPlayer._validate_order_pre_queue()** - Enhanced error messages:
- Keep existing validation logic
- Enhance error message templates to match new format
- Return detailed context for insufficient ships error

---

## Section 4: Implementation Details

### 4.1 Changes to command_parser.py

**Location**: `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/command_parser.py`

**Step 1**: Add error classification system (after imports, before CommandParser class)

```python
from enum import Enum


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
```

**Step 2**: Modify CommandParser.parse() method

Replace lines 58-68 with:

```python
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
```

**Step 3**: Enhance pattern parsers with detailed syntax errors

Modify `_parse_move_pattern()` to detect and report specific syntax errors:

```python
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
        if not ship_part.isdigit():
            raise OrderParseError(
                ErrorType.SYNTAX_ERROR,
                f"Invalid ship count: '{ship_part}' is not a number"
            )

        ship_count = int(ship_part)
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
```

**Step 4**: Update `_parse_simple_pattern()` similarly

```python
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
            from_star = match.group(2).upper()
            to_star = match.group(3).upper()
            return Order(from_star=from_star, to_star=to_star, ships=ships)

        # Pattern didn't match - provide specific syntax error
        ship_count = int(parts[0])
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
```

**Note**: `_parse_attack_pattern()` can remain simpler since 'attack' syntax is not the primary pattern. It can return None if pattern doesn't match, and let the final catch-all handle it.

### 4.2 Changes to human_player.py

**Location**: `/Users/robert.bastian/github.com/rbastian/space-conquest/src/interface/human_player.py`

**Step 1**: Update imports (line 7)

```python
from typing import List

from ..models.game import Game
from ..models.order import Order
from .command_parser import CommandParser, OrderParseError, ErrorType
from .display import DisplayManager
from .renderer import MapRenderer
```

**Step 2**: Add error formatting method (after `__init__`, around line 33)

```python
    def _format_error_message(self, error_type: ErrorType, message: str) -> str:
        """Format error message with emoji and optional help.

        Args:
            error_type: Classification of the error
            message: Error message content

        Returns:
            Formatted error message string
        """
        # All errors start with ❌ emoji
        formatted = f"❌ {message}"

        # Only Unknown Command errors show help hint
        if error_type == ErrorType.UNKNOWN_COMMAND:
            formatted += "\n\nAvailable commands: move, done, list, clear, help, status, quit"
            formatted += "\nExample: move 5 ships from A to B"

        return formatted
```

**Step 3**: Update `_get_orders_continuous()` error handling

Replace lines 164-196 with:

```python
                # Try to parse as order
                try:
                    order = self.parser.parse(command)

                    if order is None:
                        # Parser returned None for unrecognized command
                        # This shouldn't happen now with OrderParseError, but keep as fallback
                        print(self._format_error_message(
                            ErrorType.UNKNOWN_COMMAND,
                            f"Unknown command: '{cmd_lower.split()[0] if cmd_lower.split() else cmd_lower}'"
                        ))
                        continue

                    # Pre-validate order before queuing
                    error = self._validate_order_pre_queue(
                        game, player, order, commitment_tracker
                    )

                    if error:
                        # Validation error - no help hint
                        print(self._format_error_message(ErrorType.VALIDATION_ERROR, error))
                        continue

                    # Order is valid - queue it
                    orders.append(order)

                    # Update commitment tracker
                    if order.from_star not in commitment_tracker:
                        commitment_tracker[order.from_star] = 0
                    commitment_tracker[order.from_star] += order.ships

                    # Show success feedback
                    self._show_order_queued(order, orders, commitment_tracker)

                except OrderParseError as e:
                    # Parser raised classified error
                    print(self._format_error_message(e.error_type, e.message))

                except ValueError as e:
                    # Unexpected ValueError (fallback - shouldn't happen)
                    print(self._format_error_message(ErrorType.SYNTAX_ERROR, str(e)))

            except KeyboardInterrupt:
                print("\nInterrupted. Type 'done' to submit queued orders.")
                continue

            except Exception as e:
                # Truly unexpected error
                print(f"❌ Unexpected error: {e}")
```

**Step 4**: Update validation error messages in `_validate_order_pre_queue()`

Replace lines 229-268 with:

```python
        # Check ships > 0
        if order.ships <= 0:
            return f"Invalid ship count: must be positive (got {order.ships})"

        # Check stars exist
        from_star = None
        to_star = None
        for star in game.stars:
            if star.id == order.from_star:
                from_star = star
            if star.id == order.to_star:
                to_star = star

        if from_star is None and to_star is None:
            return f"Stars '{order.from_star}' and '{order.to_star}' do not exist"
        if from_star is None:
            return f"Origin star '{order.from_star}' does not exist"
        if to_star is None:
            return f"Destination star '{order.to_star}' does not exist"

        # Check not same star
        if order.from_star == order.to_star:
            return f"Cannot send fleet from {order.from_star} to itself"

        # Check ownership
        if from_star.owner != player.id:
            return f"You do not control star '{order.from_star}'"

        # Check sufficient ships (accounting for already committed ships)
        available = from_star.stationed_ships.get(player.id, 0)
        already_committed = commitment_tracker.get(order.from_star, 0)
        remaining = available - already_committed

        if order.ships > remaining:
            return (
                f"Insufficient ships at {order.from_star}\n"
                f"Requested: {order.ships}, Available: {available}, "
                f"Already committed: {already_committed}, Remaining: {remaining}"
            )

        return ""  # Valid
```

---

## Section 5: Testing Requirements

### 5.1 Unit Tests

**Test File**: Create `tests/test_error_messages.py`

**Test Cases**:

1. **test_unknown_command_shows_help**
   - Input: "attack A"
   - Verify: Error contains "Unknown command: 'attack'"
   - Verify: Error contains "Available commands:"
   - Verify: Error contains example

2. **test_syntax_error_no_help**
   - Input: "move abc from A to B"
   - Verify: Error contains "Invalid ship count: 'abc' is not a number"
   - Verify: Error does NOT contain "Available commands:"

3. **test_validation_error_no_help**
   - Input: "move 100 from A to B" (A only has 50 ships)
   - Verify: Error contains "Insufficient ships"
   - Verify: Error does NOT contain "Available commands:"

4. **test_zero_ships**
   - Input: "move 0 from A to B"
   - Verify: Error contains "must be positive (got 0)"

5. **test_negative_ships**
   - Input: "move -5 from A to B"
   - Verify: Error contains "must be positive (got -5)"

6. **test_missing_from_keyword**
   - Input: "move 5 ships A to B"
   - Verify: Error contains "expected 'from' after ship count"

7. **test_typo_from_keyword**
   - Input: "move 5 form A to B"
   - Verify: Error contains "did you mean 'from'? Got 'form'"

8. **test_missing_to_keyword**
   - Input: "move 5 from A B"
   - Verify: Error contains "expected 'to' after origin star"

9. **test_missing_origin_star**
   - Input: "move 5 from to B"
   - Verify: Error contains "missing origin star ID after 'from'"

10. **test_missing_destination_star**
    - Input: "move 5 from A to"
    - Verify: Error contains "missing destination star ID after 'to'"

11. **test_nonexistent_origin_star**
    - Input: "move 5 from Z to B"
    - Verify: Error contains "Origin star 'Z' does not exist"

12. **test_nonexistent_destination_star**
    - Input: "move 5 from A to Z"
    - Verify: Error contains "Destination star 'Z' does not exist"

13. **test_same_star_error**
    - Input: "move 5 from A to A"
    - Verify: Error contains "Cannot send fleet from A to itself"

14. **test_not_controlled_star**
    - Input: "move 5 from E to B" (E is enemy-controlled)
    - Verify: Error contains "You do not control star 'E'"

15. **test_insufficient_ships_detail**
    - Input: "move 50 from A to B" (A has 30 ships, 10 committed)
    - Verify: Error contains all values: Requested: 50, Available: 30, Already committed: 10, Remaining: 20

16. **test_all_errors_use_emoji**
    - Verify: All error messages start with ❌ emoji

17. **test_simple_pattern_syntax_errors**
    - Input: "5 form A to B"
    - Verify: Handles typo in simple pattern

### 5.2 Manual Test Scenarios

**Test Scenario 1: New Player Experience**
- Start new game
- Try these commands in sequence:
  1. "help" → Should show help
  2. "attack B" → Should show unknown command with help
  3. "move abc from A to B" → Should show syntax error WITHOUT help
  4. "move 5 from A to B" → Should succeed (assuming valid)

**Test Scenario 2: Common Typos**
- Try: "move 5 form A to B"
- Try: "send 5 from A to B"
- Try: "move 5 ships A B"
- Verify each shows appropriate error without redundant help

**Test Scenario 3: Validation Errors Flow**
- Queue order: "move 5 from A to B"
- Try: "move 100 from A to C" (insufficient ships)
- Verify detailed ship count shown
- Verify no help message
- Try: "move 5 from A to A" (same star)
- Verify clear error without help

**Test Scenario 4: Unknown Command vs Syntax Error**
- Try: "attack A" → Should say "Unknown command"
- Try: "move" → Should say "Syntax error"
- Verify distinction is clear

**Test Scenario 5: Edge Cases**
- Empty input → Silent re-prompt
- Just spaces → Silent re-prompt
- "move -1 from A to B" → Negative ships error
- "move 0 from A to B" → Zero ships error
- "move 5 from Z to B" → Nonexistent star

### 5.3 Regression Tests

Ensure existing functionality still works:

1. **Valid orders still process correctly**
   - "move 5 from A to B"
   - "move 10 ships from C to D"
   - "5 from E to F"

2. **Special commands still work**
   - "done" → Submits orders
   - "list" → Shows queued orders
   - "clear" → Clears orders
   - "help" → Shows help
   - "status" → Shows game state
   - "quit" → Exits game

3. **Commitment tracking still accurate**
   - Queue multiple orders from same star
   - Verify commitment tracker prevents over-commitment
   - Verify error message shows correct remaining ships

4. **Success messages unchanged**
   - ✓ Order queued message
   - Order count and commitment summary

---

## Section 6: Visual Examples

### Example 1: Unknown Command (SHOWS HELP)

**Before:**
```
[Turn 1] [p1] > attack A
Error: Invalid command. Type 'help' for command syntax.
```

**After:**
```
[Turn 1] [p1] > attack A
❌ Unknown command: 'attack'

Available commands: move, done, list, clear, help, status, quit
Example: move 5 ships from A to B
```

---

### Example 2: Syntax Error - Invalid Ship Count (NO HELP)

**Before:**
```
[Turn 1] [p1] > move abc from A to B
Error: Invalid command format. Type 'help' for command syntax.
Try again or type 'help' for command syntax.
```

**After:**
```
[Turn 1] [p1] > move abc from A to B
❌ Invalid ship count: 'abc' is not a number
```

---

### Example 3: Syntax Error - Zero Ships (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 0 from A to B
Error: Invalid command format. Type 'help' for command syntax.
Try again or type 'help' for command syntax.
```

**After:**
```
[Turn 1] [p1] > move 0 from A to B
❌ Invalid ship count: must be positive (got 0)
```

---

### Example 4: Syntax Error - Missing Keyword (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 5 ships A to B
Error: Invalid command format. Type 'help' for command syntax.
Try again or type 'help' for command syntax.
```

**After:**
```
[Turn 1] [p1] > move 5 ships A to B
❌ Syntax error: expected 'from' after ship count
Correct format: move <ships> from <star> to <star>
```

---

### Example 5: Syntax Error - Typo Detection (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 5 form A to B
Error: Invalid command format. Type 'help' for command syntax.
Try again or type 'help' for command syntax.
```

**After:**
```
[Turn 1] [p1] > move 5 form A to B
❌ Syntax error: did you mean 'from'? Got 'form'
Correct format: move <ships> from <star> to <star>
```

---

### Example 6: Validation Error - Nonexistent Star (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 5 from Z to B
Error: Origin star 'Z' does not exist
```

**After:**
```
[Turn 1] [p1] > move 5 from Z to B
❌ Origin star 'Z' does not exist
```

---

### Example 7: Validation Error - Insufficient Ships (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 50 from A to B
Error: Insufficient ships at A: requested 50, available 30, already committed 10, remaining 20
```

**After:**
```
[Turn 1] [p1] > move 50 from A to B
❌ Insufficient ships at A
Requested: 50, Available: 30, Already committed: 10, Remaining: 20
```

---

### Example 8: Validation Error - Same Star (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 5 from A to A
Error: Cannot send fleet from star to itself
```

**After:**
```
[Turn 1] [p1] > move 5 from A to A
❌ Cannot send fleet from A to itself
```

---

### Example 9: Validation Error - Not Controlled (NO HELP)

**Before:**
```
[Turn 1] [p1] > move 5 from E to B
Error: You do not control star 'E'
```

**After:**
```
[Turn 1] [p1] > move 5 from E to B
❌ You do not control star 'E'
```

---

### Example 10: Complete Session Flow

**Before:**
```
[Turn 1] [p1] > attack B
Error: Invalid command. Type 'help' for command syntax.
[Turn 1] [p1] > move abc from A to B
Error: Invalid command format. Type 'help' for command syntax.
Try again or type 'help' for command syntax.
[Turn 1] [p1] > move 100 from A to B
Error: Insufficient ships at A: requested 100, available 30, already committed 0, remaining 30
Try again or type 'help' for command syntax.
[Turn 1] [p1] > move 5 from A to B
✓ Order queued: 5 ships from A to B
  Orders: 1 | Committed: A(5)
```

**After:**
```
[Turn 1] [p1] > attack B
❌ Unknown command: 'attack'

Available commands: move, done, list, clear, help, status, quit
Example: move 5 ships from A to B

[Turn 1] [p1] > move abc from A to B
❌ Invalid ship count: 'abc' is not a number

[Turn 1] [p1] > move 100 from A to B
❌ Insufficient ships at A
Requested: 100, Available: 30, Already committed: 0, Remaining: 30

[Turn 1] [p1] > move 5 from A to B
✓ Order queued: 5 ships from A to B
  Orders: 1 | Committed: A(5)
```

**Key Differences:**
1. Help shown ONLY for unknown command
2. No redundant "Try again or type 'help'" messages
3. Consistent ❌ emoji prefix
4. More structured error messages with better formatting
5. Context-specific error details without overwhelming user

---

## Section 7: Edge Cases

### 7.1 Empty and Whitespace Input
- Empty string: Silent re-prompt (existing behavior maintained)
- Only spaces/tabs: Silent re-prompt
- Multiple spaces between words: Should parse correctly

### 7.2 Case Sensitivity
- "MOVE 5 FROM A TO B" → Should work (already lowercased)
- "Move 5 From a To b" → Should work
- Star IDs should be uppercased consistently (A, not a)

### 7.3 Multiple Errors
- Command with multiple issues: Report FIRST detected error only
- Example: "move abc form Z to A" → Report "Invalid ship count" (caught first)
- Don't overwhelm with multiple error messages per command

### 7.4 Very Long Commands
- Truncate command display if >50 chars in error message
- Example: "Unknown command: 'attackattackattackatta...'"

### 7.5 Special Characters
- "move 5 from A-1 to B-2" → Should handle hyphens if stars have them
- "move 5 from A! to B" → Should handle or reject gracefully
- Non-ASCII characters → Should handle gracefully (might be in star names)

### 7.6 Concurrent Commitment Issues
- Multiple orders exhausting same star
- Ensure commitment tracker accuracy
- Error should show up-to-date committed count

### 7.7 Attack Pattern Edge Case
- "attack" command not fully supported but might be partially parsed
- Should fall back to unknown command or syntax error gracefully

---

## Section 8: Implementation Checklist

### Phase 1: Parser Updates
- [ ] Add ErrorType enum to command_parser.py
- [ ] Add OrderParseError exception to command_parser.py
- [ ] Update CommandParser.parse() to raise OrderParseError
- [ ] Enhance _parse_move_pattern() with detailed syntax errors
- [ ] Enhance _parse_simple_pattern() with detailed syntax errors
- [ ] Update _parse_attack_pattern() (optional, can stay simple)
- [ ] Test parser changes in isolation

### Phase 2: HumanPlayer Updates
- [ ] Update imports to include OrderParseError and ErrorType
- [ ] Add _format_error_message() method
- [ ] Update _get_orders_continuous() error handling
- [ ] Update _validate_order_pre_queue() error messages
- [ ] Remove "Try again or type 'help'" messages
- [ ] Test error display formatting

### Phase 3: Testing
- [ ] Write unit tests for all error types
- [ ] Test unknown command detection
- [ ] Test syntax error classification
- [ ] Test validation error formatting
- [ ] Test help hint display logic
- [ ] Manual testing of all scenarios
- [ ] Regression testing of valid commands

### Phase 4: Documentation & Review
- [ ] Update any user-facing documentation
- [ ] Update help text if needed
- [ ] Code review
- [ ] Playtest with real users
- [ ] Gather feedback on error clarity

---

## Section 9: Acceptance Criteria

This implementation is considered complete when:

1. ✅ **All errors use ❌ emoji** instead of "Error:" text
2. ✅ **Unknown command errors show help hint** with available commands and example
3. ✅ **Syntax errors do NOT show help hint**
4. ✅ **Validation errors do NOT show help hint**
5. ✅ **No "Try again or type 'help'" messages** appear anywhere
6. ✅ **Ship count errors are specific** (invalid vs zero vs negative)
7. ✅ **Keyword errors are specific** (missing from/to, typos detected)
8. ✅ **Validation errors show context** (star IDs, ship counts, etc.)
9. ✅ **Insufficient ships error shows breakdown** (requested, available, committed, remaining)
10. ✅ **All existing functionality works** (valid orders, special commands, commitment tracking)
11. ✅ **All unit tests pass**
12. ✅ **All manual test scenarios pass**
13. ✅ **No regression in existing features**
14. ✅ **Error messages are clear and actionable**
15. ✅ **Help is shown only when appropriate**

---

## Section 10: Migration Notes

### Breaking Changes
- None expected - this is purely a UX improvement
- Error message format changes, but no API changes
- CommandParser raises new exception type, but caught immediately by HumanPlayer

### Backward Compatibility
- All existing valid commands continue to work
- Error handling is internal to HumanPlayer, no external API changes
- Game logic unchanged

### Rollback Plan
If issues arise:
1. Revert command_parser.py changes
2. Revert human_player.py error handling
3. Existing ValueError-based error system will work as before

---

## Appendix A: Error Message Quick Reference

| Error Type | Show Help? | Example Input | Error Message |
|------------|-----------|---------------|---------------|
| Unknown Command | YES | "attack A" | ❌ Unknown command: 'attack'<br><br>Available commands: move, done, list, clear, help, status, quit<br>Example: move 5 ships from A to B |
| Invalid Ship Count (non-numeric) | NO | "move abc from A to B" | ❌ Invalid ship count: 'abc' is not a number |
| Invalid Ship Count (zero) | NO | "move 0 from A to B" | ❌ Invalid ship count: must be positive (got 0) |
| Invalid Ship Count (negative) | NO | "move -5 from A to B" | ❌ Invalid ship count: must be positive (got -5) |
| Missing FROM | NO | "move 5 ships A to B" | ❌ Syntax error: expected 'from' after ship count<br>Correct format: move <ships> from <star> to <star> |
| Typo in FROM | NO | "move 5 form A to B" | ❌ Syntax error: did you mean 'from'? Got 'form'<br>Correct format: move <ships> from <star> to <star> |
| Missing TO | NO | "move 5 from A B" | ❌ Syntax error: expected 'to' after origin star<br>Correct format: move <ships> from <star> to <star> |
| Missing Origin Star | NO | "move 5 from to B" | ❌ Syntax error: missing origin star ID after 'from'<br>Correct format: move <ships> from <star> to <star> |
| Missing Dest Star | NO | "move 5 from A to" | ❌ Syntax error: missing destination star ID after 'to'<br>Correct format: move <ships> from <star> to <star> |
| Origin Not Exist | NO | "move 5 from Z to B" | ❌ Origin star 'Z' does not exist |
| Dest Not Exist | NO | "move 5 from A to Z" | ❌ Destination star 'Z' does not exist |
| Same Star | NO | "move 5 from A to A" | ❌ Cannot send fleet from A to itself |
| Not Controlled | NO | "move 5 from E to B" | ❌ You do not control star 'E' |
| Insufficient Ships | NO | "move 50 from A to B" | ❌ Insufficient ships at A<br>Requested: 50, Available: 30, Already committed: 10, Remaining: 20 |

---

## Appendix B: Implementation Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Parser Updates | Add error classes, enhance pattern parsers | 3-4 hours |
| Phase 2: HumanPlayer Updates | Update error handling, formatting | 2-3 hours |
| Phase 3: Testing | Unit tests, manual testing, regression | 3-4 hours |
| Phase 4: Documentation & Review | Code review, documentation, feedback | 1-2 hours |
| **Total** | | **9-13 hours** |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-21 | Initial specification | game-design-oracle |

---

**END OF SPECIFICATION**
