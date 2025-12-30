"""Tests for message content parsing helpers."""

from src.agent.message_helpers import (
    extract_anthropic_claude_blocks,
    extract_nova_blocks,
    normalize_content_blocks,
)


class TestExtractAnthropicClaudeBlocks:
    """Tests for extract_anthropic_claude_blocks function."""

    def test_string_content(self):
        """Plain string content returns as-is with no reasoning."""
        text, reasoning = extract_anthropic_claude_blocks("Hello world")
        assert text == "Hello world"
        assert reasoning is None

    def test_empty_string(self):
        """Empty string returns empty text with no reasoning."""
        text, reasoning = extract_anthropic_claude_blocks("")
        assert text == ""
        assert reasoning is None

    def test_text_block_only(self):
        """Single text block extracts correctly."""
        content = [{"type": "text", "text": "This is visible text"}]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "This is visible text"
        assert reasoning is None

    def test_reasoning_block_only(self):
        """Single reasoning block extracts correctly."""
        content = [{"type": "reasoning_content", "reasoning_content": {"text": "Let me think..."}}]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == ""
        assert reasoning == "Let me think..."

    def test_text_and_reasoning(self):
        """Both text and reasoning blocks extract correctly."""
        content = [
            {"type": "reasoning_content", "reasoning_content": {"text": "Analyzing..."}},
            {"type": "text", "text": "The answer is 42"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "The answer is 42"
        assert reasoning == "Analyzing..."

    def test_multiple_text_blocks(self):
        """Multiple text blocks are joined with newlines."""
        content = [
            {"type": "text", "text": "First paragraph"},
            {"type": "text", "text": "Second paragraph"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "First paragraph\nSecond paragraph"
        assert reasoning is None

    def test_multiple_reasoning_blocks(self):
        """Multiple reasoning blocks are joined with newlines."""
        content = [
            {"type": "reasoning_content", "reasoning_content": {"text": "Step 1..."}},
            {"type": "reasoning_content", "reasoning_content": {"text": "Step 2..."}},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == ""
        assert reasoning == "Step 1...\nStep 2..."

    def test_tool_use_ignored(self):
        """Tool use blocks are ignored."""
        content = [
            {"type": "text", "text": "Using calculator"},
            {"type": "tool_use", "name": "calculate", "input": {"x": 5}},
            {"type": "text", "text": "Result ready"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "Using calculator\nResult ready"
        assert reasoning is None

    def test_mixed_blocks(self):
        """Complex message with all block types."""
        content = [
            {"type": "reasoning_content", "reasoning_content": {"text": "Need to calculate"}},
            {"type": "text", "text": "Let me compute that"},
            {"type": "tool_use", "name": "calc", "input": {}},
            {"type": "reasoning_content", "reasoning_content": {"text": "Verified result"}},
            {"type": "text", "text": "The answer is correct"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "Let me compute that\nThe answer is correct"
        assert reasoning == "Need to calculate\nVerified result"

    def test_non_dict_blocks_ignored(self):
        """Non-dict items in list are skipped."""
        content = [
            {"type": "text", "text": "Valid text"},
            "invalid item",
            None,
            {"type": "text", "text": "More text"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "Valid text\nMore text"
        assert reasoning is None

    def test_missing_text_key(self):
        """Blocks missing text key are skipped."""
        content = [
            {"type": "text"},  # Missing text key
            {"type": "text", "text": "Valid"},
        ]
        text, reasoning = extract_anthropic_claude_blocks(content)
        assert text == "Valid"
        assert reasoning is None

    def test_empty_list(self):
        """Empty list returns empty strings."""
        text, reasoning = extract_anthropic_claude_blocks([])
        assert text == ""
        assert reasoning is None

    def test_non_list_non_string(self):
        """Unexpected types are stringified."""
        text, reasoning = extract_anthropic_claude_blocks(42)
        assert text == "42"
        assert reasoning is None


class TestExtractNovaBlocks:
    """Tests for extract_nova_blocks function."""

    def test_same_as_claude(self):
        """Nova uses same format as Claude."""
        content = [
            {"type": "reasoning_content", "reasoning_content": {"text": "Thinking..."}},
            {"type": "text", "text": "Response"},
        ]
        claude_text, claude_reasoning = extract_anthropic_claude_blocks(content)
        nova_text, nova_reasoning = extract_nova_blocks(content)

        assert nova_text == claude_text
        assert nova_reasoning == claude_reasoning


class TestNormalizeContentBlocks:
    """Tests for normalize_content_blocks function."""

    def test_string_wrapped_in_text_block(self):
        """Plain string is wrapped in text block."""
        blocks = normalize_content_blocks("Hello")
        assert blocks == [{"type": "text", "text": "Hello"}]

    def test_empty_string_returns_empty_list(self):
        """Empty string returns empty list."""
        blocks = normalize_content_blocks("")
        assert blocks == []

    def test_structured_blocks_preserved(self):
        """Well-formed content blocks are preserved."""
        content = [
            {"type": "text", "text": "Hello"},
            {"type": "reasoning_content", "reasoning_content": {"text": "Thinking"}},
            {"type": "tool_use", "name": "calc", "input": {}},
        ]
        blocks = normalize_content_blocks(content)
        assert blocks == content

    def test_invalid_blocks_filtered(self):
        """Invalid blocks are filtered out."""
        content = [
            {"type": "text", "text": "Valid"},
            {"type": "unknown_type", "data": "invalid"},  # Unknown type
            {"no_type_key": "invalid"},  # Missing type
            "string item",  # Not a dict
            {"type": "text", "text": "Also valid"},
        ]
        blocks = normalize_content_blocks(content)
        assert len(blocks) == 2
        assert blocks[0] == {"type": "text", "text": "Valid"}
        assert blocks[1] == {"type": "text", "text": "Also valid"}

    def test_non_dict_list_items_skipped(self):
        """Non-dict items in list are skipped."""
        content = [
            {"type": "text", "text": "Valid"},
            None,
            42,
            {"type": "text", "text": "Also valid"},
        ]
        blocks = normalize_content_blocks(content)
        assert len(blocks) == 2

    def test_empty_list_returns_empty_list(self):
        """Empty list returns empty list."""
        blocks = normalize_content_blocks([])
        assert blocks == []

    def test_non_string_non_list_stringified(self):
        """Unexpected types are stringified and wrapped."""
        blocks = normalize_content_blocks(42)
        assert blocks == [{"type": "text", "text": "42"}]

        blocks = normalize_content_blocks(None)
        assert blocks == [{"type": "text", "text": "None"}]
