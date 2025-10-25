"""Tests for error message improvements in order submission."""

import pytest

from src.interface.command_parser import CommandParser, OrderParseError, ErrorType
from src.interface.human_player import HumanPlayer
from src.models.game import Game
from src.models.order import Order
from src.models.player import Player
from src.models.star import Star


class TestErrorMessageFormatting:
    """Test error message formatting and classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()
        self.human_player = HumanPlayer("p1")

    def test_unknown_command_shows_help(self):
        """Unknown command should show help hint."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("attack A")

        error = exc_info.value
        assert error.error_type == ErrorType.UNKNOWN_COMMAND
        assert "Unknown command: 'attack'" in error.message

        # Format and verify help is shown
        formatted = self.human_player._format_error_message(error.error_type, error.message)
        assert "❌" in formatted
        assert "Available commands:" in formatted
        assert "Example:" in formatted

    def test_syntax_error_no_help(self):
        """Syntax error should NOT show help hint."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move abc from A to B")

        error = exc_info.value
        assert error.error_type == ErrorType.SYNTAX_ERROR
        assert "Invalid ship count: 'abc' is not a number" in error.message

        # Format and verify NO help shown
        formatted = self.human_player._format_error_message(error.error_type, error.message)
        assert "❌" in formatted
        assert "Available commands:" not in formatted
        assert "Example:" not in formatted

    def test_validation_error_no_help(self):
        """Validation error should NOT show help hint."""
        # Create a simple error message
        error_msg = "Insufficient ships at A\nRequested: 100, Available: 30, Already committed: 10, Remaining: 20"

        formatted = self.human_player._format_error_message(ErrorType.VALIDATION_ERROR, error_msg)
        assert "❌" in formatted
        assert "Insufficient ships" in formatted
        assert "Available commands:" not in formatted

    def test_all_errors_use_emoji(self):
        """All error types should use ❌ emoji."""
        test_cases = [
            (ErrorType.UNKNOWN_COMMAND, "Unknown command: 'test'"),
            (ErrorType.SYNTAX_ERROR, "Invalid ship count"),
            (ErrorType.VALIDATION_ERROR, "Origin star does not exist"),
        ]

        for error_type, message in test_cases:
            formatted = self.human_player._format_error_message(error_type, message)
            assert formatted.startswith("❌"), f"Failed for {error_type}"


class TestUnknownCommandErrors:
    """Test unknown command error detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_attack_command_unknown(self):
        """'attack' command should be unknown."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("attack A")

        assert exc_info.value.error_type == ErrorType.UNKNOWN_COMMAND
        assert "Unknown command: 'attack'" in exc_info.value.message

    def test_send_command_unknown(self):
        """'send' command should be unknown."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("send 5 from A to B")

        assert exc_info.value.error_type == ErrorType.UNKNOWN_COMMAND
        assert "Unknown command: 'send'" in exc_info.value.message


class TestSyntaxErrors:
    """Test syntax error detection and messages."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_zero_ships(self):
        """Zero ships should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 0 from A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "must be positive (got 0)" in exc_info.value.message

    def test_negative_ships(self):
        """Negative ships should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move -5 from A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "must be positive (got -5)" in exc_info.value.message

    def test_non_numeric_ship_count(self):
        """Non-numeric ship count should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move abc from A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "Invalid ship count: 'abc' is not a number" in exc_info.value.message

    def test_missing_from_keyword(self):
        """Missing 'from' keyword should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 5 ships A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "expected 'from' after ship count" in exc_info.value.message

    def test_typo_from_keyword(self):
        """Typo in 'from' keyword should be detected."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 5 form A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "did you mean 'from'? Got 'form'" in exc_info.value.message

    def test_missing_to_keyword(self):
        """Missing 'to' keyword should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 5 from A B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "expected 'to' after origin star" in exc_info.value.message

    def test_missing_origin_star(self):
        """Missing origin star should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 5 from to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "missing origin star ID after 'from'" in exc_info.value.message

    def test_missing_destination_star(self):
        """Missing destination star should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("move 5 from A to")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "missing destination star ID after 'to'" in exc_info.value.message


class TestSimplePatternSyntaxErrors:
    """Test syntax errors in simple pattern (number-first format)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_simple_pattern_typo_from(self):
        """Simple pattern with typo in 'from' should be detected."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("5 form A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "did you mean 'from'? Got 'form'" in exc_info.value.message

    def test_simple_pattern_zero_ships(self):
        """Simple pattern with zero ships should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("0 from A to B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "must be positive (got 0)" in exc_info.value.message

    def test_simple_pattern_missing_to(self):
        """Simple pattern missing 'to' should give specific error."""
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("5 from A B")

        assert exc_info.value.error_type == ErrorType.SYNTAX_ERROR
        assert "expected 'to' after origin star" in exc_info.value.message


class TestValidationErrors:
    """Test validation error messages."""

    def setup_method(self):
        """Set up test fixtures."""
        self.human_player = HumanPlayer("p1")

        # Create a simple game state
        self.game = Game(seed=42, turn=1)
        self.game.stars = [
            Star(id="A", name="Alpha", x=0, y=0, base_ru=4, owner="p1", npc_ships=0),
            Star(id="B", name="Beta", x=9, y=9, base_ru=3, owner="p2", npc_ships=0),
            Star(id="C", name="Gamma", x=5, y=5, base_ru=2, owner="p1", npc_ships=0),
        ]

        # Set up ships at stars
        self.game.stars[0].stationed_ships = {"p1": 30}  # Star A
        self.game.stars[1].stationed_ships = {"p2": 20}  # Star B
        self.game.stars[2].stationed_ships = {"p1": 15}  # Star C

        self.game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        self.player = self.game.players["p1"]
        self.commitment_tracker = {}

    def test_nonexistent_origin_star(self):
        """Nonexistent origin star should give specific error."""
        order = Order(from_star="Z", to_star="B", ships=5)
        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "Origin star 'Z' does not exist" in error

    def test_nonexistent_destination_star(self):
        """Nonexistent destination star should give specific error."""
        order = Order(from_star="A", to_star="Z", ships=5)
        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "Destination star 'Z' does not exist" in error

    def test_same_star_error(self):
        """Same star for origin and destination should give specific error."""
        # The Order model validates this in __post_init__, so we can't create
        # an Order with same from_star and to_star. However, we can test that
        # the validation logic would catch it by creating an order object
        # without calling __post_init__ (using object.__new__)
        order = object.__new__(Order)
        order.from_star = "A"
        order.to_star = "A"
        order.ships = 5

        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "Cannot send fleet from A to itself" in error

    def test_not_controlled_star(self):
        """Not controlling origin star should give specific error."""
        order = Order(from_star="B", to_star="A", ships=5)
        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "You do not control star 'B'" in error

    def test_insufficient_ships_detail(self):
        """Insufficient ships error should show detailed breakdown."""
        # First commit 10 ships from A
        self.commitment_tracker["A"] = 10

        # Try to commit 50 ships when only 20 remain (30 total - 10 committed)
        order = Order(from_star="A", to_star="C", ships=50)
        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "Insufficient ships at A" in error
        assert "Requested: 50" in error
        assert "Available: 30" in error
        assert "Already committed: 10" in error
        assert "Remaining: 20" in error

    def test_both_stars_nonexistent(self):
        """Both stars nonexistent should give specific error."""
        order = Order(from_star="X", to_star="Z", ships=5)
        error = self.human_player._validate_order_pre_queue(
            self.game, self.player, order, self.commitment_tracker
        )

        assert "Stars 'X' and 'Z' do not exist" in error


class TestValidOrdersParsing:
    """Test that valid orders still parse correctly (regression tests)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_valid_move_pattern(self):
        """Valid move pattern should parse correctly."""
        order = self.parser.parse("move 5 from A to B")
        assert order is not None
        assert order.ships == 5
        assert order.from_star == "A"
        assert order.to_star == "B"

    def test_valid_move_with_ships_word(self):
        """Valid move with 'ships' word should parse correctly."""
        order = self.parser.parse("move 10 ships from C to D")
        assert order is not None
        assert order.ships == 10
        assert order.from_star == "C"
        assert order.to_star == "D"

    def test_valid_simple_pattern(self):
        """Valid simple pattern should parse correctly."""
        order = self.parser.parse("5 from E to F")
        assert order is not None
        assert order.ships == 5
        assert order.from_star == "E"
        assert order.to_star == "F"

    def test_special_commands_return_none(self):
        """Special commands should return None."""
        assert self.parser.parse("done") is None
        assert self.parser.parse("list") is None
        assert self.parser.parse("clear") is None
        assert self.parser.parse("pass") is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CommandParser()

    def test_case_insensitivity(self):
        """Commands should be case-insensitive."""
        order1 = self.parser.parse("MOVE 5 FROM A TO B")
        order2 = self.parser.parse("Move 5 From a To b")

        assert order1 is not None
        assert order2 is not None
        assert order1.ships == order2.ships == 5
        assert order1.from_star == order2.from_star == "A"
        assert order1.to_star == order2.to_star == "B"

    def test_extra_whitespace(self):
        """Commands with extra whitespace should parse correctly."""
        order = self.parser.parse("move  5  from  A  to  B")
        assert order is not None
        assert order.ships == 5
        assert order.from_star == "A"
        assert order.to_star == "B"

    def test_negative_ships_simple_pattern(self):
        """Negative ships in simple pattern should give error."""
        # Since "-5" doesn't start with a digit, it's treated as unknown command
        with pytest.raises(OrderParseError) as exc_info:
            self.parser.parse("-5 from A to B")

        assert exc_info.value.error_type == ErrorType.UNKNOWN_COMMAND
        assert "Unknown command: '-5'" in exc_info.value.message
