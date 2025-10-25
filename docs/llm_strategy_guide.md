# Space Conquest: LLM Player Strategy Guide (REVISED)

## Purpose
This guide provides mathematically-grounded strategic principles for LLM agents playing Space Conquest. It translates game mechanics into actionable decision rules and quantitative thresholds.

---

## 1. Opening Strategy (Turns 1-5)

### Turn 1 Priority: CONQUER, Not Scout
**Goal**: Capture nearby high-production stars immediately. Opponent is 8-12 parsecs away (no early threat).

**Expansion Pattern**:
- Send conquest fleets to 2-3 nearest unknown stars (distance 2-4)
- ANY RU value is worth capturing (even 1 RU > 0 RU)
- You'll discover RU when you capture (same info, but you own the star)
- Keep minimum 2 ships at home star (50% of starting garrison)

**Fleet Sizing for NPC Conquest** (vs FULL garrison):
- **1 RU star**: 3 ships (2 beats 1, lose 1, have 1 survivor; need 1 for garrison)
- **2 RU star**: 4 ships (3 beats 2, lose 1, have 2 survivors; need 2 for garrison)
- **3 RU star**: 5-6 ships (4 beats 3, lose 2, have 2 survivors; need 3 for garrison → send 6 or wait for production)

**Decision Rule**: Turn 1, conquer 2-3 nearby stars. Do NOT waste ships on scouting unless distance >5 or strategic value unclear.

### Turns 2-3: Consolidate Early Empire
**Garrison Management**:
- Ensure all captured stars have garrison ≥ RU (50% rebellion is too risky)
- Rebellion resets NPC garrison to full RU value
- Non-rebelling NPC garrisons stay depleted (see "Re-attacking Weakened Stars" below)

**Continued Expansion**:
- Conquer all nearby stars (distance ≤4) regardless of RU
- Production snowball: Each star captured by Turn 3 = +10 ships by Turn 6

### Turns 4-5: Transition to Mid-Game
- Maintain home defense: **minimum 4 ships** (enough to repel early raid)
- Begin scouting distant regions (distance 5-8) to find:
  - High-RU stars (3 RU targets)
  - Opponent home star location
  - Enemy garrison strengths at contested stars

### Re-attacking Weakened Stars (CRITICAL MECHANIC)
**NPC garrisons do NOT regenerate unless rebellion occurs**:
- Example: 3 RU star, you attacked with 4 ships, mutual destruction → Star now has 0 defenders
- Next turn: Send 3 ships to capture (need garrison only, no combat)
- If partial loss: 3 RU star, you sent 2 ships, lost → Star has 3 - ceil(2/2) = 2 defenders remaining
- Next turn: Send 3 ships to capture (3 beats 2, lose 1, have 2 survivors; need 1 more for garrison)

**Track your combat history**: Don't send full-strength fleets to weakened targets.

**Rebellion resets garrison**: If rebellion occurs at your under-defended star and rebels win, star reverts to NPC with full RU garrison restored.

---

## 2. Economic Decision-Making

### Expected Value Framework
When evaluating whether to capture a distant star, calculate:

**EV(capture) = Production_Value × Probability_Survival - Cost**

Where:
- **Production_Value** = RU × (remaining_turns_in_game)
- **Probability_Survival** = (0.98)^distance (both ways)
- **Cost** = ships_lost_in_combat + opportunity_cost

**CRITICAL MECHANIC CLARIFICATION**:
Hyperspace loss is **ALL-OR-NOTHING**:
- A fleet in transit rolls 2% chance per turn to be COMPLETELY DESTROYED (all ships lost)
- If the roll succeeds, the fleet continues with 0 casualties
- **Do NOT calculate per-ship losses** - e.g., "lose 6 out of 30 ships" is impossible

**Example**:
- 30-ship fleet traveling distance 8:
  - Cumulative fleet loss probability: 14.93%
  - **Outcome 1** (85.07% chance): All 30 ships arrive safely
  - **Outcome 2** (14.93% chance): All 30 ships destroyed, 0 arrive
  - **Never**: Partial losses like 24 ships arriving

**Expected Value vs Realized Outcomes**:
The formula `Probability_Survival = (0.98)^distance` gives the FLEET's survival probability, not a per-ship rate.
- Expected fleet size on arrival = original_size × (0.98)^distance
- But realized fleet size is binary: either original_size or 0
- High variance on long-range operations makes them "boom or bust"

**Break-even Distance by RU**:
With 2% hyperspace loss per turn (using Chebyshev distance):

| RU Value | Max Distance for Positive EV | Cumulative Fleet Loss Risk |
|----------|-------------------------------|----------------------------|
| 1 RU     | 3 parsecs                     | 5.9%                       |
| 2 RU     | 5 parsecs                     | 9.6%                       |
| 3 RU     | 8 parsecs                     | 14.9%                      |

**Decision Rule** (Distance Thresholds):

**Early Game (Turns 1-5)**:
- Distance ≤4: Conquer ALL nearby stars immediately (any RU value)
- Distance 5-6: Conquer if RU ≥2 or strategic value (blocks opponent corridor)

**Mid/Late Game (Turns 6+)**:
- Distance ≤3: Capture any star (RU ≥1)
- Distance 4-5: Only capture if RU ≥2
- Distance 6-8: Only capture if RU=3 OR strategically critical (opponent blocking)
- Distance >8: Only justified for home star assault or decisive territorial control

### Production Snowball Mechanics
Early production advantage compounds exponentially:

**Turn 5 fleet comparison**:
- 1 star (4 RU): 4 + 4 + 4 + 4 + 4 = 20 ships
- 2 stars (4 + 2 RU): 6 + 6 + 6 + 6 + 6 = 30 ships (+50% advantage)
- 3 stars (4 + 2 + 2 RU): 8 × 5 = 40 ships (+100% advantage)

**Implication**: Each additional star captured by turn 3 gives ~10 extra ships by turn 6. Aggressive early expansion pays dividends.

---

## 2.5. Combat Math & Fleet Sizing

### Conquest Fleet Formula
To capture an NPC star with **full garrison** (RU = N):
```
Minimum to win combat: N + 1 ships
Losses in combat: ceil(N/2) ships
Survivors after combat: (N+1) - ceil(N/2)
Required garrison: N ships
```

**Practical Fleet Sizes** (vs full NPC garrison):
| Star RU | NPC Defenders | Min Fleet | Combat Losses | Survivors | Garrison Need | Shortfall |
|---------|---------------|-----------|---------------|-----------|---------------|-----------|
| 1 RU    | 1             | 2         | 1             | 1         | 1             | 0 (OK)    |
| 2 RU    | 2             | 3         | 1             | 2         | 2             | 0 (OK)    |
| 3 RU    | 3             | 4         | 2             | 2         | 3             | -1        |

**3 RU Star Special Case**:
- 4 ships: Win combat, have 2 survivors, need 3 for garrison → 1 ship short
- **Option A**: Send 5-6 ships (6 for safety margin)
- **Option B**: Send 4 ships, wait 1 turn for production, then garrison

**Re-attacking Weakened NPC Stars**:
If NPC garrison was damaged in prior combat (and no rebellion occurred):
- Calculate remaining defenders: Original_RU - ceil(your_losses/2)
- Send (remaining_defenders + 1) ships + garrison buffer
- Example: 3 RU star, you sent 4 ships, both died → 0 defenders remain → Send 3 ships (just for garrison)

---

## 3. Garrison Mathematics

### Rebellion Risk Calculation
For a captured NPC star with RU = N and garrison = G:

**Rebellion occurs with 50% probability when G < N**

**Expected Loss** from rebellion:
- 50% chance × (G ships lost + loss of star)
- If rebellion succeeds: lose G ships AND lose N RU/turn production
- If rebellion fails: no loss

**Optimal Garrison Strategy**:
- **Always maintain G ≥ N** unless you're abandoning the star
- Exception: If you plan to recapture within 2 turns, 50% rebellion risk may be acceptable
- Over-garrisoning (G > N) has opportunity cost but zero rebellion risk

**Decision Rule**:
- Default: Garrison exactly RU ships (optimal)
- Under pressure: Accept 50% rebellion on low-value (1 RU) stars if ships needed elsewhere urgently
- Never accept rebellion risk on 3 RU stars (too valuable)

### Opportunity Cost Analysis
Keeping 1 extra ship as garrison costs:
- **Direct cost**: 1 fewer ship for offense/expansion
- **Opportunity cost**: ~0.5 combats prevented (each combat needs ~2 ships advantage)

Rebellion costs:
- **Loss of production**: N RU × turns until recapture
- **Fleet loss**: G ships destroyed
- **Recapture cost**: N+1 ships to retake (if full garrison restored by rebellion)

**Math**: If average time to recapture is 3 turns, rebellion on 2 RU star costs 2×3 = 6 ship-equivalents. Maintaining 2-ship garrison only costs 2 ships. **Always garrison.**

---

## 4. Fog-of-War Tactics

### Information States
Each star has one of three information states:
1. **Visited (known_ru ≠ null)**: You know exact RU and ownership
2. **Visible but unvisited (known_ru = null)**: You see coordinates but not strategic value
3. **Home stars**: Always visible with RU = 4

### Efficient Scouting (Mid-Game Only)
**When to scout** (Turns 5+):
- You've captured all nearby stars (distance ≤4)
- Need to identify high-RU distant targets (distance 5-8)
- Need to locate opponent home star
- Need to assess enemy garrison strengths

**Cost-benefit of scouting**:
- 1-ship scout costs: 1 ship + (0.02 × distance) expected hyperspace loss
- Value: Reveals RU, enabling informed expansion decisions

**Optimal scouting distance**: ≤ 4 parsecs
- At distance 4: ~7.7% chance scout is lost (acceptable)
- At distance 6: ~11.5% loss (only scout if strategically critical)

**Multi-star scouting**: Send 1 scout to multiple stars from same origin, rather than sequential scouting. Parallelism reveals more information per turn.

### Inferring Opponent Position
**Use visited_stars to deduce enemy activity**:
- If a star's ownership changed without your involvement: opponent captured it
- If an unvisited star becomes visited: opponent or you sent fleet there
- Opponent home star is typically 8-15 parsecs from your home (opposite corner)

**Tactical inference**:
- If opponent captures 3 RU star at distance 5: they likely have 5-7 ships there now (min garrison)
- If no new stars captured in 2 turns: opponent is consolidating or preparing offensive

---

## 5. Distance & Hyperspace Risk

### Risk-Adjusted Fleet Sizing
With 2% loss per turn in transit, adjust fleet size by expected losses:

**Fleet sizing formula**:
Send ships = Required_ships / (0.98)^distance

**Practical table**:
| Distance | Loss Factor | Send 10 to deliver... |
|----------|-------------|------------------------|
| 3        | 5.9%        | 10 ships → 9.4 arrive  |
| 5        | 9.6%        | 10 ships → 9.0 arrive  |
| 8        | 14.9%       | 10 ships → 8.5 arrive  |

**Decision rule**: For critical operations (home star assault), add +15% buffer:
- To deliver 10 ships at distance 5: send 12 ships
- To deliver 15 ships at distance 8: send 18 ships

### Route Optimization
**Chebyshev distance advantage**: Diagonal movement costs the same as orthogonal movement.
- Distance from (0,0) to (3,3) = 3 (not 6)
- All 8 directions (N, NE, E, SE, S, SW, W, NW) are equally efficient
- This makes ~25% more of the map economically accessible compared to Manhattan distance

**Strategic routing**:
- Take advantage of diagonal paths to reach distant stars faster
- Avoid routes that pass near opponent's strong garrisons (they might intercept)
- Route through your own stars for staging: send in waves rather than one large fleet

---

## 6. Mid-Game Strategy (Turns 6-12)

### Production Advantage
By turn 6, total production determines strategic options:
- **8+ RU total**: You can expand AND prepare offense
- **6-7 RU**: Focus on denying opponent expansion (interference)
- **≤5 RU**: Defensive posture, raid opponent expansions

**Key metric**: Production differential
- If you produce 8 RU/turn and opponent produces 6: you gain +2 ships/turn net advantage
- After 5 turns, you're +10 ships ahead (decisive)

### Denying Opponent Expansion
**Interference tactics**:
- Race to capture high-RU stars opponent is approaching
- Send small fleets (2-3 ships) to "poison" NPC stars opponent might want
- Force opponent into long-distance moves (higher hyperspace risk)

**Math**: If opponent must travel 8 parsecs while you travel 3:
- Their loss: ~15%
- Your loss: ~6%
- Net advantage: ~9% more ships arrive for you

### Fleet Concentration Principle
**Combat is deterministic winner-take-all**. Key insights:
- 6 ships vs 5 ships: 6 wins, loses 3, nets 3 survivors
- 6 ships vs 3 ships: 6 wins, loses 2, nets 4 survivors
- 12 ships vs 5 ships: 12 wins, loses 3, nets 9 survivors

**Implication**: Concentrate fleets. Two 5-ship fleets arriving sequentially lose to one 7-ship fleet. One 10-ship fleet beats two 5-ship fleets arriving together.

**Tactical rule**: When attacking, ensure fleet > defender by at least 3 ships for comfortable margin.

---

## 7. Endgame Transition (Turns 13-20)

### Recognizing Endgame
Transition to endgame when:
- You know opponent's home star location
- You have production advantage (≥8 total RU)
- You have sufficient ships to mount home star assault

### Minimum Home Star Assault Force
**Base calculation**:
- Home star produces 4 ships/turn
- Defender likely has 6-12 ships garrison (if rational)
- You need fleet > defender by 5+ ships for safety

**Recommended assault fleet**: 15-20 ships
- Defeats 12-ship defense: 15 wins, loses 6, nets 9 (captures star)
- Accounts for 10-15% hyperspace loss over distance 5-8

**Staging**: Build fleet over 2-3 turns at forward star (distance 3-4 from enemy home), then strike.

### Defending Against Counter-Rush
**Simultaneous home star trades = draw** (you both lose). Must defend.

**Home defense minimum**:
- If opponent can reach your home in 3 turns: keep 8 ships home
- If opponent 5+ turns away: 4-6 ships sufficient
- Never drop below 4 ships at home star

**Detection**: If opponent stops expanding and their captured stars accumulate ships, **they're preparing assault**. Immediate response:
1. Reinforce home star to 10+ ships
2. Send small fleets to intercept if you can estimate their route
3. Consider counter-rush if you'd arrive first

---

## 8. Common Pitfalls & Counter-Strategies

### Pitfall 1: Over-Expansion Leading to Rebellions
**Symptom**: Capturing 4+ stars without maintaining garrisons
**Cost**: 50% rebellion chance = ~2 stars lost, ~6 ships destroyed, production collapses
**Fix**: Only expand as fast as you can garrison. Better to control 3 stars well than 5 stars poorly.

### Pitfall 2: Under-Defending Home Star
**Symptom**: Leaving 0-2 ships at home to maximize expansion
**Cost**: Opponent raids home star with 5 ships, you lose game instantly
**Fix**: **Always keep minimum 4 ships at home**. Non-negotiable until you've confirmed opponent position and fleet status.

### Pitfall 3: Early Scouting (Wasting Ships)
**Symptom**: Sending 1-ship scouts on Turn 1-3 to nearby stars
**Cost**: Waste 3 ships on scouting = 1 fewer expansion
**Fix**: Conquer nearby stars immediately (discover RU on capture). Scout only mid-game (Turn 5+) for distant/unknown regions.

### Pitfall 4: Sending Full Fleets to Weakened NPC Stars
**Symptom**: Re-attacking 3 RU star (previously damaged, now has 1 defender) with 6 ships
**Cost**: Waste 3 ships that could capture another star
**Fix**: Track combat history. If you damaged NPC garrison, send right-sized fleet:
- Check NPC losses from prior combat: ceil(your_lost_ships/2)
- Remaining defenders = Original_RU - NPC_losses
- Send (remaining + 1) + garrison = economical re-conquest fleet

**Example**:
- Turn 5: Attack 3 RU star with 4 ships → Mutual destruction (both die)
- Star now has 3 - ceil(4/2) = 3 - 2 = 1 defender
- Turn 6: Send 2 ships (beats 1, lose 1, have 1 survivor) + 2 more for garrison = 4 ships total (not 6)

### Pitfall 5: Ignoring Hyperspace Losses
**Symptom**: Routing all expansion through distance-8+ paths
**Cost**: Lose 15%+ of fleets, arrive undermanned, lose combats
**Fix**: Prefer shorter routes. Take advantage of diagonal paths (Chebyshev distance). If distant star is valuable (3 RU), send 20% extra ships to compensate for losses.

### Pitfall 6: Sequential Fleet Arrivals
**Symptom**: Sending waves of 5 ships/turn that arrive at different times
**Cost**: Opponent defeats each wave separately with concentrated force
**Fix**: Coordinate arrivals. If attacking defended star, mass 15-ship fleet, send all at once.

### Pitfall 7: Neglecting Production Differential
**Symptom**: Engaging in even trades while behind in production
**Cost**: Opponent rebuilds faster, you lose war of attrition
**Fix**: If behind in production, avoid fair fights. Raid lightly-defended expansions, force opponent to split fleets, then strike when they're divided.

---

## 9. Decision Flowchart for Each Turn

**Step 1: Assess Threats**
- Is my home star under immediate threat? (enemy fleet <3 turns away)
  - YES: Reinforce home, abandon other operations
  - NO: Proceed

**Step 2: Check Garrisons**
- Do all my captured stars have garrison ≥ RU?
  - NO: Prioritize garrisoning (send ships from home)
  - YES: Proceed

**Step 3: Evaluate Production**
- Do I have production advantage over opponent?
  - UNKNOWN: Scout to determine
  - YES: Prepare offense (build assault fleet)
  - NO: Focus on expansion, deny opponent resources

**Step 4: Choose Primary Action**
- If turns 1-5: EXPAND (conquer nearest stars immediately, scout later)
- If turns 6-12: CONTEST (deny opponent expansion, build fleet)
- If turns 13+: ASSAULT (strike opponent home star)

**Step 5: Execute & Record**
- Validate orders with propose_orders()
- Submit with submit_orders()
- Record discoveries and strategic notes in memory

---

## 10. Quick Reference Tables

### RU Value vs Distance
| Star RU | Max Efficient Distance | Min Fleet Size (Full Garrison) | Min Fleet (Weakened) |
|---------|------------------------|--------------------------------|----------------------|
| 1 RU    | 3 parsecs              | 3 ships (2+1 buffer)           | 2 ships (if 0 NPC)   |
| 2 RU    | 5 parsecs              | 4 ships (3+1 buffer)           | 3 ships (if 0 NPC)   |
| 3 RU    | 8 parsecs              | 5-6 ships (5 min, 6 safe)      | 4 ships (if 0 NPC)   |
| 4 RU    | Any (home star)        | 15+ ships (expect 6-12 defense)| N/A                  |

### Hyperspace Loss by Distance (Chebyshev)
| Distance | Single Trip Loss | Round Trip Loss | Risk Level |
|----------|------------------|-----------------|------------|
| 1-3      | 2-6%             | 4-12%           | Minimal    |
| 4-5      | 8-10%            | 15-19%          | Acceptable |
| 6-8      | 11-15%           | 21-28%          | Moderate   |
| 9-11     | 17-20%           | 31-36%          | High       |

### Combat Resolution Quick Math
| Attacker | Defender | Winner   | Attacker Survives | Defender Survives |
|----------|----------|----------|-------------------|-------------------|
| 10       | 5        | Attacker | 7                 | 0                 |
| 8        | 8        | Tie      | 0                 | 0                 |
| 6        | 4        | Attacker | 4                 | 0                 |
| 5        | 6        | Defender | 0                 | 3                 |

Formula: Winner loses ceil(loser/2) ships

---

## Conclusion

Success in Space Conquest requires:
1. **Aggressive early expansion** (turns 1-5): Capture 2-3 stars immediately (conquer, don't scout)
2. **Disciplined garrison management**: Always maintain garrison ≥ RU
3. **Production snowball**: Each star captured early = 10+ ship advantage by turn 8
4. **Risk management**: Prefer distance ≤5 routes, add 15% buffer for critical operations. Leverage diagonal movement (Chebyshev distance).
5. **Information gathering**: Scout efficiently mid-game (distance 5-8, find enemy positions)
6. **Concentration of force**: Mass fleets for decisive battles
7. **Home defense**: Never drop below 4 ships at home star
8. **Track combat history**: Don't waste ships re-attacking weakened NPC stars with full fleets

The player who expands fastest while maintaining garrisons typically wins. The player who over-extends or under-defends typically loses to rebellion or home star rush.

**Final advice**: When in doubt, prefer expansion over hoarding. A 6-RU empire beats a 4-RU empire 95% of the time, regardless of tactical cleverness.
