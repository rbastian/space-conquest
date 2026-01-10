"""GraphReactPlayer - LangGraph-based player with structured decision workflow.

This player uses LangGraph's StateGraph to enforce a specific decision-making
order, preventing strategic failures like:
- Ignoring immediate victory/defeat scenarios
- Leaving home star vulnerable while expanding
- Not prioritizing threats correctly

The graph structure ensures decisions are made in priority order:
START → Victory/Defeat Check → Threat Assessment → Victory Opportunity
  → Expansion Planning → Validation → END
"""

import json
import logging
import re
from operator import add
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from ..analysis import calculate_strategic_metrics
from ..analysis.strategic_logger import StrategicLogger
from ..models.game import Game
from ..models.order import Order

logger = logging.getLogger(__name__)


class DecisionState(TypedDict):
    """State that accumulates through the decision graph.

    This state is passed between nodes and accumulates information
    at each step of the decision-making process.
    """

    # Input (set at start)
    game_state_json: str  # JSON formatted game state
    player_id: str
    current_turn: int

    # Tools and LLM (injected)
    tools: dict  # Map of tool name to tool function
    llm: object  # LLM instance

    # Node 1: Victory/Defeat Check outputs
    immediate_victory_possible: bool
    immediate_defeat_risk: bool
    home_defense_adequate: bool
    victory_check_reasoning: str

    # Node 2: Threat Assessment outputs
    identified_threats: list[dict]
    defensive_orders: Annotated[list[dict], add]  # Accumulates
    threat_assessment_reasoning: str

    # Node 3: Victory Opportunity outputs
    opponent_home_attack_viable: bool
    attack_plan: dict | None
    attack_orders: Annotated[list[dict], add]  # Accumulates
    victory_opportunity_reasoning: str

    # Node 4: Expansion Planning outputs
    expansion_targets: list[dict]
    expansion_orders: Annotated[list[dict], add]  # Accumulates
    expansion_reasoning: str

    # Node 5: Validation outputs
    all_orders: list[dict]  # Combined from all sources
    validation_results: dict
    final_orders_json: str  # JSON string to be parsed

    # Control flow
    skip_to_validation: bool  # If true, skip some nodes (emergency)

    # Tool tracking
    tool_calls_made: Annotated[list[str], add]  # Tool names called across all nodes


def _extract_json_from_content(content: str | list) -> dict | None:
    """Extract JSON from AI message content.

    Handles both string content and structured content blocks.

    Args:
        content: AI message content (string or list of blocks)

    Returns:
        Parsed JSON dict or None if parsing fails
    """
    # Extract text from content
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        # Extract text from content blocks
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")

    # Try to find JSON in text
    # Look for {...} pattern
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Content: {json_match.group()}")

    return None


def victory_defeat_check_node(state: DecisionState, config: RunnableConfig) -> dict:
    """Node 1: Check for immediate win/loss scenarios.

    Focused on THIS turn only:
    - Can I win by capturing opponent's home?
    - Is my home under attack?
    - Is my home defense adequate?

    Args:
        state: Current decision state
        config: LangGraph config

    Returns:
        Updated state dict with victory/defeat check results
    """
    logger.info("=" * 80)
    logger.info("NODE 1: VICTORY/DEFEAT CHECK")
    logger.info("=" * 80)

    system_prompt = """You are analyzing victory/defeat conditions for THIS turn only.

CRITICAL: The ONLY way to win is to capture the opponent's HOME STAR.
CRITICAL: If your HOME STAR is captured, you LOSE INSTANTLY.

Your ONLY job in this step is to answer:
1. Can I capture opponent's home THIS turn? (Do I have a fleet arriving with sufficient force?)
2. Is my home being attacked THIS turn? (Could enemy fleets arrive at my home this turn?)
3. Is my home defense adequate?

To assess home defense:

IMPORTANT: Enemy fleets in hyperspace are INVISIBLE. You cannot see them in transit.
You must INFER threats from last known positions.

Threat assessment steps:
1. Check opponent.last_known_positions for historical enemy intel
2. For EACH enemy position, calculate the threat:
   - distance_from_home: How far that enemy position is from your home
   - turns_ago: How many turns since that enemy was observed there
   - CRITICAL LOGIC: If turns_ago >= distance_from_home, that enemy fleet COULD be attacking your home THIS turn!

Example threat calculation:
  - Enemy position: 39 ships at star X
  - distance_from_home: 2 turns
  - turns_ago: 2 turns
  - Analysis: 2 >= 2, so those 39 ships COULD arrive THIS turn!
  - Action: Ensure home garrison can defend against 39 ships

3. Check opponent.visible_stars for current enemy garrisons at nearby stars
4. Use calculate_distance tool to verify distances if needed
5. Check your current home garrison
6. Consider home production (check your home star's RU value)

Defense adequacy:
- Your home garrison should be >= largest potential threat
- Account for production this turn (home produces RU ships per turn)
- If multiple threats possible, assume worst case (largest fleet)

If both sides are attacking each other's homes, calculate who wins the race.

Output your analysis as JSON:
{
    "immediate_victory_possible": true/false,
    "immediate_defeat_risk": true/false,
    "home_defense_adequate": true/false,
    "reasoning": "explanation including: threats identified from last_known_positions, threat calculations (turns_ago vs distance), home garrison strength, and defense assessment"
}
"""

    # Build messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["game_state_json"]),
    ]

    # Bind tools (calculate_distance, get_nearby_garrisons)
    tools_to_bind = []
    for tool_name in ["calculate_distance", "get_nearby_garrisons"]:
        if tool_name in state["tools"]:
            tools_to_bind.append(state["tools"][tool_name])

    llm = state["llm"]
    if tools_to_bind:
        llm = llm.bind_tools(tools_to_bind)

    # Run agent loop with tools
    max_iterations = 5
    for iteration in range(max_iterations):
        logger.info(f"Victory check iteration {iteration + 1}/{max_iterations}")

        # Invoke LLM
        ai_message = llm.invoke(messages)
        messages.append(ai_message)

        # Check if LLM wants to use tools
        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            # Execute tools
            tool_results = []
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"  Calling tool: {tool_name}")

                try:
                    # Get tool function
                    tool_func = state["tools"].get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Tool {tool_name} not found")

                    # Execute tool
                    result = tool_func.invoke(tool_args)

                    # Track tool usage
                    if "tool_calls_made" not in state:
                        state["tool_calls_made"] = []
                    state["tool_calls_made"].append(tool_name)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            # Add tool results to messages
            messages.append(HumanMessage(content=tool_results))
        else:
            # LLM finished, extract response
            break

    # Parse final response
    result = _extract_json_from_content(ai_message.content)

    if result:
        logger.info(f"Victory check result: {json.dumps(result, indent=2)}")
        return {
            "immediate_victory_possible": result.get("immediate_victory_possible", False),
            "immediate_defeat_risk": result.get("immediate_defeat_risk", False),
            "home_defense_adequate": result.get("home_defense_adequate", True),
            "victory_check_reasoning": result.get("reasoning", ""),
        }
    else:
        logger.warning("Failed to parse victory check response, using safe defaults")
        return {
            "immediate_victory_possible": False,
            "immediate_defeat_risk": False,
            "home_defense_adequate": True,
            "victory_check_reasoning": "Failed to parse response",
        }


def threat_assessment_node(state: DecisionState, config: RunnableConfig) -> dict:
    """Node 2: Assess threats to player's territory.

    Focused on:
    - What enemy fleets are incoming?
    - Which stars are at risk?
    - What reinforcements are needed?

    Args:
        state: Current decision state
        config: LangGraph config

    Returns:
        Updated state dict with threat assessment results
    """
    logger.info("=" * 80)
    logger.info("NODE 2: THREAT ASSESSMENT")
    logger.info("=" * 80)

    system_prompt = """You are analyzing threats to your territory.

IMPORTANT: Enemy fleets in hyperspace are INVISIBLE. You cannot see them in transit.

Your job:
1. Review opponent.visible_stars for current enemy garrison positions
2. Review opponent.last_known_positions for historical enemy intel (may be outdated)
3. Check recent_events.combat_reports for attacks that just occurred
4. Assess which of YOUR stars are most vulnerable based on:
   - Enemy garrison size at nearby stars
   - Distance from enemy positions to your stars
   - Your current garrison strength
5. Plan defensive orders if needed to reinforce vulnerable positions

Defense priority: Home > High production stars > Frontier stars

Threat assessment is based on:
- Enemy garrison strength at known positions
- Proximity to your territory
- Your garrison adequacy
NOT on seeing enemy fleets in transit (which is impossible)

IMPORTANT: Only plan defensive orders if actually needed. If no threats exist, return empty defensive_orders list.

Output as JSON:
{
    "threats": [
        {
            "your_star": "A",
            "enemy_nearby": "Enemy garrison of 20 at star X (distance 3)",
            "current_garrison": 10,
            "reinforcement_needed": 15,
            "reasoning": "why this star is threatened"
        }
    ],
    "defensive_orders": [
        {"from": "B", "to": "A", "ships": 15, "rationale": "reinforce"}
    ],
    "reasoning": "overall threat assessment"
}
"""

    # Build messages
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["game_state_json"]),
    ]

    # Bind tools
    tools_to_bind = []
    for tool_name in ["get_nearby_garrisons", "calculate_distance"]:
        if tool_name in state["tools"]:
            tools_to_bind.append(state["tools"][tool_name])

    llm = state["llm"]
    if tools_to_bind:
        llm = llm.bind_tools(tools_to_bind)

    # Run agent loop
    max_iterations = 5
    for iteration in range(max_iterations):
        logger.info(f"Threat assessment iteration {iteration + 1}/{max_iterations}")

        ai_message = llm.invoke(messages)
        messages.append(ai_message)

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            tool_results = []
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"  Calling tool: {tool_name}")

                try:
                    tool_func = state["tools"].get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Tool {tool_name} not found")

                    result = tool_func.invoke(tool_args)

                    # Track tool usage
                    if "tool_calls_made" not in state:
                        state["tool_calls_made"] = []
                    state["tool_calls_made"].append(tool_name)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            messages.append(HumanMessage(content=tool_results))
        else:
            break

    # Parse response
    result = _extract_json_from_content(ai_message.content)

    if result:
        logger.info(f"Threat assessment result: {json.dumps(result, indent=2)}")
        return {
            "identified_threats": result.get("threats", []),
            "defensive_orders": result.get("defensive_orders", []),
            "threat_assessment_reasoning": result.get("reasoning", ""),
        }
    else:
        logger.warning("Failed to parse threat assessment response")
        return {
            "identified_threats": [],
            "defensive_orders": [],
            "threat_assessment_reasoning": "Failed to parse response",
        }


def victory_opportunity_node(state: DecisionState, config: RunnableConfig) -> dict:
    """Node 3: Assess if opponent's home can be attacked.

    Focused on:
    - Where is opponent's home?
    - Can I attack it in next 2-3 turns?
    - What force is needed? Do I have it?
    - What's the safest route?

    Args:
        state: Current decision state
        config: LangGraph config

    Returns:
        Updated state dict with victory opportunity results
    """
    logger.info("=" * 80)
    logger.info("NODE 3: VICTORY OPPORTUNITY")
    logger.info("=" * 80)

    system_prompt = """You are planning an attack on the opponent's HOME STAR.

Capturing their home = instant victory!

Your job:
1. Check if opponent home is discovered in game_state
2. If yes, assess opponent home garrison strength:
   - Check opponent.visible_stars for current garrison (if recently visited)
   - Check opponent.last_known_positions for historical intel
   - If garrison unknown or outdated (>3 turns old), consider 1-ship probe
3. Calculate distance and required force
4. Check if you have sufficient ships nearby (use get_nearby_garrisons)
5. Plan safest route (use find_safest_route for long distances)
6. CRITICAL: Ensure your home remains defended if you attack

Note: If opponent home garrison is unknown, a 1-ship probe can provide valuable intel.
Only probe ENEMY-controlled stars (not NPC stars, which have garrison = base_ru).

Only plan attack if:
- You have overwhelming force (2x their expected garrison)
- Your home will remain adequately defended
- Route is reasonably safe

Output as JSON:
{
    "attack_viable": true/false,
    "attack_plan": {
        "target": "H",
        "required_force": 30,
        "available_force": 45,
        "route": ["A", "M", "H"],
        "arrival_turn": 25
    },
    "attack_orders": [
        {"from": "A", "to": "H", "ships": 30, "rationale": "attack"}
    ],
    "reasoning": "explanation"
}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["game_state_json"]),
    ]

    # Bind tools
    tools_to_bind = []
    for tool_name in ["find_safest_route", "calculate_distance", "get_nearby_garrisons"]:
        if tool_name in state["tools"]:
            tools_to_bind.append(state["tools"][tool_name])

    llm = state["llm"]
    if tools_to_bind:
        llm = llm.bind_tools(tools_to_bind)

    # Run agent loop
    max_iterations = 5
    for iteration in range(max_iterations):
        logger.info(f"Victory opportunity iteration {iteration + 1}/{max_iterations}")

        ai_message = llm.invoke(messages)
        messages.append(ai_message)

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            tool_results = []
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"  Calling tool: {tool_name}")

                try:
                    tool_func = state["tools"].get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Tool {tool_name} not found")

                    result = tool_func.invoke(tool_args)

                    # Track tool usage
                    if "tool_calls_made" not in state:
                        state["tool_calls_made"] = []
                    state["tool_calls_made"].append(tool_name)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            messages.append(HumanMessage(content=tool_results))
        else:
            break

    # Parse response
    result = _extract_json_from_content(ai_message.content)

    if result:
        logger.info(f"Victory opportunity result: {json.dumps(result, indent=2)}")
        return {
            "opponent_home_attack_viable": result.get("attack_viable", False),
            "attack_plan": result.get("attack_plan"),
            "attack_orders": result.get("attack_orders", []),
            "victory_opportunity_reasoning": result.get("reasoning", ""),
        }
    else:
        logger.warning("Failed to parse victory opportunity response")
        return {
            "opponent_home_attack_viable": False,
            "attack_plan": None,
            "attack_orders": [],
            "victory_opportunity_reasoning": "Failed to parse response",
        }


def expansion_planning_node(state: DecisionState, config: RunnableConfig) -> dict:
    """Node 4: Plan expansion to neutral/NPC stars.

    Focused on:
    - What nearby stars can I capture?
    - Which give best economic value?
    - Do I have spare forces after defense?

    Args:
        state: Current decision state
        config: LangGraph config

    Returns:
        Updated state dict with expansion planning results
    """
    logger.info("=" * 80)
    logger.info("NODE 4: EXPANSION PLANNING")
    logger.info("=" * 80)

    system_prompt = """You are planning territorial expansion.

IMPORTANT: Expansion is LOWEST priority. Only expand if:
- Home is safe (checked in previous steps)
- No immediate threats (checked in previous steps)
- You have spare forces

Your job:
1. Review game_state for neutral/NPC stars
2. Identify nearby, valuable targets (high RU, low distance)
3. For NPC stars: garrison = base_ru (visible in game state)
4. Calculate required force: send 2x the NPC garrison for safe capture
5. Plan expansion orders with remaining forces

Note: Probing is NOT needed for NPC stars - their garrison equals their base_ru value,
which is visible in the game state (maximum 3 ships).

Output as JSON:
{
    "expansion_targets": [
        {"star": "N", "distance": 3, "ru": 4, "required_force": 15}
    ],
    "expansion_orders": [
        {"from": "A", "to": "N", "ships": 15, "rationale": "expand"}
    ],
    "reasoning": "explanation"
}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["game_state_json"]),
    ]

    # Bind tools
    tools_to_bind = []
    for tool_name in ["calculate_distance", "get_nearby_garrisons"]:
        if tool_name in state["tools"]:
            tools_to_bind.append(state["tools"][tool_name])

    llm = state["llm"]
    if tools_to_bind:
        llm = llm.bind_tools(tools_to_bind)

    # Run agent loop
    max_iterations = 5
    for iteration in range(max_iterations):
        logger.info(f"Expansion planning iteration {iteration + 1}/{max_iterations}")

        ai_message = llm.invoke(messages)
        messages.append(ai_message)

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            tool_results = []
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"  Calling tool: {tool_name}")

                try:
                    tool_func = state["tools"].get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Tool {tool_name} not found")

                    result = tool_func.invoke(tool_args)

                    # Track tool usage
                    if "tool_calls_made" not in state:
                        state["tool_calls_made"] = []
                    state["tool_calls_made"].append(tool_name)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            messages.append(HumanMessage(content=tool_results))
        else:
            break

    # Parse response
    result = _extract_json_from_content(ai_message.content)

    if result:
        logger.info(f"Expansion planning result: {json.dumps(result, indent=2)}")
        return {
            "expansion_targets": result.get("expansion_targets", []),
            "expansion_orders": result.get("expansion_orders", []),
            "expansion_reasoning": result.get("reasoning", ""),
        }
    else:
        logger.warning("Failed to parse expansion planning response")
        return {
            "expansion_targets": [],
            "expansion_orders": [],
            "expansion_reasoning": "Failed to parse response",
        }


def validation_finalization_node(state: DecisionState, config: RunnableConfig) -> dict:
    """Node 5: Combine all orders, validate, and finalize.

    Focused on:
    - Combine defensive_orders + attack_orders + expansion_orders
    - Use validate_orders tool to check legality
    - Final-check home security
    - Output final orders as JSON array

    Args:
        state: Current decision state
        config: LangGraph config

    Returns:
        Updated state dict with final validated orders
    """
    logger.info("=" * 80)
    logger.info("NODE 5: VALIDATION & FINALIZATION")
    logger.info("=" * 80)

    # Combine all orders
    all_orders = []
    all_orders.extend(state.get("defensive_orders", []))
    all_orders.extend(state.get("attack_orders", []))
    all_orders.extend(state.get("expansion_orders", []))

    logger.info(f"Combined {len(all_orders)} orders from all nodes")
    logger.info(f"  Defensive: {len(state.get('defensive_orders', []))}")
    logger.info(f"  Attack: {len(state.get('attack_orders', []))}")
    logger.info(f"  Expansion: {len(state.get('expansion_orders', []))}")

    if not all_orders:
        logger.info("No orders to validate, passing turn")
        return {
            "all_orders": [],
            "validation_results": {"valid": True, "summary": "No orders (pass turn)"},
            "final_orders_json": "[]",
        }

    system_prompt = """You are finalizing and validating all orders.

CONFLICT RESOLUTION PRIORITY (when ship availability conflicts):
1. DEFENSIVE orders (protect home, reinforce threatened stars) - HIGHEST PRIORITY
   - Never reduce defensive orders if home is threatened
   - Home defense is non-negotiable
2. ATTACK orders (capture opponent home) - HIGH PRIORITY
   - Winning the game takes precedence over expansion
   - Only reduce if absolutely necessary
3. EXPANSION orders (capture new stars, economic growth) - LOWER PRIORITY
   - Can be reduced or cancelled to free ships for defense/attack
   - Growth is important but not at cost of losing

Your job:
1. Combine all orders from previous steps
2. Use validate_orders tool to check all orders are legal
3. If validation fails due to ship conflicts, apply priority rules:
   - Reduce/cancel EXPANSION orders first
   - Then reduce ATTACK orders if still needed
   - Only reduce DEFENSIVE orders as absolute last resort
4. Output final orders as JSON array

Output format (this will be parsed by the game):
[
    {"from": "A", "to": "B", "ships": 10, "rationale": "reinforce"},
    {"from": "C", "to": "D", "ships": 15, "rationale": "attack"}
]
"""

    # Build validation request message
    validation_request = f"""All orders to validate:
{json.dumps(all_orders, indent=2)}

Please validate these orders and output the final valid orders as a JSON array."""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=validation_request)]

    # Bind validate_orders tool
    tools_to_bind = []
    if "validate_orders" in state["tools"]:
        tools_to_bind.append(state["tools"]["validate_orders"])

    llm = state["llm"]
    if tools_to_bind:
        llm = llm.bind_tools(tools_to_bind)

    # Run agent loop
    max_iterations = 5
    validation_results = {}

    for iteration in range(max_iterations):
        logger.info(f"Validation iteration {iteration + 1}/{max_iterations}")

        ai_message = llm.invoke(messages)
        messages.append(ai_message)

        if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
            tool_results = []
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                logger.info(f"  Calling tool: {tool_name}")

                try:
                    tool_func = state["tools"].get(tool_name)
                    if tool_func is None:
                        raise ValueError(f"Tool {tool_name} not found")

                    result = tool_func.invoke(tool_args)

                    # Track tool usage
                    if "tool_calls_made" not in state:
                        state["tool_calls_made"] = []
                    state["tool_calls_made"].append(tool_name)

                    # Store validation results
                    if tool_name == "validate_orders":
                        validation_results = result

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        }
                    )

                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            messages.append(HumanMessage(content=tool_results))
        else:
            break

    # Parse final response - should be JSON array of orders
    final_orders_text = ""
    if isinstance(ai_message.content, str):
        final_orders_text = ai_message.content
    elif isinstance(ai_message.content, list):
        for block in ai_message.content:
            if isinstance(block, dict) and block.get("type") == "text":
                final_orders_text += block.get("text", "")

    # Look for JSON array in response
    json_match = re.search(r"\[[\s\S]*?\]", final_orders_text)
    if json_match:
        final_orders_json = json_match.group()
        logger.info(f"Final orders: {final_orders_json}")
    else:
        # Fallback: use all_orders as JSON
        final_orders_json = json.dumps(all_orders)
        logger.warning("Could not extract JSON array from response, using all_orders")

    return {
        "all_orders": all_orders,
        "validation_results": validation_results,
        "final_orders_json": final_orders_json,
    }


def route_after_victory_check(state: DecisionState) -> Literal["threat_assessment", "validation"]:
    """Route based on victory/defeat check results.

    If immediate victory is possible or home is under critical threat,
    we might want to skip some steps and go straight to validation.

    Args:
        state: Current decision state

    Returns:
        Next node to execute
    """
    # For now, always go through normal flow
    # In future could add emergency paths
    return "threat_assessment"


def should_continue_to_expansion(
    state: DecisionState,
) -> Literal["expansion_planning", "validation"]:
    """Decide if we should do expansion or skip to validation.

    Skip expansion if:
    - Home defense is not adequate
    - Immediate defeat risk exists

    Args:
        state: Current decision state

    Returns:
        Next node to execute
    """
    # Skip expansion if home defense inadequate
    if not state.get("home_defense_adequate", True):
        logger.info("Skipping expansion (home defense inadequate)")
        return "validation"

    # Skip expansion if immediate defeat risk
    if state.get("immediate_defeat_risk", False):
        logger.info("Skipping expansion (immediate defeat risk)")
        return "validation"

    return "expansion_planning"


def create_decision_graph(llm, tools: list, player_id: str):
    """Create the decision workflow graph.

    Args:
        llm: LLM instance
        tools: List of tool functions
        player_id: Player ID

    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(DecisionState)

    # Add nodes
    graph.add_node("victory_defeat_check", victory_defeat_check_node)
    graph.add_node("threat_assessment", threat_assessment_node)
    graph.add_node("victory_opportunity", victory_opportunity_node)
    graph.add_node("expansion_planning", expansion_planning_node)
    graph.add_node("validation", validation_finalization_node)

    # Define edges
    graph.set_entry_point("victory_defeat_check")

    # Conditional routing after victory check
    graph.add_conditional_edges(
        "victory_defeat_check",
        route_after_victory_check,
        {"threat_assessment": "threat_assessment", "validation": "validation"},
    )

    # Normal flow
    graph.add_edge("threat_assessment", "victory_opportunity")

    # Conditional: skip expansion if emergency
    graph.add_conditional_edges(
        "victory_opportunity",
        should_continue_to_expansion,
        {"expansion_planning": "expansion_planning", "validation": "validation"},
    )

    graph.add_edge("expansion_planning", "validation")

    # End
    graph.add_edge("validation", END)

    return graph.compile()


class GraphReactPlayer:
    """LangGraph-based player with structured decision workflow.

    This player uses LangGraph to create a directed graph that enforces
    a specific decision-making order:
    1. Victory/Defeat Check (immediate win/loss scenarios)
    2. Threat Assessment (defend territory)
    3. Victory Opportunity (attack opponent home)
    4. Expansion Planning (capture neutral stars)
    5. Validation (combine and validate orders)

    Each node has a focused prompt and specific tools, and the agent
    MUST traverse nodes in order.
    """

    def __init__(
        self,
        llm,
        game: Game,
        player_id: str,
        tools: list,
        system_prompt: str,
        verbose: bool = False,
    ):
        """Initialize GraphReactPlayer with injected dependencies.

        Args:
            llm: LangChain ChatModel instance
            game: Game object reference
            player_id: Player ID ("p1" or "p2")
            tools: List of @tool decorated functions (from react_tools.py)
            system_prompt: System prompt text (not used by graph nodes)
            verbose: Enable verbose logging
        """
        self.llm = llm
        self.game = game
        self.player_id = player_id
        self.tools = tools
        self.system_prompt = system_prompt
        self.verbose = verbose

        # Create tools map for easy access
        self.tools_map = {tool.name: tool for tool in tools}

        # Create the decision graph
        self.graph = create_decision_graph(llm, tools, player_id)

        # Per-turn state
        self.strategic_logger = None

        # Tool usage tracking
        self._tool_usage_counts: dict[str, int] = {
            "validate_orders": 0,
            "calculate_distance": 0,
            "get_nearby_garrisons": 0,
            "find_safest_route": 0,
        }

        # Log successful initialization
        llm_model = (
            getattr(llm, "model_id", None)
            or getattr(llm, "model", None)
            or getattr(llm, "model_name", None)
            or "unknown"
        )
        logger.info(
            f"GraphReactPlayer initialized for {player_id} with {len(tools)} tools and model {llm_model}"
        )

    def get_orders(self, game: Game) -> list[Order]:
        """Main entry point - implements Player interface.

        Called each turn by game orchestrator. Runs the decision graph
        and returns validated orders.

        Args:
            game: Current game state

        Returns:
            List of Order objects for this turn
        """
        from ..agent.prompts import format_game_state_prompt

        # Format game state
        game_state_json = format_game_state_prompt(game, self.player_id)

        logger.info(f"GraphReactPlayer {self.player_id} starting turn {game.turn}")
        logger.info(f"[USER] Game state:\n{game_state_json}")

        # Initialize state
        initial_state: DecisionState = {
            "game_state_json": game_state_json,
            "player_id": self.player_id,
            "current_turn": game.turn,
            "tools": self.tools_map,
            "llm": self.llm,
            "tool_calls_made": [],
            "immediate_victory_possible": False,
            "immediate_defeat_risk": False,
            "home_defense_adequate": True,
            "victory_check_reasoning": "",
            "identified_threats": [],
            "defensive_orders": [],
            "threat_assessment_reasoning": "",
            "opponent_home_attack_viable": False,
            "attack_plan": None,
            "attack_orders": [],
            "victory_opportunity_reasoning": "",
            "expansion_targets": [],
            "expansion_orders": [],
            "expansion_reasoning": "",
            "all_orders": [],
            "validation_results": {},
            "final_orders_json": "[]",
            "skip_to_validation": False,
        }

        # Run graph
        try:
            final_state = self.graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            return []

        # Aggregate tool usage from state
        tool_calls = final_state.get("tool_calls_made", [])
        for tool_name in tool_calls:
            if tool_name in self._tool_usage_counts:
                self._tool_usage_counts[tool_name] += 1

        # Parse final orders
        orders = self._parse_orders_from_json(final_state["final_orders_json"])

        # Log orders
        logger.info(
            f"GraphReactPlayer {self.player_id} returned {len(orders)} orders for turn {game.turn}"
        )
        for order in orders:
            logger.info(
                f"  Order: {order.ships} ships from {order.from_star} to {order.to_star} ({order.rationale})"
            )

        # Log strategic metrics
        self._log_strategic_metrics(game)

        return orders

    def _parse_orders_from_json(self, orders_json: str) -> list[Order]:
        """Parse JSON orders into Order objects.

        Args:
            orders_json: JSON string with list of order dicts

        Returns:
            List of Order objects
        """
        try:
            orders_data = json.loads(orders_json)

            if not isinstance(orders_data, list):
                logger.error(f"Orders JSON is not a list: {type(orders_data)}")
                return []

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

            return orders

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse orders JSON: {e}")
            logger.error(f"Content: {orders_json}")
            return []

    def _log_strategic_metrics(self, game: Game):
        """Log strategic metrics for this turn.

        Args:
            game: Current game state
        """
        try:
            if self.strategic_logger is None:
                self.strategic_logger = StrategicLogger(self.player_id)

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
        """Cleanup strategic logger and log tool usage statistics."""
        # Log tool usage statistics
        logger.info(f"Tool usage statistics for {self.player_id}:")
        for tool_name, count in self._tool_usage_counts.items():
            logger.info(f"  {tool_name}: {count} calls")

        # Cleanup strategic logger
        if self.strategic_logger:
            self.strategic_logger.close()
