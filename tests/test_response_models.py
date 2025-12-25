"""Tests for LLM response models and helper classes."""

from src.agent.response_models import (
    AgentTurnResult,
    ContentBlock,
    LLMResponse,
    ResponseView,
    ToolCall,
    UsageMetadata,
    _extract_content_blocks,
)


class TestExtractContentBlocks:
    """Test content block extraction."""

    def test_extract_text_only(self):
        """Extract simple text content."""
        blocks: list[ContentBlock] = [{"type": "text", "text": "Hello world"}]

        text, reasoning = _extract_content_blocks(blocks)

        assert text == "Hello world"
        assert reasoning is None

    def test_extract_multiple_text_blocks(self):
        """Concatenate multiple text blocks."""
        blocks: list[ContentBlock] = [
            {"type": "text", "text": "First part"},
            {"type": "text", "text": "Second part"},
        ]

        text, reasoning = _extract_content_blocks(blocks)

        assert text == "First part\nSecond part"
        assert reasoning is None

    def test_extract_reasoning_content(self):
        """Extract extended thinking content."""
        blocks: list[ContentBlock] = [
            {"type": "text", "text": "Visible text"},
            {"type": "reasoning_content", "reasoning_content": {"text": "Internal thinking"}},
        ]

        text, reasoning = _extract_content_blocks(blocks)

        assert text == "Visible text"
        assert reasoning == "Internal thinking"

    def test_ignore_tool_use_blocks(self):
        """Tool use blocks don't appear in visible text."""
        blocks: list[ContentBlock] = [
            {"type": "text", "text": "I'll submit orders"},
            {"type": "tool_use", "id": "tool_123", "name": "submit_orders", "input": {}},
        ]

        text, reasoning = _extract_content_blocks(blocks)

        assert text == "I'll submit orders"
        assert reasoning is None
        assert "tool_use" not in text

    def test_empty_blocks(self):
        """Handle empty block list."""
        blocks: list[ContentBlock] = []

        text, reasoning = _extract_content_blocks(blocks)

        assert text == ""
        assert reasoning is None

    def test_multiple_reasoning_blocks(self):
        """Concatenate multiple reasoning blocks."""
        blocks: list[ContentBlock] = [
            {"type": "reasoning_content", "reasoning_content": {"text": "First thought"}},
            {"type": "reasoning_content", "reasoning_content": {"text": "Second thought"}},
        ]

        text, reasoning = _extract_content_blocks(blocks)

        assert text == ""
        assert reasoning == "First thought\nSecond thought"


class TestResponseView:
    """Test ResponseView class."""

    def test_from_response_text_only(self):
        """Create view from text-only response."""
        response: LLMResponse = {
            "response": "Just text",
            "content_blocks": [{"type": "text", "text": "Just text"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        view = ResponseView.from_response(response)

        assert view.text == "Just text"
        assert view.reasoning is None
        assert view.tool_calls == []
        assert view.stop_reason == "end_turn"
        assert view.usage is None

    def test_from_response_with_tool_calls(self):
        """Create view from response with tool calls."""
        tool_call: ToolCall = {
            "name": "submit_orders",
            "input": {"orders": [{"from": "A", "to": "B", "ships": 5, "rationale": "attack"}]},
        }

        response: LLMResponse = {
            "response": [
                {"type": "text", "text": "I'll attack"},
                {
                    "type": "tool_use",
                    "id": "tool_1",
                    "name": "submit_orders",
                    "input": tool_call["input"],
                },
            ],
            "content_blocks": [
                {"type": "text", "text": "I'll attack"},
                {
                    "type": "tool_use",
                    "id": "tool_1",
                    "name": "submit_orders",
                    "input": tool_call["input"],
                },
            ],
            "tool_calls": [tool_call],
            "stop_reason": "tool_use",
            "requires_tool_execution": True,
            "usage_metadata": None,
        }

        view = ResponseView.from_response(response)

        assert view.text == "I'll attack"
        assert view.has_tool_calls()
        assert len(view.tool_calls) == 1
        assert view.tool_calls[0]["name"] == "submit_orders"

    def test_from_response_with_reasoning(self):
        """Create view from response with extended thinking."""
        response: LLMResponse = {
            "response": [
                {"type": "reasoning_content", "reasoning_content": {"text": "Let me think..."}},
                {"type": "text", "text": "I've decided"},
            ],
            "content_blocks": [
                {"type": "reasoning_content", "reasoning_content": {"text": "Let me think..."}},
                {"type": "text", "text": "I've decided"},
            ],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        view = ResponseView.from_response(response)

        assert view.text == "I've decided"
        assert view.reasoning == "Let me think..."

    def test_from_response_with_usage(self):
        """Create view with token usage metadata."""
        usage: UsageMetadata = {
            "input_tokens": 1000,
            "output_tokens": 200,
            "total_tokens": 1200,
            "cache_read_input_tokens": 500,
            "cache_creation_input_tokens": 0,
        }

        response: LLMResponse = {
            "response": "Text",
            "content_blocks": [{"type": "text", "text": "Text"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": usage,
        }

        view = ResponseView.from_response(response)

        assert view.usage == usage
        assert view.usage["input_tokens"] == 1000
        assert view.usage["cache_read_input_tokens"] == 500

    def test_has_tool_calls(self):
        """Test has_tool_calls method."""
        view_without = ResponseView(
            text="text", reasoning=None, tool_calls=[], stop_reason="end_turn", usage=None
        )

        view_with = ResponseView(
            text="text",
            reasoning=None,
            tool_calls=[{"name": "submit_orders", "input": {}}],
            stop_reason="tool_use",
            usage=None,
        )

        assert not view_without.has_tool_calls()
        assert view_with.has_tool_calls()

    def test_get_tool_names(self):
        """Test get_tool_names method."""
        view = ResponseView(
            text="text",
            reasoning=None,
            tool_calls=[
                {"name": "submit_orders", "input": {}},
                {"name": "get_observation", "input": {}},
            ],
            stop_reason="tool_use",
            usage=None,
        )

        names = view.get_tool_names()

        assert names == ["submit_orders", "get_observation"]

    def test_format_usage_no_data(self):
        """Format usage when no data available."""
        view = ResponseView(
            text="text", reasoning=None, tool_calls=[], stop_reason="end_turn", usage=None
        )

        formatted = view.format_usage()

        assert formatted == "No usage data"

    def test_format_usage_basic(self):
        """Format basic token usage."""
        view = ResponseView(
            text="text",
            reasoning=None,
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 1000, "output_tokens": 200, "total_tokens": 1200},
        )

        formatted = view.format_usage()

        assert "in=1000" in formatted
        assert "out=200" in formatted

    def test_format_usage_with_cache(self):
        """Format usage with cache metrics."""
        view = ResponseView(
            text="text",
            reasoning=None,
            tool_calls=[],
            stop_reason="end_turn",
            usage={
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_read_input_tokens": 800,
                "cache_creation_input_tokens": 100,
            },
        )

        formatted = view.format_usage()

        assert "cache_hit=800" in formatted
        assert "cache_write=100" in formatted

    def test_str_representation(self):
        """Test __str__ returns text."""
        view = ResponseView(
            text="Hello world", reasoning=None, tool_calls=[], stop_reason="end_turn", usage=None
        )

        assert str(view) == "Hello world"

    def test_repr_representation(self):
        """Test __repr__ shows metadata."""
        view = ResponseView(
            text="text",
            reasoning=None,
            tool_calls=[{"name": "submit_orders", "input": {}}],
            stop_reason="tool_use",
            usage={"input_tokens": 100, "output_tokens": 50},
        )

        repr_str = repr(view)

        assert "submit_orders" in repr_str
        assert "tools=" in repr_str


class TestAgentTurnResult:
    """Test AgentTurnResult class."""

    def test_initialization(self):
        """Create basic turn result."""
        result = AgentTurnResult(responses=[], final_orders=None, error=None)

        assert result.responses == []
        assert result.final_orders is None
        assert result.error is None

    def test_all_responses(self):
        """Iterate all responses."""
        response1: LLMResponse = {
            "response": "First",
            "content_blocks": [{"type": "text", "text": "First"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        response2: LLMResponse = {
            "response": "Second",
            "content_blocks": [{"type": "text", "text": "Second"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response1, response2], final_orders=None, error=None)

        responses = list(result.all_responses())

        assert len(responses) == 2
        assert responses[0] == response1
        assert responses[1] == response2

    def test_response_views(self):
        """Get ResponseView for each response."""
        response: LLMResponse = {
            "response": "Text",
            "content_blocks": [{"type": "text", "text": "Text"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response], final_orders=None, error=None)

        views = list(result.response_views())

        assert len(views) == 1
        assert isinstance(views[0], ResponseView)
        assert views[0].text == "Text"

    def test_final_response(self):
        """Get last response in turn."""
        response1: LLMResponse = {
            "response": "First",
            "content_blocks": [{"type": "text", "text": "First"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        response2: LLMResponse = {
            "response": "Last",
            "content_blocks": [{"type": "text", "text": "Last"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response1, response2], final_orders=None, error=None)

        final = result.final_response()

        assert final == response2

    def test_final_response_empty(self):
        """Final response when no responses."""
        result = AgentTurnResult(responses=[], final_orders=None, error=None)

        assert result.final_response() is None

    def test_final_view(self):
        """Get ResponseView of final response."""
        response: LLMResponse = {
            "response": "Final text",
            "content_blocks": [{"type": "text", "text": "Final text"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response], final_orders=None, error=None)

        view = result.final_view()

        assert view is not None
        assert view.text == "Final text"

    def test_all_tool_calls(self):
        """Get all tool calls across responses."""
        response1: LLMResponse = {
            "response": "First",
            "content_blocks": [],
            "tool_calls": [{"name": "tool1", "input": {}}],
            "stop_reason": "tool_use",
            "requires_tool_execution": True,
            "usage_metadata": None,
        }

        response2: LLMResponse = {
            "response": "Second",
            "content_blocks": [],
            "tool_calls": [{"name": "tool2", "input": {}}, {"name": "tool3", "input": {}}],
            "stop_reason": "tool_use",
            "requires_tool_execution": True,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response1, response2], final_orders=None, error=None)

        all_calls = result.all_tool_calls()

        assert len(all_calls) == 3
        assert all_calls[0]["name"] == "tool1"
        assert all_calls[1]["name"] == "tool2"
        assert all_calls[2]["name"] == "tool3"

    def test_total_tokens(self):
        """Sum tokens across all responses."""
        response1: LLMResponse = {
            "response": "First",
            "content_blocks": [],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        }

        response2: LLMResponse = {
            "response": "Second",
            "content_blocks": [],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
        }

        result = AgentTurnResult(responses=[response1, response2], final_orders=None, error=None)

        total = result.total_tokens()

        assert total == 450  # 150 + 300

    def test_total_tokens_no_usage(self):
        """Total tokens when no usage data."""
        response: LLMResponse = {
            "response": "Text",
            "content_blocks": [],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response], final_orders=None, error=None)

        assert result.total_tokens() == 0

    def test_last_reasoning(self):
        """Get most recent reasoning content."""
        response1: LLMResponse = {
            "response": "First",
            "content_blocks": [
                {"type": "reasoning_content", "reasoning_content": {"text": "Early thinking"}}
            ],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        response2: LLMResponse = {
            "response": "Second",
            "content_blocks": [
                {"type": "reasoning_content", "reasoning_content": {"text": "Later thinking"}}
            ],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response1, response2], final_orders=None, error=None)

        reasoning = result.last_reasoning()

        assert reasoning == "Later thinking"

    def test_last_reasoning_none(self):
        """Last reasoning when no reasoning exists."""
        response: LLMResponse = {
            "response": "Text only",
            "content_blocks": [{"type": "text", "text": "Text only"}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
            "usage_metadata": None,
        }

        result = AgentTurnResult(responses=[response], final_orders=None, error=None)

        assert result.last_reasoning() is None

    def test_succeeded(self):
        """Check if turn succeeded."""
        success_result = AgentTurnResult(
            responses=[],
            final_orders=[{"from": "A", "to": "B", "ships": 5, "rationale": "attack"}],
            error=None,
        )

        fail_result = AgentTurnResult(responses=[], final_orders=None, error="Something went wrong")

        assert success_result.succeeded()
        assert not fail_result.succeeded()

    def test_failed(self):
        """Check if turn failed."""
        success_result = AgentTurnResult(responses=[], final_orders=[], error=None)

        fail_result = AgentTurnResult(responses=[], final_orders=None, error="Error message")

        assert not success_result.failed()
        assert fail_result.failed()

    def test_with_final_orders(self):
        """Turn result with submitted orders."""
        orders = [
            {"from": "D", "to": "G", "ships": 2, "rationale": "expand"},
            {"from": "D", "to": "I", "ships": 1, "rationale": "probe"},
        ]

        result = AgentTurnResult(responses=[], final_orders=orders, error=None)

        assert result.final_orders == orders
        assert len(result.final_orders) == 2
        assert result.succeeded()
