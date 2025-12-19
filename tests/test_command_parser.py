"""Tests for natural language command parser."""

import pytest

from src.interface.command_parser import CommandParser


def test_parse_move_pattern():
    """Test parsing 'move X ships from Y to Z' pattern."""
    parser = CommandParser()

    order = parser.parse("move 5 ships from A to B")
    assert order is not None
    assert order.from_star == "A"
    assert order.to_star == "B"
    assert order.ships == 5


def test_parse_move_pattern_without_ships():
    """Test parsing 'move X from Y to Z' pattern."""
    parser = CommandParser()

    order = parser.parse("move 10 from C to D")
    assert order is not None
    assert order.from_star == "C"
    assert order.to_star == "D"
    assert order.ships == 10


def test_parse_send_pattern_removed():
    """Test that 'send' command is no longer supported."""
    from src.interface.command_parser import ErrorType, OrderParseError

    parser = CommandParser()

    # 'send' command should now raise an error
    with pytest.raises(OrderParseError) as exc_info:
        parser.parse("send 3 from E to F")
    assert exc_info.value.error_type == ErrorType.UNKNOWN_COMMAND


def test_parse_attack_pattern():
    """Test parsing 'attack X with Y from Z' pattern."""
    parser = CommandParser()

    order = parser.parse("attack D with 8 from A")
    assert order is not None
    assert order.from_star == "A"
    assert order.to_star == "D"
    assert order.ships == 8


def test_parse_simple_pattern():
    """Test parsing 'X from Y to Z' pattern."""
    parser = CommandParser()

    order = parser.parse("15 from I to J")
    assert order is not None
    assert order.from_star == "I"
    assert order.to_star == "J"
    assert order.ships == 15


def test_parse_case_insensitive():
    """Test that parsing is case insensitive."""
    parser = CommandParser()

    order = parser.parse("MOVE 5 FROM a TO b")
    assert order is not None
    assert order.from_star == "A"
    assert order.to_star == "B"
    assert order.ships == 5


def test_parse_pass_command():
    """Test that 'pass' returns None."""
    parser = CommandParser()

    order = parser.parse("pass")
    assert order is None


def test_parse_done_command():
    """Test that 'done' returns None."""
    parser = CommandParser()

    order = parser.parse("done")
    assert order is None


def test_parse_help_command():
    """Test that 'help' raises special ValueError."""
    parser = CommandParser()

    with pytest.raises(ValueError, match="HELP"):
        parser.parse("help")


def test_parse_status_command():
    """Test that 'status' raises special ValueError."""
    parser = CommandParser()

    with pytest.raises(ValueError, match="STATUS"):
        parser.parse("status")


def test_parse_quit_command():
    """Test that 'quit' raises special ValueError."""
    parser = CommandParser()

    with pytest.raises(ValueError, match="QUIT"):
        parser.parse("quit")


def test_parse_quit_aliases():
    """Test that 'exit' and 'q' are recognized as quit commands."""
    parser = CommandParser()

    with pytest.raises(ValueError, match="QUIT"):
        parser.parse("exit")

    with pytest.raises(ValueError, match="QUIT"):
        parser.parse("q")


def test_parse_invalid_command():
    """Test that invalid command raises OrderParseError."""
    from src.interface.command_parser import ErrorType, OrderParseError

    parser = CommandParser()

    with pytest.raises(OrderParseError) as exc_info:
        parser.parse("this is not a valid command")
    assert exc_info.value.error_type == ErrorType.UNKNOWN_COMMAND


def test_parse_multi_digit_numbers():
    """Test parsing commands with multi-digit numbers."""
    parser = CommandParser()

    order = parser.parse("move 123 from K to L")
    assert order is not None
    assert order.ships == 123


def test_parse_lowercase_star_ids():
    """Test that star IDs are converted to uppercase."""
    parser = CommandParser()

    order = parser.parse("move 5 from abc to xyz")
    assert order is not None
    assert order.from_star == "ABC"
    assert order.to_star == "XYZ"
