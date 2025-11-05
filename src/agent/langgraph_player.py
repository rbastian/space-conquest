"""LangGraph-based LLM player with state management and dynamic context.

This module implements a production-ready LLM agent using LangGraph's
StateGraph pattern. It includes:
- Proper state management with message history trimming
- Dynamic system prompt generation based on game state
- Conditional tool filtering based on game phase
- Middleware for threat assessment and error recovery
- Clean separation of concerns between state, tools, and reasoning
"""

import json
import logging
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from ..models.game import Game
from ..models.order import Order
from .langchain_client import LangChainClient, MockLangChainClient
from .middleware import (
    filter_tools_by_game_state,
    handle_tool_error,
    inject_defensive_urgency,
    inject_threat_vector_analysis,
    reset_error_tracking,
    trim_message_history,
    update_game_context_from_observation,
)
from .prompts import get_system_prompt
from .state_models import AgentState
from .tool_models import TOOL_DEFINITIONS
from .tools import AgentTools

logger = logging.getLogger(__name__)


class LangGraphPlayer:
    """LangGraph-based LLM player with state management.

    This player uses LangGraph's StateGraph to manage conversation flow,
    implement dynamic tool filtering, and maintain game context across
    tool calls. It's designed for production use with proper error handling
    and resource management.

    Key features:
    - Message history trimming to prevent unbounded growth
    - Dynamic system prompts based on game phase and threat level
    - Conditional tool availability based on game state
    - Automatic threat assessment from observations
    - Error recovery with circuit breaker pattern
    """

    def __init__(
        self,
        player_id: str = "p2",
        use_mock: bool = False,
        provider: str = "bedrock",
        model: str | None = None,
        region: str = "us-east-1",
        api_base: str | None = None,
        verbose: bool = False,
    ):
        """Initialize LangGraph player.

        Args:
            player_id: Player ID ("p1" or "p2", default: "p2")
            use_mock: Use mock client instead of real LLM (for testing)
            provider: LLM provider ("bedrock", "openai", "anthropic", "ollama")
            model: Model name (provider-specific) or None for provider default
            region: AWS region (for Bedrock, default: us-east-1)
            api_base: API base URL (for Ollama)
            verbose: Print detailed reasoning (uses more tokens)
        """
        self.player_id = player_id
        self.verbose = verbose

        # Initialize LLM client
        if use_mock:
            self.client = MockLangChainClient(provider=provider, model_id=model)
            logger.info(f"Using mock {provider} client")
        else:
            try:
                self.client = LangChainClient(
                    provider=provider,
                    model_id=model,
                    region=region,
                    api_base=api_base,
                    temperature=0.7,
                    max_tokens=4096,
                )
                logger.info(f"Initialized {provider} client: {self.client.model_id}")
            except Exception as e:
                logger.error(f"Failed to initialize {provider} client: {e}")
                logger.info("Falling back to mock client")
                self.client = MockLangChainClient(provider=provider, model_id=model)

        # Build the state graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph for agent execution.

        The graph structure:
        1. START -> call_llm: Invoke LLM with current state
        2. call_llm -> should_continue: Check if we need to execute tools
        3. If tools needed -> execute_tools -> call_llm (loop)
        4. If done -> END

        Returns:
            Compiled StateGraph ready for execution
        """
        # Create graph with AgentState
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("call_llm", self._call_llm_node)
        workflow.add_node("execute_tools", self._execute_tools_node)

        # Set entry point
        workflow.set_entry_point("call_llm")

        # Add conditional routing
        workflow.add_conditional_edges(
            "call_llm",
            self._should_continue,
            {
                "continue": "execute_tools",
                "end": END,
            },
        )

        # After executing tools, go back to LLM
        workflow.add_edge("execute_tools", "call_llm")

        return workflow.compile()

    def _call_llm_node(self, state: AgentState) -> AgentState:
        """Node that invokes the LLM with current state.

        This node:
        1. Trims message history if needed
        2. Generates dynamic system prompt based on game context
        3. Filters available tools based on game state
        4. Invokes LLM with context-aware prompt

        Args:
            state: Current agent state

        Returns:
            Updated state with LLM response
        """
        # Trim message history to prevent unbounded growth
        state = trim_message_history(state)

        # Get game context for dynamic prompt
        game_context = state.get("game_context")

        # Generate context-aware system prompt
        if game_context:
            system_prompt = get_system_prompt(
                verbose=self.verbose,
                game_phase=game_context.get("game_phase"),
                threat_level=game_context.get("threat_level"),
                turn=game_context.get("turn"),
            )

            # Inject defensive urgency if threat is elevated
            urgency_injection = inject_defensive_urgency(game_context)
            if urgency_injection:
                system_prompt += urgency_injection
        else:
            system_prompt = get_system_prompt(verbose=self.verbose)

        # Inject threat vector analysis if available (from previous observation)
        threat_vectors = state.get("_threat_vectors", [])
        if threat_vectors:
            threat_injection = inject_threat_vector_analysis(threat_vectors)
            if threat_injection:
                logger.debug("Injecting threat vector analysis into system prompt")
                system_prompt += "\n\n" + threat_injection

        # Filter tools based on game state
        available_tool_names = filter_tools_by_game_state(state)
        available_tools = [
            tool_def for tool_def in TOOL_DEFINITIONS if tool_def["name"] in available_tool_names
        ]

        logger.debug(f"Available tools: {available_tool_names}")

        # Convert messages to format expected by LangChain client
        messages_for_client = self._convert_messages_for_client(state["messages"])

        # Invoke LLM
        try:
            response = self.client.invoke(
                messages=messages_for_client,
                system=system_prompt,
                tools=available_tools,
                max_iterations=1,
            )

            # Parse response and update state
            if response.get("requires_tool_execution"):
                # LLM wants to use tools
                content_blocks = response["content_blocks"]

                # Log reasoning if present
                for block in content_blocks:
                    if block.get("type") == "text" and block.get("text"):
                        provider_name = getattr(self.client, "provider", "LLM").upper()
                        logger.info(f"[{provider_name}] {block['text']}")

                # Add assistant message to state
                ai_message = AIMessage(content=content_blocks)
                # Store tool calls in additional_kwargs for access in routing
                ai_message.additional_kwargs["tool_calls"] = response.get("tool_calls", [])

                return {
                    **state,
                    "messages": [*state["messages"], ai_message],
                }
            else:
                # LLM finished without tools
                response_text = response.get("response", "")
                ai_message = AIMessage(content=response_text)

                logger.debug(f"LLM finished: {response['stop_reason']}")

                return {
                    **state,
                    "messages": [*state["messages"], ai_message],
                }

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            # Return state with error handling
            return handle_tool_error(state, e, "call_llm")

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """Node that executes tool calls requested by the LLM.

        This node:
        1. Extracts tool calls from last assistant message
        2. Executes each tool via AgentTools
        3. Updates game context if get_observation was called
        4. Adds tool results to conversation
        5. Resets error tracking on success

        Args:
            state: Current agent state with tool calls to execute

        Returns:
            Updated state with tool results and updated context
        """
        # Get last assistant message with tool calls
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            logger.error("Last message is not AIMessage, skipping tool execution")
            return state

        # Extract tool calls from message content or additional_kwargs
        content = last_message.content
        tool_calls = []

        if isinstance(content, list):
            # Content blocks format
            for block in content:
                if block.get("type") == "tool_use":
                    tool_calls.append(block)
        elif "tool_calls" in last_message.additional_kwargs:
            # Tool calls in metadata
            tool_calls = last_message.additional_kwargs["tool_calls"]

        if not tool_calls:
            logger.warning("No tool calls found in last message")
            return state

        # Get AgentTools instance from state (should be set by get_orders)
        tools = state.get("_tools_instance")
        if not tools:
            logger.error("No AgentTools instance in state")
            return state

        # Execute each tool
        tool_results = []
        observation_data = None
        threat_vectors = None
        orders_submitted = False

        # Critical tools that should halt execution on failure
        CRITICAL_TOOLS = {"get_observation", "submit_orders"}  # noqa: N806

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_use_id = tool_call.get("id", "unknown")

            logger.info(f"  → Calling tool: {tool_name}")
            if tool_input and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"    Input: {json.dumps(tool_input, indent=2)}")

            try:
                # Execute tool
                result = tools.execute_tool(tool_name, tool_input)
                result_json = json.dumps(result)

                if logger.isEnabledFor(logging.DEBUG):
                    if tool_name == "get_observation":
                        logger.debug(f"    Result: {json.dumps(result, indent=2)}")
                    else:
                        preview = result_json[:200] + ("..." if len(result_json) > 200 else "")
                        logger.debug(f"    Result: {preview}")

                # Store observation for context update
                if tool_name == "get_observation":
                    observation_data = result
                    # Extract threat vectors for middleware injection
                    threat_vectors = result.get("active_threat_vectors", [])
                    if threat_vectors:
                        logger.info(
                            f"Detected {len(threat_vectors)} threat vector(s) from enemy positions"
                        )

                # Track if orders were submitted
                if tool_name == "submit_orders":
                    orders_submitted = True
                    logger.info("Orders submitted successfully")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_json,
                    }
                )

            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.warning(f"  ✗ Error: {error_msg}")

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({"error": error_msg}),
                    }
                )

                # Critical tool failure - halt execution
                if tool_name in CRITICAL_TOOLS:
                    logger.error(f"Critical tool {tool_name} failed, halting execution")
                    return {
                        **state,
                        "error_count": 999,  # Trigger circuit breaker
                        "last_error": f"Critical tool {tool_name} failed: {error_msg}",
                        "messages": [*state["messages"], HumanMessage(content=tool_results)],
                    }

                # Update state with error
                state = handle_tool_error(state, e, tool_name)

        # Update game context if we got observation
        updated_game_context = state.get("game_context", {})
        if observation_data:
            # Defensive check: ensure home_star exists
            if not hasattr(tools.player, "home_star") or not tools.player.home_star:
                logger.error("Home star ID not found in player object")
            else:
                home_star_id = tools.player.home_star
                # Defensive check: ensure turn exists in observation
                turn = observation_data.get("turn")
                if turn is None:
                    logger.warning("Turn not found in observation data, using current game turn")
                    turn = tools.game.turn

                updated_game_context = update_game_context_from_observation(
                    observation_data,
                    turn,
                    home_star_id,
                )
                logger.debug(
                    f"Updated context: phase={updated_game_context['game_phase']}, "
                    f"threat={updated_game_context['threat_level']}"
                )

        # Update orders_submitted flag if needed (immutable update)
        if orders_submitted:
            updated_game_context = {
                **updated_game_context,
                "orders_submitted": True,
            }

        # Add tool results to messages
        tool_result_message = HumanMessage(content=tool_results)

        # Reset error tracking on successful execution
        state = reset_error_tracking(state)

        # Store threat vectors in state for next LLM call (if any)
        updated_state = {
            **state,
            "game_context": updated_game_context,
            "messages": [*state["messages"], tool_result_message],
        }

        if threat_vectors is not None:
            updated_state["_threat_vectors"] = threat_vectors

        return updated_state

    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """Conditional routing: determine if we should continue or end.

        Continue if:
        - Last message is AIMessage with tool calls
        - Orders not yet submitted
        - Error count below threshold

        End if:
        - No tool calls in last message
        - Orders submitted
        - Too many errors (circuit breaker)

        Args:
            state: Current agent state

        Returns:
            "continue" to execute tools, "end" to finish
        """
        # Check error threshold (circuit breaker)
        if state.get("error_count", 0) >= 5:
            logger.error("Circuit breaker: ending due to too many errors")
            return "end"

        # Check if orders were submitted
        game_context = state.get("game_context")
        if game_context and game_context.get("orders_submitted"):
            logger.debug("Orders submitted, ending conversation")
            return "end"

        # Check last message for tool calls
        if not state["messages"]:
            return "end"

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return "end"

        # Check for tool calls in content or metadata
        content = last_message.content
        has_tool_calls = False

        if isinstance(content, list):
            has_tool_calls = any(block.get("type") == "tool_use" for block in content)
        elif "tool_calls" in last_message.additional_kwargs:
            has_tool_calls = len(last_message.additional_kwargs["tool_calls"]) > 0

        return "continue" if has_tool_calls else "end"

    def _convert_messages_for_client(self, messages: list[BaseMessage]) -> list[dict]:
        """Convert LangChain messages to format expected by client.

        Args:
            messages: List of LangChain BaseMessage objects

        Returns:
            List of message dicts with "role" and "content"
        """
        converted = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                # System messages handled separately in invoke
                continue
            else:
                # Unknown message type, treat as user
                converted.append({"role": "user", "content": str(msg.content)})

        return converted

    def get_orders(self, game: Game) -> list[Order]:
        """Get orders from LLM agent for this turn.

        This is the main entry point called by the game engine. It:
        1. Initializes AgentTools with current game state
        2. Creates initial state for the graph
        3. Runs the StateGraph to completion
        4. Extracts and returns validated orders

        Args:
            game: Current game state

        Returns:
            List of Order objects (may be empty if LLM passes)
        """
        logger.info(f"Getting orders for {self.player_id} (Turn {game.turn})")

        # Initialize tools for this turn
        tools = AgentTools(game, self.player_id)
        tools.reset_turn()

        # Create initial state
        initial_state: AgentState = {
            "messages": [
                HumanMessage(
                    content=(
                        f"It is now turn {game.turn}. "
                        "Please analyze the game state and submit your orders."
                    )
                )
            ],
            "game_context": {
                "turn": game.turn,
                "game_phase": "early",
                "threat_level": "low",
                "controlled_stars_count": 1,
                "total_production": 4,
                "total_ships": 4,
                "enemy_stars_known": 0,
                "nearest_enemy_distance": None,
                "home_garrison": 4,
                "orders_submitted": False,
            },
            "available_tools": [],
            "error_count": 0,
            "last_error": None,
            "_tools_instance": tools,  # Store tools in state for nodes to access
        }

        # Run the graph
        try:
            self.graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            # Return empty orders on catastrophic failure
            return []

        # Save memory back to game for next turn
        game.agent_memory[self.player_id] = tools.memory

        # Get the validated orders
        orders = tools.get_pending_orders()

        if orders is None:
            logger.info("No orders generated, passing turn")
            return []

        logger.info(f"Returning {len(orders)} order(s)")
        for order in orders:
            logger.debug(f"  - {order.ships} ships: {order.from_star} -> {order.to_star}")

        return orders
