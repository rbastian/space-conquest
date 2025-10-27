"""LangChain-based LLM client wrapper supporting multiple providers.

Provides a unified interface to invoke LLMs via LangChain with
function calling support for the agent tools. Supports AWS Bedrock,
OpenAI, Anthropic API, and Ollama.
"""

import json
import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from .tool_models import BedrockResponse

try:
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from langchain_core.utils.function_calling import convert_to_openai_tool

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)


# Provider-specific model configurations
PROVIDER_MODELS = {
    "bedrock": {
        "haiku": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "haiku45": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "sonnet": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "opus": "us.anthropic.claude-3-opus-20240229-v1:0",
    },
    "openai": {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
    },
    "anthropic": {
        "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022": "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229": "claude-3-opus-20240229",
        "sonnet": "claude-3-5-sonnet-20241022",  # alias
        "haiku": "claude-3-5-haiku-20241022",  # alias
        "opus": "claude-3-opus-20240229",  # alias
    },
    "ollama": {
        # Common local models - these are just defaults
        # Users can specify any model name installed in Ollama
        "llama3": "llama3",
        "llama3.1": "llama3.1",
        "mistral": "mistral",
        "mixtral": "mixtral",
        "gemma": "gemma",
        "phi": "phi",
    },
}

DEFAULT_MODELS = {
    "bedrock": "haiku",
    "openai": "gpt-4o-mini",
    "anthropic": "sonnet",
    "ollama": "llama3",
}


def get_model_id(provider: str, model_name: str | None) -> str:
    """Get the full model ID for a given provider and model name.

    Args:
        provider: LLM provider ("bedrock", "openai", "anthropic", "ollama")
        model_name: Short name or full model ID

    Returns:
        Full model ID for the provider

    Raises:
        ValueError: If provider or model name is not recognized
    """
    if provider not in PROVIDER_MODELS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: {', '.join(PROVIDER_MODELS.keys())}"
        )

    # Use default model if none specified
    if model_name is None:
        model_name = DEFAULT_MODELS[provider]

    # Check if it's a configured model
    if model_name in PROVIDER_MODELS[provider]:
        return PROVIDER_MODELS[provider][model_name]

    # For Ollama, allow any model name
    if provider == "ollama":
        return model_name

    # For other providers, if it looks like a full model ID, use it as-is
    return model_name


class LangChainClient:
    """Wrapper for LangChain LLM providers.

    Handles communication with various LLM providers via LangChain,
    including tool/function calling and response parsing.
    """

    def __init__(
        self,
        provider: str = "bedrock",
        model_id: str | None = None,
        region: str = "us-east-1",
        api_base: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """Initialize LangChain client.

        Args:
            provider: LLM provider ("bedrock", "openai", "anthropic", "ollama")
            model_id: Model ID or friendly name (provider-specific)
            region: AWS region (for Bedrock, default: us-east-1)
            api_base: API base URL (for Ollama, default: http://localhost:11434)
            max_tokens: Maximum tokens in response (default: 4096)
            temperature: Sampling temperature (default: 0.7)

        Raises:
            ImportError: If langchain is not installed
            ValueError: If provider or model_id is invalid
            Exception: If provider initialization fails
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain is required. Install with: uv sync"
            )

        self.provider = provider
        self.model_id = get_model_id(provider, model_id)
        self.region = region
        self.api_base = api_base or "http://localhost:11434"
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize provider-specific client
        self.client = self._create_client()
        logger.info(f"Initialized {provider} client with model: {self.model_id}")

    def _create_client(self):
        """Create provider-specific LangChain client.

        Returns:
            LangChain chat model instance

        Raises:
            ImportError: If provider-specific package is not installed
            Exception: If client initialization fails
        """
        try:
            if self.provider == "bedrock":
                from langchain_aws import ChatBedrock

                return ChatBedrock(
                    model_id=self.model_id,
                    region_name=self.region,
                    model_kwargs={
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature,
                    },
                )

            elif self.provider == "openai":
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=self.model_id,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

            elif self.provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model_name=self.model_id,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

            elif self.provider == "ollama":
                from langchain_ollama import ChatOllama

                return ChatOllama(
                    model=self.model_id,
                    base_url=self.api_base,
                    temperature=self.temperature,
                    num_predict=self.max_tokens,
                )

            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        except ImportError as e:
            raise ImportError(
                f"Provider '{self.provider}' requires additional packages: {e}\n"
                f"Install with: uv sync"
            )
        except Exception as e:
            raise Exception(f"Failed to initialize {self.provider} client: {e}")

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list:
        """Convert Bedrock-style messages to LangChain message format.

        Args:
            messages: List of message dicts with "role" and "content"

        Returns:
            List of LangChain message objects
        """
        from langchain_core.messages import ToolMessage

        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            # Handle content blocks (for tool results and assistant messages with tools)
            if isinstance(content, list):
                # Check if this is a tool result message
                if role == "user" and any(block.get("type") == "tool_result" for block in content):
                    # Convert tool result blocks to ToolMessage objects
                    for block in content:
                        if block.get("type") == "tool_result":
                            lc_messages.append(ToolMessage(
                                content=block.get("content", ""),
                                tool_call_id=block.get("tool_use_id", ""),
                            ))
                elif role == "assistant":
                    # For assistant messages with content blocks, extract text and tool calls
                    text_parts = [block.get("text", "") for block in content if block.get("type") == "text"]
                    tool_calls = []

                    # Extract tool_use blocks and convert to tool_calls format
                    for block in content:
                        if block.get("type") == "tool_use":
                            tool_calls.append({
                                "name": block.get("name"),
                                "args": block.get("input", {}),
                                "id": block.get("id"),
                            })

                    # Create AIMessage with tool_calls if present
                    ai_msg = AIMessage(
                        content="\n".join(text_parts) if text_parts else "",
                    )
                    if tool_calls:
                        ai_msg.tool_calls = tool_calls

                    lc_messages.append(ai_msg)
                else:
                    # Fallback: convert to string
                    lc_messages.append(HumanMessage(content=str(content)))
            else:
                # Simple string content
                if role == "user":
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    lc_messages.append(AIMessage(content=content))

        return lc_messages

    def _convert_tools_to_langchain(self, tools: list[dict[str, Any]] | None) -> list:
        """Convert Bedrock-style tool definitions to LangChain format.

        Args:
            tools: List of tool definition dicts

        Returns:
            List of LangChain tool objects
        """
        if not tools:
            return []

        lc_tools = []
        for tool in tools:
            # Convert to OpenAI tool format (LangChain standard)
            lc_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            })

        return lc_tools

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def invoke(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """Invoke LLM with messages and optional tools.

        Args:
            messages: List of message dicts with "role" and "content"
            system: System prompt string
            tools: Optional list of tool definitions
            max_iterations: Maximum tool use iterations (not used, for compatibility)

        Returns:
            Dict containing:
                - response: Final assistant message content
                - tool_calls: List of tool calls made
                - stop_reason: Why the model stopped
                - requires_tool_execution: Whether tools need to be executed

        Raises:
            Exception: If LLM API call fails
        """
        try:
            # Convert messages to LangChain format
            lc_messages = self._convert_messages(messages)

            # Prepend system message
            if system:
                from langchain_core.messages import SystemMessage

                lc_messages.insert(0, SystemMessage(content=system))

            # Bind tools if provided
            if tools:
                lc_tools = self._convert_tools_to_langchain(tools)
                client_with_tools = self.client.bind_tools(lc_tools)
                response = client_with_tools.invoke(lc_messages)
            else:
                response = self.client.invoke(lc_messages)

            # Check if model wants to use tools
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls_made = []
                content_blocks = []

                # Add any text content first (reasoning/thinking)
                if response.content:
                    content_blocks.append({
                        "type": "text",
                        "text": response.content,
                    })
                else:
                    # Log when there's no reasoning text (common with OpenAI)
                    logger.debug(f"{self.provider}: No reasoning text provided with tool calls")

                # Then add tool calls
                for tool_call in response.tool_calls:
                    tool_calls_made.append({
                        "name": tool_call["name"],
                        "input": tool_call["args"],
                    })
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "input": tool_call["args"],
                    })

                return BedrockResponse(
                    response=content_blocks,
                    content_blocks=content_blocks,
                    tool_calls=tool_calls_made,
                    stop_reason="tool_use",
                    requires_tool_execution=True,
                ).model_dump()
            else:
                # No tool calls, return text response
                text_content = response.content if hasattr(response, "content") else str(response)

                return BedrockResponse(
                    response=text_content,
                    content_blocks=[{"type": "text", "text": text_content}],
                    tool_calls=[],
                    stop_reason="end_turn",
                    requires_tool_execution=False,
                ).model_dump()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"{self.provider} API call failed: {e}\n{error_details}")
            raise Exception(f"{self.provider} API call failed: {e}")

    def continue_with_tool_results(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tool_results: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Continue conversation with tool execution results.

        Args:
            messages: Previous conversation messages
            system: System prompt
            tool_results: Results from tool executions
            tools: Tool definitions

        Returns:
            Response dict from invoke()
        """
        # Add tool results to conversation
        tool_result_blocks = []
        for result in tool_results:
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": result["tool_use_id"],
                "content": json.dumps(result["content"]),
            })

        messages.append({"role": "user", "content": tool_result_blocks})

        return self.invoke(messages, system, tools)


class MockLangChainClient:
    """Mock LangChain client for testing without API credentials.

    Simulates the LangChain API for unit testing and development.
    """

    def __init__(self, **kwargs):
        """Initialize mock client.

        Args:
            **kwargs: Ignored (for compatibility with LangChainClient)
        """
        self.call_count = 0
        self.last_request = None
        self.model_id = kwargs.get("model_id", "mock-model")
        self.provider = kwargs.get("provider", "mock")

    def invoke(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]] | None = None,
        max_iterations: int = 10,
    ) -> dict[str, Any]:
        """Mock invoke that returns a simple response.

        Args:
            messages: Message history
            system: System prompt
            tools: Tool definitions
            max_iterations: Max iterations

        Returns:
            Mock response with empty orders
        """
        self.call_count += 1
        self.last_request = {"messages": messages, "system": system, "tools": tools}

        # Return a simple response that doesn't use tools
        return {
            "response": "Mock LLM response: Passing this turn.",
            "content_blocks": [{"type": "text", "text": "Mock LLM response: Passing this turn."}],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
        }

    def continue_with_tool_results(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tool_results: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Mock continue with tool results.

        Args:
            messages: Previous messages
            system: System prompt
            tool_results: Tool results
            tools: Tool definitions

        Returns:
            Mock response
        """
        return self.invoke(messages, system, tools)
