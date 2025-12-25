"""Response models for LLM agent interactions.

Provides type-safe response structures and helper classes for
extracting information from LLM responses.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

# ========== TypedDict Definitions ==========


class ContentBlock(TypedDict, total=False):
    """A single content block in the LLM response.

    Can be one of:
    - Text block: {"type": "text", "text": "..."}
    - Tool use block: {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
    - Reasoning block: {"type": "reasoning_content", "reasoning_content": {"text": "..."}}
    """

    type: Literal["text", "tool_use", "reasoning_content"]
    text: str  # For text blocks
    id: str  # For tool_use blocks
    name: str  # For tool_use blocks
    input: dict[str, Any]  # For tool_use blocks
    reasoning_content: dict[str, str]  # For reasoning blocks


class ToolCall(TypedDict):
    """Extracted tool call information."""

    name: str
    input: dict[str, Any]


class UsageMetadata(TypedDict, total=False):
    """Token usage metadata from LLM response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cache_read_input_tokens: int  # Prompt cache hits
    cache_creation_input_tokens: int  # Prompt cache writes


class LLMResponse(TypedDict):
    """Raw LLM response structure.

    This is the structure returned by langchain_client.invoke().
    """

    response: str | list[ContentBlock]  # Text string OR list of content blocks
    content_blocks: list[ContentBlock]  # Always present
    tool_calls: list[ToolCall]  # Extracted tool calls
    stop_reason: Literal["tool_use", "end_turn", "max_tokens"]
    requires_tool_execution: bool
    usage_metadata: UsageMetadata | None  # Optional usage stats


# ========== Helper Classes ==========


@dataclass
class ResponseView:
    """Extracted view of a single LLM response.

    Similar to AIMessageView from experimental repo, but for our response structure.
    """

    text: str  # Visible text (excludes tool_use blocks)
    reasoning: str | None  # Extended thinking content (if present)
    tool_calls: list[ToolCall]  # Tools the LLM wants to use
    stop_reason: str
    usage: UsageMetadata | None

    @classmethod
    def from_response(cls, response: LLMResponse) -> "ResponseView":
        """Extract a view from raw LLM response.

        Args:
            response: Raw LLM response dict

        Returns:
            ResponseView with extracted information
        """
        # Extract text and reasoning from content blocks
        text, reasoning = _extract_content_blocks(response["content_blocks"])

        return cls(
            text=text,
            reasoning=reasoning,
            tool_calls=response.get("tool_calls", []),
            stop_reason=response.get("stop_reason", "unknown"),
            usage=response.get("usage_metadata"),
        )

    def has_tool_calls(self) -> bool:
        """Check if response includes tool calls."""
        return len(self.tool_calls) > 0

    def get_tool_names(self) -> list[str]:
        """Get names of all tools called."""
        return [tc["name"] for tc in self.tool_calls]

    def format_usage(self) -> str:
        """Format usage metadata as string."""
        if not self.usage:
            return "No usage data"

        parts = []
        if "input_tokens" in self.usage:
            parts.append(f"in={self.usage['input_tokens']}")
        if "output_tokens" in self.usage:
            parts.append(f"out={self.usage['output_tokens']}")
        if "cache_read_input_tokens" in self.usage and self.usage["cache_read_input_tokens"] > 0:
            parts.append(f"cache_hit={self.usage['cache_read_input_tokens']}")
        if (
            "cache_creation_input_tokens" in self.usage
            and self.usage["cache_creation_input_tokens"] > 0
        ):
            parts.append(f"cache_write={self.usage['cache_creation_input_tokens']}")

        return ", ".join(parts) if parts else "No tokens"

    def __str__(self) -> str:
        """String representation shows visible text."""
        return self.text

    def __repr__(self) -> str:
        """Repr shows key metadata."""
        tools = f"tools={self.get_tool_names()}" if self.has_tool_calls() else "no tools"
        return f"ResponseView({tools}, {self.format_usage()})"


@dataclass
class AgentTurnResult:
    """Result of a complete agent turn (may include multiple LLM calls).

    Similar to AgentResult from experimental repo, but specialized for
    our agent's needs.
    """

    responses: list[LLMResponse]  # All LLM responses in this turn
    final_orders: list[dict[str, Any]] | None  # Final submitted orders (if any)
    error: str | None  # Error message (if failed)

    # ---- core helpers ----

    def all_responses(self) -> Iterable[LLMResponse]:
        """Iterate over all LLM responses."""
        return iter(self.responses)

    def response_views(self) -> Iterable[ResponseView]:
        """Get ResponseView for each response."""
        return (ResponseView.from_response(r) for r in self.responses)

    # ---- common extractions ----

    def final_response(self) -> LLMResponse | None:
        """Get the last LLM response in this turn."""
        return self.responses[-1] if self.responses else None

    def final_view(self) -> ResponseView | None:
        """Get ResponseView of final response."""
        final = self.final_response()
        return ResponseView.from_response(final) if final else None

    def all_tool_calls(self) -> list[ToolCall]:
        """Get all tool calls across all responses."""
        calls: list[ToolCall] = []
        for response in self.responses:
            calls.extend(response.get("tool_calls", []))
        return calls

    def total_tokens(self) -> int:
        """Sum total tokens across all responses."""
        total = 0
        for response in self.responses:
            usage = response.get("usage_metadata")
            if usage and "total_tokens" in usage:
                total += usage["total_tokens"]
        return total

    def last_reasoning(self) -> str | None:
        """Get the most recent extended reasoning content."""
        for response in reversed(self.responses):
            _, reasoning = _extract_content_blocks(response["content_blocks"])
            if reasoning:
                return reasoning
        return None

    def succeeded(self) -> bool:
        """Check if the turn succeeded (no error)."""
        return self.error is None

    def failed(self) -> bool:
        """Check if the turn failed (has error)."""
        return self.error is not None


# ========== Helper Functions ==========


def _extract_content_blocks(blocks: list[ContentBlock]) -> tuple[str, str | None]:
    """Extract visible text and reasoning from content blocks.

    Args:
        blocks: List of content blocks from LLM response

    Returns:
        Tuple of (visible_text, reasoning_text)
        - visible_text: Concatenated text blocks (excludes tool_use)
        - reasoning_text: Extended thinking content (if present)
    """
    visible_parts: list[str] = []
    reasoning_parts: list[str] = []

    for block in blocks:
        block_type = block.get("type")

        if block_type == "text":
            text = block.get("text", "")
            if text:
                visible_parts.append(text)

        elif block_type == "reasoning_content":
            # Extended thinking (Claude 3.5+ with extended thinking enabled)
            rc = block.get("reasoning_content", {})
            if isinstance(rc, dict):
                text = rc.get("text", "")
                if text:
                    reasoning_parts.append(text)

        # Ignore tool_use blocks for visible text

    visible_text = "\n".join(visible_parts).strip()
    reasoning_text = "\n".join(reasoning_parts).strip() if reasoning_parts else None

    return visible_text, reasoning_text
