# Combat Report Display Specification

**Version:** 1.0
**Date:** 2025-10-16
**Status:** APPROVED

---

## 1. Overview & Objectives

### 1.1 Purpose

Combat reports are critical feedback moments that inform players about the outcomes of fleet engagements. This specification defines how combat results are presented to both human players and LLM agents, ensuring clarity, immersion, and strategic utility.

### 1.2 Design Goals

- **Clarity**: Make attacker/defender roles and control changes immediately obvious
- **Narrative Immersion**: Use active voice and evocative language ("emerged from hyperspace", "repelled", "clashed")
- **Brevity**: Keep reports to 1-2 sentences maximum
- **Consistency**: Maintain uniform structure across all combat scenarios
- **Strategic Value**: Provide actionable information (casualties, control changes) without overwhelming detail
- **Perspective Transformation**: Present data from the observer's point of view ("me" vs "opp")

### 1.3 Cross-References

- [Space Conquest Core Spec](/specs/space_conquest_spec.md) — Combat mechanics and resolution
- [LLM Player 2 Agent Spec](/specs/llm_player_2_agent_spec.md) — Observation format and data structures
- [LLM Opponent Naming Design](/specs/llm_opponent_naming_design.md) — Admiral naming conventions

---

## 2. Human Display Format

### 2.1 General Principles

- **Star Identification**: Always show star letter AND name: `K (Kappa Phoenicis)`
- **Combat Emoji**: Use ⚔️ prefix for visual prominence
- **Active Voice**: "Your fleet defeated" not "The fleet was defeated"
- **Casualty Format**: Parenthetical suffix with losses: `(-3 ships)` or `(mutual destruction)`
- **Control Change Markers**: Use exclamation mark for captures: `You now control K!`
- **Attacker/Defender Clarity**: Use explicit role language ("emerged from hyperspace and attacked", "defending garrison")

### 2.2 Narrative Templates

#### 2.2.1 Attacker Wins & Takes Control (Player Attacking)

**Template:**
```
⚔️ Your fleet ([attacker_ships] ships) emerged from hyperspace and defeated the [defender] garrison ([defender_ships] ships) at [STAR] ([Star Name]). You now control [STAR]! (You lost [your_losses] ships)
```

**Example:**
```
⚔️ Your fleet (15 ships) emerged from hyperspace and defeated the NPC garrison (5 ships) at K (Kappa Phoenicis). You now control K! (You lost 2 ships)
```

**When to Use:**
- `attacker == "me"`
- `control_before != "me"`
- `control_after == "me"`
- `defender_losses == defender_ships_before` (defender eliminated)

---

#### 2.2.2 Attacker Wins & Takes Control (Opponent Attacking)

**Template:**
```
⚔️ [Opponent Name]'s fleet ([attacker_ships] ships) emerged from hyperspace and captured [STAR] ([Star Name]). [Opponent Name] now controls [STAR]! (They lost [their_losses] ships)
```

**Example:**
```
⚔️ Admiral Sonnet Krios's fleet (18 ships) emerged from hyperspace and captured K (Kappa Phoenicis). Admiral Sonnet Krios now controls K! (They lost 1 ship)
```

**When to Use:**
- `attacker == "opp"`
- `control_before != "opp"`
- `control_after == "opp"`
- `defender_losses == defender_ships_before` (defender eliminated)

---

#### 2.2.3 Defender Repels Attacker (Player Defending)

**Template:**
```
⚔️ Your defending forces ([defender_ships] ships) at [STAR] ([Star Name]) repelled [opponent name]'s attacking fleet ([attacker_ships] ships). (You lost [your_losses] ships)
```

**Example:**
```
⚔️ Your defending forces (12 ships) at K (Kappa Phoenicis) repelled Admiral Sonnet Krios's attacking fleet (8 ships). (You lost 4 ships)
```

**When to Use:**
- `defender == "me"`
- `attacker == "opp"`
- `control_after == "me"` (control unchanged or regained)
- `attacker_losses == attacker_ships_before` (attacker eliminated)

---

#### 2.2.4 Defender Repels Attacker (Player Attacking)

**Template:**
```
⚔️ Your attacking fleet ([attacker_ships] ships) at [STAR] ([Star Name]) was repelled by the defending forces ([defender_ships] ships). (They lost [their_losses] ships)
```

**Example:**
```
⚔️ Your attacking fleet (5 ships) at K (Kappa Phoenicis) was repelled by the defending forces (10 ships). (They lost 2 ships)
```

**When to Use:**
- `attacker == "me"`
- `defender == "opp"` or `defender == "npc"`
- `control_after != "me"` (attack failed)
- `attacker_losses == attacker_ships_before` (attacker eliminated)

---

#### 2.2.5 Mutual Destruction (Tie)

**Template:**
```
⚔️ Battle at [STAR] ([Star Name]) resulted in mutual destruction ([attacker_ships] vs [defender_ships] ships). The star is now uncontrolled. (Both fleets destroyed)
```

**Example:**
```
⚔️ Battle at K (Kappa Phoenicis) resulted in mutual destruction (7 vs 7 ships). The star is now uncontrolled. (Both fleets destroyed)
```

**When to Use:**
- `attacker_losses == attacker_ships_before`
- `defender_losses == defender_ships_before`
- `control_after == null` (uncontrolled)

---

#### 2.2.6 Simultaneous Arrival (Fleet Clash)

**Template for Winner:**
```
⚔️ Your fleet ([your_ships] ships) clashed with [opponent name]'s fleet ([their_ships] ships) arriving simultaneously at [STAR] ([Star Name]). You emerged victorious and now control [STAR]! (You lost [your_losses] ships)
```

**Template for Loser:**
```
⚔️ Your fleet ([your_ships] ships) clashed with [opponent name]'s fleet ([their_ships] ships) arriving simultaneously at [STAR] ([Star Name]). [Opponent Name] emerged victorious and now controls [STAR]! (They lost [their_losses] ships)
```

**Example (Player wins):**
```
⚔️ Your fleet (10 ships) clashed with Admiral Sonnet Krios's fleet (8 ships) arriving simultaneously at K (Kappa Phoenicis). You emerged victorious and now control K! (You lost 4 ships)
```

**When to Use:**
- Both fleets arrive same turn at uncontrolled star
- Determine primary attacker alphabetically by player ID (`"p1"` < `"p2"`)
- Use "clashed" language instead of attacker/defender framing
- Winner determined by standard combat resolution

---

#### 2.2.7 NPC Combat (Player Wins)

**Template:**
```
⚔️ Your fleet ([attacker_ships] ships) emerged from hyperspace and defeated the NPC garrison ([defender_ships] ships) at [STAR] ([Star Name]). You now control [STAR]! (You lost [your_losses] ships)
```

**Example:**
```
⚔️ Your fleet (10 ships) emerged from hyperspace and defeated the NPC garrison (3 ships) at K (Kappa Phoenicis). You now control K! (You lost 1 ship)
```

**When to Use:**
- `attacker == "me"`
- `defender == "npc"` (inferred from `control_before == null` and `defender_ships_before > 0`)
- `control_after == "me"`

---

#### 2.2.8 NPC Combat (Player Loses)

**Template:**
```
⚔️ Your attacking fleet ([attacker_ships] ships) at [STAR] ([Star Name]) was repelled by the NPC garrison ([defender_ships] ships). (They lost [their_losses] ships)
```

**Example:**
```
⚔️ Your attacking fleet (5 ships) at K (Kappa Phoenicis) was repelled by the NPC garrison (8 ships). (They lost 2 ships)
```

**When to Use:**
- `attacker == "me"`
- `defender == "npc"` (inferred from `control_before == null` and `defender_ships_before > 0`)
- `control_after == null` (player failed to capture)
- `attacker_losses == attacker_ships_before`

---

### 2.3 Casualty Display Rules

**NEW FORMAT:** Show only the winner's losses, since the loser always loses all ships (implicit from fleet sizes shown):

**Format:** `(You lost X ships)` or `(They lost X ships)`

**Variants:**
- **Standard losses:** `(You lost 3 ships)` or `(They lost 3 ships)`
- **Single ship loss:** `(You lost 1 ship)` or `(They lost 1 ship)` (singular form)
- **No losses:** `(You lost 0 ships)` (rare but possible)
- **Mutual destruction:** `(Both fleets destroyed)` (special case for 2.2.5)

**Rationale:**
- The loser always loses their entire fleet (shown in initial fleet size)
- Showing both sides' losses was redundant: `(You: -3 ships, Them: -8 ships)` when we already know "Them" had 8 ships
- Cleaner format focuses on the strategic cost to the winner

---

## 3. LLM Observation Format

### 3.1 Data Schema

LLM agents receive combat reports in a simplified JSON format with perspective transformation applied. All player references are converted to `"me"` (the observing player) or `"opp"` (the opponent).

**Schema:**
```json
{
  "star": "K",
  "attacker": "me|opp",
  "defender": "me|opp",
  "attacker_ships_before": 51,
  "defender_ships_before": 6,
  "attacker_losses": 3,
  "defender_losses": 6,
  "control_before": "me|opp|null",
  "control_after": "me|opp|null"
}
```

### 3.2 Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `star` | string | Star letter identifier (e.g., "K") |
| `attacker` | string | `"me"` or `"opp"` — who initiated the attack |
| `defender` | string | `"me"` or `"opp"` — who was defending |
| `attacker_ships_before` | int | Attacker fleet size before combat |
| `defender_ships_before` | int | Defender fleet size before combat |
| `attacker_losses` | int | Ships lost by attacker (0 to `attacker_ships_before`) |
| `defender_losses` | int | Ships lost by defender (0 to `defender_ships_before`) |
| `control_before` | string | Star owner before combat: `"me"`, `"opp"`, or `null` (NPC/uncontrolled) |
| `control_after` | string | Star owner after combat: `"me"`, `"opp"`, or `null` |

### 3.3 Design Decisions

**Why NO `combat_type` field?**
- The `combat_type` field (e.g., "attacker_victory", "defender_repels", "mutual_destruction") is **redundant** and can be inferred from the provided data
- Combat outcomes are fully determined by comparing ship counts and control states
- Removing redundant fields simplifies the schema and reduces potential inconsistencies
- LLM agents can infer combat type from the data if needed for narrative generation

**Perspective Transformation:**
- Internal game state uses `"p1"` and `"p2"` player IDs
- Before sending to LLM agents, transform perspective:
  - If observing player is `"p1"`: `"p1"` → `"me"`, `"p2"` → `"opp"`
  - If observing player is `"p2"`: `"p2"` → `"me"`, `"p1"` → `"opp"`
- This makes the data self-consistent and easier for LLM agents to reason about

### 3.4 Example LLM Combat Reports

**Player conquers opponent star:**
```json
{
  "star": "K",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 51,
  "defender_ships_before": 6,
  "attacker_losses": 3,
  "defender_losses": 6,
  "control_before": "opp",
  "control_after": "me"
}
```

**Opponent conquers player star:**
```json
{
  "star": "F",
  "attacker": "opp",
  "defender": "me",
  "attacker_ships_before": 20,
  "defender_ships_before": 5,
  "attacker_losses": 2,
  "defender_losses": 5,
  "control_before": "me",
  "control_after": "opp"
}
```

**Player repels opponent attack:**
```json
{
  "star": "M",
  "attacker": "opp",
  "defender": "me",
  "attacker_ships_before": 8,
  "defender_ships_before": 12,
  "attacker_losses": 8,
  "defender_losses": 4,
  "control_before": "me",
  "control_after": "me"
}
```

**Mutual destruction:**
```json
{
  "star": "K",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 5,
  "defender_ships_before": 5,
  "attacker_losses": 5,
  "defender_losses": 5,
  "control_before": "opp",
  "control_after": null
}
```

**NPC conquest:**
```json
{
  "star": "G",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 10,
  "defender_ships_before": 3,
  "attacker_losses": 1,
  "defender_losses": 3,
  "control_before": null,
  "control_after": "me"
}
```

**Note:** In the NPC conquest example, `defender` is set to `"opp"` as a placeholder because the schema requires `"me"` or `"opp"`. The LLM agent can infer NPC involvement by checking if `control_before == null` and `defender_ships_before > 0`.

---

## 4. Attacker/Defender Determination Logic

### 4.1 Primary Rule: Fleet Arrival

**Definition:** The **attacker** is the player whose fleet arrived at the star this turn. The **defender** is the player (or NPC) who already had ships present at the star.

### 4.2 Determination Algorithm

```python
def determine_roles(combat_star, arriving_fleet, garrison_ships, control_before):
    """
    Determine attacker and defender roles for a combat engagement.

    Args:
        combat_star: Star letter where combat occurred
        arriving_fleet: Fleet object that arrived this turn (has .owner attribute)
        garrison_ships: Number of ships already present (int)
        control_before: Star owner before combat ("p1", "p2", or None)

    Returns:
        tuple: (attacker_id, defender_id)
    """
    attacker = arriving_fleet.owner  # "p1" or "p2"

    if garrison_ships > 0:
        # Defender is whoever controlled the star (or NPC if no owner)
        if control_before is not None:
            defender = control_before  # "p1" or "p2"
        else:
            defender = "npc"  # NPC garrison present
    else:
        # No garrison present (shouldn't happen in combat, but defensive coding)
        defender = None

    return (attacker, defender)
```

### 4.3 Simultaneous Arrival Special Case

When **two player fleets arrive at an uncontrolled star on the same turn:**

1. **Both are considered attackers** (no defender present)
2. **Primary attacker** is determined alphabetically by player ID:
   - `"p1"` < `"p2"` → Player 1 is primary attacker
3. **Display language** uses "clashed" instead of "attacked"
4. **Combat resolution** proceeds normally with standard damage calculations
5. **Winner takes control** of the star

**Implementation Note:**
```python
def handle_simultaneous_arrival(fleet1, fleet2, star):
    """Handle two fleets arriving at uncontrolled star simultaneously."""
    # Determine primary attacker alphabetically
    if fleet1.owner < fleet2.owner:  # "p1" < "p2"
        primary_attacker = fleet1.owner
        secondary_attacker = fleet2.owner
    else:
        primary_attacker = fleet2.owner
        secondary_attacker = fleet1.owner

    # For display purposes, use "clashed" language
    # For data structure, treat primary as attacker, secondary as defender
    return {
        "attacker": primary_attacker,
        "defender": secondary_attacker,
        "simultaneous": True  # Flag for display logic
    }
```

### 4.4 Edge Cases

**Case 1: Player attacks their own star**
- Should not occur due to order validation
- If it occurs, treat as no combat (fleet merges with garrison)

**Case 2: Empty star with no garrison**
- Fleet arrives and takes control unopposed
- No combat report generated

**Case 3: Multiple fleets arrive from same player**
- Fleets combine before engaging defender
- Treat as single attacker force

---

## 5. Display Examples by Scenario

### 5.1 Player Conquers Opponent Star

**Data:**
```json
{
  "star": "K",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 51,
  "defender_ships_before": 6,
  "attacker_losses": 3,
  "defender_losses": 6,
  "control_before": "opp",
  "control_after": "me"
}
```

**Display:**
```
⚔️ Your fleet emerged from hyperspace and defeated Admiral Sonnet Krios's garrison at K (Kappa Phoenicis). You now control K! (-9 ships)
```

---

### 5.2 Opponent Conquers Player Star

**Data:**
```json
{
  "star": "F",
  "attacker": "opp",
  "defender": "me",
  "attacker_ships_before": 20,
  "defender_ships_before": 5,
  "attacker_losses": 2,
  "defender_losses": 5,
  "control_before": "me",
  "control_after": "opp"
}
```

**Display:**
```
⚔️ Admiral Sonnet Krios's fleet emerged from hyperspace and captured F (Fomalhaut). Admiral Sonnet Krios now controls F! (-7 ships)
```

---

### 5.3 Player Defense Succeeds

**Data:**
```json
{
  "star": "M",
  "attacker": "opp",
  "defender": "me",
  "attacker_ships_before": 8,
  "defender_ships_before": 12,
  "attacker_losses": 8,
  "defender_losses": 4,
  "control_before": "me",
  "control_after": "me"
}
```

**Display:**
```
⚔️ Your defending garrison at M (Mintaka) repelled Admiral Sonnet Krios's attacking fleet. (-12 ships)
```

---

### 5.4 Player Attack Fails

**Data:**
```json
{
  "star": "D",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 10,
  "defender_ships_before": 15,
  "attacker_losses": 10,
  "defender_losses": 5,
  "control_before": "opp",
  "control_after": "opp"
}
```

**Display:**
```
⚔️ Your attacking fleet at D (Deneb) was repelled by the defending garrison. (-10 ships, all lost)
```

---

### 5.5 Mutual Destruction

**Data:**
```json
{
  "star": "K",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 7,
  "defender_ships_before": 7,
  "attacker_losses": 7,
  "defender_losses": 7,
  "control_before": "opp",
  "control_after": null
}
```

**Display:**
```
⚔️ Battle at K (Kappa Phoenicis) resulted in mutual destruction. The star is now uncontrolled. (mutual destruction)
```

---

### 5.6 Simultaneous Arrival (Player Wins)

**Data:**
```json
{
  "star": "G",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 15,
  "defender_ships_before": 10,
  "attacker_losses": 3,
  "defender_losses": 10,
  "control_before": null,
  "control_after": "me"
}
```

**Display:**
```
⚔️ Your fleet clashed with Admiral Sonnet Krios's fleet arriving simultaneously at G (Gliese 581). You emerged victorious and now control G! (-13 ships)
```

---

### 5.7 NPC Conquest Success

**Data:**
```json
{
  "star": "B",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 10,
  "defender_ships_before": 3,
  "attacker_losses": 1,
  "defender_losses": 3,
  "control_before": null,
  "control_after": "me"
}
```

**Display:**
```
⚔️ Your fleet emerged from hyperspace and defeated the NPC garrison at B (Betelgeuse). You now control B! (-4 ships)
```

---

### 5.8 NPC Defense Success

**Data:**
```json
{
  "star": "T",
  "attacker": "me",
  "defender": "opp",
  "attacker_ships_before": 2,
  "defender_ships_before": 3,
  "attacker_losses": 2,
  "defender_losses": 1,
  "control_before": null,
  "control_after": null
}
```

**Display:**
```
⚔️ Your attacking fleet at T (Tau Ceti) was repelled by the NPC garrison. (-2 ships, all lost)
```

---

## 6. Implementation Guidance

### 6.1 Data Structures

**Internal Combat Result (Core Game State):**
```python
@dataclass
class CombatResult:
    star_id: str
    attacker_id: str  # "p1" or "p2"
    defender_id: str  # "p1", "p2", or "npc"
    attacker_ships_before: int
    defender_ships_before: int
    attacker_losses: int
    defender_losses: int
    control_before: Optional[str]  # "p1", "p2", or None
    control_after: Optional[str]   # "p1", "p2", or None
    simultaneous: bool = False  # Flag for simultaneous arrival
```

**Perspective-Transformed Combat Report (For LLM):**
```python
def transform_combat_for_llm(combat: CombatResult, observing_player: str) -> dict:
    """Transform combat result into LLM-friendly perspective."""
    def transform_player_id(player_id: str) -> str:
        if player_id == "npc":
            # NPC treated as opponent placeholder
            return "opp"
        return "me" if player_id == observing_player else "opp"

    return {
        "star": combat.star_id,
        "attacker": transform_player_id(combat.attacker_id),
        "defender": transform_player_id(combat.defender_id),
        "attacker_ships_before": combat.attacker_ships_before,
        "defender_ships_before": combat.defender_ships_before,
        "attacker_losses": combat.attacker_losses,
        "defender_losses": combat.defender_losses,
        "control_before": transform_player_id(combat.control_before) if combat.control_before else None,
        "control_after": transform_player_id(combat.control_after) if combat.control_after else None
    }
```

### 6.2 Display Generation Function

**Signature:**
```python
def format_combat_report_for_human(
    combat: CombatResult,
    observing_player: str,
    star_name: str,
    opponent_name: str
) -> str:
    """
    Generate human-readable combat report.

    Args:
        combat: CombatResult object with raw combat data
        observing_player: "p1" or "p2" — perspective for display
        star_name: Full star name (e.g., "Kappa Phoenicis")
        opponent_name: Opponent display name (e.g., "Admiral Sonnet Krios")

    Returns:
        Formatted combat report string with emoji and narrative
    """
    pass  # Implementation handles template selection and formatting
```

**Key Implementation Steps:**
1. Transform player IDs to perspective ("me" vs "opp")
2. Detect combat scenario from data (conquest, repel, mutual destruction, etc.)
3. Select appropriate narrative template
4. Format star identification: `{star_id} ({star_name})`
5. Calculate casualty text
6. Return formatted string

### 6.3 Combat Scenario Detection Logic

```python
def detect_combat_scenario(combat: CombatResult, observing_player: str) -> str:
    """
    Determine which narrative template to use.

    Returns one of:
        - "attacker_conquest_me"
        - "attacker_conquest_opp"
        - "defender_repels_me"
        - "defender_repels_opp"
        - "mutual_destruction"
        - "simultaneous_clash"
        - "npc_conquest_success"
        - "npc_defense_success"
    """
    is_me_attacker = (combat.attacker_id == observing_player)
    is_me_defender = (combat.defender_id == observing_player)
    is_npc_defender = (combat.defender_id == "npc")

    # Check for simultaneous arrival
    if combat.simultaneous:
        return "simultaneous_clash"

    # Check for mutual destruction
    if (combat.attacker_losses == combat.attacker_ships_before and
        combat.defender_losses == combat.defender_ships_before):
        return "mutual_destruction"

    # Attacker victory scenarios
    if combat.defender_losses == combat.defender_ships_before:
        if is_npc_defender:
            if is_me_attacker:
                return "npc_conquest_success"
            else:
                return "attacker_conquest_opp"  # Opp conquers NPC
        else:
            return "attacker_conquest_me" if is_me_attacker else "attacker_conquest_opp"

    # Defender victory scenarios
    if combat.attacker_losses == combat.attacker_ships_before:
        if is_npc_defender:
            return "npc_defense_success"
        else:
            return "defender_repels_me" if is_me_defender else "defender_repels_opp"

    # Inconclusive combat (both sides survive but control changes)
    # Treat as attacker victory if control changed to attacker
    if combat.control_after == combat.attacker_id:
        return "attacker_conquest_me" if is_me_attacker else "attacker_conquest_opp"
    else:
        return "defender_repels_me" if is_me_defender else "defender_repels_opp"
```

---

## 7. Testing Requirements

### 7.1 Unit Tests

**Test Categories:**

1. **Perspective Transformation Tests**
   - Verify `"p1"` → `"me"` / `"p2"` → `"opp"` for Player 1
   - Verify `"p2"` → `"me"` / `"p1"` → `"opp"` for Player 2
   - Verify `"npc"` → `"opp"` for both players
   - Verify `None` (null control) remains `None`

2. **Scenario Detection Tests**
   - Test all 8 narrative scenarios with correct data patterns
   - Verify mutual destruction detection
   - Verify simultaneous arrival flag handling
   - Verify NPC combat detection via `control_before == null`

3. **Casualty Formatting Tests**
   - Single ship: `(-1 ship)`
   - Multiple ships: `(-5 ships)`
   - Total loss: `(-10 ships, all lost)`
   - Mutual destruction: `(mutual destruction)`
   - Zero losses: `(-0 ships)` (edge case)

4. **Template Rendering Tests**
   - Verify star identification format: `K (Kappa Phoenicis)`
   - Verify emoji presence: `⚔️`
   - Verify control change markers: `You now control K!`
   - Verify opponent name insertion: `Admiral Sonnet Krios`
   - Verify sentence structure and grammar

### 7.2 Integration Tests

**Test Scenarios:**

1. **Player vs Player Conquest**
   - Player 1 attacks Player 2 star → Player 1 wins
   - Verify both players receive correct perspective

2. **Player vs Player Defense**
   - Player 2 attacks Player 1 star → Player 1 defends successfully
   - Verify attacker sees "repelled" message

3. **Player vs NPC Conquest**
   - Player attacks uncontrolled NPC star → wins
   - Verify "NPC garrison" language

4. **Player vs NPC Failure**
   - Player attacks strong NPC garrison → loses
   - Verify "repelled by NPC garrison" language

5. **Mutual Destruction**
   - Equal fleets clash → both eliminated
   - Verify "mutual destruction" message and star becomes uncontrolled

6. **Simultaneous Arrival**
   - Two player fleets arrive same turn at empty star
   - Verify "clashed" language
   - Verify primary attacker determined alphabetically

### 7.3 Edge Case Tests

1. **Empty Star Arrival (No Combat)**
   - Fleet arrives at empty star → no combat report
   - Verify control change logged but no ⚔️ report

2. **Multiple Fleets Same Player**
   - Two fleets from same player arrive simultaneously
   - Verify they combine before combat resolution

3. **Zero Losses Victory**
   - Attacker wins without casualties (rare but possible with rounding)
   - Verify `(-0 ships)` displays correctly

4. **Very Long Star Names**
   - Test truncation or wrapping for display
   - Ensure format remains readable

---

## 8. Design Rationale

### 8.1 Why Remove `combat_type` Field?

**Redundancy Analysis:**
The `combat_type` field (e.g., `"attacker_victory"`, `"defender_repels"`) can be **fully derived** from existing fields:

- **Attacker Victory:** `defender_losses == defender_ships_before` AND `control_after == attacker`
- **Defender Repels:** `attacker_losses == attacker_ships_before` AND `control_after != attacker`
- **Mutual Destruction:** `attacker_losses == attacker_ships_before` AND `defender_losses == defender_ships_before`
- **Simultaneous Clash:** Separate flag (`simultaneous == True`)

**Benefits of Removal:**
- **Simplicity:** Fewer fields = less cognitive load for implementers and consumers
- **Consistency:** Eliminates risk of `combat_type` conflicting with actual data
- **Flexibility:** LLM agents can infer outcome based on their own logic/priorities
- **Maintenance:** One less field to validate and keep synchronized

**User Confirmation:**
User explicitly confirmed: *"It makes sense to not have combat_type since the winner is determined by comparing ships before and after."*

### 8.2 Why Use "Clashed" for Simultaneous Arrivals?

**Problem:** When two fleets arrive at an empty star simultaneously, neither is technically "defending."

**Solution:** Use neutral "clashed" language instead of attacker/defender framing.

**Rationale:**
- **Accuracy:** Reflects the reality that no garrison was present
- **Fairness:** Doesn't privilege one player's perspective over the other
- **Narrative Clarity:** Makes the simultaneous nature explicit
- **Consistency:** Aligns with sci-fi tropes of "hyperspace emergence" battles

### 8.3 Why Include Star Names in Reports?

**Problem:** Star letters alone (e.g., "K") are not memorable or immersive.

**Solution:** Always display both letter and name: `K (Kappa Phoenicis)`

**Rationale:**
- **Immersion:** Star names add flavor and make the universe feel alive
- **Clarity:** Players can use either letter (for brevity) or name (for memorability)
- **Accessibility:** New players learn star names through repeated exposure
- **Consistency:** Matches format used in other game reports (production, arrivals, etc.)

### 8.4 Why Transform Perspective for LLM Agents?

**Problem:** Internal game state uses absolute player IDs (`"p1"`, `"p2"`), which forces LLM agents to track which player they are.

**Solution:** Transform all player references to `"me"` vs `"opp"` before sending to LLM.

**Rationale:**
- **Cognitive Load:** LLM doesn't need to remember "I am Player 2" every turn
- **Prompt Simplicity:** Eliminates conditional logic in system prompts
- **Error Reduction:** Prevents LLM from accidentally planning for opponent
- **Consistency:** Matches other observation data (fleets, stars, etc.) which are already perspective-transformed

### 8.5 Why Limit Reports to 1-2 Sentences?

**Problem:** Verbose reports clutter the UI and obscure critical information.

**Solution:** Enforce strict brevity with clear templates.

**Rationale:**
- **Scannability:** Players need to quickly assess multiple combats per turn
- **Signal-to-Noise:** Every word should carry strategic information
- **Pacing:** Short reports maintain game tempo and momentum
- **Accessibility:** Less text = easier to parse under time pressure

---

## 9. Future Enhancements (Out of Scope for v1.0)

### 9.1 Combat Replay Visualization

**Description:** Animated replay showing ship movements and destruction during combat.

**Benefits:**
- Enhanced immersion and spectacle
- Better understanding of combat mechanics
- Opportunities for tactical analysis

**Implementation Considerations:**
- Requires frame-by-frame combat simulation
- UI complexity for rendering
- Performance impact on large battles

### 9.2 Detailed Combat Logs

**Description:** Optional verbose mode showing round-by-round damage calculations.

**Benefits:**
- Educational for new players learning combat math
- Debugging tool for balance testing
- Competitive players want detailed analysis

**Implementation Considerations:**
- Separate toggle or panel to avoid clutter
- Integration with combat resolution engine
- Storage and retrieval of historical combat data

### 9.3 Combat Notifications/Alerts

**Description:** Special UI treatment for critical combats (e.g., home star under attack).

**Benefits:**
- Ensures players don't miss critical events
- Adds tension and drama
- Supports "glance-ability" for experienced players

**Implementation Considerations:**
- Notification system architecture
- Priority/severity levels
- Sound effects and visual flourishes

### 9.4 LLM Narrative Generation

**Description:** Allow LLM agents to generate their own combat narration instead of using templates.

**Benefits:**
- More dynamic and varied language
- Personality expression for AI opponents
- Emergent storytelling

**Implementation Considerations:**
- Prompt engineering for consistent quality
- Token cost per combat report
- Filtering for inappropriate content
- Balance with readability and brevity

---

## 10. Appendix: Complete Template Reference

### Human Display Templates (Quick Reference)

| Scenario | Key Indicators | Template Start |
|----------|---------------|----------------|
| **Attacker Conquest (Me)** | `attacker==me`, `control_after==me`, defender eliminated | `⚔️ Your fleet emerged from hyperspace and defeated...` |
| **Attacker Conquest (Opp)** | `attacker==opp`, `control_after==opp`, defender eliminated | `⚔️ [Opponent]'s fleet emerged from hyperspace and captured...` |
| **Defender Repels (Me)** | `defender==me`, `control_after==me`, attacker eliminated | `⚔️ Your defending garrison at [STAR] repelled...` |
| **Defender Repels (Opp)** | `attacker==me`, `control_after!=me`, attacker eliminated | `⚔️ Your attacking fleet at [STAR] was repelled...` |
| **Mutual Destruction** | Both sides eliminated, `control_after==null` | `⚔️ Battle at [STAR] resulted in mutual destruction...` |
| **Simultaneous Clash** | `simultaneous==true`, no prior garrison | `⚔️ Your fleet clashed with [Opponent]'s fleet arriving simultaneously...` |
| **NPC Conquest (Win)** | `attacker==me`, `control_before==null`, defender eliminated | `⚔️ Your fleet emerged from hyperspace and defeated the NPC garrison...` |
| **NPC Conquest (Loss)** | `attacker==me`, `control_before==null`, attacker eliminated | `⚔️ Your attacking fleet at [STAR] was repelled by the NPC garrison...` |

---

## 11. Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-16 | Initial specification based on user requirements | game-design-oracle |

---

**END OF SPECIFICATION**
