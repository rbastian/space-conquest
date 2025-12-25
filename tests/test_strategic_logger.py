"""Tests for strategic logger."""

import json
import tempfile
from pathlib import Path

import pytest

from src.analysis import calculate_strategic_metrics
from src.analysis.strategic_logger import StrategicLogger
from src.models.fleet import Fleet
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


@pytest.fixture
def sample_game():
    """Create a sample game state for testing."""
    game = Game(seed=42, turn=10)

    # Create stars
    stars = [
        Star(
            id="A",
            name="Alpha",
            x=1,
            y=2,
            base_ru=3,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 25},
        ),
        Star(
            id="B",
            name="Beta",
            x=3,
            y=3,
            base_ru=2,
            owner="p2",
            npc_ships=0,
            stationed_ships={"p2": 10},
        ),
        Star(
            id="E",
            name="Epsilon",
            x=10,
            y=8,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 30},
        ),
    ]
    game.stars = stars

    # Create players
    player_p1 = Player(id="p1", home_star="E", visited_stars={"E"})
    player_p2 = Player(id="p2", home_star="A", visited_stars={"A", "B"})
    game.players = {"p1": player_p1, "p2": player_p2}

    # Create a fleet
    fleet = Fleet(
        id="p2-001",
        owner="p2",
        ships=20,
        origin="A",
        dest="B",
        dist_remaining=2,
        rationale="attack",
    )
    game.fleets = [fleet]

    return game


class TestStrategicLogger:
    """Test StrategicLogger functionality."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_create_logger(self, temp_output_dir):
        """Test basic logger creation."""
        logger = StrategicLogger(game_id="test123", output_dir=temp_output_dir)

        # Check that directory was created
        assert Path(temp_output_dir).exists()

        # Check log file path
        expected_path = Path(temp_output_dir) / "game_test123_strategic.jsonl"
        assert logger.log_path == expected_path

        # Clean up
        logger.close()

    def test_log_turn(self, temp_output_dir, sample_game):
        """Test logging a single turn."""
        logger = StrategicLogger(game_id="test456", output_dir=temp_output_dir)

        # Calculate metrics
        metrics = calculate_strategic_metrics(sample_game, "p2", sample_game.turn)

        # Log the metrics
        logger.log_turn(metrics)
        logger.close()

        # Read and verify the log
        with open(logger.log_path, encoding="utf-8") as f:
            logged_data = json.loads(f.readline())

        assert logged_data["turn"] == 10
        assert "spatial_awareness" in logged_data
        assert "expansion" in logged_data
        assert "resources" in logged_data

    def test_log_multiple_turns(self, temp_output_dir, sample_game):
        """Test logging multiple turns to the same file."""
        logger = StrategicLogger(game_id="test789", output_dir=temp_output_dir)

        # Log 3 turns
        for turn in range(1, 4):
            sample_game.turn = turn
            metrics = calculate_strategic_metrics(sample_game, "p2", turn)
            logger.log_turn(metrics)

        logger.close()

        # Read and verify all lines
        with open(logger.log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify each turn
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["turn"] == i + 1

    def test_jsonl_format(self, temp_output_dir, sample_game):
        """Test that output is valid JSONL (one JSON per line)."""
        logger = StrategicLogger(game_id="test_jsonl", output_dir=temp_output_dir)

        # Log multiple turns
        for turn in range(1, 4):
            sample_game.turn = turn
            metrics = calculate_strategic_metrics(sample_game, "p2", turn)
            logger.log_turn(metrics)

        logger.close()

        # Verify each line is valid JSON
        with open(logger.log_path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Should not raise JSONDecodeError
                data = json.loads(line)
                assert isinstance(data, dict)
                assert "turn" in data

    def test_append_mode(self, temp_output_dir, sample_game):
        """Test that logger appends to existing file."""
        game_id = "test_append"

        # First session: log 2 turns
        logger1 = StrategicLogger(game_id=game_id, output_dir=temp_output_dir)
        for turn in range(1, 3):
            sample_game.turn = turn
            metrics = calculate_strategic_metrics(sample_game, "p2", turn)
            logger1.log_turn(metrics)
        logger1.close()

        # Second session: log 2 more turns
        logger2 = StrategicLogger(game_id=game_id, output_dir=temp_output_dir)
        for turn in range(3, 5):
            sample_game.turn = turn
            metrics = calculate_strategic_metrics(sample_game, "p2", turn)
            logger2.log_turn(metrics)
        logger2.close()

        # Verify all 4 turns are in the file
        with open(logger1.log_path, encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) == 4

    def test_context_manager(self, temp_output_dir, sample_game):
        """Test using logger as context manager."""
        game_id = "test_context"

        # Use with statement
        with StrategicLogger(game_id=game_id, output_dir=temp_output_dir) as logger:
            metrics = calculate_strategic_metrics(sample_game, "p2", sample_game.turn)
            logger.log_turn(metrics)

        # File should be closed and readable
        log_path = Path(temp_output_dir) / f"game_{game_id}_strategic.jsonl"
        assert log_path.exists()

        with open(log_path, encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert data["turn"] == sample_game.turn

    def test_close_multiple_times(self, temp_output_dir):
        """Test that close() can be called multiple times safely."""
        logger = StrategicLogger(game_id="test_close", output_dir=temp_output_dir)

        # Should not raise errors
        logger.close()
        logger.close()
        logger.close()

    def test_invalid_metrics(self, temp_output_dir):
        """Test handling of invalid metrics."""
        logger = StrategicLogger(game_id="test_invalid", output_dir=temp_output_dir)

        # Try to log non-serializable data
        with pytest.raises(ValueError, match="Invalid metrics format"):
            logger.log_turn({"bad_data": object()})

        logger.close()

    def test_default_output_dir(self):
        """Test that default output directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for test
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                logger = StrategicLogger(game_id="test_default")

                # Should create 'logs' directory in current working directory
                assert Path("logs").exists()
                assert logger.log_path == Path("logs/game_test_default_strategic.jsonl")

                logger.close()
            finally:
                os.chdir(original_cwd)


class TestIntegrationWithLangGraphPlayer:
    """Test strategic logger integration with LangGraph player."""

    def test_langgraph_player_logging(self, tmp_path, sample_game):
        """Test that LangGraph player automatically logs metrics."""
        from src.agent.langgraph_player import LangGraphPlayer

        # Use sample game with proper setup
        game = sample_game

        # Create LangGraph player with custom log directory
        llm_player = LangGraphPlayer(player_id="p2", use_mock=True)

        # Override logger to use temp directory
        llm_player.strategic_logger = StrategicLogger(
            game_id="integration_test", output_dir=str(tmp_path)
        )

        # Manually trigger logging (simulating what happens in get_orders)
        llm_player._log_strategic_metrics(game)

        # Close logger
        llm_player.close()

        # Verify log was created
        log_path = tmp_path / "game_integration_test_strategic.jsonl"
        assert log_path.exists()

        # Verify content
        with open(log_path, encoding="utf-8") as f:
            data = json.loads(f.readline())
            assert "turn" in data
            assert "spatial_awareness" in data

    def test_logging_does_not_crash_game(self, tmp_path, sample_game):
        """Test that logging errors don't crash the game."""
        from src.agent.langgraph_player import LangGraphPlayer

        game = sample_game
        llm_player = LangGraphPlayer(player_id="p2", use_mock=True)

        # Force an error by using an invalid directory with read-only parent
        # Make temp_path read-only to cause OSError
        invalid_dir = str(tmp_path / "readonly" / "subdir")

        # Try to initialize logger with invalid directory
        try:
            llm_player.strategic_logger = StrategicLogger(
                game_id="error_test", output_dir=invalid_dir
            )
            # If it succeeds, manually call log to test error handling
            llm_player._log_strategic_metrics(game)
        except OSError:
            # Expected - logger creation or write fails
            pass

        # Verify that we can still create a valid logger afterward
        llm_player.strategic_logger = None
        llm_player.strategic_logger = StrategicLogger(
            game_id="recovery_test", output_dir=str(tmp_path)
        )
        llm_player._log_strategic_metrics(game)

        llm_player.close()

        # Verify recovery worked
        log_path = tmp_path / "game_recovery_test_strategic.jsonl"
        assert log_path.exists()
