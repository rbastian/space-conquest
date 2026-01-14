# PythonReactAgent

## Overview

PythonReactAgent is an experimental AI agent for Space Conquest that uses Python REPL capabilities for computational game strategies. Unlike the standard ReactPlayer with its predefined analytical tools, PythonReactAgent can write and execute arbitrary Python code to analyze game state and compute complex strategies.

## Key Features

### 1. Python REPL Tool
- Execute arbitrary Python code during gameplay
- Access to game state variables in execution context
- Perform complex calculations and algorithmic analysis
- No limitations of predefined tools

### 2. Minimal Tool Set
- `validate_orders`: Validate proposed orders before submission
- `python_repl`: Execute Python code with game state context

### 3. Game State Access
The Python REPL has the following variables available:
- `stars`: List of all Star objects
- `my_player_id`: Agent's player ID (string)
- `game`: Full Game object with all state
- `game_turn`: Current turn number (int)

## Architecture

### Component Structure

```
PythonReactAgent
├── llm: LangChain ChatModel (AWS Bedrock, etc.)
├── game: Game state reference (updated each turn)
├── player_id: Agent's player ID
├── tools: List of available tools
│   ├── validate_orders: Order validation tool
│   └── python_repl: Code execution tool
└── system_prompt: Optimized prompt for REPL usage
```

### Tool Implementation

The `python_repl` tool:
1. Receives Python code as a string
2. Injects game state variables into execution context
3. Executes code in a controlled environment
4. Captures and returns output
5. Handles errors gracefully

## Usage

### Basic Setup

```python
from agent.llm_factory import LLMFactory
from agent.prompts import get_python_react_system_prompt
from agent.python_react_agent import PythonReactAgent
from agent.python_react_tools import create_python_react_tools

# Create LLM instance
llm_factory = LLMFactory(region="us-east-1")
llm = llm_factory.create_bedrock_llm(model="haiku", temperature=0.7)

# Create tools with game state reference
tools = create_python_react_tools(game, player_id="p2")

# Get optimized system prompt
system_prompt = get_python_react_system_prompt(verbose=False)

# Create agent
agent = PythonReactAgent(
    llm=llm,
    game=game,
    player_id="p2",
    tools=tools,
    system_prompt=system_prompt,
    verbose=True
)

# Get orders for current turn
orders = agent.get_orders(game)
```

### Example Code Patterns

The agent can execute various analytical patterns:

#### 1. Distance Calculations

```python
# Calculate distances to all stars from home
home = [s for s in stars if s.owner == my_player_id and s.base_ru == 4][0]
for star in stars:
    if star.id != home.id:
        distance = max(abs(home.x - star.x), abs(home.y - star.y))
        print(f"{star.id} ({star.name}): {distance} turns away")
```

#### 2. Target Selection

```python
# Find closest uncontrolled stars
my_stars = [s for s in stars if s.owner == my_player_id]
uncontrolled = [s for s in stars if s.owner != my_player_id]

for my_star in my_stars:
    closest = min(uncontrolled,
                  key=lambda s: max(abs(my_star.x - s.x), abs(my_star.y - s.y)))
    distance = max(abs(my_star.x - closest.x), abs(my_star.y - closest.y))
    print(f"From {my_star.id}: closest target is {closest.id} at {distance} turns")
```

#### 3. Combat Calculation

```python
import math

def calculate_combat(attackers, defenders):
    if attackers > defenders:
        survivors = attackers - math.ceil(defenders / 2)
        return "WIN", survivors
    elif defenders > attackers:
        return "LOSS", 0
    else:
        return "TIE", 0

# Check if attack is viable
target_garrison = 3  # Assume worst case
my_available_ships = 10
result, survivors = calculate_combat(my_available_ships, target_garrison)
print(f"Attack outcome: {result} with {survivors} survivors")
```

#### 4. Fleet Timing Analysis

```python
# Find which stars can reinforce target before enemy arrives
target_star_id = "E"
enemy_arrival_turn = 25
target_star = [s for s in stars if s.id == target_star_id][0]

reinforcement_options = []
for star in stars:
    if star.owner == my_player_id:
        ships = star.stationed_ships.get(my_player_id, 0)
        if ships > 0:
            distance = max(abs(star.x - target_star.x),
                          abs(star.y - target_star.y))
            arrival_turn = game_turn + distance
            if arrival_turn <= enemy_arrival_turn:
                print(f"{star.id}: {ships} ships, arrives turn {arrival_turn}")
```

#### 5. Hyperspace Risk Calculation

```python
import math

def hyperspace_survival(distance):
    if distance <= 0:
        return 1.0
    cumulative_risk = 0.02 * distance * math.log2(distance)
    return 1.0 - cumulative_risk

# Compare direct vs multi-hop routes
direct_distance = 8
survival_direct = hyperspace_survival(direct_distance)
print(f"Direct route: {survival_direct * 100:.1f}% survival")

# Two-hop route
hop1, hop2 = 4, 4
survival_multihop = hyperspace_survival(hop1) * hyperspace_survival(hop2)
print(f"Multi-hop route: {survival_multihop * 100:.1f}% survival")
```

## System Prompt

The agent uses a specialized system prompt (`get_python_react_system_prompt`) that:
- Emphasizes Python REPL as the PRIMARY analytical tool
- Provides examples of useful code patterns
- Explains available variables in REPL context
- Encourages computational approaches to strategy
- Includes all standard game rules and mechanics

Key prompt features:
- "YOU HAVE PYTHON REPL ACCESS - USE IT!" header
- Detailed REPL variable documentation
- 5+ example code snippets for common tasks
- Recommended workflow: analyze → validate → submit

## Comparison with ReactPlayer

| Feature | ReactPlayer | PythonReactAgent |
|---------|-------------|------------------|
| Tools | 4 predefined tools | 2 minimal tools |
| Analysis Method | Tool calls | Python code execution |
| Flexibility | Limited to tool capabilities | Arbitrary computation |
| Distance Calculation | `calculate_distance` tool | Python: `max(abs(x1-x2), abs(y1-y2))` |
| Route Finding | `find_safest_route` tool | Custom pathfinding algorithms |
| Strategic Analysis | `get_nearby_garrisons` tool | Any algorithm in Python |
| Learning Curve | Lower (tools guide usage) | Higher (needs programming) |

## Advantages

1. **Unlimited Flexibility**: Can implement any algorithm or calculation
2. **Computational Power**: Perform complex analysis not possible with predefined tools
3. **Custom Strategies**: Write specialized algorithms for specific scenarios
4. **Iterative Refinement**: Test multiple approaches in single turn
5. **Educational Value**: See actual code the agent writes

## Disadvantages

1. **Higher Token Usage**: Code can be verbose
2. **Error Prone**: Syntax errors or logic bugs possible
3. **Slower Execution**: Code execution adds overhead
4. **Model Dependent**: Requires strong coding capabilities from LLM

## Experiment Goals

This agent is designed to test whether computational capabilities improve strategic decision-making compared to predefined analytical tools. Key questions:

1. Does Python REPL access lead to better strategic decisions?
2. Is the flexibility worth the added complexity and token cost?
3. Can LLMs effectively write game analysis code?
4. What types of calculations benefit most from code execution?

## Implementation Details

### Tool Context Injection

The `python_repl` tool injects game state into the execution context:

```python
context = {
    "stars": game.stars,
    "my_player_id": player_id,
    "game": game,
    "game_turn": game.turn,
    # Standard library functions
    "max": max, "min": min, "abs": abs, "sum": sum, "len": len,
    "sorted": sorted, "enumerate": enumerate, "range": range,
    # Type constructors
    "list": list, "dict": dict, "set": set,
    "str": str, "int": int, "float": float,
}

exec(code, context)
```

### Output Capture

The tool captures stdout to return results:

```python
import sys
from io import StringIO

old_stdout = sys.stdout
sys.stdout = StringIO()

exec(code, context)

output = sys.stdout.getvalue()
sys.stdout = old_stdout

return output if output else "Code executed successfully (no output)"
```

### Error Handling

The tool catches and returns exceptions:

```python
try:
    exec(code, context)
except Exception as e:
    return f"Error executing code: {e}"
```

## Best Practices

### For Agent Developers

1. **Start Simple**: Test with basic distance calculations first
2. **Provide Examples**: Include code examples in system prompt
3. **Handle Errors Gracefully**: Expect and manage execution errors
4. **Monitor Token Usage**: Code can consume significant tokens
5. **Test Edge Cases**: Verify behavior with invalid code

### For Agent Users

1. **Use Verbose Mode**: Enable verbose logging to see code execution
2. **Monitor Tool Usage**: Track `python_repl` vs `validate_orders` calls
3. **Compare Performance**: Run against standard ReactPlayer for benchmarks
4. **Analyze Strategies**: Review generated code to understand agent reasoning

## Future Enhancements

Potential improvements to consider:

1. **Sandboxing**: More restrictive execution environment for safety
2. **Code Libraries**: Pre-loaded utility functions for common tasks
3. **Persistent Context**: Share code/functions across turns
4. **Performance Optimization**: Cache frequently used calculations
5. **Interactive Debugging**: REPL session management across tool calls

## Security Considerations

The current implementation has basic protections but should not be used with untrusted LLMs:

- Code executes in process (not fully sandboxed)
- Has access to game state objects (read/write)
- Can import standard library modules
- Output is captured but side effects possible

For production use:
- Consider containerized execution
- Implement timeout mechanisms
- Restrict available imports
- Audit generated code

## Example Output

Here's what a typical agent interaction looks like:

```
[TOOL] python_repl: Executing code:
home = [s for s in stars if s.owner == my_player_id and s.base_ru == 4][0]
for star in stars:
    if star.id != home.id:
        distance = max(abs(home.x - star.x), abs(home.y - star.y))
        print(f"{star.id}: {distance} turns")

[TOOL] python_repl: Output:
A: 3 turns
B: 5 turns
C: 7 turns
D: 4 turns
...

Agent response: I'll analyze the strategic situation and select targets...
```

## Troubleshooting

### Common Issues

**Issue**: `NameError: name 'stars' is not defined`
- **Cause**: Context injection failed
- **Solution**: Verify game state is passed to tool creation

**Issue**: `SyntaxError: invalid syntax`
- **Cause**: LLM generated invalid Python code
- **Solution**: Improve system prompt with examples, use more capable model

**Issue**: Code executes but no output
- **Cause**: Code doesn't use `print()` statements
- **Solution**: Prompt includes "use print() to see results"

**Issue**: Execution timeout
- **Cause**: Infinite loop or complex calculation
- **Solution**: Implement timeout mechanism in tool

## References

- `src/agent/python_react_agent.py`: Main agent implementation
- `src/agent/python_react_tools.py`: Tool definitions
- `src/agent/prompts.py`: System prompt (`get_python_react_system_prompt`)
- `examples/python_react_agent_example.py`: Usage example

## License

Same as Space Conquest project.
