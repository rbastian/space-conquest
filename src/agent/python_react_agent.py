"""PythonReactAgent - Experimental agent with Python REPL for computational strategies.

This player is similar to ReactPlayer but with a key difference:
- Uses Python REPL tool for arbitrary code execution
- Minimal predefined tool set (only validate_orders)
- Agent can write Python code to analyze game state and compute complex strategies

The goal is to test if computational capabilities improve strategic decision-making
compared to the standard ReactPlayer with its predefined analytical tools.
"""

import json
import logging
import re

from langchain.agents import create_agent
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)

from ..analysis import calculate_strategic_metrics
from ..analysis.strategic_logger import StrategicLogger
from ..models.game import Game
from ..models.order import Order

logger = logging.getLogger(__name__)

# Message history limits
MAX_MESSAGES = 20
MAX_TOKENS = 8000


class PythonReactAgent:
    """PythonReactAgent with Python REPL for computational strategies.

    This agent uses:
    - validate_orders tool for order validation
    - Python REPL tool for arbitrary code execution and analysis

    The REPL has access to game state variables, allowing the agent to:
    - Calculate distances and optimal routes programmatically
    - Analyze strategic positions with custom algorithms
    - Compute complex combat scenarios
    - Optimize fleet distributions
    - Perform statistical analysis on game state
    """

    def __init__(
        self,
        llm,
        game: Game,
        player_id: str,
        tools: list,
        system_prompt: str,
        verbose: bool = False,
        enable_decision_logging: bool = False,
    ):
        """Initialize PythonReactAgent with injected dependencies.

        Creates the agent ONCE here, to be reused across all turns.

        Args:
            llm: LangChain ChatModel instance (created by LLMFactory in game.py)
            game: Game object reference (mutated each turn by TurnExecutor)
            player_id: Player ID ("p1" or "p2")
            tools: List of tools (validate_orders + python_repl)
            system_prompt: System prompt text for the agent
            verbose: Enable verbose logging
            enable_decision_logging: Enable detailed decision logging
        """
        self.llm = llm
        self.game = game  # Reference to Game object (always current state)
        self.player_id = player_id
        self.tools = tools
        self.system_prompt = system_prompt
        self.verbose = verbose
        self.enable_decision_logging = enable_decision_logging

        # Create agent ONCE with injected LLM and tools
        self.agent = self._create_agent()

        # Per-turn state
        self.strategic_logger = None
        self.decision_logger = None

        # Tool usage tracking
        self._tool_usage_counts: dict[str, int] = {
            "validate_orders": 0,
            "python_repl": 0,
        }

        # Log successful initialization
        # Different LLM classes use different attribute names for model identifier
        llm_model = (
            getattr(llm, "model_id", None)  # ChatBedrockConverse
            or getattr(llm, "model", None)  # ChatAnthropic, ChatOllama
            or getattr(llm, "model_name", None)  # ChatOpenAI
            or "unknown"
        )
        logger.info(
            f"PythonReactAgent initialized for {player_id} with {len(tools)} tools and model {llm_model}"
        )
        logger.info(f"[SYSTEM] System prompt:\n{system_prompt}")

    def _create_agent(self):
        """Create agent ONCE with injected LLM and tools.

        Called only from __init__. Agent is reused across all turns.
        Tools access self.game at runtime (always current state).
        """
        return create_agent(
            self.llm,
            tools=self.tools,
            system_prompt=SystemMessage(content=self.system_prompt),
        )

    def _run_agent_loop(
        self, initial_message: str, max_iterations: int = 20
    ) -> tuple[list[BaseMessage], list[Order]]:
        """Run agent with manual message history management.

        Loop continues until agent doesn't request any more tool calls.

        Args:
            initial_message: Formatted game state to send to agent
            max_iterations: Maximum number of agent invocations

        Returns:
            Tuple of (message_history, orders)
        """
        message_history = [HumanMessage(content=initial_message)]

        consecutive_errors = 0

        for iteration in range(1, max_iterations + 1):
            logger.info(f"Agent iteration {iteration}/{max_iterations}")

            # Trim history if needed
            if len(message_history) > MAX_MESSAGES:
                message_history = trim_messages(
                    message_history,
                    max_tokens=MAX_TOKENS,
                    strategy="last",
                    token_counter=len,
                    start_on="human",
                )

            try:
                # Invoke agent (created in __init__)
                result = self.agent.invoke({"messages": message_history})
                consecutive_errors = 0

                # Track new messages added in this iteration
                new_messages = []
                for msg in result["messages"]:
                    if msg not in message_history:
                        message_history.append(msg)
                        new_messages.append(msg)

                # Extract and log information from new AIMessages
                self._log_iteration_messages(new_messages)

                # Track tool usage and log to decision logger
                for msg in new_messages:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.get("name")
                            if tool_name in self._tool_usage_counts:
                                self._tool_usage_counts[tool_name] += 1

                # Log tool calls to decision logger
                if self.enable_decision_logging and self.decision_logger:
                    self._log_tool_calls_to_decision_logger(new_messages)

                # Check termination: loop continues until agent doesn't request more tools
                # Find last AIMessage and check if it has tool_calls
                last_ai_message = None
                for msg in reversed(message_history):
                    if isinstance(msg, AIMessage):
                        last_ai_message = msg
                        break

                if last_ai_message and not last_ai_message.tool_calls:
                    logger.info(
                        f"Agent finished - no more tool calls requested on iteration {iteration}"
                    )
                    break

            except Exception as e:
                logger.error(f"Agent error on iteration {iteration}: {e}")
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    logger.error("Too many consecutive errors, aborting")
                    break

        # Extract orders from final AI message
        orders = self._extract_orders_from_messages(message_history)

        return message_history, orders

    def _log_iteration_messages(self, messages: list[BaseMessage]) -> None:
        """Extract and log information from new messages in this iteration.

        Args:
            messages: New messages added in this iteration
        """
        from ..agent.message_helpers import extract_anthropic_claude_blocks

        for msg in messages:
            if not isinstance(msg, AIMessage):
                continue

            # Extract visible text and reasoning
            visible_text = None
            reasoning = None
            if isinstance(msg.content, list | str):
                visible_text, reasoning = extract_anthropic_claude_blocks(msg.content)

            # Log visible text content at INFO level (if not just tool calls)
            if visible_text and visible_text.strip():
                # Truncate long messages for readability
                max_length = 500
                if len(visible_text) > max_length:
                    logger.info(f"Agent response: {visible_text[:max_length]}...")
                else:
                    logger.info(f"Agent response: {visible_text}")

            # Extract reasoning (log at DEBUG level as it can be verbose)
            if reasoning:
                logger.debug(f"Agent reasoning: {reasoning[:200]}...")  # First 200 chars

            # Extract and log token usage
            usage = None
            if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                usage = msg.usage_metadata
            elif hasattr(msg, "additional_kwargs") and "usage" in msg.additional_kwargs:
                u = msg.additional_kwargs["usage"]
                usage = {
                    "input_tokens": u.get("prompt_tokens", u.get("input_tokens")),
                    "output_tokens": u.get("completion_tokens", u.get("output_tokens")),
                    "total_tokens": u.get("total_tokens"),
                }

            if usage:
                input_tok = usage.get("input_tokens", 0)
                output_tok = usage.get("output_tokens", 0)
                total_tok = usage.get("total_tokens", 0)
                logger.info(f"Token usage: {input_tok} in, {output_tok} out, {total_tok} total")

                # Log to decision logger
                if self.enable_decision_logging and self.decision_logger:
                    self.decision_logger.log_token_usage(input_tok, output_tok, total_tok)

    def _log_tool_calls_to_decision_logger(self, messages: list[BaseMessage]) -> None:
        """Log tool calls from messages to decision logger.

        Args:
            messages: Messages to extract tool calls from
        """
        from langchain_core.messages import ToolMessage

        if not self.decision_logger:
            return

        # Find AI messages with tool calls
        for i, msg in enumerate(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name")
                    tool_input = tool_call.get("args", {})
                    tool_id = tool_call.get("id")

                    # Find corresponding ToolMessage with result
                    tool_output = None
                    success = True

                    # Look ahead for ToolMessage with matching tool_use_id
                    for next_msg in messages[i + 1 :]:
                        if isinstance(next_msg, ToolMessage) and next_msg.tool_call_id == tool_id:
                            tool_output = next_msg.content
                            # Check if output indicates error
                            if "error" in str(tool_output).lower():
                                success = False
                            break

                    # If no output found yet, tool call might not have completed
                    if tool_output is None:
                        continue

                    # Log the tool call
                    self.decision_logger.log_tool_call(
                        tool_name=tool_name,
                        tool_input=tool_input,
                        tool_output=str(tool_output),
                        success=success,
                    )

    def _extract_orders_from_messages(self, messages: list[BaseMessage]) -> list[Order]:
        """Extract orders from final AI message.

        The agent's final response should contain JSON orders like:
        [{"from": "A", "to": "B", "ships": 10, "rationale": "attack"}]

        Args:
            messages: Message history from agent loop

        Returns:
            List of Order objects
        """
        # Find last AIMessage with content
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content

                # Try to extract JSON array from content
                # Look for [ ... ] pattern
                json_match = re.search(r"\[[\s\S]*?\]", content)
                if json_match:
                    try:
                        orders_data = json.loads(json_match.group())

                        # Validate it's a list
                        if not isinstance(orders_data, list):
                            logger.error(f"Extracted JSON is not a list: {type(orders_data)}")
                            continue

                        # Convert to Order objects
                        orders = []
                        for order_dict in orders_data:
                            try:
                                orders.append(
                                    Order(
                                        from_star=order_dict["from"],
                                        to_star=order_dict["to"],
                                        ships=order_dict["ships"],
                                        rationale=order_dict.get("rationale", ""),
                                    )
                                )
                            except (KeyError, ValueError) as e:
                                logger.error(f"Invalid order dict {order_dict}: {e}")
                                continue

                        logger.info(f"Extracted {len(orders)} orders from AI message")

                        return orders

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON from AI message: {e}")
                        logger.error(f"Content: {json_match.group()}")

        logger.warning("No valid orders found in AI messages")
        return []

    def get_orders(self, game: Game) -> list[Order]:
        """Main entry point - implements Player interface.

        Called each turn by GameOrchestrator. Invokes the agent (created in __init__).
        Game state has been updated by TurnExecutor, tools access via self.game reference.

        Args:
            game: Current game state

        Returns:
            List of Order objects for this turn
        """
        from ..agent.prompts import format_game_state_prompt
        from ..analysis.decision_logger import DecisionLogger

        # Initialize decision logger if enabled
        if self.enable_decision_logging:
            if self.decision_logger is None:
                game_id = f"seed{game.seed}_{self.player_id}_turn{game.turn}"
                self.decision_logger = DecisionLogger(game_id)
            from ..analysis.game_stage import calculate_game_stage

            game_stage = calculate_game_stage(game, self.player_id)
            self.decision_logger.start_turn(game.turn, game_stage)

        # Format game state as initial message
        formatted_state = format_game_state_prompt(game, self.player_id)

        logger.info(f"PythonReactAgent {self.player_id} starting turn {game.turn}")
        logger.debug(f"[USER] Game state:\n{formatted_state}")

        # Run agent loop (invokes self.agent which was created in __init__)
        # Tools access current game state via self.game reference
        message_history, orders = self._run_agent_loop(formatted_state)

        # Log orders
        logger.info(
            f"PythonReactAgent {self.player_id} returned {len(orders)} orders for turn {game.turn}"
        )
        for order in orders:
            logger.info(
                f"  Order: {order.ships} ships from {order.from_star} to {order.to_star} ({order.rationale})"
            )

        # Log to decision logger if enabled
        if self.enable_decision_logging and self.decision_logger:
            # Convert orders to dict format for logging
            orders_dict = [
                {
                    "from": o.from_star,
                    "to": o.to_star,
                    "ships": o.ships,
                    "rationale": o.rationale,
                }
                for o in orders
            ]
            self.decision_logger.log_orders(orders_dict)
            self.decision_logger.end_turn()

        # Log strategic metrics
        self._log_strategic_metrics(game)

        return orders

    def _log_strategic_metrics(self, game: Game):
        """Log strategic metrics for this turn.

        Copies pattern from LangGraphPlayer for consistency.
        """
        try:
            if self.strategic_logger is None:
                game_id = f"seed{game.seed}_{self.player_id}_turn{game.turn}"
                self.strategic_logger = StrategicLogger(game_id)

            metrics = calculate_strategic_metrics(game, self.player_id, game.turn)
            self.strategic_logger.log_turn(metrics)

        except Exception as e:
            logger.warning(f"Failed to log strategic metrics: {e}")

    def get_tool_usage_stats(self) -> dict[str, int]:
        """Return a copy of the tool usage statistics.

        Returns:
            Dictionary mapping tool names to call counts
        """
        return self._tool_usage_counts.copy()

    def close(self):
        """Cleanup strategic logger, decision logger, and log tool usage statistics."""
        # Log tool usage statistics
        logger.info(f"Tool usage statistics for {self.player_id}:")
        for tool_name, count in self._tool_usage_counts.items():
            logger.info(f"  {tool_name}: {count} calls")

        # Cleanup strategic logger
        if self.strategic_logger:
            self.strategic_logger.close()

        # Cleanup decision logger
        if self.decision_logger:
            self.decision_logger.close()
