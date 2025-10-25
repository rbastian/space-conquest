# Design Revision: NPC Garrison Depletion Mechanic

## Document Purpose
This document specifies a critical but under-documented game mechanic that significantly impacts strategic decision-making: **NPC garrison depletion**.

## Issue Summary
Current strategic guidance incorrectly assumes or implies that NPC garrisons regenerate between combat attempts. This leads to wasteful re-attack strategies where LLM agents send full-strength fleets to stars with already-depleted defenders.

## Authoritative Game Rule (from space_conquest_spec.md line 153)
> "NPCs do **not** rebuild or regenerate."

## Detailed Mechanic Specification

### NPC Garrison Depletion Rules

1. **Initial NPC Garrison**:
   - NPC star with RU = N has N defender ships
   - Example: 3 RU star has 3 NPC defender ships

2. **Combat Reduces NPC Garrison**:
   - When player attacks NPC star, standard combat rules apply
   - If player loses: NPC loses ceil(player_ships/2) ships
   - If mutual destruction: NPC garrison reduced to 0
   - **NPC garrison does NOT regenerate to original RU value**

3. **Garrison Persists Between Attacks**:
   - Damaged NPC garrison remains at reduced level
   - Only way to restore full garrison: rebellion that rebels win

4. **Rebellion Reset Mechanic**:
   - If player captures star but under-garrisons (garrison < RU)
   - 50% chance of rebellion spawning RU rebel ships
   - If rebels win: star reverts to NPC with FULL RU garrison restored
   - If rebels lose: garrison remains at post-combat level

### Examples

#### Example 1: Mutual Destruction
```
Turn 5: 3 RU star (3 NPC defenders)
Player sends: 4 ships
Combat: 4 vs 3 → Player loses 0, NPC loses ceil(4/2) = 2
Result: Both fleets destroyed (4-2=2 vs 3-2=1, tie → mutual)
Turn 6: Star now has 0 defenders (not 3)
Re-conquest: Send 3 ships (for garrison only, no combat needed)
```

#### Example 2: Player Loss
```
Turn 5: 3 RU star (3 NPC defenders)
Player sends: 2 ships
Combat: 2 vs 3 → NPC wins
NPC losses: ceil(2/2) = 1 ship
Turn 6: Star now has 3 - 1 = 2 defenders (not 3)
Re-conquest: Send 3 ships (3 beats 2, lose 1, have 2 survivors; need 3 for garrison → send 1 more)
Total needed: 4 ships (not 6)
```

#### Example 3: Rebellion Reset
```
Turn 5: Player captures 3 RU star, garrisons with 2 ships
Turn 6: Rebellion occurs (50% chance)
  - 3 rebel ships spawn
  - Combat: 2 vs 3 → Rebels win
  - Star reverts to NPC with 3 defenders (FULL garrison restored)
Turn 7: Must send full conquest fleet again (5-6 ships)
```

### Strategic Implications

1. **Track Combat History**:
   - LLM agents must record partial victories against NPC stars
   - Weakened stars require smaller re-conquest fleets
   - Significant ship savings over course of game

2. **Re-attack Economics**:
   - Full-strength attack on 3 RU: 6 ships
   - Re-attack after partial damage: 3-4 ships
   - Savings: 2-3 ships = another 1-2 RU star conquest

3. **Rebellion Risk**:
   - Only rebellion resets NPC garrison
   - Under-garrisoning becomes riskier (lose reset progress)
   - Incentive to maintain proper garrisons increases

## Required Updates

### 1. Update llm_player_2_agent_spec.md

**INSERT AFTER LINE 153 (NPC Combat section):**

```markdown
### NPC Garrison Depletion Mechanic
- **NPC defenders do NOT regenerate after combat** unless rebellion occurs
- After combat, NPC garrison is reduced by ceil(player_losses/2) per combat rules
- Example: 3 RU star with 3 defenders, player sends 4 ships:
  - If mutual destruction: Star now has 0 defenders (not 3)
  - If player loses: Star has 3 - ceil(4/2) = 1 defender remaining
- **Re-conquering weakened stars**: Send right-sized fleet based on remaining defenders
- **Rebellion resets garrison**: If player loses rebellion, star reverts to NPC with FULL RU garrison restored
- **Strategic implication**: Track partial victories; don't waste ships re-attacking with full-strength fleets
```

### 2. Update System Prompt (Decision Template, Section 8)

**ADD TO LINE 240 CONSTRAINTS:**

```markdown
> - Track NPC garrison depletion: NPCs do NOT regenerate unless rebellion occurs. Re-attack weakened stars with right-sized fleets.
```

### 3. Replace llm_strategy_guide.md

Replace entire file with `/Users/robert.bastian/github.com/rbastian/space-conquest/docs/llm_strategy_guide_REVISED.md`

## Validation Checklist

- [ ] Spec clearly states NPC non-regeneration
- [ ] System prompt includes garrison tracking guidance
- [ ] Strategy guide includes re-attack fleet sizing
- [ ] Examples demonstrate mechanic with math
- [ ] Rebellion reset mechanic explained
- [ ] Strategic implications highlighted

## Version History
- **v1.0** (2025-10-20): Initial specification based on expert player feedback
