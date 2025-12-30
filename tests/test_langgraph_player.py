"""Tests for LangGraph-based player implementation."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.agent.langgraph_player import LangGraphPlayer
from src.agent.prompts import get_system_prompt
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

    def test_initialization_with_dependency_injection(self, game):
        """Test LangGraphPlayer with injected dependencies."""
        from src.agent.langgraph_tools import create_langgraph_tools

        # Create mock LLM
        mock_llm = MagicMock()
        mock_llm.model_id = "test-model"

        # Create tools
        tools_instance, tool_defs = create_langgraph_tools(game, "p2")

        # Get system prompt
        system_prompt = get_system_prompt(verbose=False)

        # Inject dependencies
        player = LangGraphPlayer(
            player_id="p2",
            llm=mock_llm,
            game=game,
            tools=tools_instance,
            tool_definitions=tool_defs,
            system_prompt=system_prompt,
            verbose=False,
        )

        # Verify initialization
        assert player.llm is not None
        assert player.client is None  # No wrapper when using raw LLM
        assert player.tools is not None
        assert player.tool_definitions is not None
        assert player.system_prompt is not None
        assert player.player_id == "p2"

    def test_with_mock_llm(self, game):
        """Test with mock LLM for testing."""
        from src.agent.langgraph_tools import create_langgraph_tools

        # Create mock LLM
        mock_llm = MagicMock()
        mock_llm.model_id = "mock-llm"

        # Mock bind_tools to return itself
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        # Mock invoke to return AIMessage with Pass orders
        orders_json = '{"turn": 1, "moves": [], "strategy_notes": "Passing turn"}'
        mock_llm.invoke = MagicMock(return_value=AIMessage(content=orders_json, tool_calls=[]))

        # Create tools
        tools_instance, tool_defs = create_langgraph_tools(game, "p2")

        # Create player with mocked LLM
        player = LangGraphPlayer(
            player_id="p2",
            llm=mock_llm,
            game=game,
            tools=tools_instance,
            tool_definitions=tool_defs,
            system_prompt="Test prompt",
            verbose=False,
        )

        # Verify player is initialized with mock LLM
        assert player.llm is mock_llm
        assert player.client is None

        # Get orders (should use mock LLM)
        orders = player.get_orders(game)
        assert isinstance(orders, list)

    def test_backward_compatibility_with_legacy_constructor(self):
        """Test that old constructor still works (backward compatibility)."""
        # Old pattern: creates client internally
        player = LangGraphPlayer("p2", use_mock=True, verbose=False)

        # Verify old path works
        assert player.player_id == "p2"
        assert player.client is not None  # Client wrapper created
        assert player.llm is None  # No raw LLM

    def test_game_orchestrator_with_dependency_injection(self, game):
        """Test GameOrchestrator can extract model ID with dependency injection."""
        import sys
        from pathlib import Path

        from src.agent.langgraph_tools import create_langgraph_tools
        from src.interface.human_player import HumanPlayer

        # Import GameOrchestrator from game module at root level
        # Add parent directory to path to import game.py
        root_dir = Path(__file__).parent.parent
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from game import GameOrchestrator

        # Create mock LLM with model_id attribute
        mock_llm = MagicMock()
        mock_llm.model_id = "test-model-id-123"

        # Create tools
        tools_instance, tool_defs = create_langgraph_tools(game, "p2")

        # Create player with dependency injection
        p2 = LangGraphPlayer(
            player_id="p2",
            llm=mock_llm,
            game=game,
            tools=tools_instance,
            tool_definitions=tool_defs,
            system_prompt="Test",
            verbose=False,
        )

        # Create orchestrator (this should not crash)
        p1 = HumanPlayer("p1")
        orchestrator = GameOrchestrator(game, p1, p2, use_tui=False)

        # Verify model ID was extracted correctly
        assert orchestrator.game.p2_model_id == "test-model-id-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
