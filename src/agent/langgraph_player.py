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

from ..analysis import calculate_strategic_metrics
from ..analysis.strategic_logger import StrategicLogger
from ..models.game import Game
from ..models.order import Order
from .langchain_client import LangChainClient, MockLangChainClient
from .middleware import (
    handle_tool_error,
    inject_threat_vector_analysis,
    reset_error_tracking,
    trim_message_history,
)
from .prompts import get_system_prompt
from .response_models import ResponseView
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
        # NEW: Dependency injection params
        llm=None,  # Raw LLM (ChatBedrockConverse, ChatAnthropic, etc.)
        game: Game | None = None,  # Game reference
        tools=None,  # AgentTools instance
        tool_definitions: list | None = None,  # TOOL_DEFINITIONS list
        system_prompt: str | None = None,  # System prompt string
        verbose: bool = False,
        # OLD: Legacy params (for backward compatibility)
        use_mock: bool = False,
        provider: str = "bedrock",
        model: str | None = None,
        region: str = "us-east-1",
        api_base: str | None = None,
        reasoning_effort: str | None = None,
    ):
        """Initialize LangGraph player.

        Supports two initialization patterns:

        1. Dependency Injection (NEW - Preferred):
           llm = create_llm_for_agent(...)
           tools_instance, tool_defs = create_langgraph_tools(game, "p2")
           system_prompt = get_system_prompt(verbose=False)
           player = LangGraphPlayer(
               player_id="p2", llm=llm, game=game,
               tools=tools_instance, tool_definitions=tool_defs,
               system_prompt=system_prompt, verbose=False
           )

        2. Legacy (OLD - Backward Compatible):
           player = LangGraphPlayer(
               "p2", use_mock=False, provider="bedrock",
               model="haiku", verbose=False
           )

        Args:
            player_id: Player ID ("p1" or "p2", default: "p2")

            Dependency injection params (NEW):
            llm: Raw LLM instance (ChatBedrockConverse, ChatAnthropic, etc.)
            game: Game object reference
            tools: AgentTools instance
            tool_definitions: TOOL_DEFINITIONS list
            system_prompt: System prompt string
            verbose: Print detailed reasoning (uses more tokens)

            Legacy params (OLD - for backward compatibility):
            use_mock: Use mock client instead of real LLM (for testing)
            provider: LLM provider ("bedrock", "openai", "anthropic", "ollama")
            model: Model name (provider-specific) or None for provider default
            region: AWS region (for Bedrock, default: us-east-1)
            api_base: API base URL (for Ollama)
            reasoning_effort: Nova reasoning effort ("low", "medium", "high", or None)
        """
        self.player_id = player_id
        self.verbose = verbose

        # Store injected dependencies
        self.game = game
        self.tools = tools
        self.tool_definitions = (
            tool_definitions if tool_definitions is not None else TOOL_DEFINITIONS
        )
        self.system_prompt = system_prompt

        # Dual path: injected LLM or create client wrapper
        if llm is not None:
            # NEW PATH: Use injected raw LLM
            self.llm = llm
            self.client = None  # No wrapper when using raw LLM

            # Extract model name for logging
            llm_model = (
                getattr(llm, "model_id", None)  # ChatBedrockConverse
                or getattr(llm, "model", None)  # ChatAnthropic, ChatOllama
                or getattr(llm, "model_name", None)  # ChatOpenAI
                or "unknown"
            )
            logger.info(
                f"LangGraphPlayer initialized for {player_id} with injected LLM: {llm_model}"
            )
        else:
            # OLD PATH: Create LangChainClient wrapper
            self.llm = None

            if use_mock:
                self.client = MockLangChainClient(
                    provider=provider, model_id=model, reasoning_effort=reasoning_effort
                )
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
                        reasoning_effort=reasoning_effort,
                    )
                    logger.info(f"Initialized {provider} client: {self.client.model_id}")
                except Exception as e:
                    logger.error(f"Failed to initialize {provider} client: {e}")
                    logger.info("Falling back to mock client")
                    self.client = MockLangChainClient(
                        provider=provider, model_id=model, reasoning_effort=reasoning_effort
                    )

        # Build the state graph
        self.graph = self._build_graph()

        # Strategic logger (initialized on first turn)
        self.strategic_logger: StrategicLogger | None = None

    def _convert_raw_llm_response_to_internal(self, ai_message: AIMessage) -> dict:
        """Convert raw LLM AIMessage to internal LLMResponse format.

        Extracts tool_calls, content blocks, and usage metadata from AIMessage
        and returns a dict compatible with existing code expecting LLMResponse.

        Args:
            ai_message: AIMessage from raw LLM invoke

        Returns:
            Dict with keys: content_blocks, requires_tool_execution, tool_calls,
            stop_reason, response, usage_metadata
        """
        # Extract content blocks
        content_blocks = []
        if isinstance(ai_message.content, str):
            if ai_message.content.strip():
                content_blocks.append({"type": "text", "text": ai_message.content})
        elif isinstance(ai_message.content, list):
            # Already in block format
            content_blocks = ai_message.content

        # Extract tool calls
        tool_calls = []
        requires_tool_execution = False

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            requires_tool_execution = True
            # Convert LangChain tool_calls format to our format
            # LangChain: {"name": ..., "args": ..., "id": ..., "type": "tool_call"}
            # Our format: {"name": ..., "input": ..., "id": ...}
            for tc in ai_message.tool_calls:
                tool_calls.append(
                    {
                        "name": tc.get("name"),
                        "input": tc.get("args", {}),  # Convert "args" to "input"
                        "id": tc.get("id"),
                    }
                )

        # Extract usage metadata
        usage = self._extract_usage_metadata(ai_message)

        # Build response dict
        response_text = ""
        if isinstance(ai_message.content, str):
            response_text = ai_message.content
        elif isinstance(ai_message.content, list):
            # Extract text from blocks
            text_parts = []
            for block in ai_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            response_text = "\n".join(text_parts)

        return {
            "content_blocks": content_blocks,
            "requires_tool_execution": requires_tool_execution,
            "tool_calls": tool_calls,
            "stop_reason": "end_turn" if not requires_tool_execution else "tool_use",
            "response": response_text,
            "usage_metadata": usage,
        }

    def _extract_usage_metadata(self, ai_message: AIMessage) -> dict:
        """Extract token usage from AIMessage.

        Handles both usage_metadata and additional_kwargs["usage"] formats.

        Args:
            ai_message: AIMessage from LLM

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        usage = {}

        if hasattr(ai_message, "usage_metadata") and ai_message.usage_metadata:
            # LangChain's usage_metadata attribute
            usage = {
                "input_tokens": ai_message.usage_metadata.get("input_tokens", 0),
                "output_tokens": ai_message.usage_metadata.get("output_tokens", 0),
                "total_tokens": ai_message.usage_metadata.get("total_tokens", 0),
            }
        elif hasattr(ai_message, "additional_kwargs") and "usage" in ai_message.additional_kwargs:
            # Usage in additional_kwargs
            u = ai_message.additional_kwargs["usage"]
            usage = {
                "input_tokens": u.get("prompt_tokens", u.get("input_tokens", 0)),
                "output_tokens": u.get("completion_tokens", u.get("output_tokens", 0)),
                "total_tokens": u.get("total_tokens", 0),
            }

        return usage

    def _convert_tools_to_langchain(self, tools: list[dict]) -> list[dict]:
        """Convert tool definitions to LangChain bind_tools format.

        Our TOOL_DEFINITIONS format uses "input_schema" with JSON Schema.
        LangChain expects similar format for bind_tools.

        Args:
            tools: List of tool definition dicts from TOOL_DEFINITIONS

        Returns:
            List of tool defs in LangChain format
        """
        # TOOL_DEFINITIONS format is already compatible with LangChain bind_tools
        # Just return as-is (both use JSON Schema with "name", "description", "input_schema")
        return tools

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

        # Use injected system prompt if available, otherwise generate it
        if self.system_prompt is not None:
            system_prompt = self.system_prompt
        else:
            # Legacy path: generate system prompt
            system_prompt = get_system_prompt(verbose=self.verbose)

        # Inject threat vector analysis if available (from previous observation)
        threat_vectors = state.get("_threat_vectors", [])
        if threat_vectors:
            threat_injection = inject_threat_vector_analysis(threat_vectors)
            if threat_injection:
                logger.debug("Injecting threat vector analysis into system prompt")
                system_prompt += "\n\n" + threat_injection

        # Invoke LLM with all available tools
        try:
            if self.llm is not None:
                # NEW PATH: Use raw LLM with bind_tools
                # Build messages: [SystemMessage, ...conversation...]
                from langchain_core.messages import SystemMessage

                lc_messages = state["messages"]
                full_messages = [SystemMessage(content=system_prompt)] + lc_messages

                # Bind tools to LLM
                lc_tools = self._convert_tools_to_langchain(self.tool_definitions)
                llm_with_tools = self.llm.bind_tools(lc_tools)

                # Invoke and convert response
                ai_message = llm_with_tools.invoke(full_messages)
                response = self._convert_raw_llm_response_to_internal(ai_message)
            else:
                # OLD PATH: Use LangChainClient wrapper
                # Convert messages to format expected by LangChain client
                messages_for_client = self._convert_messages_for_client(state["messages"])

                response = self.client.invoke(
                    messages=messages_for_client,
                    system=system_prompt,
                    tools=self.tool_definitions,
                    max_iterations=1,
                )

            # Create view for easier inspection
            view = ResponseView.from_response(response)

            # Log LLM response at INFO level (only for tool-using responses)
            if response.get("requires_tool_execution"):
                logger.info("=" * 80)
                logger.info("LLM RESPONSE:")
                logger.info("=" * 80)
                if view.text:
                    logger.info(view.text)
                if view.reasoning:
                    logger.info(f"[REASONING] {view.reasoning}")
                if view.has_tool_calls():
                    for tool_call in view.tool_calls:
                        logger.info(
                            f"[TOOL CALL] {tool_call['name']} with input: {tool_call['input']}"
                        )
                if view.usage:
                    logger.info(f"[USAGE] {view.format_usage()}")
                logger.info("=" * 80)

            # Parse response and update state
            if response.get("requires_tool_execution"):
                # LLM wants to use tools
                content_blocks = response["content_blocks"]

                # Filter content blocks to exclude tool_use blocks (they'll be in tool_calls)
                # Only keep text and reasoning_content blocks for the message content
                filtered_content = [
                    block
                    for block in content_blocks
                    if block.get("type") in ("text", "reasoning_content")
                ]

                # Extract tool calls from response
                tool_calls = response.get("tool_calls", [])

                # Convert our tool calls format to LangChain format for native attribute
                # Our format: {"name": ..., "input": ..., "id": ...}
                # LangChain format: {"name": ..., "args": ..., "id": ..., "type": "tool_call"}
                langchain_tool_calls = [
                    {
                        "name": tc["name"],
                        "args": tc.get("input", {}),  # Convert "input" to "args"
                        "id": tc["id"],  # ID is now guaranteed to exist
                        "type": "tool_call",
                    }
                    for tc in tool_calls
                ]

                # Add assistant message to state with native tool_calls attribute in LangChain format
                ai_message = AIMessage(
                    content=filtered_content if filtered_content else "",
                    tool_calls=langchain_tool_calls,  # Use LangChain format
                )
                # Also store our format in additional_kwargs for tool execution
                ai_message.additional_kwargs["tool_calls"] = tool_calls

                return {
                    **state,
                    "messages": [*state["messages"], ai_message],
                }
            else:
                # LLM finished without tools
                response_text = response.get("response", "")
                ai_message = AIMessage(content=response_text)

                # Log final response at INFO level
                logger.info("=" * 80)
                logger.info("LLM FINAL RESPONSE:")
                logger.info("=" * 80)
                logger.info(response_text)
                if view.usage:
                    logger.info(f"[USAGE] {view.format_usage()}")
                logger.info("=" * 80)
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

        # Extract tool calls from message (prefer additional_kwargs for our format)
        tool_calls = []

        if "tool_calls" in last_message.additional_kwargs:
            # Tool calls in metadata (our format with "input" key)
            tool_calls = last_message.additional_kwargs["tool_calls"]
            logger.debug(f"Found {len(tool_calls)} tool calls in additional_kwargs")
        elif isinstance(last_message.content, list):
            # Fallback: Content blocks format (shouldn't happen after our fix)
            for block in last_message.content:
                if block.get("type") == "tool_use":
                    tool_calls.append(block)
            if tool_calls:
                logger.debug(f"Found {len(tool_calls)} tool calls in content blocks")

        if not tool_calls:
            logger.warning("No tool calls found in last message")
            logger.debug(f"Message content type: {type(last_message.content)}")
            logger.debug(f"additional_kwargs keys: {last_message.additional_kwargs.keys()}")
            return state

        logger.info(f"Executing {len(tool_calls)} tool call(s)")

        # Get AgentTools instance from state (should be set by get_orders)
        tools = state.get("_tools_instance")
        if not tools:
            logger.error("No AgentTools instance in state")
            return state

        # Execute each tool
        tool_results = []
        orders_submitted = False

        # Critical tools that should halt execution on failure
        CRITICAL_TOOLS = {"submit_orders"}  # noqa: N806

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            # ID is guaranteed to exist from langchain_client
            tool_use_id = tool_call["id"]

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

        # Update game context with orders_submitted flag
        updated_game_context = state.get("game_context", {})
        if orders_submitted:
            updated_game_context = {
                **updated_game_context,
                "orders_submitted": True,
            }

        # Log tool results at INFO level
        logger.info("=" * 80)
        logger.info("TOOL RESULTS:")
        logger.info("=" * 80)
        for result in tool_results:
            if result.get("type") == "tool_result":
                content = result.get("content", "")
                if isinstance(content, str):
                    # Try to parse JSON for pretty printing
                    try:
                        parsed = json.loads(content)
                        logger.info(json.dumps(parsed, indent=2))
                    except Exception:
                        logger.info(content)
                else:
                    logger.info(str(content))
        logger.info("=" * 80)

        # Add tool results to messages
        tool_result_message = HumanMessage(content=tool_results)

        # Reset error tracking on successful execution
        state = reset_error_tracking(state)

        return {
            **state,
            "game_context": updated_game_context,
            "messages": [*state["messages"], tool_result_message],
        }

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

        # Check for tool calls in LangChain's tool_calls attribute or additional_kwargs
        has_tool_calls = False

        # Check LangChain's native tool_calls attribute (set by ChatBedrockConverse)
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            has_tool_calls = True
            logger.debug(
                f"Routing: found {len(last_message.tool_calls)} tool calls in tool_calls attribute"
            )
        # Fallback: check additional_kwargs (where we store tool_calls for routing)
        elif "tool_calls" in last_message.additional_kwargs:
            tool_calls_list = last_message.additional_kwargs["tool_calls"]
            has_tool_calls = len(tool_calls_list) > 0
            logger.debug(f"Routing: found {len(tool_calls_list)} tool calls in additional_kwargs")

        decision = "continue" if has_tool_calls else "end"
        logger.debug(f"Routing decision: {decision} (has_tool_calls={has_tool_calls})")
        return decision

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
                # For AIMessage, check if it has tool calls
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    # Build content blocks with text and tool_use blocks
                    content_blocks = []

                    # Extract text from content if it's a list of blocks
                    text_content = msg.content
                    if isinstance(text_content, list):
                        # Extract text from content blocks
                        text_parts = []
                        for block in text_content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                        text_content = "\n".join(text_parts) if text_parts else ""

                    # Add text block if there's text
                    if text_content:
                        content_blocks.append({"type": "text", "text": text_content})

                    # Add tool_use blocks from tool_calls
                    for tc in msg.tool_calls:
                        content_blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc.get("id", "unknown"),
                                "name": tc.get("name"),
                                "input": tc.get("args", {}),
                            }
                        )

                    converted.append({"role": "assistant", "content": content_blocks})
                else:
                    # No tool calls - simple text content
                    content = msg.content
                    if isinstance(content, list):
                        # Extract text from content blocks
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                        content = "\n".join(text_parts) if text_parts else ""

                    converted.append({"role": "assistant", "content": content})
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

        # Use injected tools if available, otherwise create them (legacy path)
        if self.tools is not None:
            tools = self.tools
            tools.game = game  # Update game reference (mutated each turn)
            tools.reset_turn()
        else:
            # Legacy path: create AgentTools
            tools = AgentTools(game, self.player_id)
            tools.reset_turn()

        # Import format function
        from .prompts import format_game_state_prompt

        # Format game state as text
        formatted_state = format_game_state_prompt(game, self.player_id)

        # Log compact JSON (indent=1 for better readability without huge output)
        logger.info("=" * 80)
        logger.info(f"USER PROMPT (Turn {game.turn}):")
        logger.info("=" * 80)
        try:
            import json

            state_data = json.loads(formatted_state)
            # Re-serialize with compact indent
            compact_json = json.dumps(state_data, indent=1)
            logger.info(compact_json)
        except Exception:
            # Fallback if JSON parsing fails
            logger.info(formatted_state)
        logger.info("=" * 80)

        # Create initial state with formatted game state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=formatted_state)],
            "game_context": {
                "orders_submitted": False,
            },
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

        # Get orders from tools (if submit_orders was called)
        orders = tools.get_pending_orders()

        # If no orders, LLM is passing the turn
        if orders is None:
            logger.info("No orders submitted (LLM passed turn or failed to call submit_orders)")
            return []

        logger.info(f"Returning {len(orders)} order(s)")
        for order in orders:
            logger.debug(f"  - {order.ships} ships: {order.from_star} -> {order.to_star}")

        # Log strategic metrics for this turn (always-on)
        self._log_strategic_metrics(game)

        return orders

    def _log_strategic_metrics(self, game: Game) -> None:
        """Log strategic metrics for this turn.

        Initializes the logger on first call and logs metrics to JSONL.
        Errors in logging do not interrupt gameplay.

        Args:
            game: Current game state
        """
        # Initialize logger on first turn
        if self.strategic_logger is None:
            game_id = f"seed{game.seed}_{self.player_id}_turn{game.turn}"
            try:
                self.strategic_logger = StrategicLogger(game_id)
                logger.debug(f"Initialized strategic logger: {self.strategic_logger.log_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize strategic logger: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                return

        # Calculate and log metrics
        try:
            metrics = calculate_strategic_metrics(game, self.player_id, game.turn)
            self.strategic_logger.log_turn(metrics)
            logger.debug(f"Logged strategic metrics for turn {game.turn}")
        except Exception as e:
            # Don't fail the game if logging fails
            logger.warning(
                f"Failed to log strategic metrics for turn {game.turn}: {type(e).__name__}: {e}",
                exc_info=True,
            )

    def close(self) -> None:
        """Clean up resources.

        Closes the strategic logger if initialized.
        Should be called when the game ends.
        """
        if self.strategic_logger:
            self.strategic_logger.close()
