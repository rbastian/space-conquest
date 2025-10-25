# SPEC.md — LLM Player 2 Agent (Space Conquest)

This spec defines how a Large Language Model (LLM) can operate autonomously as **Player 2** in Space Conquest using constrained tools, stable prompts, and deterministic I/O. It is designed to be model‑agnostic and suitable for local or cloud models.

---

## 1. Objectives
- **Primary goal:** Win by capturing the opponent’s Home Star.
- **Secondary goals:**
  - Expand to high‑RU stars early while maintaining garrisons to prevent rebellions.
  - Deny opponent expansion via interceptions and strikes.
  - Minimize exposure to hyperspace losses by staging movements and avoiding overlong routes unless tactically justified.

---

## 2. High‑Level Agent Loop (per Turn)
1. **Observe**: Pull current known game state via tools (map, known RU, controlled stars, fleets, last turn events).
2. **Orient**: Update/consult long‑term memory (enemy sightings, battle outcomes, discovered RU).
3. **Decide**: Produce a plan for expansion, defense, and offense.
4. **Act**: Emit **Orders JSON** (moves list), adhering to validation.
5. **Reflect**: Record rationale, risks, and what to watch next turn.

---

## 3. Observation Space (what the LLM is allowed to see)
All observations are **from Player 2’s perspective** under fog‑of‑war.

### 3.1 Mandatory Inputs each turn
```json
{
  "turn": 5,
  "seed": 42,
  "grid": {"width": 12, "height": 10},
  "stars": [
    {"id":"A","x":2,"y":7,"letter":"A","name":"Altair","owner":"p1|p2|null","known_ru":4,"last_seen_control":"p1|p2|npc|none","is_home":false},
    {"id":"P","x":10,"y":8,"letter":"P","name":"Procyon","owner":"p2","known_ru":4,"last_seen_control":"p2","is_home":true}
  ],
  "my_fleets": [
    {"id":"p2-004","ships":3,"origin":"P","dest":"F","dist_remaining":2}
  ],
  "arrivals_this_turn": [{"fleet_id":"p2-003","dest":"F"}],
  "combats_last_turn": [
    {"star":"D","my_ships_before":3,"opp_ships_before":0,"winner":"p2","my_losses":0,"opp_losses":0}
  ],
  "rebellions_last_turn": [
    {"star":"F","star_name":"Fomalhaut","ru":2,"garrison_before":1,"rebel_ships":2,"outcome":"loss","garrison_after":0,"rebel_survivors":2,"owner":"p2"}
  ],
  "production_report": [{"star":"P","ships_produced":4}],
  "rules": {
    "hyperspace_loss": 0.02,
    "rebellion_chance": 0.5
  }
}
```
Notes:
- `known_ru` is what Player 2 knows now (may be `null` for unknown NPC stars). 4 for Home Stars.
- `last_seen_control` tracks the last confirmed control for fog-of-war rendering.
- **No opponent fleet counts** are surfaced unless a combat occurred last turn at that star.
- `rebellions_last_turn` reports rebellions that occurred on your controlled stars during Phase 4:
  - `star` and `star_name`: Star identifier and name where rebellion occurred
  - `ru`: Resource units of the star (determines rebel ship count)
  - `garrison_before`: Your ship count before rebellion combat
  - `rebel_ships`: Number of rebel ships spawned (always equals RU)
  - `outcome`: "win" (you retained control) or "loss" (star reverted to NPC)
  - `garrison_after`: Your surviving ship count after rebellion combat
  - `rebel_survivors`: Surviving NPC ships (relevant if outcome is "loss")
  - `owner`: Your player ID (always "p2" for Player 2 agent)
  - Only includes rebellions at your own stars; opponent rebellions are not visible

### 3.2 Optional Inputs
- **Heuristics state** (e.g., target list and scores from a submodule).
- **Evaluation** (estimated win chance from rollout/sim bot).

---

## 4. Tools (capabilities the LLM can call)
All tools are **pure functions** returning JSON; they do not mutate state unless stated.

### 4.1 `tool.get_observation()` → Observation JSON
Returns the object in §3.1.

### 4.2 `tool.get_ascii_map(view="current")` → string
- Returns the Player 2 map as ASCII, using `?X` for unknown RU.
- For debugging and spatial reasoning.

### 4.3 `tool.query_star(ref)` → Star JSON
- `ref` can be star `id` or letter.
- Returns coordinates, known RU, last seen control, distance matrix from all controlled stars.

### 4.4 `tool.estimate_route(from, to)` → {"distance":int, "risk":float}
- Chebyshev distance and expected hyperspace loss probability across that duration: `1 - (1-0.02)^distance`.

### 4.5 `tool.propose_orders(draft_orders)` → Validation Result
- **Purpose:** Pre-validate orders before submission to catch errors within iteration budget.
- **Validation rules:**
  - **Over-commitment check:** Sum of ships from each star must not exceed available ships
  - Star existence (origin and destination)
  - Origin star ownership (must be controlled by player)
  - Ship counts must be positive integers
  - Origin and destination must differ
- **Returns:**
  - Success: `{"ok": true}`
  - Failure: `{"ok": false, "errors": ["Order 0: error message", "Order 2: error message", ...]}`
- **Error format:** Each error includes order index, star IDs, and specific problem
- **Strategy:** Always call propose_orders() before submit_orders() to iterate on fixes within your 15-iteration budget

### 4.6 `tool.submit_orders(orders)` → Ack
- **Purpose:** Commit final orders for this turn (executed in Phase 5)
- **Execution-time validation:** Orders are re-validated at execution:
  - **Over-commitment:** Entire order set rejected if total ships from any star exceeds available
  - **Individual errors:** Invalid orders skipped; valid orders execute
  - **Game state changes:** Stars lost to combat/rebellion between planning and execution cause order skips
- **Error handling:** Errors logged in game.order_errors for your review next turn
- **No retries:** Cannot revise orders after submission; game proceeds to next turn
- **Returns:** Acknowledgment (orders queued for execution)

### 4.7 `tool.memory.upsert(records)` / `tool.memory.query(filter)`
- Persist and retrieve Player 2’s private memory. See §6.

> Implementation note: Expose these tools as function-calling specs or ReAct-style tool calls.

---

## 5. Orders Schema (action output)
```json
{
  "turn": 5,
  "moves": [
    {"from": "P", "to": "F", "ships": 3},
    {"from": "P", "to": "L", "ships": 2}
  ],
  "strategy_notes": "Expand to F (2 RU) and threaten D; retain 3 at P for defense vs home rush."
}
```
- `moves` may be empty (pass).
- `strategy_notes` is optional metadata for audit and future fine‑tuning.

---

## 6. Agent Memory (private, not visible to Player 1)
Memory is a simple vector/store or key‑value DB. Minimum tables:

### 6.1 `discovery_log`
- Schema: `{turn:int, star_id:string, ru:int}`
- Purpose: track discovered RU; never forget.

### 6.2 `battle_log`
- Schema: `{turn:int, star_id:string, my:int, opp:int, outcome:"win|loss|tie"}`
- Purpose: infer opponent expansion/fronts and likely garrisons.

### 6.3 `sighting_log`
- Schema: `{turn:int, star_id:string, opp_presence:bool}`
- Purpose: keep last proof of opponent presence/control.

### 6.4 `threat_map`
- Aggregated feature map by star: `{star_id, threat_score:float, last_update:int}` using recency‑weighted hints.

### 6.5 `plan_journal`
- Rationale snapshots for self‑consistency: `{turn, goals, targets, reserves}`.

---

## 7. Policy & Heuristics (deterministic defaults)
Provide a baseline strategy the LLM can follow or override with reasoning.

### 7.1 Target Scoring
For each **unknown or NPC** star `s` compute:
```
score(s) =  w_ru * E[RU(s)]
          - w_dist * min_distance_from_my_control(s)
          - w_threat * threat_score(s)
```
Default weights: `w_ru=3.0`, `w_dist=1.0`, `w_threat=1.5`.
- `E[RU(s)]` = known RU if discovered, else 2.0 prior.

### 7.2 Garrison Rule
- Keep ≥ `RU` ships at captured NPC stars to avoid 50% rebellion.
- Home star default reserve: `min(4, ceil(total_ships/6))` or explicit 3 if under pressure.

### 7.3 Strike/Interception Rules
- If opponent home star location is known, form a strike group ≥ `4 + frontier_pressure` and route via shortest path; avoid splitting below 3 unless scouting.
- Intercept if battle estimate > 65% favored (based on last seen forces and production at nearby stars).

### 7.4 Hyperspace Risk (ALL-OR-NOTHING MECHANIC)

**CRITICAL**: Hyperspace loss is a BINARY outcome for each fleet:
- Each turn in transit: 2% chance the ENTIRE fleet is destroyed (all ships lost)
- If survival roll succeeds: fleet continues with 0 casualties
- **This is NOT per-ship attrition** - you cannot "lose 6 out of 30 ships"

**Cumulative Fleet Loss Probability**:
- Distance 3: 5.88% (entire fleet lost)
- Distance 5: 9.61% (entire fleet lost)
- Distance 8: 14.93% (entire fleet lost)
- Distance 11: 19.89% (entire fleet lost)

**Strategic Guidelines**:
- Distance ≤ 5: Low risk for routine operations
- Distance 6-8: Acceptable for high-value targets (3 RU) or strategic strikes
- Distance ≥ 9: Reserve for critical operations only (home star assaults, decisive battles)
- **Risk is "boom or bust"**: A 30-ship fleet at distance 11 either arrives with all 30 ships (80.11% chance) or is completely destroyed (19.89% chance). Plan accordingly.

**Example Calculation**:
- Sending 30 ships distance 11 to enemy home:
  - ❌ WRONG: "Expect to lose ~6 ships, arriving with ~24"
  - ✅ RIGHT: "19.89% chance to lose all 30 ships; 80.11% chance to arrive with all 30 ships"

**Note**: Chebyshev distance makes diagonal routes as efficient as orthogonal, expanding tactical options

### 7.5 Fleet Sizing for Hyperspace Risk

Because hyperspace loss is all-or-nothing, fleet sizing must account for binary outcomes:

**DO NOT over-size fleets to compensate for "expected losses"**:
- ❌ WRONG: "Distance 8 has 14.93% loss, so send 35 ships instead of 30 to compensate"
- ✅ RIGHT: "Send exactly what's needed if the fleet arrives; accept the 14.93% chance of total failure"

**Redundancy Strategy** (for critical strikes):
- Consider sending 2+ smaller fleets rather than 1 large fleet
- Example: Attacking enemy home (distance 11, 19.89% loss risk)
  - Option A: Send 1 fleet of 30 ships → 80.11% chance of success
  - Option B: Send 2 fleets of 16 ships → 96.05% chance at least one arrives
  - Trade-off: Option B has higher survival probability but spreads forces thinner

### 7.6 NPC Garrison Depletion Mechanic
- **NPC defenders do NOT regenerate after combat** unless rebellion occurs
- After combat, NPC garrison is reduced by ceil(player_losses/2) per combat rules
- Example: 3 RU star with 3 defenders, player sends 4 ships:
  - If mutual destruction: Star now has 0 defenders (not 3)
  - If player loses: Star has 3 - ceil(4/2) = 1 defender remaining
- **Re-conquering weakened stars**: Send right-sized fleet based on remaining defenders
- **Rebellion resets garrison**: If player loses rebellion, star reverts to NPC with FULL RU garrison restored
- **Strategic implication**: Track partial victories; don't waste ships re-attacking with full-strength fleets

---

## 8. Decision Template (LLM system prompt)
> You are Player 2 in Space Conquest. You must win by capturing Player 1's Home Star. Use only the provided tools. Adhere to fog-of-war: do not invent unknown RU or opponent positions. Produce valid JSON orders.
>
> **Process:**
> 1) Call `tool.get_observation()`.
> 2) **Assess enemy threats** (use available fog-of-war information):
>    - **Combat history**: Query `combats_last_turn` and memory (`battle_log`) to identify:
>      - Where enemy fleets appeared (star locations)
>      - Enemy fleet sizes at moment of combat
>      - Stars that changed from your control to enemy control
>    - **Ownership changes**: Compare star ownership to `last_seen_control` to detect:
>      - Stars enemy captured from NPC (expansion pattern)
>      - Stars enemy captured from you (direct threats)
>    - **Proximity analysis**: For each enemy-controlled star, calculate:
>      - Chebyshev distance to your home star
>      - Chebyshev distance to your high-RU stars (3 RU stars)
>      - Fleets required to defend if enemy launches immediate strike
>    - **Inferred enemy strength**: Based on combat reports + ownership changes:
>      - Minimum enemy production (each enemy star produces RU/turn)
>      - Likely enemy fleet sizes (last combat + turns since)
>      - Threat level: HIGH (within 3 parsecs of home), MEDIUM (4-6 parsecs), LOW (7+ parsecs)
> 3) Identify expansion targets and defense needs (informed by threat assessment).
> 4) Compute moves that maximize near‑term production while protecting against rebellions and home‑star rushes.
> 5) Validate with `tool.propose_orders()`; if invalid, fix and re‑validate.
> 6) Submit with `tool.submit_orders()` and write a short rationale to memory.
>
> **Constraints:**
> - Do not exceed available ships at any origin.
> - Keep garrisons ≥ RU where possible.
> - **IMPORTANT**: Hyperspace loss is ALL-OR-NOTHING (2% chance per turn to lose ENTIRE fleet, not per-ship). Prefer shorter distances but understand risk is binary.
> - **Track NPC garrison depletion**: NPCs do NOT regenerate unless rebellion occurs. Re-attack weakened stars with right-sized fleets (don't waste ships).
> - If simultaneous home‑star trades are likely, prefer defending home.

**Assistant output** must be **only** a single JSON object conforming to the Orders schema.

---

## 9. Validation & Guardrails

### 9.1 Order Validation Strategy
- **Pre-submission validation (propose_orders):**
  - Validates schema and constraints before submission
  - Returns structured errors for iteration
  - Use this to fix errors within your 15-iteration budget
  - **Always validate before submitting**

- **Execution-time validation (Phase 5):**
  - **Strict over-commitment:** Entire order set rejected if total ships from any star exceeds available
  - **Lenient individual errors:** Invalid individual orders skipped; valid orders execute
  - Errors logged to game.order_errors for next turn review
  - No crashes: game continues regardless of order validity

### 9.2 Error Recovery Guidelines
- **Over-commitment errors:**
  - Check total ships across all orders from same origin
  - Leave garrison reserves (≥ RU ships to prevent rebellion)
  - Verify ship counts at planning time match execution time

- **Lost star errors:**
  - Game state changes between planning and execution (combat, rebellion)
  - Orders for lost stars are skipped (not your fault)
  - Query observation each turn to update your known_control

- **Iteration budget management:**
  - propose_orders() catches most errors before submission
  - Fix errors immediately; don't waste iterations
  - If validation passes, submit immediately

- **Strategic considerations:**
  - Over-commitment rejection forfeits entire turn's orders
  - Plan conservatively: use propose_orders() to verify
  - Individual order skips are lenient but reduce your turn's effectiveness

### 9.3 Security Guardrails
- Tool access restricted to whitelisted calls only
- Cannot access Player 1's private information
- Cannot modify game state except through submit_orders()
- Red-team prompts filtered

---

## 10. Telemetry & Logging
- Persist per‑turn:
  - Orders JSON
  - Observation snapshot hash
  - Validation result
  - Rationale notes
- Enable offline audits, training data extraction, and A/B testing of heuristics.

---

## 11. Evaluation Metrics
- **Win rate** vs baseline scripted bot.
- **Time to first RU gain** (expansion speed).
- **Rebellion rate** (should be low).
- **Fleet utilization** (percent of ships idle at end of Phase 5).
- **Risk efficiency** (expected losses from hyperspace vs RU gained).

---

## 12. Example Turn (tool call outline)
1. `obs = tool.get_observation()`
2. `map = tool.get_ascii_map()`
3. Update memory with new discoveries/combats.
4. Score targets; compute reserves.
5. Build candidate moves, validate via `tool.propose_orders()`.
6. Fix errors if any; then `tool.submit_orders(orders)`.
7. `tool.memory.upsert([...])` with rationale and sightings.

**Example Orders JSON**
```json
{
  "turn": 5,
  "moves": [
    {"from": "P", "to": "F", "ships": 3},
    {"from": "P", "to": "L", "ships": 2}
  ],
  "strategy_notes": "Capture F (likely 2 RU), keep 3 at P to deter rush; next turn pivot to D."
}
```

---

## 13. Implementation Notes
- Keep tools synchronous and side‑effect‑free except `submit_orders`.
- Provide deterministic seeds for any Monte Carlo subroutines.
- Plan for future: swap heuristic weights at runtime, plug in rollouts.

---

## 14. Security & Fair Play
- The LLM must only access Player 2 data.
- No reading of opponent’s private map or RNG state.
- Logs must not leak hidden RU values.

---

## 15. Future Extensions (optional)
- Add a lightweight **rollout simulator** tool the LLM can query (`tool.simulate(moves, horizon=2)`) for lookahead.
- Add **priority queues** for tasks (explore, defend, strike) with budgeted ships.
- Add **deception behaviors** (feints) once opponent modeling is implemented.

---
This spec is sufficient to implement a tool‑driven LLM agent that plays as Player 2, respects fog‑of‑war, and outputs valid, auditable orders each turn.

