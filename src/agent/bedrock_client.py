"""AWS Bedrock client wrapper for Claude API.

Provides a simple interface to invoke Claude via AWS Bedrock with
function calling support for the agent tools.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    retry_if_exception,
)

from .tool_models import BedrockResponse

try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    ClientError = Exception  # Fallback for type hints


logger = logging.getLogger(__name__)


# Model configuration mapping friendly names to Bedrock model IDs
MODEL_CONFIG = {
    "haiku": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "haiku45": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "opus": "us.anthropic.claude-3-opus-20240229-v1:0",
}

DEFAULT_MODEL = "haiku"


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception is retryable.

    Args:
        exception: Exception to check

    Returns:
        True if the error is retryable (throttling, timeout, service unavailable)
    """
    if not isinstance(exception, ClientError):
        return False

    error_code = exception.response.get("Error", {}).get("Code", "")
    retryable_codes = {
        "ThrottlingException",
        "TooManyRequestsException",
        "ServiceUnavailable",
        "RequestTimeout",
        "InternalServerError",
    }

    return error_code in retryable_codes


def get_model_id(model_name: str) -> str:
    """Get the Bedrock model ID for a given model name.

    Args:
        model_name: Short name ("haiku", "haiku45", "sonnet", "opus") or full model ID

    Returns:
        Full Bedrock model ID

    Raises:
        ValueError: If model name is not recognized
    """
    # If it's already a full model ID (starts with "us.anthropic.", "anthropic.", or "global.anthropic."), return as-is
    if (
        model_name.startswith("us.anthropic.")
        or model_name.startswith("anthropic.")
        or model_name.startswith("global.anthropic.")
    ):
        return model_name

    # Look up in config
    if model_name in MODEL_CONFIG:
        return MODEL_CONFIG[model_name]

    # Invalid model name
    supported = ", ".join(MODEL_CONFIG.keys())
    raise ValueError(f"Unknown model '{model_name}'. Supported models: {supported}")


class BedrockClient:
    """Wrapper for AWS Bedrock Runtime API.

    Handles communication with Claude via Bedrock, including tool/function
    calling and response parsing.
    """

    def __init__(
        self,
        model_id: str = None,
        region: str = "us-east-1",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """Initialize Bedrock client.

        Args:
            model_id: Bedrock model ID or friendly name ("haiku", "haiku45", "sonnet", "opus")
                     Default: Haiku 3.5
            region: AWS region (default: us-east-1)
            max_tokens: Maximum tokens in response (default: 4096)
            temperature: Sampling temperature (default: 0.7)

        Raises:
            ImportError: If boto3 is not installed
            ValueError: If model_id is invalid
            Exception: If AWS credentials are not configured
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for Bedrock client. Install with: pip install boto3"
            )

        # Resolve model ID from friendly name or use default
        if model_id is None:
            self.model_id = get_model_id(DEFAULT_MODEL)
        else:
            self.model_id = get_model_id(model_id)

        self.region = region
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize Bedrock runtime client
        try:
            self.client = boto3.client(
                service_name="bedrock-runtime", region_name=region
            )
        except Exception as e:
            raise Exception(
                f"Failed to initialize Bedrock client: {e}\n"
                "Make sure AWS credentials are configured with 'aws configure'"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_retryable_error),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _invoke_model_with_retry(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke Bedrock model with retry logic.

        Retries on throttling and transient errors with exponential backoff.

        Args:
            request_body: Request body dict

        Returns:
            Bedrock response dict

        Raises:
            Exception: If all retries are exhausted
        """
        logger.debug(f"Invoking model {self.model_id}")
        return self.client.invoke_model(
            modelId=self.model_id, body=json.dumps(request_body)
        )

    def invoke(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Invoke Claude with messages and optional tools.

        Handles the tool use loop: if Claude requests tool calls, executes them
        and returns the results in a new message, continuing until Claude provides
        a final response.

        Args:
            messages: List of message dicts with "role" and "content"
            system: System prompt string
            tools: Optional list of tool definitions
            max_iterations: Maximum tool use iterations to prevent infinite loops

        Returns:
            Dict containing:
                - response: Final assistant message content
                - tool_calls: List of tool calls made
                - stop_reason: Why the model stopped

        Raises:
            Exception: If Bedrock API call fails
            ValueError: If max_iterations exceeded
        """
        conversation = messages.copy()
        tool_calls_made = []
        iterations = 0

        while iterations < max_iterations:
            iterations += 1

            # Build request body
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system,
                "messages": conversation,
            }

            # Add tools if provided
            if tools:
                request_body["tools"] = tools

            # Invoke model with retry logic
            try:
                response = self._invoke_model_with_retry(request_body)
                response_body = json.loads(response["body"].read())

            except Exception as e:
                logger.error(f"Bedrock API call failed after retries: {e}")
                raise Exception(f"Bedrock API call failed: {e}")

            # Parse response
            stop_reason = response_body.get("stop_reason")
            content = response_body.get("content", [])

            # Check if model wants to use tools
            if stop_reason == "tool_use":
                # Extract tool use blocks
                for block in content:
                    if block.get("type") == "tool_use":
                        tool_name = block["name"]
                        tool_input = block["input"]

                        # Record the tool call
                        tool_calls_made.append({"name": tool_name, "input": tool_input})

                        # For now, we don't actually execute tools here
                        # That's handled by the LLMPlayer controller
                        # Just return the tool use request
                        return BedrockResponse(
                            response=content,
                            content_blocks=content,
                            tool_calls=tool_calls_made,
                            stop_reason=stop_reason,
                            requires_tool_execution=True,
                        ).model_dump()

            else:
                # Final response without tool use
                # Extract text content
                text_content = []
                for block in content:
                    if block.get("type") == "text":
                        text_content.append(block["text"])

                return BedrockResponse(
                    response="\n".join(text_content) if text_content else "",
                    content_blocks=content,
                    tool_calls=tool_calls_made,
                    stop_reason=stop_reason,
                    requires_tool_execution=False,
                ).model_dump()

        raise ValueError(f"Exceeded max iterations ({max_iterations}) in tool use loop")

    def continue_with_tool_results(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tool_results: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
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
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": result["tool_use_id"],
                    "content": json.dumps(result["content"]),
                }
            )

        messages.append({"role": "user", "content": tool_result_blocks})

        return self.invoke(messages, system, tools)


class MockBedrockClient:
    """Mock Bedrock client for testing without AWS credentials.

    Simulates the Bedrock API for unit testing and development.
    """

    def __init__(self, **kwargs):
        """Initialize mock client.

        Args:
            **kwargs: Ignored (for compatibility with BedrockClient)
        """
        self.call_count = 0
        self.last_request = None
        # Set default model_id for compatibility with naming system
        self.model_id = "us.anthropic.claude-3-5-haiku-20241022-v1:0"

    def invoke(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
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
            "content_blocks": [
                {"type": "text", "text": "Mock LLM response: Passing this turn."}
            ],
            "tool_calls": [],
            "stop_reason": "end_turn",
            "requires_tool_execution": False,
        }

    def continue_with_tool_results(
        self,
        messages: List[Dict[str, Any]],
        system: str,
        tool_results: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
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
