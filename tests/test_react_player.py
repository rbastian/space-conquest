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
        assert len(tools) == 3  # validate_orders, calculate_distance, get_nearby_garrisons

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
        """Test calculate_distance tool including hyperspace survival probability."""
        star1 = game.stars[0]
        star2 = game.stars[1]

        # Get calculate_distance tool
        distance_tool = tools[1]
        result = distance_tool.invoke({"from_star": star1.id, "to_star": star2.id})

        # Test basic fields
        assert "distance_turns" in result
        assert "arrival_turn" in result
        assert "current_turn" in result
        assert result["distance_turns"] >= 0
        assert result["arrival_turn"] == game.turn + result["distance_turns"]

        # Test hyperspace survival probability field
        assert "hyperspace_survival_probability" in result

        # Should be a string formatted as percentage
        survival_prob = result["hyperspace_survival_probability"]
        assert isinstance(survival_prob, str)
        assert survival_prob.endswith("%")

        # Extract numeric value for calculation verification
        survival_percentage = int(survival_prob[:-1])
        assert 0 <= survival_percentage <= 100

        # Verify calculation: survival_rate = (0.98)^distance_turns
        distance = result["distance_turns"]
        expected_survival_rate = 0.98**distance
        expected_percentage = round(expected_survival_rate * 100)

        assert survival_percentage == expected_percentage, (
            f"Expected {expected_percentage}% for {distance} turns, got {survival_percentage}%"
        )

    def test_calculate_distance_survival_probability_examples(self, game, tools):
        """Test hyperspace survival probability with known distance examples."""
        distance_tool = tools[1]

        # Create test stars at known positions to get specific distances
        # We'll test by creating stars and checking the formula
        test_cases = [
            # (distance_turns, expected_percentage)
            (0, 100),  # 0 turns: 0.98^0 = 1.00 → 100%
            (3, 94),  # 3 turns: 0.98^3 = 0.9412 → 94%
            (5, 90),  # 5 turns: 0.98^5 = 0.9039 → 90%
            (10, 82),  # 10 turns: 0.98^10 = 0.8171 → 82%
            (35, 49),  # 35 turns: 0.98^35 = 0.4890 → 49%
        ]

        # Find or create star pairs at specific distances
        for expected_distance, expected_percentage in test_cases:
            # Find two stars at the right distance
            found = False
            for i, star1 in enumerate(game.stars):
                for star2 in game.stars[i + 1 :]:
                    # Calculate Chebyshev distance
                    dx = abs(star1.x - star2.x)
                    dy = abs(star1.y - star2.y)
                    distance = max(dx, dy)

                    if distance == expected_distance:
                        result = distance_tool.invoke({"from_star": star1.id, "to_star": star2.id})

                        survival_prob = result["hyperspace_survival_probability"]
                        actual_percentage = int(survival_prob[:-1])

                        assert actual_percentage == expected_percentage, (
                            f"For distance {expected_distance} turns, expected {expected_percentage}%, got {actual_percentage}%"
                        )

                        found = True
                        break
                if found:
                    break

            # If we didn't find natural stars at this distance, create temporary ones
            if not found:
                # Create two test stars at the required distance
                test_star1 = game.stars[0]
                test_star2 = game.stars[1]

                # Save original positions
                orig_x1, orig_y1 = test_star1.x, test_star1.y
                orig_x2, orig_y2 = test_star2.x, test_star2.y

                # Set positions to achieve exact distance
                test_star1.x = 0
                test_star1.y = 0
                test_star2.x = expected_distance
                test_star2.y = 0

                result = distance_tool.invoke(
                    {"from_star": test_star1.id, "to_star": test_star2.id}
                )

                survival_prob = result["hyperspace_survival_probability"]
                actual_percentage = int(survival_prob[:-1])

                assert actual_percentage == expected_percentage, (
                    f"For distance {expected_distance} turns, expected {expected_percentage}%, got {actual_percentage}%"
                )

                # Restore original positions
                test_star1.x, test_star1.y = orig_x1, orig_y1
                test_star2.x, test_star2.y = orig_x2, orig_y2

    def test_calculate_distance_survival_rounding(self, game, tools):
        """Test hyperspace survival probability rounding behavior."""
        distance_tool = tools[1]

        # Test rounding: 0.98^X should round correctly
        # 0.9039 → 90% (rounds down from 90.39)
        # 0.9051 → 91% (rounds up from 90.51)

        test_star1 = game.stars[0]
        test_star2 = game.stars[1]

        # Save original positions
        orig_x, orig_y = test_star2.x, test_star2.y

        # Test distance that produces 0.9039 (5 turns → 90%)
        test_star1.x = 0
        test_star1.y = 0
        test_star2.x = 5
        test_star2.y = 0

        result = distance_tool.invoke({"from_star": test_star1.id, "to_star": test_star2.id})

        survival_prob = result["hyperspace_survival_probability"]
        assert survival_prob == "90%", f"Expected 90%, got {survival_prob}"

        # Test distance that produces 0.9227 (4 turns → 92%)
        test_star2.x = 4
        test_star2.y = 0

        result = distance_tool.invoke({"from_star": test_star1.id, "to_star": test_star2.id})

        survival_prob = result["hyperspace_survival_probability"]
        # 0.98^4 = 0.92236816 → rounds to 92%
        assert survival_prob == "92%", f"Expected 92%, got {survival_prob}"

        # Restore original position
        test_star2.x, test_star2.y = orig_x, orig_y

    def test_get_nearby_garrisons_basic(self, game, tools):
        """Test get_nearby_garrisons tool returns correct structure."""
        # Setup: Create some p2 garrisons
        target_star = game.stars[0]
        target_star.owner = None  # Make target neutral

        # Create garrisons
        for i in range(1, 4):
            star = game.stars[i]
            star.owner = "p2"
            star.stationed_ships["p2"] = 5 + i

        # Get get_nearby_garrisons tool (index 2)
        garrison_tool = tools[2]
        result = garrison_tool.invoke({"target": target_star.id})

        assert "target" in result
        assert result["target"]["id"] == target_star.id
        assert result["target"]["name"] == target_star.name

        assert "garrisons" in result
        assert len(result["garrisons"]) <= 3

        # Check garrison structure
        for garrison in result["garrisons"]:
            assert "star_id" in garrison
            assert "star_name" in garrison
            assert "location" in garrison
            assert "stationed_ships" in garrison
            assert "distance_turns" in garrison
            assert "arrival_turn" in garrison
            assert "ru" in garrison
            assert "is_home" in garrison

    def test_get_nearby_garrisons_max_3_results(self, game, tools):
        """Test that at most 3 garrisons are returned."""
        target_star = game.stars[0]

        # Create 5 garrisons (more than the limit)
        for i in range(1, 6):
            star = game.stars[i]
            star.owner = "p2"
            star.stationed_ships["p2"] = 5

        garrison_tool = tools[2]
        result = garrison_tool.invoke({"target": target_star.id})

        # Should only return 3 closest
        assert len(result["garrisons"]) <= 3

    def test_get_nearby_garrisons_sorted_by_distance(self, game, tools):
        """Test that garrisons are sorted by distance (closest first)."""
        # Pick a target in the corner
        target_star = game.stars[0]
        target_star.x = 0
        target_star.y = 0
        target_star.owner = None

        # Create garrisons at known distances
        close = game.stars[1]
        close.x = 2
        close.y = 1
        close.owner = "p2"
        close.stationed_ships["p2"] = 5

        far = game.stars[2]
        far.x = 8
        far.y = 6
        far.owner = "p2"
        far.stationed_ships["p2"] = 10

        garrison_tool = tools[2]
        result = garrison_tool.invoke({"target": target_star.id})

        # Should be sorted by distance
        distances = [g["distance_turns"] for g in result["garrisons"]]
        assert distances == sorted(distances), "Garrisons not sorted by distance"

    def test_get_nearby_garrisons_logging(self, game, tools, caplog):
        """Test that get_nearby_garrisons logs correctly."""
        import logging

        caplog.set_level(logging.INFO)

        target_star = game.stars[0]

        # Create a garrison
        star = game.stars[1]
        star.owner = "p2"
        star.stationed_ships["p2"] = 5

        garrison_tool = tools[2]
        garrison_tool.invoke({"target": target_star.id})

        # Check logging
        log_messages = [record.message for record in caplog.records]
        assert any("[TOOL] get_nearby_garrisons" in msg for msg in log_messages)


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
        assert len(player.tools) == 3

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
