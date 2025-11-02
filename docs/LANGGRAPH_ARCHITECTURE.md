# LangGraph Agent Architecture

This document describes the production-ready LangGraph-based agent implementation for Space Conquest.

## Overview

The `LangGraphPlayer` is an advanced AI player implementation that uses LangGraph's StateGraph pattern to manage conversation flow, implement dynamic context engineering, and provide robust error handling. It supersedes the simpler `LLMPlayer` with a more maintainable and reliable architecture.

## Key Improvements Over LLMPlayer

### 1. State Management with LangGraph

**Problem Solved**: The original `LLMPlayer` used a simple list for conversation history, which could grow unbounded and lacked structured state management.

**Solution**: LangGraph's `StateGraph` provides:
- Structured state with typed fields (`AgentState`)
- Automatic state flow between nodes
- Clear separation of concerns (reasoning, tool execution, routing)

### 2. Message History Management

**Problem Solved**: Without message trimming, conversations could exceed context windows and waste tokens.

**Solution**: Middleware function `trim_message_history()`:
- Automatically trims old messages when history grows too large
- Preserves recent context (last 2-3 tool results)
- Uses LangChain's `trim_messages()` utility
- Keeps token usage under control (~8000 tokens max)

### 3. Dynamic System Prompts

**Problem Solved**: Static system prompts couldn't adapt to changing game situations.

**Solution**: Context-aware prompt generation in `get_system_prompt()`:
- **Game Phase**: Adjusts strategy based on turn number (early/mid/late)
- **Threat Level**: Changes tone based on enemy proximity (low/medium/high/critical)
- **Turn-Specific**: Special guidance for turn 1, etc.

Example:
```python
# Turn 5, enemy 4 parsecs away
prompt = get_system_prompt(
    game_phase="early",
    threat_level="high",
    turn=5
)
# → Includes "HIGH THREAT: Enemy nearby. Increase home defenses."
```

### 4. Dynamic Tool Filtering

**Problem Solved**: LLM could waste calls on unavailable/inappropriate tools.

**Solution**: State-based tool filtering in `filter_tools_by_game_state()`:
- **Turn 1**: Hide `memory_query` (no history yet)
- **After submission**: Hide `submit_orders` (can't submit twice)
- **Always available**: Core tools (get_observation, query_star, etc.)

### 5. Middleware Architecture

**Problem Solved**: Cross-cutting concerns (threat assessment, error handling) were scattered.

**Solution**: Dedicated middleware functions:

#### Context Management
- `trim_message_history()`: Prevents unbounded growth
- `update_game_context_from_observation()`: Extracts strategic metrics

#### Threat Assessment
- `assess_threat_level()`: Calculates threat based on enemy distance
  - Critical: ≤2 parsecs
  - High: 3-4 parsecs
  - Medium: 5-6 parsecs
  - Low: 7+ parsecs or unknown

#### Error Recovery
- `handle_tool_error()`: Tracks consecutive errors
- `reset_error_tracking()`: Clears counters on success
- Circuit breaker: After 5 errors, suggests passing turn

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      LangGraphPlayer                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              StateGraph Workflow                    │    │
│  │                                                      │    │
│  │   START → call_llm → should_continue?               │    │
│  │              ↑            │         │                │    │
│  │              │            │         └─→ END          │    │
│  │              │            ↓                          │    │
│  │              └─── execute_tools                     │    │
│  │                                                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │                 AgentState                          │    │
│  │                                                      │    │
│  │  • messages: list[BaseMessage]                      │    │
│  │  • game_context: GameContext                        │    │
│  │  • available_tools: list[str]                       │    │
│  │  • error_count: int                                 │    │
│  │  • last_error: str | None                           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
   ┌─────────┐        ┌──────────┐        ┌──────────┐
   │Middleware│        │  Prompts │        │  Tools   │
   │         │        │          │        │          │
   │ • trim  │        │ • dynamic│        │ • observe│
   │ • threat│        │ • phase  │        │ • query  │
   │ • error │        │ • turn   │        │ • submit │
   └─────────┘        └──────────┘        └──────────┘
```

## State Flow

### 1. Initialization (`get_orders()`)
```python
initial_state = {
    "messages": [HumanMessage("It is now turn 5...")],
    "game_context": {
        "turn": 5,
        "game_phase": "early",
        "threat_level": "low",
        ...
    },
    "available_tools": [],
    "error_count": 0,
}
```

### 2. Call LLM Node (`_call_llm_node()`)
- Trim message history if needed
- Generate dynamic system prompt
- Filter available tools
- Invoke LLM with context
- Add response to state

### 3. Conditional Routing (`_should_continue()`)
- Check for tool calls in response
- Check if orders submitted
- Check error threshold
- Route to `execute_tools` or `END`

### 4. Execute Tools Node (`_execute_tools_node()`)
- Extract tool calls from last message
- Execute each tool via `AgentTools`
- Update game context if `get_observation` called
- Reset error tracking on success
- Add results to state
- Loop back to `call_llm`

## Usage

### Basic Usage

```python
from src.agent import LangGraphPlayer

# Create player
player = LangGraphPlayer(
    player_id="p2",
    provider="bedrock",
    model="haiku",
    verbose=False
)

# Get orders for current turn
orders = player.get_orders(game)
```

### Advanced Configuration

```python
# Use different provider
player = LangGraphPlayer(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    verbose=True  # Show detailed reasoning
)

# Mock mode for testing
player = LangGraphPlayer(
    use_mock=True,
    verbose=False
)
```

## Configuration Options

### Game Phase Detection
- **Early** (T1-10): Aggressive expansion
- **Mid** (T11-30): Consolidation
- **Late** (T31+): Endgame strikes

### Threat Level Calculation
Based on nearest enemy star distance:
- **Critical**: ≤2 parsecs → Urgent defense
- **High**: 3-4 parsecs → Defensive posture
- **Medium**: 5-6 parsecs → Balanced approach
- **Low**: 7+ or unknown → Aggressive expansion

### Tool Filtering Rules
- **Always available**: get_observation, query_star, estimate_route, get_ascii_map, propose_orders
- **Conditional**:
  - `memory_query`: Only after turn 1
  - `submit_orders`: Only if not already submitted

### Error Recovery
- Track consecutive errors
- Circuit breaker at 5 errors
- Suggest passing turn after threshold
- Reset counter on successful tool call

## Testing

### Unit Tests

```bash
# Test middleware functions
uv run pytest tests/test_langgraph_player.py::TestMiddleware -v

# Test dynamic prompts
uv run pytest tests/test_langgraph_player.py::TestDynamicPrompts -v

# Test full player
uv run pytest tests/test_langgraph_player.py::TestLangGraphPlayer -v
```

### Integration Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Test with existing game engine
uv run pytest tests/test_agent.py -v
```

## Performance Considerations

### Token Usage
- Message trimming keeps history under ~8000 tokens
- Dynamic prompts add ~200-400 tokens per turn
- Total per turn: ~2000-4000 tokens (input) + 500-1000 (output)

### Latency
- Graph overhead: <50ms per turn
- Middleware: <10ms per turn
- Most latency from LLM API calls (~1-3s)

### Memory
- State size: ~100KB per turn
- History grows slowly with trimming
- Recommendation: Reset conversation after 50+ turns

## Comparison: LLMPlayer vs LangGraphPlayer

| Feature | LLMPlayer | LangGraphPlayer |
|---------|-----------|-----------------|
| State Management | Simple list | TypedDict with structure |
| Message Trimming | ❌ None | ✅ Automatic |
| Dynamic Prompts | ❌ Static | ✅ Context-aware |
| Tool Filtering | ❌ All tools always | ✅ State-based filtering |
| Error Handling | ⚠️ Basic try/catch | ✅ Circuit breaker + recovery |
| Middleware | ❌ None | ✅ Pluggable architecture |
| Threat Assessment | ❌ None | ✅ Automatic from obs |
| Production Ready | ⚠️ For simple cases | ✅ Yes |

## Migration Guide

### From LLMPlayer to LangGraphPlayer

```python
# Old code
from src.agent import LLMPlayer
player = LLMPlayer("p2", provider="bedrock", model="haiku")

# New code
from src.agent import LangGraphPlayer
player = LangGraphPlayer("p2", provider="bedrock", model="haiku")

# Interface is identical - no other changes needed!
```

Both classes implement the same `get_orders(game) -> list[Order]` interface, so they're drop-in replacements.

## Future Enhancements

Potential improvements:
1. **Persistent Memory**: Use LangGraph's checkpointing for cross-game learning
2. **Multi-Agent**: Coordinate multiple sub-agents (scout, attack, defense)
3. **Model Selection**: Dynamically choose model based on situation complexity
4. **Streaming**: Stream reasoning in real-time for interactive mode
5. **A/B Testing**: Compare strategies with different prompt configurations

## Troubleshooting

### Issue: "Circuit breaker triggered"
**Cause**: 5+ consecutive tool errors
**Solution**: Check game state validity, review tool execution logs

### Issue: Message history growing too large
**Cause**: Trimming disabled or insufficient
**Solution**: Verify `trim_message_history()` is called in `_call_llm_node()`

### Issue: Wrong tools available
**Cause**: Tool filtering logic incorrect
**Solution**: Check `filter_tools_by_game_state()` conditions

### Issue: Threat level incorrect
**Cause**: Enemy distance calculation wrong
**Solution**: Verify `update_game_context_from_observation()` logic

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Core](https://python.langchain.com/docs/concepts/architecture/)
- [Context Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering)
