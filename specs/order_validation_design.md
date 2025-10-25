# Order Validation & Error Handling Design

## Executive Summary

**STATUS: IMPLEMENTED (2025-10-15)**

This specification defines how Space Conquest handles invalid fleet orders to prevent crashes while maintaining excellent UX for both human and LLM players. The design prioritizes **CLARITY** (clear error messages), **FAIRNESS** (forgiving honest mistakes), and **CONSISTENCY** (same rules for all player types).

**Core Principle**: Invalid orders should never crash the game. They should produce clear, actionable error messages that help players self-correct.

**Implementation Summary:**
- ✅ Strict over-commitment rejection (entire order set)
- ✅ Lenient individual error skipping (execute valid orders)
- ✅ Graceful error handling (no crashes)
- ✅ Error logging in game.order_errors
- ✅ Ownership validated BEFORE ship counting
- ✅ Clear error messages with order index, star IDs, and reasons

---

## 1. Current State Analysis

### What Works
- **LLM agents** have `propose_orders()` tool that validates before submission
- **Turn executor** has comprehensive validation logic checking:
  - Star existence
  - Star ownership
  - Ship availability
  - Cumulative ship limits across multiple orders
- Validation occurs at order execution time (Phase 5 of turn)

### Critical Problem
- **ValueError exceptions crash the game** for both humans and LLMs
- No graceful degradation path
- Players lose entire turn on any validation failure
- Error messages appear in stack traces instead of user-friendly format

### Current Validation Points
1. **LLM pre-validation** (`propose_orders()` in `AgentTools`) - validates schema and constraints
2. **Turn execution validation** (`_validate_all_orders()` in `TurnExecutor`) - validates at execution time
3. **Individual order validation** (`_validate_order()`) - validates each order independently

---

## 2. Design Decisions

### 2.1 When Should Validation Occur?

**RECOMMENDATION: Hybrid approach with pre-validation + graceful execution-time handling**

**Rationale:**
- **Pre-validation** (Option A) is essential for LLM agents to iterate and self-correct within their 15-iteration budget
- **Execution-time validation** (Option B) is necessary as final safety check since game state can change
- **During-execution skipping** (Option C) creates unpredictable behavior and undermines strategic planning

**Implementation:**
- Keep `propose_orders()` for LLM agents (no changes needed)
- Keep execution-time validation but **replace crashes with graceful error handling**
- For humans: Add optional pre-validation in CLI (show warnings but allow submission)

**Validation Flow:**
```
LLM Flow:
  propose_orders() → validation errors → retry → submit_orders() → execution validates → success

Human Flow:
  enter orders → optional warnings → submit → execution validates → if error, log and skip turn gracefully
```

### 2.2 How Should Errors Be Communicated?

**RECOMMENDATION: Option D (Return structured error details) with graceful degradation**

**Error Communication Strategy:**

1. **For LLM agents:**
   - `propose_orders()` returns: `{"ok": False, "errors": ["Order 0: not enough ships at A", ...]}`
   - Detailed, actionable messages that LLMs can parse and fix
   - Already implemented correctly in `AgentTools.propose_orders()`

2. **For Human players:**
   - Display errors in CLI with clear formatting
   - Show which orders succeeded vs failed
   - Suggest corrections based on error type

3. **At execution time (both player types):**
   - **NEVER crash** - catch all ValueError exceptions
   - Log errors to game log for debugging
   - For single-order failures: skip that order, execute valid ones
   - For systemic failures (all orders invalid): log and continue to next turn

**Error Message Format:**
```
ERROR: Invalid Order
  Order: 7 ships from A to B
  Problem: Not enough ships at A (have 5, need 7)
  Suggestion: Reduce ships to 5 or split across multiple turns
```

### 2.3 Should Invalid Orders Cost the Turn?

**RECOMMENDATION: Option B (Partial execution) with logging**

**Turn Cost Policy:**
- **Invalid orders are skipped** - don't crash or forfeit entire turn
- **Valid orders execute normally** - player retains partial agency
- **Errors are logged** - visible in game log for review
- **No retry within turn** - maintains turn-based pacing for both humans and LLMs

**Rationale:**
- **FUN**: Harsh punishment (Option A) is frustrating and discourages experimentation
- **BALANCE**: Forgiving invalid orders doesn't create exploits - players still lose the opportunity to move those ships
- **CLARITY**: Partial execution shows players what worked and what failed
- **CONSISTENCY**: Same behavior for humans and LLMs

**Special Cases:**
- If **all orders invalid** for a player: skip turn entirely, log reason, continue game
- If **over-commitment** detected: apply strict rejection for fairness (see 2.4)

### 2.4 Should Validation Rules Be Strict or Lenient?

**RECOMMENDATION: Strict validation with clear error messages (Option A)**

**Validation Policy:**

| Error Type | Handling | Rationale |
|------------|----------|-----------|
| **Over-commitment** (total ships > available) | **REJECT entire order set** | Forces strategic planning; prevents exploitation |
| **Non-existent star** | **SKIP individual order** | Typo/confusion - don't penalize entire turn |
| **Not owned star** | **SKIP individual order** | Game state changed - forgiving |
| **Insufficient ships** (single order) | **SKIP individual order** | Production/combat changed count - forgiving |
| **Same origin/destination** | **SKIP individual order** | Obvious mistake - no strategic value |
| **Invalid ship count** (≤0, non-integer) | **SKIP individual order** | Data error - no strategic value |

**Over-Commitment Example:**
Player has 10 ships at star A and submits:
- Order 1: A → B, 7 ships
- Order 2: A → C, 5 ships
- Total: 12 ships (exceeds 10 available)

**Action**: Reject entire order set with error:
```
"Invalid orders: Total ships from A (12) exceeds available (10). Orders from A: [7 to B, 5 to C]"
```

**Why strict for over-commitment?**
- Prevents "try everything and see what sticks" exploitation
- Proportional reduction (Option B) undermines strategic planning
- First-come-first-serve (Option C) makes order sequence matter unexpectedly
- Priority systems (Option D) add complexity without value

**Why lenient for other errors?**
- Game state changes between planning and execution (combat, production, rebellions)
- Single typos shouldn't forfeit entire turn
- Encourages aggressive play and risk-taking

### 2.5 Should Human and LLM Error Handling Differ?

**RECOMMENDATION: Same validation rules, different presentation**

**Unified Validation Logic:**
- Use identical validation functions for both player types
- Same strictness thresholds (over-commitment = reject all)
- Same partial execution behavior (skip invalid, execute valid)

**Different Presentation:**

| Aspect | Human Players | LLM Players |
|--------|---------------|-------------|
| **Pre-validation** | Optional warnings in CLI | Required via `propose_orders()` |
| **Error format** | Formatted text with colors/bullets | Structured JSON with error arrays |
| **Retry opportunity** | No (maintains turn pacing) | Yes (within 15-iteration budget before submission) |
| **Error visibility** | Immediate CLI display | Returned in tool response |

**Rationale:**
- **CONSISTENCY**: Same game rules eliminate confusion and potential exploits
- **FAIRNESS**: Neither player type has advantage from lenient/strict rules
- **CLARITY**: Presentation matches interface (CLI vs tool calls)
- **FUN**: Both player types get helpful, actionable feedback

---

## 3. Implementation Requirements

### 3.1 Modify TurnExecutor

**File**: `/src/engine/turn_executor.py`

**Changes to `_process_orders()`**:
```python
def _process_orders(self, game: Game, orders: Dict[str, List[Order]]) -> Game:
    """Process player orders with graceful error handling."""
    for player_id, player_orders in orders.items():
        try:
            # Validate all orders collectively (strict for over-commitment)
            self._validate_all_orders(game, player_id, player_orders)

            # Execute each order individually with error tolerance
            for order in player_orders:
                try:
                    self._execute_order(game, player_id, order)
                except ValueError as e:
                    # Log error but continue processing other orders
                    self._log_order_error(game, player_id, order, str(e))

        except ValueError as e:
            # All orders failed collective validation - skip entire order set
            self._log_player_order_failure(game, player_id, str(e))

    return game
```

**Add Error Logging**:
```python
def _log_order_error(self, game: Game, player_id: str, order: Order, error: str):
    """Log individual order failure."""
    if not hasattr(game, 'order_errors'):
        game.order_errors = []
    game.order_errors.append({
        'turn': game.turn,
        'player': player_id,
        'order': {'from': order.from_star, 'to': order.to_star, 'ships': order.ships},
        'error': error
    })

def _log_player_order_failure(self, game: Game, player_id: str, error: str):
    """Log when all orders for a player fail validation."""
    if not hasattr(game, 'order_errors'):
        game.order_errors = []
    game.order_errors.append({
        'turn': game.turn,
        'player': player_id,
        'order': 'ALL',
        'error': error
    })
```

### 3.2 Enhance Human Player Error Display

**File**: `/src/interface/human_player.py`

**Add Pre-Validation Warnings** (optional):
```python
def get_orders(self, game: Game) -> List[Order]:
    """Get orders from human player with validation warnings."""
    # ... existing code ...

    # Before finishing, show warnings for potential issues
    if orders:
        warnings = self._check_order_warnings(game, orders)
        if warnings:
            print("\nWARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
            confirm = input("Submit anyway? (y/n): ").strip().lower()
            if confirm not in ('y', 'yes'):
                # Let player revise
                continue

    return orders

def _check_order_warnings(self, game: Game, orders: List[Order]) -> List[str]:
    """Check for potential issues without blocking submission."""
    warnings = []
    player = game.players[self.player_id]

    # Check over-commitment
    ships_by_star = {}
    for order in orders:
        ships_by_star[order.from_star] = ships_by_star.get(order.from_star, 0) + order.ships

    for star_id, total in ships_by_star.items():
        star = next((s for s in game.stars if s.id == star_id), None)
        if star:
            available = star.stationed_ships.get(self.player_id, 0)
            if total > available:
                warnings.append(f"Over-commitment at {star_id}: {total} ships ordered but only {available} available")

    return warnings
```

### 3.3 Display Order Errors After Turn

**File**: `/src/interface/display.py`

**Add Error Display Method**:
```python
def display_order_errors(self, game: Game, player_id: str):
    """Display any order errors from the previous turn."""
    if not hasattr(game, 'order_errors'):
        return

    player_errors = [e for e in game.order_errors if e['player'] == player_id and e['turn'] == game.turn - 1]

    if player_errors:
        print(f"\n{'='*60}")
        print("ORDER ERRORS FROM LAST TURN")
        print(f"{'='*60}")
        for error in player_errors:
            if error['order'] == 'ALL':
                print(f"\nAll orders rejected: {error['error']}")
            else:
                order = error['order']
                print(f"\nOrder skipped: {order['ships']} ships from {order['from']} to {order['to']}")
                print(f"  Reason: {error['error']}")
        print()
```

### 3.4 Update Game Model

**File**: `/src/models/game.py`

**Add Error Tracking**:
```python
@dataclass
class Game:
    # ... existing fields ...
    order_errors: List[Dict[str, Any]] = field(default_factory=list)
```

### 3.5 No Changes Needed for LLM Agents

The `propose_orders()` tool already implements proper validation:
- Returns structured errors
- Checks all validation rules
- Allows iteration before submission

Keep this implementation unchanged.

---

## 4. Validation Rules Reference

### 4.1 Individual Order Validation

Checked by `_validate_order()`:

| Rule | Check | Error Message | Action |
|------|-------|---------------|--------|
| Star existence (origin) | Star ID in game.stars | "Origin star X does not exist" | Skip order |
| Star existence (destination) | Star ID in game.stars | "Destination star X does not exist" | Skip order |
| Star ownership | star.owner == player_id | "Player p1 does not control origin star X" | Skip order |
| Ship availability | available >= ordered | "Not enough ships at X: have Y, need Z" | Skip order |
| Ship count positive | ships > 0 | "Ships must be positive, got X" | Skip order |
| Same origin/dest | from != to | "Cannot send fleet to same star" | Skip order |

### 4.2 Collective Order Validation

Checked by `_validate_all_orders()`:

| Rule | Check | Error Message | Action |
|------|-------|---------------|--------|
| Over-commitment | Sum(ships) <= available per star | "Total ships from X (Y) exceeds available (Z)" | Reject all orders |

### 4.3 Edge Cases

| Scenario | Handling | Rationale |
|----------|----------|-----------|
| Empty order list | Allow (pass turn) | Valid strategic choice |
| Zero ships in order | Skip order | No strategic value |
| Negative ships | Skip order | Data error |
| Fleet to same star | Skip order | Meaningless move |
| Lost star mid-turn (rebellion) | Skip order | Game state changed legitimately |

---

## 5. Error Message Examples

### For LLM Agents (propose_orders)

**Success**:
```json
{
  "ok": true
}
```

**Validation Errors**:
```json
{
  "ok": false,
  "errors": [
    "Order 0: Total ships from A (12) exceeds available (10)",
    "Order 2: Destination star Z does not exist"
  ]
}
```

### For Human Players (CLI)

**Pre-Submission Warning**:
```
WARNINGS:
  - Over-commitment at A: 12 ships ordered but only 10 available
  - Star F is controlled by opponent (may change by execution)

Submit anyway? (y/n):
```

**Post-Turn Error Display**:
```
====================================================
ORDER ERRORS FROM LAST TURN
====================================================

Order skipped: 7 ships from A to B
  Reason: Not enough ships at A: have 5, need 7

Order skipped: 3 ships from F to G
  Reason: Player p1 does not control origin star F
```

---

## 6. Testing Requirements

### 6.1 Unit Tests

**File**: `tests/test_order_validation.py`

Required test cases:
1. **Over-commitment rejection**: Multiple orders exceed available ships → reject all
2. **Partial execution**: Mix of valid/invalid orders → execute valid only
3. **Non-existent star**: Order with invalid star ID → skip order
4. **Lost ownership**: Star controlled at planning but lost before execution → skip order
5. **Zero ships**: Order with 0 ships → skip order
6. **Same origin/destination**: Order from A to A → skip order
7. **Negative ships**: Order with negative ships → skip order
8. **Empty order set**: No orders submitted → allow (pass turn)
9. **Error logging**: Verify errors recorded in game.order_errors
10. **No crashes**: All invalid orders produce errors, never crash

### 6.2 Integration Tests

**Scenarios**:
1. Human player submits invalid orders → game continues with errors logged
2. LLM agent uses propose_orders → receives structured errors → retries → succeeds
3. Both players submit invalid orders on same turn → both get errors, game continues
4. Player loses star between turns → orders for that star skip gracefully

### 6.3 Playtesting Checklist

- Human vs Human: Submit deliberately invalid orders, verify game doesn't crash
- Human vs LLM: Verify both see consistent validation behavior
- LLM vs LLM: Verify LLMs can recover from validation errors via iteration
- Edge case: Over-commitment by 1 ship - verify rejection message is clear

---

## 7. Design Rationale Summary

### Priority Alignment

| Priority | Design Choice | How It's Achieved |
|----------|---------------|-------------------|
| **FUN** | Partial execution | Players keep agency; mistakes aren't game-ending |
| **BALANCE** | Strict over-commitment | Prevents exploitation; maintains strategic depth |
| **CLARITY** | Structured errors | Actionable messages explain what's wrong and how to fix |
| **CONSISTENCY** | Unified validation | Same rules for humans and LLMs; only presentation differs |

### Trade-offs Made

1. **Strict over-commitment vs forgiving everything**:
   - Chose strict for over-commitment (strategic importance)
   - Chose lenient for single-order errors (game state changes)
   - Result: Balanced between planning discipline and execution forgiveness

2. **Retry within turn vs no retry**:
   - Chose no retry for both player types
   - Maintains turn-based pacing
   - LLMs get retry via propose_orders before submission
   - Humans get optional pre-validation warnings

3. **Crash vs graceful degradation**:
   - Chose graceful degradation
   - Better UX, maintains game continuity
   - No gameplay exploits from this choice

### Why This Design Wins

- **Never crashes**: Game always continues, even with invalid orders
- **Clear feedback**: Players know exactly what went wrong
- **Fair to all**: Same rules regardless of player type or skill level
- **Strategically sound**: Over-commitment still punished, preventing exploits
- **Implementation-ready**: Leverages existing validation logic with minimal changes

---

## 8. Implementation Checklist

### Phase 1: Core Error Handling (Critical)
- [ ] Wrap order execution in try-catch in `TurnExecutor._process_orders()`
- [ ] Add error logging methods to TurnExecutor
- [ ] Add `order_errors` field to Game model
- [ ] Update unit tests to verify no crashes on invalid orders

### Phase 2: Error Display (High Priority)
- [ ] Add `display_order_errors()` to DisplayManager
- [ ] Call error display at start of human player turns
- [ ] Update human player get_orders to show errors from previous turn

### Phase 3: Enhanced UX (Medium Priority)
- [ ] Add pre-validation warnings to human player CLI
- [ ] Add confirmation prompt when warnings present
- [ ] Improve error message formatting (colors, bullets)

### Phase 4: Polish (Low Priority)
- [ ] Add error statistics to end-game summary
- [ ] Add error export to game replay JSON
- [ ] Add error filtering/querying for debugging

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-15 | Initial specification |
| 1.1 | 2025-10-15 | Marked as implemented; added implementation summary |

---

## 10. Implementation Verification

### Implemented Features
- ✅ **Game model updated:** Added `order_errors: Dict[str, List[str]]` field
- ✅ **Strict over-commitment:** `_validate_all_orders()` checks total ships before individual validation
- ✅ **Ownership priority:** Ownership checked BEFORE ship counting in over-commitment logic
- ✅ **Lenient individual validation:** Invalid orders skipped; valid orders execute
- ✅ **Error logging:** All errors stored with format "Order {index}: {from} -> {to} with {ships} ships: {reason}"
- ✅ **No crashes:** All ValueError exceptions caught and logged
- ✅ **Clear error messages:** Include order index, star IDs, ship counts, and specific problem

### Error Types Handled
| Error Type | Handling | Verified |
|------------|----------|----------|
| Over-commitment | Strict rejection (entire order set) | ✅ |
| Non-existent star | Lenient skip (individual order) | ✅ |
| Not owned star | Lenient skip (individual order) | ✅ |
| Insufficient ships | Lenient skip (individual order) | ✅ |
| Same origin/destination | Lenient skip (individual order) | ✅ |
| Invalid ship count ≤0 | Lenient skip (individual order) | ✅ |

### Specification Alignment
This implementation fully aligns with the approved design in sections 2.1-2.5:
- **Hybrid validation approach:** Pre-validation (propose_orders) + execution-time validation (Phase 5)
- **Structured error details:** Clear messages for both humans and LLMs
- **Partial execution:** Valid orders execute even if some orders invalid
- **Strict over-commitment:** Forces strategic planning; prevents exploitation
- **Same rules for all:** Humans and LLMs follow identical validation logic

---

**End of Specification**
