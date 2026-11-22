# Spec: Anthropic SDK Agent Layer

Beads: `space-conquest-88m` (this spec) · child issues: `space-conquest-c11` (timeline),
`space-conquest-lub` (plan object), `space-conquest-fvm` (prompt), `space-conquest-5tq`
(guardrail), `space-conquest-4u8` (provider factory), `space-conquest-w4e` (player),
`space-conquest-29f` (eval), `space-conquest-7bx` (retirement).

## 1. Motivation

The five existing LLM players (basic tool-calling player, `ReactPlayer`,
`LangGraphPlayer`, `GraphReactPlayer`, `PythonReactAgent`) share three structural
defects that made agents unable to reason about turns:

1. **Per-turn amnesia.** Each turn starts a fresh conversation; the agent carries no
   plan or acknowledged threats between turns, so multi-turn commitments ("defend
   until turn 18") cannot exist.
2. **The temporal join is left to the model.** The observation hands over raw
   positions and distances; the model must mentally project garrisons, production,
   and arrival schedules — precisely what LLMs are worst at. 600 lines of prompt
   doctrine accumulated to compensate.
3. **Fragile harness mechanics.** Message trimming that could drop the game state
   mid-turn and regex order extraction (both fixed in PR #24, but symptomatic of
   the framework indirection).

This rewrite replaces the agent layer with a single player on the raw Anthropic SDK.
The engine does the arithmetic; the model does plan selection and revision.

## 2. Architecture

Per turn, one short-lived conversation:

```
┌─ system (frozen, cache_control: ephemeral) ──────────────────┐
│ rules + output contract (~80 lines, see §6)                  │
├─ user message (volatile, after cache breakpoint) ────────────┤
│ 1. carried plan from turn N-1 (§4)                           │
│ 2. engine-computed timeline for turns T..T+K (§3)            │
│ 3. game state JSON (existing prompts_json observation)       │
├─ tool loop (SDK tool runner) ────────────────────────────────┤
│ validate_orders / query_route  (@beta_tool, close over game) │
├─ final structured output ────────────────────────────────────┤
│ TurnDecision: orders + updated plan (§5)                     │
└──────────────────────────────────────────────────────────────┘
```

The `Player` protocol is unchanged: `get_orders(game: Game) -> list[Order]`, plus
`close()`. `game.py` and `src/server/session.py` keep working with a one-line
player-construction change.

## 3. Engine: turn projection / timeline (`space-conquest-c11`)

New module `src/engine/projection.py`. Pure functions, no LLM, fully unit-testable.

```python
@dataclass
class StarProjection:
    star_id: str
    turn: int                       # absolute turn number
    projected_garrison: int         # current + production - departures + arrivals
    arrivals: list[FleetArrival]    # own fleets landing this turn
    threat: ThreatArrival | None    # known/inferred enemy arrival this turn
    deficit: int                    # max(0, threat.ships - projected_garrison)

@dataclass
class ReinforcementOption:
    from_star: str
    available_ships: int
    distance: int
    arrival_turn: int               # game.turn + distance
    survival_probability: float     # hyperspace risk for that leg

def project_turns(game: Game, player_id: str, horizon: int = 8) -> TimelineReport
```

`TimelineReport` carries, for each turn T..T+horizon: per-star projections, plus for
every star with a nonzero deficit the list of `ReinforcementOption`s that arrive **on
or before** the threat turn. Fog of war is respected: enemy arrivals are only listed
when derivable from observed fleets or combat history; otherwise a `worst_case`
block gives earliest-possible enemy arrival at the home star from last-known
positions.

Rendering: `render_timeline(report) -> str` produces the compact human/LLM-readable
block that goes into the user message, e.g.:

```
TURN 18 (3 turns from now):
  YOUR HOME (H): enemy ~25 ships arrive. Projected garrison 12 + 3x4 production = 24. DEFICIT 1.
    Reinforcements in time: F (8 ships, dist 2, arrives T17, 96% survival)
```

All absolute turn numbers, never countdowns, in every rendered line (the relative
form appears once, parenthesized, for readability).

## 4. Agent: persistent plan (`space-conquest-lub`)

New module `src/agent/plan.py`.

```python
class Intent(BaseModel):
    action: str                     # e.g. "defend H", "stage at F for strike on C"
    expires_turn: int               # absolute turn after which intent is void
    reason: str

class Plan(BaseModel):
    strategy: str                   # one-paragraph current strategy
    threats_acknowledged: list[str] # e.g. "enemy fleet ~25 -> H arriving T18"
    intents: list[Intent]
    updated_turn: int
```

Lifecycle: the player holds the `Plan` between turns; it is injected verbatim at the
top of the user message ("Your plan from last turn — update or continue it") and the
model returns the revised plan as part of its structured output (§5). Expired intents
(`expires_turn < game.turn`) are pruned before injection. The plan is serialized to
the decision log each turn so replay tooling can inspect drift.

## 5. Agent: the player (`space-conquest-w4e`)

New module `src/agent/sdk_player.py`, class `SdkPlayer`.

**Request shape** (per turn):

- `model`: from provider factory (§7); develop against `claude-opus-4-8`.
- `thinking={"type": "adaptive"}` — replaces most timing doctrine.
- `system=[{"type": "text", "text": RULES_PROMPT, "cache_control": {"type": "ephemeral"}}]`.
- `max_tokens=16000`.
- Tool loop via `client.beta.messages.tool_runner(...)` with `@beta_tool` functions
  closing over the current `Game`:
  - `validate_orders(orders)` — legality + guardrail (§8); returns specific
    violations so the model can revise.
  - `query_route(from_star, to_star)` — distance, arrival turn, direct vs.
    waypoint survival comparison (port of `calculate_distance`/`find_safest_route`).
- Final output extracted with structured outputs, **not** text parsing:

```python
class OrderOut(BaseModel):
    from_star: str
    to_star: str
    ships: int
    rationale: str

class TurnDecision(BaseModel):
    orders: list[OrderOut]
    plan: Plan
```

After the tool loop ends, one `client.messages.parse(..., output_format=TurnDecision)`
call converts the runner's final message into the validated decision (conversation
context reused; the parse call carries the same cached system prefix). If the parse
response hits `stop_reason` other than `end_turn`, log and fall back to empty orders
(pass) rather than crash the game loop.

**Logging:** wire into the existing `DecisionLogger`/`StrategicLogger` exactly as
`ReactPlayer` does — per-turn tool calls, token usage (`response.usage`, including
`cache_read_input_tokens` to verify caching), orders, and the serialized plan.

**Errors:** SDK typed-exception chain (`RateLimitError` → retry with backoff via the
SDK's built-in `max_retries`; `APIStatusError`/`APIConnectionError` → log, pass turn).
A passed turn must never raise out of `get_orders`.

## 6. Prompt (`space-conquest-fvm`)

New `src/agent/sdk_prompt.py`, target ≤100 lines:

1. Game rules (victory, production, movement, combat formula, rebellion, hyperspace
   risk formula, fog of war) — facts only, no doctrine.
2. Input contract: "you receive your prior plan, a computed timeline, and the game
   state; the timeline already contains all arrival/production arithmetic — do not
   recompute it, read it."
3. Output contract: revise the plan, then produce orders consistent with it;
   validate before finalizing.

Explicitly dropped: TIMING AND COORDINATION, MANDATORY COMBAT CALCULATION,
OVERWHELMING FORCE, FLEET CONCENTRATION, ROUTE OPTIMIZATION, PROBING sections —
these are either computed by the engine now or within adaptive thinking's reach.
Keep the version header + changelog convention from `prompts.py`.

## 7. Provider factory (`space-conquest-4u8`)

New `src/agent/client_factory.py`:

```python
def make_client(provider: str) -> Anthropic | AnthropicBedrockMantle
def resolve_model(provider: str, alias: str) -> str   # "opus" -> "claude-opus-4-8" / "anthropic.claude-opus-4-8"
```

- `anthropic` (default): `anthropic.Anthropic()` — credentials from env/profile.
- `bedrock`: `AnthropicBedrockMantle(aws_region=...)` — `anthropic.`-prefixed IDs.
- Model aliases: `opus -> claude-opus-4-8`, `sonnet -> claude-sonnet-5`,
  `haiku -> claude-haiku-4-5`.
- OpenAI/Ollama are dropped. `game.py` gains `--player sdk` (default for hvl/lvl once
  eval passes); old flags keep working until retirement (§9).

## 8. Guardrail (`space-conquest-5tq`)

`validate_orders` becomes enforcement, layered on existing legality checks:

- Reject orders that reduce a star's projected garrison below a known threat's
  deficit within the horizon (uses §3's `TimelineReport`).
- Reject captured-NPC garrison drops below RU while no threat justifies it.
- Each rejection returns the specific violated projection line so the model can
  revise in the next tool-loop iteration (max 3 revision rounds, then pass).

## 9. Migration & retirement (`space-conquest-29f`, `space-conquest-7bx`)

1. Land §3–§8 behind `--player sdk`; existing players untouched.
2. Eval: LLM-vs-LLM runs, `SdkPlayer` vs fixed `ReactPlayer`, existing metrics
   tooling; verify temporal behaviors (commitments held across turns, too-late
   reinforcements ignored, coordinated arrivals). Model sweep opus/sonnet/haiku.
3. On parity-or-better: delete the five old players, their prompts/tools/middleware,
   and tests; drop the eight `langchain*`/`langgraph` deps from `pyproject.toml`;
   `anthropic` becomes the only LLM dependency. Update README, QUICKSTART, docs/.
4. Update CLAUDE.md delegation rule (`space-conquest-wl8`).

## 10. Non-goals

- No changes to engine combat/movement/production semantics.
- No changes to the TUI, server protocol, or frontend.
- No multi-provider abstraction beyond the two Anthropic clients — no adapter layer
  "in case we add OpenAI back."
