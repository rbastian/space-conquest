# SPEC.md – Space Conquest (Simplified 4X Game)

## 1. Overview
Two-player strategic space exploration and conquest game. Players expand from a Home Star, exploring and conquering NPC (neutral) stars to gather resources and build fleets. Victory is achieved by conquering the opponent’s Home Star.

Game emphasizes deterministic combat, fog-of-war intelligence, and simultaneous movement orders.

## 2. Map & Coordinates
- 12×10 grid (x ∈ [0..11], y ∈ [0..9]).
- One star per grid cell.
- Distance metric: **Chebyshev** (`max(|dx|, |dy|)`).
- Movement rate: 1 parsec/turn.
- Travel time = Chebyshev distance between origin and destination.
- Movement allowed from any controlled star to any other star (no range limit).
- Note: Diagonal movement costs the same as orthogonal movement, making all 8 directions economically equal.

## 3. Star Placement

### Overview
- Total stars: **16** (2 player home stars + 14 NPC stars)
- Star density: 13.3% (16 stars / 120 cells)
- Distribution method: **Balanced quadrant allocation** ensures fair strategic balance
- **Star IDs (A-P) are assigned randomly** using the game's RNG seed:
  - Shuffle the list ['A','B',...,'P'] using seeded RNG
  - Assign letters to stars in generation order (not coordinate order)
  - **Rationale**: Random assignment eliminates information leakage - letter codes reveal no strategic information about star location or importance
  - Maintains determinism: same seed always produces same letter assignments

### Quadrant Structure
The 12×10 board is divided into 4 equal quadrants to ensure balanced star distribution:

- **Q1 (Northwest)**: x ∈ [0,5], y ∈ [0,4] (30 cells) - P1 home region
- **Q2 (Northeast)**: x ∈ [6,11], y ∈ [0,4] (30 cells) - Neutral
- **Q3 (Southwest)**: x ∈ [0,5], y ∈ [5,9] (30 cells) - Neutral
- **Q4 (Southeast)**: x ∈ [6,11], y ∈ [5,9] (30 cells) - P2 home region

### Star Distribution by Quadrant
- **Q1 (P1 region)**: 4 stars total (1 home + 3 NPC)
- **Q2 (Neutral)**: 3 NPC stars
- **Q3 (Neutral)**: 3 NPC stars
- **Q4 (P2 region)**: 4 stars total (1 home + 3 NPC)

**Rationale**:
- Guarantees balanced expansion opportunities for both players
- Home regions (Q1, Q4) are slightly richer to support early expansion
- Neutral regions (Q2, Q3) create contested border zones
- Prevents scenarios where one player has 5+ nearby stars while other has 2
- Preserves randomness within quadrants for replayability

### Home Star Placement
- Player 1 Home Star: **0–3 parsecs** (Chebyshev distance) from corner (0,0)
  - 16 possible cells in upper-left region
  - Placed randomly within this constraint (using seeded RNG)
- Player 2 Home Star: **0–3 parsecs** (Chebyshev distance) from corner (11,9)
  - 16 possible cells in lower-right region
  - Placed randomly within this constraint (using seeded RNG)
- **Guaranteed separation**: ≥7 parsecs minimum between player home stars
- **Home region guarantee**: Each home region (3-parsec radius) contains 3-4 total stars (including home star)
  - This ensures 2-3 NPC targets within 3 parsecs of each home
  - Prevents trivial home star identification
  - Provides fair early expansion opportunities

### NPC Star Placement
- 14 NPC stars distributed across quadrants per allocation (Q1:3, Q2:3, Q3:3, Q4:3)
- **Within-quadrant placement**: Random selection of unoccupied cells within each quadrant
- **Home region constraint**: 1-2 NPC stars placed within 3 parsecs of each home star
- **Collision avoidance**: Stars never placed on occupied cells

### Resource Unit (RU) Distribution
- **Total NPC RU**: 28 (average 2 RU per star)
- **Balanced per quadrant**: Each quadrant has predetermined RU budget
  - Q1 (4 NPC stars): {1, 2, 2, 3} = 8 RU total
  - Q2 (3 NPC stars): {1, 2, 3} = 6 RU total
  - Q3 (3 NPC stars): {1, 2, 3} = 6 RU total
  - Q4 (4 NPC stars): {1, 2, 2, 3} = 8 RU total
- **Assignment**: RU values shuffled randomly within each quadrant (preserves local variance)
- **Rationale**: Ensures both players have access to similar total economic potential (±2 RU variance between home regions vs ±6 RU with pure random)

### Design Goals
1. **Fair starting positions**: Both players have 3-4 stars in home region
2. **Balanced economy**: Quadrants have similar total RU value (6-8 RU per quadrant)
3. **Strategic variety**: Exact star positions and RU assignments vary by seed
4. **Contested zones**: Border areas between quadrants create natural battlegrounds
5. **Replayability**: Trillions of unique map configurations despite balanced structure

## 4. Player Setup
Each player:
- Starts at a Class 4 Home Star (4 RU).
- Begins with **4 ships** at the Home Star.
- Controls a fog-of-war map:
  - `known_ru[star]` → `None | 1..4` (4 = Home Star)
  - `known_control[star]` → `me | opp | npc | none`

## 5. Data Model
### Star
```json
{
  "id": "A",
  "name": "Altair",
  "x": 2,
  "y": 6,
  "base_ru": 4,
  "owner": "p1",  // p1 | p2 | null
  "npc_ships": 0
}
```
### Fleet
```json
{
  "id": "p1-003",
  "owner": "p1",
  "ships": 3,
  "origin": "A",
  "dest": "F",
  "dist_remaining": 4
}
```
### Player
```json
{
  "id": "p1",
  "home_star": "A",
  "known_ru": {"A": 4, "D": 3},
  "known_control": {"A": "me", "P": "opp"}
}
```

## 6. Turn Structure

Each turn executes in 5 sequential phases. Players submit orders AFTER seeing results from the previous turn (combat, hyperspace losses, rebellions). Orders create fleets that depart at the START of the next turn.

### Phase 1 – Fleet Movement
1. **Hyperspace Survival Roll (ALL-OR-NOTHING)**: Each hyperspace fleet rolls for survival:
   - **2% chance**: ENTIRE fleet is destroyed (all ships lost)
   - **98% chance**: Fleet survives intact (0 ships lost)
   - Implementation: d50 roll of 1 = fleet destroyed, 2-50 = fleet survives
   - **IMPORTANT**: This is NOT per-ship attrition. Either the entire fleet is lost or none of it is.
2. Surviving fleets reduce `dist_remaining` by 1.
3. Fleets with distance 0 **arrive** and merge with stationed ships at destination.
4. Upon arrival at unknown stars, reveal RU to that player.

**Key Timing:** Fleets created in the previous turn's Phase 4 (Orders) move for the first time in this phase.

### Phase 2 – Combat Resolution
- Merge same-owner fleets at each star.
- For every star with opposing fleets:
  - Compare ship counts:
    - Higher number **wins**.
    - Lower number **loses all** (no retreat).
    - Winner loses `ceil(loser/2)` ships.
    - **Tie** → mutual destruction (both fleets = 0).
  - If winner survives and didn't own star, gains control.

**Combat Events:** All combat results are stored in `game.combats_last_turn` and displayed to players before they submit next turn's orders.

### Phase 3 – Victory Assessment
- If a player wins combat at opponent's Home Star → **immediate victory**.
- If both capture enemy home stars on same turn → **draw**.
- **If victory occurs:** Game ends immediately. Phases 4 and 5 are skipped.

### Phase 4 – Process Orders
- Players submit move orders (this happens AFTER seeing Phase 2 combat results):
```json
{"moves": [
  {"from": "A", "to": "F", "ships": 3},
  {"from": "A", "to": "D", "ships": 1}
]}
```
- **Order Validation Rules:**
  - **Over-commitment (strict):** If total ships from any star exceeds available ships, entire order set is rejected. No partial execution.
  - **Individual errors (lenient):** Invalid individual orders are skipped; remaining valid orders execute:
    - Non-existent stars (origin or destination)
    - Not owned origin star
    - Insufficient ships (after over-commitment check passes)
    - Same origin and destination
    - Invalid ship counts (≤0 or non-integer)
  - **Error handling:** Invalid orders never crash the game. Errors are logged in `game.order_errors` for player review.
  - **No retries:** Order validation occurs at execution time. Players cannot retry within the same turn.
- Valid orders create Fleet objects that will depart in Phase 1 of the NEXT turn.
- Ships ordered to move remain stationed at their origin star until next turn.
- Ships in hyperspace cannot be recalled.

**Key Timing:** Orders are submitted AFTER seeing combat results from the current turn, but created fleets remain at their origin star until the START of the next turn. In the next turn's Phase 1, fleets depart BEFORE Phase 2 combat occurs. This means ships ordered to move do NOT participate in defense of their origin star - they leave before combat is resolved.

### Phase 5 – Rebellions & Production

This phase has two sub-phases that execute sequentially:

**Sub-Phase 5a: Rebellions**
- For each captured NPC star controlled by a player:
  - **Home stars are immune to rebellion** regardless of garrison strength
  - **For non-home stars**: If stationed ships < RU → 50% chance of rebellion
  - On 4–6 (d6), rebellion spawns RU rebel ships.
  - Resolve combat vs stationed ships (standard combat rules).
  - If rebels win, star reverts to NPC control with surviving rebel ships.
  - Rebellion events are reported to the affected player in the next turn's observation (via `rebellions_last_turn` field).
- Track which stars experienced rebellions (for production phase).

**Sub-Phase 5b: Production**
- For each controlled star that did NOT rebel:
  - Home stars: Always produce +4 ships (immune to rebellion)
  - Non-home stars: +RU ships
  - Ships spawn at that star and add to `stationed_ships`.
- Stars that rebelled produce NOTHING this turn.

**Key Design:** Rebellions are checked BEFORE production. A star must survive the rebellion check to produce ships. This prevents situations where new ships could prevent or fight in rebellions that should have already occurred.

## 7. NPC Rules
### NPC Combat
- When a fleet arrives at an NPC star, combat triggers.
- NPC defenders = RU ships.
- Player wins if their ships > NPC ships.
  - NPC destroyed.
  - Player loses `ceil(NPC/2)` ships.
  - Player gains control.
- If player < NPC → player destroyed; NPC loses `ceil(player/2)` ships.
- If equal → mutual destruction.
- NPCs do **not** rebuild or regenerate.

### Simultaneous Player Arrival at NPC Stars

When both players' fleets arrive at an NPC-controlled star on the same turn, combat is resolved in this sequence:

**Combat Sequence**:
1. **Player vs Player Combat** (First):
   - The two arriving fleets fight each other using standard PvP combat rules
   - Higher ship count wins, loser is eliminated
   - Winner loses `ceil(loser/2)` ships
   - Tie → mutual destruction, star becomes uncontrolled (no NPC combat)

2. **Winner vs NPC Combat** (Second):
   - If there's a PvP winner with surviving ships, they fight the NPC garrison
   - Standard NPC combat rules apply
   - Winner gains control of the star
   - If winner loses or ties with NPC, star remains/becomes NPC-controlled

**Rationale**: Players compete for the star first; the victor then faces the garrison.

**Example**:
```
P1: 3 ships arrive
P2: 4 ships arrive
NPC: 2 defenders

Phase 1 (PvP):
  3 vs 4 → P2 wins
  P2 losses: ceil(3/2) = 2 ships
  P2 survivors: 4 - 2 = 2 ships

Phase 2 (Winner vs NPC):
  2 vs 2 → Tie, mutual destruction
  Result: Star becomes NPC-controlled with 0 ships
```

### NPC Rebellions
- 50% chance per turn if stationed ships < RU.
- Rebellion spawns RU ships.
- Combat resolved normally.
- Star reverts to NPC if player loses.
- Players receive detailed rebellion reports (outcome, casualties, survivors) in their next turn's observation.

## 8. Random Events
- **Hyperspace Loss (Binary Survival):** Each fleet in transit has a 2% chance per turn to be COMPLETELY DESTROYED (all ships lost). If the fleet survives the roll, it continues intact with 0 casualties. This is NOT per-ship attrition.
- **Rebellions:** 50% chance if under-defended.

## 9. Map Rendering (ASCII)
- Cell width: 2 chars.
- Empty space: `..`
- Star token: `<RU_or_?> + <Letter>` (e.g., `4A`, `?D`).
- Rows top to bottom, columns left to right.
- Each player renders their own map using `known_ru`.

Example:
```
.. .. ?A .. .. ?B .. .. ?C .. ..
.. 4D .. .. ?E .. .. .. ?F .. ..
.. .. .. ?G .. .. .. ?H .. .. ..
```

## 10. Victory Condition
- Capture opponent’s Home Star by winning combat there.
- Immediate win; no need to hold it.
- Simultaneous captures = draw.

## 11. Object Model
- `Game` – orchestrates turns, RNG, serialization.
- `Player` – manages orders, knowledge, fleets.
- `Star` – holds static info + dynamic ownership.
- `Fleet` – tracks ships in transit.

## 12. Serialization & Replay
- Game state should include RNG seed, turn, all stars, fleets, and player states.
- Deterministic playback supported via JSON:
```json
{
  "seed": 42,
  "turn": 7,
  "stars": [...],
  "fleets": [...],
  "players": [...]
}
```

## 13. Testing Hooks
Unit tests must verify:
- Combat outcomes (including tie rule).
- Hyperspace loss applied before arrival.
- Rebellion trigger probability and resolution.
- Victory conditions.
- Fog-of-war updates on arrival.
- Deterministic setup given a seed.

## 14. Default Constants
| Constant | Value | Description |
|-----------|--------|-------------|
| GRID_X | 12 | Columns |
| GRID_Y | 10 | Rows |
| NUM_STARS | 16 | Total stars |
| HOME_RU | 4 | Home Star resource units |
| NPC_RU_RANGE | [1,3] | NPC resource unit range |
| HYPERSPACE_LOSS | 0.02 | 2% fleet destruction chance per turn |
| REBELLION_CHANCE | 0.5 | 50% if under-garrisoned |
| HOME_DISTANCE_RANGE | [0,3] | Chebyshev distance from corners (maintains 7-11 parsec separation between homes, ensures 2-4 stars per home region) |
| MOVE_RATE | 1 | Parsecs per turn |
| RNG_SEED_DEFAULT | 42 | Default seed for testing |

### Hyperspace Loss Design Rationale

The 2% per-turn hyperspace loss rate was chosen to balance several competing objectives:

**Map Utilization**: At 2%, distances up to 8 parsecs remain viable (15% cumulative risk), allowing players to contest central stars and mount long-range strikes. With Chebyshev distance, the maximum corner-to-corner distance is 11 parsecs (down from 20 with Manhattan), making ~25% more of the map strategically accessible.

**Strategic Depth**: Risk is meaningful but not prohibitive, creating interesting risk-reward decisions without invalidating long-range operations.

**Economic Balance**: Expected losses (0.02 × distance × fleet_size) are small enough that offensive operations remain profitable against high-RU targets.

**LLM Reasoning**: The 2% rate produces intuitive approximations ("~2% per parsec") that LLM agents can reason about effectively.

**Gameplay Pacing**: Reduces mid-game stalemates by enabling decisive strikes while still punishing reckless overextension.

**Cumulative fleet loss probability examples**:
- Distance 3: 5.88% (favorable for expansion)
- Distance 5: 9.61% (reasonable for contested stars)
- Distance 8: 14.93% (justifiable for home star strikes)
- Distance 11: 19.89% (extreme range operations, requires strong strategic justification)

**Mechanical Clarification**:
The 2% rate applies to the ENTIRE FLEET as a binary survival roll, not to individual ships. A 30-ship fleet traveling distance 5 has:
- 90.39% probability: arrives with all 30 ships intact
- 9.61% probability: completely destroyed, 0 ships arrive
- **Never**: arrives with partial losses (e.g., 27 ships)

The "expected losses" formula (0.02 × distance × fleet_size) is useful for calculating expected value across many engagements, but any single fleet experiences all-or-nothing outcomes. This creates significant variance in long-range operations:
- Distance 3: 5.88% chance to lose everything
- Distance 8: 14.93% chance to lose everything
- Distance 11: 19.89% chance to lose everything

**Strategic Implication**: Long-range strikes have "boom-or-bust" risk profiles. A failed hyperspace roll wastes the entire investment, while success delivers the full force. This differs fundamentally from per-ship attrition, where outcomes converge toward the mean.

---
This specification provides all parameters and state models required for a Python implementation of the Space Conquest game engine and deterministic simulation.