# GraphReactPlayer - Structured Decision Workflow

## Overview

GraphReactPlayer is a LangGraph-based player implementation that uses a directed graph to enforce a specific decision-making workflow for the Space Conquest game. Unlike the simpler ReactPlayer which makes decisions in an unstructured way, GraphReactPlayer ensures decisions are made in priority order through distinct graph nodes.

## Problem Statement

The current ReactPlayer agent makes decisions in an unstructured way, leading to strategic failures like:
- Ignoring immediate victory/defeat scenarios
- Leaving home star vulnerable while expanding
- Not prioritizing threats correctly

GraphReactPlayer solves these issues by enforcing a specific workflow order that CANNOT be skipped.

## Architecture

### Graph Structure

```
START → Victory/Defeat Check → Threat Assessment → Victory Opportunity
  → Expansion Planning → Validation → END
```

Each node:
- Has a focused system prompt for ONE specific task
- Uses specific tools relevant to that task
- Updates the state with its outputs
- Returns the updated state for the next node

### Decision State

The `DecisionState` TypedDict accumulates information through the graph:

```python
class DecisionState(TypedDict):
    # Input (set at start)
    game_state_json: str
    player_id: str
    current_turn: int

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
    all_orders: list[dict]
    validation_results: dict
    final_orders_json: str

    # Control flow
    skip_to_validation: bool
```

## Node Details

### Node 1: Victory/Defeat Check

**Purpose**: Check for immediate win/loss scenarios THIS turn only.

**Questions**:
1. Can I capture opponent's home THIS turn?
2. Is my home being attacked THIS turn?
3. Is my home defense adequate?

**Tools**: `calculate_distance`, `get_nearby_garrisons`

**Output**: Victory/defeat status, home defense assessment

### Node 2: Threat Assessment

**Purpose**: Assess threats to player's territory.

**Questions**:
1. What enemy fleets are incoming?
2. Which stars are at risk?
3. What reinforcements are needed?

**Tools**: `get_nearby_garrisons`, `calculate_distance`

**Output**: List of threats, defensive orders

**Priority**: Home > High production stars > Frontier stars

### Node 3: Victory Opportunity

**Purpose**: Assess if opponent's home can be attacked soon.

**Questions**:
1. Where is opponent's home?
2. Can I attack it in next 2-3 turns?
3. What force is needed? Do I have it?
4. What's the safest route?

**Tools**: `find_safest_route`, `calculate_distance`, `get_nearby_garrisons`

**Output**: Attack viability, attack plan, attack orders

**Constraints**:
- Only plan attack if you have overwhelming force (2x expected garrison)
- Your home must remain adequately defended
- Route must be reasonably safe

### Node 4: Expansion Planning

**Purpose**: Plan expansion to neutral/NPC stars.

**Questions**:
1. What nearby stars can I capture?
2. Which give best economic value?
3. Do I have spare forces after defense?

**Tools**: `calculate_distance`, `get_nearby_garrisons`

**Output**: Expansion targets, expansion orders

**Priority**: LOWEST - only expand if home is safe and no threats exist

### Node 5: Validation & Finalization

**Purpose**: Combine all orders, validate, and finalize.

**Process**:
1. Combine defensive_orders + attack_orders + expansion_orders
2. Use `validate_orders` tool to check legality
3. Final-check home security
4. Output final orders as JSON array

**Tools**: `validate_orders`

**Output**: Final validated orders as JSON string

## Conditional Routing

### After Victory Check

```python
def route_after_victory_check(state: DecisionState) -> Literal["threat_assessment", "validation"]:
    # For now, always go through normal flow
    # Future: add emergency paths for critical situations
    return "threat_assessment"
```

### After Victory Opportunity

```python
def should_continue_to_expansion(state: DecisionState) -> Literal["expansion_planning", "validation"]:
    # Skip expansion if home defense inadequate
    if not state.get("home_defense_adequate", True):
        return "validation"

    # Skip expansion if immediate defeat risk
    if state.get("immediate_defeat_risk", False):
        return "validation"

    return "expansion_planning"
```

## Usage

### Command Line

```bash
# Human vs GraphReactPlayer
uv run python game.py --mode hvl --agent graph-react

# GraphReactPlayer vs GraphReactPlayer
uv run python game.py --mode lvl --agent graph-react

# Mixed agents (GraphReact vs React)
uv run python game.py --mode lvl --p1-agent graph-react --p2-agent react

# With specific model
uv run python game.py --mode hvl --agent graph-react --provider bedrock --model claude-3-5-sonnet-20241022
```

### Programmatic

```python
from src.agent.graph_react_player import GraphReactPlayer
from src.agent.react_tools import create_react_tools
from src.agent.prompts import get_system_prompt
from src.agent.llm_factory import LLMFactory

# Create LLM
llm = LLMFactory.create_llm_for_agent(
    provider="bedrock",
    model="claude-3-5-sonnet-20241022",
    region="us-east-1"
)

# Create tools
tools = create_react_tools(game, "p2")

# Get system prompt
system_prompt = get_system_prompt(verbose=False)

# Create player
player = GraphReactPlayer(
    llm=llm,
    game=game,
    player_id="p2",
    tools=tools,
    system_prompt=system_prompt,
    verbose=False
)

# Get orders for a turn
orders = player.get_orders(game)
```

## Key Features

### 1. Enforced Decision Order

The graph structure ensures decisions are made in priority order:
1. Victory/defeat (most critical)
2. Defense (protect territory)
3. Attack (exploit opportunities)
4. Expansion (grow economy)
5. Validation (ensure legal orders)

Nodes CANNOT be skipped except via explicit conditional routing.

### 2. State Accumulation

Orders accumulate through the graph using `Annotated[list[dict], add]`:
- Defensive orders from threat assessment
- Attack orders from victory opportunity
- Expansion orders from expansion planning

All orders are combined in the validation node.

### 3. Focused Prompts

Each node has a laser-focused system prompt for ONE specific task:
- No overwhelming context
- Clear objective
- Specific tools available
- Well-defined output format

### 4. Tool Access Control

Each node only has access to relevant tools:
- Victory check: distance calculation, garrison lookup
- Threat assessment: garrison lookup, distance calculation
- Victory opportunity: route finding, distance, garrisons
- Expansion: distance, garrisons
- Validation: validate_orders

### 5. Error Handling

Each node handles LLM failures gracefully:
- Catches JSON parsing errors
- Provides safe defaults
- Logs warnings
- Continues execution

### 6. Strategic Logging

Comprehensive logging at each node:
- Node entry/exit
- Tool calls
- Parsed results
- Decision reasoning

## Comparison with Other Players

### vs ReactPlayer

**ReactPlayer**:
- Simple ReAct loop
- Unstructured decisions
- May ignore critical scenarios
- Less predictable

**GraphReactPlayer**:
- Structured decision graph
- Enforced priority order
- Always checks victory/defeat first
- More predictable behavior

### vs LangGraphPlayer

**LangGraphPlayer**:
- More complex state management
- Middleware system
- Dynamic tool filtering
- Observation/action pattern

**GraphReactPlayer**:
- Simpler workflow-based approach
- Fixed tool set per node
- Decision-focused (not observation-action)
- Easier to understand and debug

## Benefits

1. **Strategic Reliability**: Always checks victory/defeat first, never ignores critical scenarios
2. **Priority Enforcement**: Defense before expansion, home security always checked
3. **Predictable Behavior**: Fixed workflow makes debugging easier
4. **Focused Decision Making**: Each node has ONE job, does it well
5. **State Transparency**: All decisions are tracked in the state
6. **Tool Efficiency**: Nodes only use relevant tools, reducing token usage

## Limitations

1. **Fixed Workflow**: Cannot dynamically adjust decision order (by design)
2. **No Short-Circuit**: Must go through all nodes (unless explicitly routed)
3. **Tool Duplication**: Some tools are used in multiple nodes
4. **Token Usage**: Each node makes separate LLM calls
5. **No Memory**: State is reset each turn (no cross-turn learning)

## Future Enhancements

### Emergency Paths

Add fast-paths for critical situations:
- Immediate victory available → skip to validation
- Home under critical attack → emergency defense node

### Dynamic Node Selection

Allow skipping nodes based on game state:
- No threats → skip threat assessment
- No opponent home discovered → skip victory opportunity

### Cross-Turn Memory

Store insights between turns:
- Learned enemy patterns
- Strategic preferences
- Long-term plans

### Adaptive Tool Usage

Track which tools are most useful and prioritize them:
- Tool usage statistics
- Success rate per tool
- Cost/benefit analysis

## Implementation Notes

### Type Hints

Uses modern Python type hints:
- `dict`, `list`, `tuple` (lowercase, no typing import)
- `TypedDict` for state schema
- `Literal` for routing decisions
- `Annotated` for accumulating lists

### Error Recovery

Each node returns safe defaults on failure:
- `immediate_victory_possible: False`
- `home_defense_adequate: True` (optimistic)
- Empty lists for orders

### Tool Invocation

Tools are invoked via LangChain's tool binding:
```python
llm_with_tools = llm.bind_tools(tools_to_bind)
ai_message = llm_with_tools.invoke(messages)
```

### JSON Parsing

Robust JSON extraction from AI responses:
- Handles both string and structured content
- Regex-based JSON detection
- Fallback to empty structures

## Testing

### Manual Testing

```bash
# Test with verbose logging
uv run python game.py --mode hvl --agent graph-react --debug

# Test against different opponents
uv run python game.py --mode lvl --p1-agent graph-react --p2-agent react --debug
```

### Integration Testing

The GraphReactPlayer integrates with the existing game infrastructure:
- Implements `get_orders(game: Game) -> list[Order]` interface
- Uses `create_react_tools()` for tool creation
- Compatible with all LLM providers (Bedrock, OpenAI, Anthropic, Ollama)

## Conclusion

GraphReactPlayer provides a structured, reliable decision-making workflow that enforces strategic priorities through a directed graph. It's ideal for scenarios where predictable, principled decision-making is more important than flexibility.

For situations requiring more dynamic behavior, consider using LangGraphPlayer instead.
