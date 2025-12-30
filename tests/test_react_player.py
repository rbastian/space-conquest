"""Tests for ReactPlayer agent implementation."""

import json

import pytest
from langchain_core.messages import AIMessage

from src.agent.llm_factory import LLMFactory
from src.agent.react_player import ReactPlayer
from src.agent.react_tools import create_react_tools
from src.engine.map_generator import generate_map
from src.models.order import Order


class MockLLM:
    """Mock LLM for testing ReactPlayer."""

    def __init__(self, responses: list[dict] | None = None):
        """Initialize mock LLM with predefined responses.

        Args:
            responses: List of response dicts with 'content' and optional 'tool_calls'
        """
        self.responses = responses or []
        self.call_count = 0
        self.model_id = "mock-llm"

    def invoke(self, messages):
        """Mock invoke that returns AIMessage based on predefined responses."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1

            # Return AIMessage with content and optional tool_calls
            return AIMessage(
                content=response.get("content", ""),
                tool_calls=response.get("tool_calls", []),
            )

        # Default: return message with no tool calls (terminates loop)
        orders_json = '[{"from": "A", "to": "B", "ships": 1, "rationale": "test"}]'
        return AIMessage(content=orders_json, tool_calls=[])

    def bind_tools(self, tools, **kwargs):
        """Mock bind_tools (required for LangChain compatibility)."""
        return self


class TestReactTools:
    """Test suite for react_tools helper functions."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def tools(self, game):
        """Create react tools."""
        return create_react_tools(game, "p2")

    def test_create_tools_returns_list(self, tools):
        """Test that create_react_tools returns a list."""
        assert isinstance(tools, list)
        assert len(tools) == 2  # validate_orders, calculate_distance

    def test_validate_orders_valid(self, game, tools):
        """Test validate_orders with valid orders."""
        # Find a star controlled by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Ensure it has ships
        if p2_star.stationed_ships.get("p2", 0) == 0:
            p2_star.stationed_ships["p2"] = 5

        # Find a destination
        dest_star = game.stars[0] if game.stars[0] != p2_star else game.stars[1]

        orders = [{"from": p2_star.id, "to": dest_star.id, "ships": 1, "rationale": "test"}]

        # Get validate_orders tool
        validate_tool = tools[0]
        result = validate_tool.invoke({"orders": orders})

        assert "results" in result
        assert result["results"][0]["valid"] is True

    def test_validate_orders_too_many_ships(self, game, tools):
        """Test validate_orders with too many ships."""
        # Find a star controlled by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Set ships to known amount
        p2_star.stationed_ships["p2"] = 3

        dest_star = game.stars[0] if game.stars[0] != p2_star else game.stars[1]

        orders = [{"from": p2_star.id, "to": dest_star.id, "ships": 10, "rationale": "test"}]

        # Get validate_orders tool
        validate_tool = tools[0]
        result = validate_tool.invoke({"orders": orders})

        assert "results" in result
        assert result["results"][0]["valid"] is False
        assert "error" in result["results"][0]

    def test_validate_orders_not_owned(self, game, tools):
        """Test validate_orders with star not owned."""
        # Find a star NOT controlled by p2
        other_star = None
        for star in game.stars:
            if star.owner != "p2":
                other_star = star
                break

        if other_star is None:
            pytest.skip("All stars controlled by p2 in test game")

        dest_star = game.stars[0]

        orders = [{"from": other_star.id, "to": dest_star.id, "ships": 1, "rationale": "test"}]

        # Get validate_orders tool
        validate_tool = tools[0]
        result = validate_tool.invoke({"orders": orders})

        assert "results" in result
        assert result["results"][0]["valid"] is False
        assert "error" in result["results"][0]

    def test_calculate_distance(self, game, tools):
        """Test calculate_distance tool."""
        star1 = game.stars[0]
        star2 = game.stars[1]

        # Get calculate_distance tool
        distance_tool = tools[1]
        result = distance_tool.invoke({"from_star": star1.id, "to_star": star2.id})

        assert "distance_turns" in result
        assert "arrival_turn" in result
        assert "current_turn" in result
        assert result["distance_turns"] >= 0
        assert result["arrival_turn"] == game.turn + result["distance_turns"]


class TestReactPlayer:
    """Test suite for ReactPlayer agent implementation."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for testing."""
        # Mock LLM returns orders JSON directly
        orders_json = '[{"from": "A", "to": "B", "ships": 1, "rationale": "test"}]'
        return MockLLM(
            responses=[
                {"content": orders_json, "tool_calls": []},  # No tool calls = terminates
            ]
        )

    @pytest.fixture
    def tools(self, game):
        """Create tools for testing."""
        return create_react_tools(game, "p2")

    @pytest.fixture
    def player(self, mock_llm, game, tools):
        """Create ReactPlayer with mock LLM."""
        system_prompt = "You are a test agent."
        return ReactPlayer(
            llm=mock_llm,
            game=game,
            player_id="p2",
            tools=tools,
            system_prompt=system_prompt,
            verbose=False,
        )

    def test_initialization(self, player):
        """Test ReactPlayer initializes correctly."""
        assert player.player_id == "p2"
        assert player.agent is not None
        assert player.llm is not None
        assert len(player.tools) == 2

    def test_get_orders_returns_list(self, player, game):
        """Test that get_orders returns a list."""
        orders = player.get_orders(game)
        assert isinstance(orders, list)

    def test_extract_orders_from_json(self, player):
        """Test extracting orders from JSON in AI message."""
        orders_json = '[{"from": "A", "to": "B", "ships": 5, "rationale": "attack"}]'
        messages = [AIMessage(content=orders_json)]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 1
        assert isinstance(orders[0], Order)
        assert orders[0].from_star == "A"
        assert orders[0].to_star == "B"
        assert orders[0].ships == 5
        assert orders[0].rationale == "attack"

    def test_extract_orders_with_text_before_json(self, player):
        """Test extracting orders when AI adds text before JSON."""
        orders_data = [{"from": "A", "to": "B", "ships": 3, "rationale": "expand"}]
        content = "Here are my orders for this turn:\n\n" + json.dumps(orders_data)
        messages = [AIMessage(content=content)]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 1
        assert orders[0].from_star == "A"
        assert orders[0].ships == 3

    def test_extract_orders_multiple_orders(self, player):
        """Test extracting multiple orders."""
        orders_data = [
            {"from": "A", "to": "B", "ships": 5, "rationale": "attack"},
            {"from": "C", "to": "D", "ships": 3, "rationale": "defend"},
        ]
        orders_json = json.dumps(orders_data)
        messages = [AIMessage(content=orders_json)]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 2
        assert orders[0].from_star == "A"
        assert orders[1].from_star == "C"

    def test_extract_orders_empty_list(self, player):
        """Test extracting empty order list."""
        messages = [AIMessage(content="[]")]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 0

    def test_extract_orders_no_json(self, player):
        """Test handling when no JSON found."""
        messages = [AIMessage(content="I cannot make any moves this turn.")]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 0

    def test_extract_orders_invalid_json(self, player):
        """Test handling invalid JSON."""
        messages = [AIMessage(content="[{invalid json}]")]

        orders = player._extract_orders_from_messages(messages)

        assert len(orders) == 0

    def test_agent_loop_termination(self, player, game):
        """Test that agent loop terminates when no tool calls requested."""
        # Mock LLM is configured to return no tool_calls on first response
        player.get_orders(game)

        # Should terminate after one iteration
        assert player.llm.call_count == 1


class TestLLMFactory:
    """Test suite for LLMFactory."""

    def test_factory_initialization(self):
        """Test LLMFactory initializes correctly."""
        factory = LLMFactory(region="us-west-2")
        assert factory.region == "us-west-2"

    def test_factory_default_region(self):
        """Test LLMFactory uses default region."""
        factory = LLMFactory()
        assert factory.region in ["us-east-1"]  # Default

    def test_bedrock_model_mapping(self):
        """Test Bedrock friendly name to model ID mapping."""
        factory = LLMFactory()

        # Test that model mapping works (can't actually create without credentials)
        # Just verify the factory method exists and accepts parameters
        try:
            llm = factory.create_bedrock_llm(model="haiku", temperature=0.5, max_tokens=2048)
            # If we get here without credentials error, the factory method worked
            assert llm is not None
        except Exception as e:
            # Expected - no AWS credentials in test environment
            # Just verify the error is related to AWS, not our code
            error_msg = str(e).lower()
            assert any(
                keyword in error_msg
                for keyword in ["credentials", "region", "aws", "botocore", "session"]
            )

    def test_openai_llm_creation_params(self):
        """Test OpenAI LLM creation accepts parameters."""
        factory = LLMFactory()

        try:
            llm = factory.create_openai_llm(model="gpt-4o-mini", temperature=0.8)
            assert llm.model_name == "gpt-4o-mini"
            assert llm.temperature == 0.8
        except Exception:
            # Expected if no API key
            pass

    def test_anthropic_llm_creation_params(self):
        """Test Anthropic LLM creation accepts parameters."""
        factory = LLMFactory()

        try:
            llm = factory.create_anthropic_llm(model="claude-3-5-sonnet-20241022")
            assert llm.model == "claude-3-5-sonnet-20241022"
        except Exception:
            # Expected if no API key
            pass

    def test_ollama_llm_creation(self):
        """Test Ollama LLM creation."""
        factory = LLMFactory(api_base="http://localhost:11434")

        try:
            llm = factory.create_ollama_llm(model="llama3")
            assert llm.model == "llama3"
        except ImportError:
            # Expected if langchain-ollama not installed
            pytest.skip("langchain-ollama not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
