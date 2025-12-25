"""Tests for LangGraph-based player implementation."""

import pytest

from src.agent.langgraph_player import LangGraphPlayer
from src.agent.middleware import (
    assess_threat_level,
    filter_tools_by_game_state,
    update_game_context_from_observation,
)
from src.agent.prompts import get_system_prompt
from src.agent.state_models import AgentState, GameContext
from src.engine.map_generator import generate_map
from src.models.order import Order


class TestMiddleware:
    """Test middleware functions."""

    def test_assess_threat_level_critical(self):
        """Test critical threat assessment."""
        context: GameContext = {
            "turn": 10,
            "game_phase": "mid",
            "threat_level": "low",
            "controlled_stars_count": 3,
            "total_production": 8,
            "total_ships": 20,
            "enemy_stars_known": 2,
            "nearest_enemy_distance": 2,
            "home_garrison": 10,
            "orders_submitted": False,
        }

        threat = assess_threat_level(context)
        assert threat == "critical"

    def test_assess_threat_level_high(self):
        """Test high threat assessment."""
        context: GameContext = {
            "turn": 10,
            "game_phase": "mid",
            "threat_level": "low",
            "controlled_stars_count": 3,
            "total_production": 8,
            "total_ships": 20,
            "enemy_stars_known": 2,
            "nearest_enemy_distance": 4,
            "home_garrison": 10,
            "orders_submitted": False,
        }

        threat = assess_threat_level(context)
        assert threat == "high"

    def test_assess_threat_level_medium(self):
        """Test medium threat assessment."""
        context: GameContext = {
            "turn": 10,
            "game_phase": "mid",
            "threat_level": "low",
            "controlled_stars_count": 3,
            "total_production": 8,
            "total_ships": 20,
            "enemy_stars_known": 2,
            "nearest_enemy_distance": 6,
            "home_garrison": 10,
            "orders_submitted": False,
        }

        threat = assess_threat_level(context)
        assert threat == "medium"

    def test_assess_threat_level_low(self):
        """Test low threat assessment."""
        context: GameContext = {
            "turn": 10,
            "game_phase": "mid",
            "threat_level": "low",
            "controlled_stars_count": 3,
            "total_production": 8,
            "total_ships": 20,
            "enemy_stars_known": 0,
            "nearest_enemy_distance": None,
            "home_garrison": 10,
            "orders_submitted": False,
        }

        threat = assess_threat_level(context)
        assert threat == "low"

    def test_filter_tools_simplified_architecture(self):
        """Test tool filtering in simplified architecture (only submit_orders)."""
        context: GameContext = {
            "turn": 1,
            "game_phase": "early",
            "threat_level": "low",
            "controlled_stars_count": 1,
            "total_production": 4,
            "total_ships": 4,
            "enemy_stars_known": 0,
            "nearest_enemy_distance": None,
            "home_garrison": 4,
            "orders_submitted": False,
        }

        state: AgentState = {
            "messages": [],
            "game_context": context,
            "available_tools": [],
            "error_count": 0,
            "last_error": None,
        }

        tools = filter_tools_by_game_state(state)

        # Simplified architecture: only submit_orders tool exists
        assert "submit_orders" in tools
        assert len(tools) == 1

    def test_update_game_context_from_observation(self):
        """Test extracting game context from observation."""
        observation = {
            "turn": 5,
            "strategic_dashboard": {
                "controlled_stars_count": 3,
                "total_production_per_turn": 8,
                "total_ships": 25,
            },
            "stars": [
                {
                    "id": "A",
                    "is_home": True,
                    "stationed_ships": 12,
                    "owner": "p2",
                    "distance_from_home": 0,
                },
                {
                    "id": "B",
                    "is_home": False,
                    "stationed_ships": 5,
                    "owner": "p2",
                    "distance_from_home": 3,
                },
                {
                    "id": "C",
                    "is_home": False,
                    "owner": "p1",  # Enemy star
                    "distance_from_home": 4,
                },
            ],
        }

        context = update_game_context_from_observation(observation, 5, "A")

        assert context["turn"] == 5
        assert context["game_phase"] == "mid"  # Enemy found at distance 4 = mid game
        assert context["controlled_stars_count"] == 3
        assert context["total_production"] == 8
        assert context["total_ships"] == 25
        assert context["home_garrison"] == 12
        assert context["enemy_stars_known"] == 1
        assert context["nearest_enemy_distance"] == 4
        assert context["threat_level"] == "high"  # Enemy at distance 4


class TestDynamicPrompts:
    """Test dynamic system prompt generation."""

    def test_system_prompt_early_game(self):
        """Test early game prompt includes phase information."""
        prompt = get_system_prompt(game_phase="early", threat_level="low")

        assert "Early game" in prompt
        assert "No enemy contact detected yet" in prompt

    def test_system_prompt_mid_game(self):
        """Test mid game prompt includes phase information."""
        prompt = get_system_prompt(game_phase="mid", threat_level="medium")

        assert "Mid game" in prompt
        assert "Enemy territory located" in prompt

    def test_system_prompt_late_game(self):
        """Test late game prompt includes phase information."""
        prompt = get_system_prompt(game_phase="late", threat_level="high")

        assert "Late game" in prompt
        assert "Enemy within 3 parsecs" in prompt

    def test_system_prompt_critical_threat(self):
        """Test critical threat prompt includes threat information."""
        prompt = get_system_prompt(game_phase="mid", threat_level="critical")

        assert "Enemy detected within 2 parsecs" in prompt
        assert "INSTANT GAME OVER" in prompt  # This is in victory conditions

    def test_system_prompt_early_game_provides_guidance(self):
        """Test early game prompt includes situational context."""
        prompt = get_system_prompt(game_phase="early", threat_level="low")

        assert "Early game" in prompt
        assert "Enemy location unknown or distant" in prompt

    def test_system_prompt_no_context(self):
        """Test prompt without context still works."""
        prompt = get_system_prompt()

        # Should contain base instructions
        assert "Space Conquest" in prompt
        assert "Player 2" in prompt
        # Should not contain context-specific sections
        assert "CURRENT SITUATION ANALYSIS" not in prompt


class TestLangGraphPlayer:
    """Test LangGraph player implementation."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def player(self):
        """Create LangGraphPlayer with mock client."""
        return LangGraphPlayer("p2", use_mock=True, verbose=False)

    def test_initialization(self, player):
        """Test LangGraphPlayer initializes correctly."""
        assert player.player_id == "p2"
        assert player.graph is not None

    def test_get_orders_returns_list(self, player, game):
        """Test that get_orders returns a list."""
        orders = player.get_orders(game)
        assert isinstance(orders, list)

    def test_get_orders_valid_orders(self, player, game):
        """Test that get_orders returns valid Order objects."""
        orders = player.get_orders(game)

        for order in orders:
            assert isinstance(order, Order)
            if order.ships > 0:  # Only check if ships are being sent
                assert order.from_star != order.to_star

    def test_graph_structure(self, player):
        """Test that graph has correct structure."""
        # Graph should have nodes
        assert player.graph is not None

        # Graph should execute without errors (with mock client)
        # Note: We can't easily test full execution without a real game state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
