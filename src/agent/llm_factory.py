"""Factory for creating LLM instances with different configurations.

Inspired by genai-sourcing-langchain-experimental LLMFactory pattern.
"""

import os

from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrockConverse
from langchain_openai import ChatOpenAI


class LLMFactory:
    """Factory for creating configured LLM clients.

    Centralizes LLM creation with provider-specific configurations.
    """

    def __init__(self, region: str | None = None, api_base: str | None = None):
        """Initialize LLM factory.

        Args:
            region: AWS region for Bedrock (default: us-east-1)
            api_base: API base URL for Ollama or other providers
        """
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.api_base = api_base

    def create_bedrock_llm(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
    ) -> ChatBedrockConverse:
        """Create AWS Bedrock LLM.

        Args:
            model: Model name (haiku, sonnet, opus, nova-2-lite, etc.) or full ID
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            reasoning_effort: For Nova models (low/medium/high)

        Returns:
            Configured ChatBedrockConverse instance
        """
        # Map friendly names to full model IDs
        model_map = {
            "haiku": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            "sonnet": "global.anthropic.claude-sonnet-4-5-20251204-v1:0",
            "opus": "global.anthropic.claude-opus-4-5-20251120-v1:0",
            "nova-2-lite": "global.amazon.nova-2-lite-v1:0",
        }
        model_id = model_map.get(model, model) if model else model_map["haiku"]

        fields = {"temperature": temperature, "max_tokens": max_tokens}

        # Add reasoning config for Nova models
        if reasoning_effort and "nova" in model_id.lower():
            fields["reasoningConfig"] = {
                "type": "enabled",
                "maxReasoningEffort": reasoning_effort,
            }

        return ChatBedrockConverse(
            model=model_id,
            region_name=self.region,
            additional_model_request_fields=fields,
        )

    def create_openai_llm(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatOpenAI:
        """Create OpenAI LLM.

        Args:
            model: Model name (default: gpt-4o-mini)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Configured ChatOpenAI instance
        """
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def create_anthropic_llm(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> ChatAnthropic:
        """Create Anthropic API LLM.

        Args:
            model: Model name (default: claude-3-5-sonnet-20241022)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Configured ChatAnthropic instance
        """
        return ChatAnthropic(
            model=model or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def create_ollama_llm(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Create Ollama LLM.

        Args:
            model: Model name (default: llama3)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Configured ChatOllama instance
        """
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama not installed. Install with: pip install langchain-ollama"
            )

        return ChatOllama(
            model=model or "llama3",
            temperature=temperature,
            num_predict=max_tokens,
            base_url=self.api_base or "http://localhost:11434",
        )
