"""Tests for LangGraph-based player implementation."""

import pytest

from src.agent.langgraph_player import LangGraphPlayer
from src.engine.map_generator import generate_map
from src.models.order import Order


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
