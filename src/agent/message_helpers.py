"""Helper functions for parsing LLM message content from different providers.

Handles extraction of text, reasoning blocks, and tool calls from provider-specific
message formats (Anthropic Claude, AWS Nova, etc.).
"""


def extract_anthropic_claude_blocks(content: object) -> tuple[str, str | None]:
    """Extract text and reasoning blocks from Anthropic Claude message content.

    Claude models (via Bedrock or Anthropic API) return content as either:
    - A plain string
    - A list of content blocks with types: "text", "reasoning_content", "tool_use"

    Args:
        content: Message content from Claude (string or list of dicts)

    Returns:
        Tuple of (visible_text, reasoning_text)
        - visible_text: Concatenation of text blocks (empty string if none)
        - reasoning_text: Concatenation of reasoning blocks (None if none)

    Example:
        >>> content = [
        ...     {"type": "reasoning_content", "reasoning_content": {"text": "Let me think..."}},
        ...     {"type": "text", "text": "The answer is 42"},
        ...     {"type": "tool_use", "name": "calculate", "input": {...}}
        ... ]
        >>> text, reasoning = extract_anthropic_claude_blocks(content)
        >>> print(text)  # "The answer is 42"
        >>> print(reasoning)  # "Let me think..."
    """
    if isinstance(content, str):
        return content, None

    if not isinstance(content, list):
        # Unexpected format - stringify defensively
        return str(content), None

    visible_parts: list[str] = []
    reasoning_parts: list[str] = []

    for block in content:
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")

        if block_type == "reasoning_content":
            # Extract reasoning text
            rc = block.get("reasoning_content") or {}
            if isinstance(rc, dict):
                text = rc.get("text")
                if isinstance(text, str):
                    reasoning_parts.append(text)

        elif block_type == "text":
            # Extract visible text
            text = block.get("text")
            if isinstance(text, str):
                visible_parts.append(text)

        # Ignore tool_use blocks - they're handled separately

    visible_text = "\n".join(visible_parts).strip()
    reasoning_text = "\n".join(reasoning_parts).strip() or None

    return visible_text, reasoning_text


def extract_nova_blocks(content: object) -> tuple[str, str | None]:
    """Extract text and reasoning blocks from AWS Nova message content.

    Nova models return content in the same format as Claude when reasoning is enabled:
    - A plain string (when reasoning disabled)
    - A list of content blocks with types: "text", "reasoning_content", "tool_use"

    Args:
        content: Message content from Nova (string or list of dicts)

    Returns:
        Tuple of (visible_text, reasoning_text)
        - visible_text: Concatenation of text blocks (empty string if none)
        - reasoning_text: Concatenation of reasoning blocks (None if none)

    Example:
        >>> content = [
        ...     {"type": "reasoning_content", "reasoning_content": {"text": "Analyzing..."}},
        ...     {"type": "text", "text": "I recommend option A"},
        ... ]
        >>> text, reasoning = extract_nova_blocks(content)
        >>> print(text)  # "I recommend option A"
        >>> print(reasoning)  # "Analyzing..."
    """
    # Nova uses the same format as Claude
    return extract_anthropic_claude_blocks(content)


def normalize_content_blocks(content: object, provider: str = "unknown") -> list[dict]:
    """Normalize message content into a list of structured content blocks.

    Takes raw message content (string or list) and returns a normalized list of
    content block dicts with consistent structure.

    Args:
        content: Message content (string or list of blocks)
        provider: Provider name for logging/debugging

    Returns:
        List of content block dicts with keys:
        - type: "text", "reasoning_content", or "tool_use"
        - Additional keys based on type (text, reasoning_content, etc.)

    Example:
        >>> content = "Hello world"
        >>> blocks = normalize_content_blocks(content)
        >>> blocks
        [{"type": "text", "text": "Hello world"}]

        >>> content = [
        ...     {"type": "reasoning_content", "reasoning_content": {"text": "Thinking..."}},
        ...     {"type": "text", "text": "Answer"}
        ... ]
        >>> blocks = normalize_content_blocks(content)
        >>> len(blocks)
        2
    """
    if isinstance(content, str):
        # Plain string - wrap in text block
        return [{"type": "text", "text": content}] if content else []

    if not isinstance(content, list):
        # Unknown format - stringify and wrap
        text = str(content)
        return [{"type": "text", "text": text}] if text else []

    # Already a list - validate it's properly structured
    blocks = []
    for block in content:
        if not isinstance(block, dict):
            # Invalid block - skip
            continue

        block_type = block.get("type")
        if block_type in ("text", "reasoning_content", "tool_use"):
            blocks.append(block)
        # Skip unknown block types

    return blocks
