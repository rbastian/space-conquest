"""LLM-powered AI player controller.

Implements an AI opponent using AWS Bedrock (Claude) with function calling
to play Space Conquest. The agent observes the game state through fog-of-war
filtered tools and makes strategic decisions.
"""

import json
import logging
from typing import List

from ..models.game import Game
from ..models.order import Order
from .bedrock_client import BedrockClient, MockBedrockClient
from .prompts import SYSTEM_PROMPT
from .tools import TOOL_DEFINITIONS, AgentTools


logger = logging.getLogger(__name__)


class LLMPlayer:
    """LLM-powered AI player controller.

    Uses Claude via AWS Bedrock to make strategic decisions in Space Conquest.
    Implements the same interface as HumanPlayer so it can be used interchangeably.
    """

    def __init__(
        self,
        player_id: str = "p2",
        use_mock: bool = False,
        model: str = None,
        region: str = "us-east-1",
        verbose: bool = False,
    ):
        """Initialize LLM player controller.

        Args:
            player_id: Player ID ("p1" or "p2", default: "p2")
            use_mock: Use mock client instead of real Bedrock (for testing)
            model: Model name ("haiku", "haiku45", "sonnet", "opus") or full Bedrock model ID
                  Default: haiku (Claude 3.5 Haiku)
            region: AWS region
            verbose: Print detailed tool calls and responses
        """
        self.player_id = player_id
        self.verbose = verbose

        # Note: Logger level is configured globally in game.py based on --debug flag.
        # Do NOT set logger levels here as it overrides the centralized configuration.

        # Initialize Bedrock client
        if use_mock:
            self.client = MockBedrockClient()
            logger.info("Using mock Bedrock client")
        else:
            try:
                self.client = BedrockClient(
                    model_id=model, region=region, temperature=0.7, max_tokens=4096
                )
                logger.info(f"Initialized Bedrock client: {self.client.model_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Bedrock client: {e}")
                logger.info("Falling back to mock client")
                self.client = MockBedrockClient()

        # Conversation history (for multi-turn context if needed)
        self.conversation_history = []

    def get_orders(self, game: Game) -> List[Order]:
        """Get orders from LLM agent for this turn.

        Orchestrates the tool use loop:
        1. Initialize AgentTools with current game state
        2. Invoke Claude with tools
        3. Execute tool calls
        4. Continue conversation with results
        5. Extract and validate orders

        Args:
            game: Current game state

        Returns:
            List of Order objects (may be empty if LLM passes)
        """
        logger.info(f"Getting orders for {self.player_id} (Turn {game.turn})")

        # Initialize tools for this turn
        tools = AgentTools(game, self.player_id)
        tools.reset_turn()

        # Start conversation
        messages = [
            {
                "role": "user",
                "content": f"It is now turn {game.turn}. Please analyze the game state and submit your orders.",
            }
        ]

        # Tool use loop
        max_iterations = 15
        for iteration in range(max_iterations):
            logger.debug(f"Iteration {iteration + 1}/{max_iterations}")

            # Invoke Claude
            response = self.client.invoke(
                messages=messages,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                max_iterations=1,  # We handle the loop ourselves
            )

            # Check if tool execution is required
            if response.get("requires_tool_execution"):
                # Execute tools and continue
                tool_results = self._execute_tools(response["content_blocks"], tools)

                logger.debug(f"Executed {len(tool_results)} tool(s)")

                # Add assistant message with tool uses
                messages.append(
                    {"role": "assistant", "content": response["content_blocks"]}
                )

                # Add tool results
                tool_result_blocks = []
                for result in tool_results:
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": result["tool_use_id"],
                            "content": result["content"],
                        }
                    )

                messages.append({"role": "user", "content": tool_result_blocks})

                # Check if orders were submitted
                if tools.orders_submitted:
                    logger.info("Orders submitted successfully")
                    break

            else:
                # No more tool use - end conversation
                logger.debug(f"Conversation ended: {response['stop_reason']}")
                break

        # Save memory back to game for next turn
        game.agent_memory[self.player_id] = tools.memory

        # Get the validated orders
        orders = tools.get_pending_orders()

        if orders is None:
            logger.info("No orders generated, passing turn")
            return []

        logger.info(f"Returning {len(orders)} order(s)")
        for order in orders:
            logger.debug(
                f"  - {order.ships} ships: {order.from_star} -> {order.to_star}"
            )

        return orders

    def _execute_tools(
        self, content_blocks: List[dict], tools: AgentTools
    ) -> List[dict]:
        """Execute tool calls requested by Claude.

        Args:
            content_blocks: Content blocks from Claude response
            tools: AgentTools instance

        Returns:
            List of tool result dicts with tool_use_id and content
        """
        results = []

        for block in content_blocks:
            # Log text blocks (Claude's reasoning)
            if block.get("type") == "text":
                text_content = block.get("text", "")
                if text_content:
                    logger.info(f"[Claude] {text_content}")

            elif block.get("type") == "tool_use":
                tool_use_id = block["id"]
                tool_name = block["name"]
                tool_input = block.get("input", {})

                logger.debug(f"Executing tool: {tool_name}")
                if tool_input:
                    logger.debug(f"  Input: {json.dumps(tool_input, indent=2)}")

                # Execute the tool
                try:
                    result = self._call_tool(tool_name, tool_input, tools)
                    result_content = json.dumps(result)

                    logger.debug(
                        f"  Result: {result_content[:200]}{'...' if len(result_content) > 200 else ''}"
                    )

                    results.append(
                        {"tool_use_id": tool_use_id, "content": result_content}
                    )

                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    logger.warning(f"  Error: {error_msg}")

                    results.append(
                        {
                            "tool_use_id": tool_use_id,
                            "content": json.dumps({"error": error_msg}),
                        }
                    )

        return results

    def _call_tool(self, tool_name: str, tool_input: dict, tools: AgentTools) -> dict:
        """Call a specific tool method with Pydantic validation.

        Args:
            tool_name: Name of the tool to call
            tool_input: Input parameters for the tool
            tools: AgentTools instance

        Returns:
            Tool execution result (validated)

        Raises:
            ValueError: If tool_name is invalid or validation fails
        """
        # Use the unified execute_tool method which handles all validation
        return tools.execute_tool(tool_name, tool_input)
