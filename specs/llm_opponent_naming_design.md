# LLM Opponent Naming Design

**Version:** 1.1
**Date:** 2025-10-15
**Status:** APPROVED (with user additions)

---

## 1. Design Objectives

- **Personality**: Give the LLM opponent a memorable identity distinct from "Player 2"
- **Clarity**: Make it obvious the opponent is an AI agent, not a human
- **Model Transparency**: Display which AI model the player is facing
- **Variety**: Randomize name across games while maintaining consistency within a session
- **Simplicity**: Implement entirely at UI/display layer; keep internal game logic unchanged

---

## 2. Naming Format

### 2.1 Display Name Structure

**Format:** `Admiral [ModelName] [Surname]`

**Examples:**
- `Admiral Sonnet Krios` (Claude 3.5 Sonnet)
- `Admiral Haiku Vex` (Claude 3 Haiku)
- `Admiral Opus Thalion` (Claude 3 Opus)

**Rationale:**
- **"Admiral"** establishes military rank/authority fitting the conquest theme
- **Model name** (middle name) provides transparency about which AI is playing
- **Surname** (from name pool) adds personality and variety across games
- Three-part format feels natural and memorable (like real historical figures)

### 2.2 Alternative Format Considered (Rejected)

- `Admiral Krios (Sonnet)` - Feels like metadata in parentheses, less integrated
- `Sonnet Admiral Krios` - Awkward word order, less natural
- `Admiral Krios` (no model) - Doesn't meet user requirement for model transparency

---

## 3. Model Name Extraction

### 3.1 Extraction Logic

From model IDs like `claude-3-5-sonnet-20241022-v1:0` or `us.anthropic.claude-sonnet-4-5-20250929-v1:0`:

1. Split on hyphens and dots
2. Look for model family keywords: `["sonnet", "haiku", "opus"]`
3. Extract first matching keyword (case-insensitive)
4. Capitalize for display: `"Sonnet"`, `"Haiku"`, `"Opus"`

**Pseudocode:**
```python
def extract_model_name(model_id: str) -> str:
    model_id_lower = model_id.lower()
    if "sonnet" in model_id_lower:
        return "Sonnet"
    elif "haiku" in model_id_lower:
        return "Haiku"
    elif "opus" in model_id_lower:
        return "Opus"
    else:
        return "Claude"  # Generic fallback
```

### 3.2 Model Name Personality Alignment

Each model name brings thematic flavor:
- **Sonnet**: Elegant, poetic, strategic (14 lines of verse = deliberate planning)
- **Haiku**: Brief, focused, efficient (5-7-5 syllables = concise decision-making)
- **Opus**: Grand, masterwork, comprehensive (great work = thorough analysis)
- **Claude**: Generic, neutral (fallback for unknown or future models)

---

## 4. Name Pool Design

### 4.1 Admiral Surname Pool (10 names)

1. **Krios** - Greek-inspired, sounds commanding
2. **Vex** - Sharp, tactical, slightly ominous
3. **Thalion** - Elvish-inspired, noble
4. **Dravin** - Strong, authoritative
5. **Seris** - Elegant, strategic
6. **Korvan** - Military, disciplined
7. **Nexus** - Sci-fi, interconnected intelligence
8. **Rylon** - Clean, futuristic
9. **Thane** - Noble title, historical gravitas
10. **Vorel** - Mysterious, alien

**Design Principles:**
- 2 syllables (easy to remember and say)
- Avoid real historical names (prevents confusion with human players)
- Sci-fi/fantasy flavor (fits space conquest theme)
- Phonetically distinct (no similar-sounding names)
- Gender-neutral (AI transcends human gender concepts)
- Works with any model name prefix

---

## 5. Selection Mechanism

### 5.1 Seed-Based Selection (RECOMMENDED)

**Selection at game start:**
```python
def select_admiral_name(game_seed: int, model_id: str) -> str:
    model_name = extract_model_name(model_id)
    surnames = ["Krios", "Vex", "Thalion", "Dravin", "Seris",
                "Korvan", "Nexus", "Rylon", "Thane", "Vorel"]

    # Use game seed to deterministically select surname
    rng = Random(game_seed)
    surname = rng.choice(surnames)

    return f"Admiral {model_name} {surname}"
```

**Benefits:**
- **Reproducibility**: Same seed = same admiral name (useful for debugging/replays)
- **Consistency**: Name stays constant throughout the game session
- **Variety**: Different seeds = different names across games
- **No storage needed**: Name can be reconstructed from seed + model ID

**Alternative (True Random - NOT Recommended):**
- Random selection at game start (ignores seed)
- More variety but loses reproducibility
- Requires storing selected name in game state
- Complicates saved games and replays

### 5.2 Recommendation

**Use seed-based selection.** Space Conquest is a deterministic game with seedable RNG - the admiral name should follow the same principle.

---

## 6. Implementation Guidance

### 6.1 Where to Store

**Option A: Compute on-demand (RECOMMENDED)**
- Store only `game_seed` and `model_id` in game state
- Compute admiral name when needed for display
- Keeps game state clean; "p2" remains internal ID
- Name is deterministic from seed + model

**Option B: Store in game state**
- Add `p2_display_name: str` field to game state
- Set once at game initialization
- Faster lookup but adds state complexity
- Only use if performance profiling shows compute is expensive

**Recommendation:** Use Option A unless proven necessary otherwise.

### 6.2 Where to Apply

**UI/Display Layer Only:**
- Replace "Player 2" or "p2" in:
  - Combat messages: `"Admiral Sonnet Krios attacked your fleet at Delta!"`
  - Victory screen: `"Admiral Haiku Vex has conquered your Home Star!"`
  - Game log: `"Turn 5: Admiral Opus Thalion expanded to Fomalhaut"`
  - Status displays: `"Admiral Sonnet Krios: 7 stars, 23 ships"`

**Keep Internal:**
- Game state still uses `"p2"` for owner IDs
- LLM agent still receives `"p2"` in observations
- Validation logic unchanged
- Saved games/replays unchanged

### 6.3 Model ID Access

**Implementation must provide:**
- Pass `model_id` from LLM configuration to display layer
- If model changes mid-session (unlikely), update display name
- Handle missing model ID gracefully: fallback to `"Admiral Claude [Surname]"`

**Example integration points:**
```python
# At game initialization
game = Game(seed=42, p1="human", p2_agent=LLMAgent(model="claude-3-5-sonnet-..."))
game.p2_model_id = "claude-3-5-sonnet-20241022-v1:0"  # Store for display

# At display time
def get_p2_display_name(game: Game) -> str:
    return select_admiral_name(game.seed, game.p2_model_id)
```

---

## 7. Display Examples

### 7.1 Combat Messages

**Before:**
```
Turn 3: Player 2 fleet (5 ships) attacked your fleet at Altair (3 ships).
Player 2 won. Your fleet was destroyed. Player 2 lost 2 ships.
```

**After:**
```
Turn 3: Admiral Sonnet Krios fleet (5 ships) attacked your fleet at Altair (3 ships).
Admiral Sonnet Krios won. Your fleet was destroyed. Admiral Sonnet Krios lost 2 ships.
```

### 7.2 Victory Screen

**Before:**
```
GAME OVER
Player 2 has conquered your Home Star!
```

**After:**
```
GAME OVER
Admiral Haiku Vex has conquered your Home Star!
Better luck next time, Commander.
```

### 7.3 Game Status

**Before:**
```
Turn 7
You: 5 stars, 18 ships
Player 2: 6 stars, 21 ships
```

**After:**
```
Turn 7
You: 5 stars, 18 ships
Admiral Opus Thalion: 6 stars, 21 ships
```

### 7.4 Expansion Log

**Before:**
```
Turn 2: Player 2 captured Fomalhaut (2 RU)
Turn 3: Player 2 captured Delta (3 RU)
Turn 4: Player 2 lost Fomalhaut to rebellion
```

**After:**
```
Turn 2: Admiral Sonnet Krios captured Fomalhaut (2 RU)
Turn 3: Admiral Sonnet Krios captured Delta (3 RU)
Turn 4: Admiral Sonnet Krios lost Fomalhaut to rebellion
```

---

## 8. Edge Cases & Handling

### 8.1 Model Change Mid-Session
**Scenario:** Model ID changes during a game (config reload, failover)
**Handling:** Display name updates to reflect new model
**Example:** `Admiral Sonnet Krios` → `Admiral Haiku Krios` (surname stays constant via seed)

**Recommendation:** Accept the change. It's rare and reflects reality (player now faces different AI).

### 8.2 Unknown Model ID
**Scenario:** Model ID doesn't match known patterns (future models, custom models)
**Handling:** Use generic fallback `"Admiral Claude [Surname]"`
**Example:** `Admiral Claude Vex`

### 8.3 Missing Model ID
**Scenario:** Model ID not provided or None
**Handling:** Use `"Admiral Claude [Surname]"` fallback
**Example:** `Admiral Claude Thalion`

### 8.4 Saved Games / Replays
**Scenario:** Loading saved game from older version without model ID stored
**Handling:** Require model ID parameter at load time, or default to `"claude-3-5-sonnet"` placeholder
**Note:** Seed-based selection ensures consistent name if model ID known

---

## 9. Future Extensions (Out of Scope)

**Phase 2 possibilities (not for initial implementation):**
- Multiple AI opponents: `Admiral Sonnet Krios`, `Admiral Haiku Vex` (multiplayer)
- Rank progression: Start as "Captain", promote to "Admiral" after X wins
- Dynamic titles: `Admiral Sonnet "The Relentless" Krios` (based on playstyle)
- Voice lines: Text-to-speech greetings from the admiral
- Portrait generation: AI-generated admiral face based on name seed

---

## 10. Implementation Checklist

- [ ] Implement `extract_model_name(model_id: str) -> str` function
- [ ] Implement `select_admiral_name(seed: int, model_id: str) -> str` function
- [ ] Pass `model_id` from LLM agent config to game initialization
- [ ] Store `game.p2_model_id` (or compute on-demand from config)
- [ ] Create display helper: `get_p2_display_name(game) -> str`
- [ ] Replace "Player 2" / "p2" in all UI text with admiral name
- [ ] Test with different model IDs (Sonnet, Haiku, Opus, unknown)
- [ ] Test with different game seeds (verify variety in surnames)
- [ ] Test same seed + same model = same name (reproducibility)
- [ ] Handle edge cases (missing model ID, unknown model)
- [ ] Update documentation/help text to reference "Admiral" terminology

---

## 11. Specification Alignment

**Alignment with LLM Player 2 Agent Spec:**
- Agent still operates as "p2" internally (observation.player_id = "p2")
- No changes to agent tools, observation schema, or order format
- Agent doesn't need to know its display name (not relevant to decision-making)
- Naming is purely cosmetic UI enhancement

**Alignment with Space Conquest Core Spec:**
- Game state unchanged (Star.owner still uses "p1"/"p2"/null)
- Combat resolution unchanged (compares "p1" vs "p2")
- Victory conditions unchanged (check Home Star owner)
- Naming is display-layer only transformation

---

## 12. Design Decision Log

| Decision | Rationale |
|----------|-----------|
| "Admiral [Model] [Surname]" format | Best balance of clarity, personality, and model transparency |
| Seed-based selection | Aligns with game's deterministic design; enables reproducibility |
| 10-name surname pool | Sufficient variety without overwhelming; easy to extend |
| Model name as middle name | Most natural English word order; emphasizes AI nature |
| UI-layer only | Minimizes game state complexity; easy to implement |
| Generic "Claude" fallback | Graceful degradation for unknown models |

---

## 13. Design Rationale Summary

**Why this design works:**

1. **Meets user requirements:**
   - ✅ Model name included in display name
   - ✅ Random selection from name pool (10 surnames)
   - ✅ Variety across games via seed-based selection
   - ✅ Consistent identity within a session

2. **Maintains simplicity:**
   - UI-layer only (no game state changes)
   - Deterministic from seed + model (no new state to persist)
   - Easy to implement (two simple functions)

3. **Enhances player experience:**
   - Memorable opponent identity ("Admiral Sonnet Krios" beats "Player 2")
   - Transparent about AI nature (model name visible)
   - Variety prevents repetitive feel
   - Thematic fit (military rank for conquest game)

4. **Technical soundness:**
   - Reproducible (seed-based)
   - Extensible (easy to add more surnames or models)
   - Robust (handles edge cases gracefully)
   - Maintainable (minimal code, no state coupling)

---

**END OF SPECIFICATION**
