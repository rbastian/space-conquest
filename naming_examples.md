# LLM Opponent Naming System - Implementation Examples

## Admiral Names Generated

The system transforms generic "Player p2" displays into memorable admiral identities.

### Example 1: Different Seeds, Same Model
Using Claude 3.5 Sonnet (`us.anthropic.claude-3-5-sonnet-20241022-v1:0`):

- Seed 42: **Admiral Sonnet Vex**
- Seed 123: **Admiral Sonnet Krios**
- Seed 777: **Admiral Sonnet Dravin**
- Seed 1: **Admiral Sonnet Thalion**
- Seed 5: **Admiral Sonnet Vorel**

### Example 2: Same Seed, Different Models
Using seed 42:

- Sonnet: **Admiral Sonnet Vex**
- Haiku: **Admiral Haiku Vex**
- Opus: **Admiral Opus Vex**

### Example 3: Display Transformations

#### Before (without naming system):
```
Turn 3: Player p2 fleet (5 ships) attacked your fleet at Altair (3 ships).
Player p2 won. Your fleet was destroyed. Player p2 lost 2 ships.
```

#### After (with naming system):
```
Turn 3: Admiral Sonnet Krios fleet (5 ships) attacked your fleet at Altair (3 ships).
Admiral Sonnet Krios won. Your fleet was destroyed. Admiral Sonnet Krios lost 2 ships.
```

#### Victory Screen Before:
```
GAME OVER
Player p2 has conquered your Home Star!
```

#### Victory Screen After:
```
CONQUEST COMPLETE
Admiral Haiku Vex achieves DECISIVE VICTORY over Commander!
The assault on Alpha (A) succeeded—the enemy empire has fallen.
```

#### Statistics Table:
```
Metric                    Commander   Admiral Sonnet Krios
---------------------------------------------------------
Stars Controlled                  5                     7
Economic Output (RU/turn)        18                    23
Stationed Ships                  42                    58
Ships in Transit                  5                    12
Total Fleet Strength             47                    70
```

## Technical Implementation

### Key Files Modified:
1. `/src/utils/naming.py` - New utility module with naming functions
2. `/src/models/game.py` - Added `p2_model_id` field for display name generation
3. `/game.py` - GameOrchestrator extracts model ID from LLMPlayer
4. `/src/interface/display.py` - All display methods use admiral names
5. `/src/agent/langchain_client.py` - MockLangChainClient has model_id and provider for testing

### Display Locations Updated:
- Turn announcements
- Combat reports (PvP and NPC)
- Victory/defeat messages
- Statistics tables
- Fleet arrival notifications
- Rebellion reports
- Hyperspace losses
- Final map state
- Production summaries

## Reproducibility

The naming system is **deterministic and reproducible**:
- Same seed + same model = same admiral name every time
- Enables debugging and replay functionality
- No state storage needed - name computed on-demand from seed + model ID

## Model Name Extraction

Supports all Claude model families:
- **Sonnet**: `"sonnet"` in model ID → "Admiral Sonnet [Surname]"
- **Haiku**: `"haiku"` in model ID → "Admiral Haiku [Surname]"
- **Opus**: `"opus"` in model ID → "Admiral Opus [Surname]"
- **Fallback**: Unknown models → "Admiral Claude [Surname]"

## Surname Pool (10 names)

1. Krios - Greek-inspired, commanding
2. Vex - Sharp, tactical, ominous
3. Thalion - Elvish-inspired, noble
4. Dravin - Strong, authoritative
5. Seris - Elegant, strategic
6. Korvan - Military, disciplined
7. Nexus - Sci-fi, interconnected intelligence
8. Rylon - Clean, futuristic
9. Thane - Noble title, historical gravitas
10. Vorel - Mysterious, alien

All surnames are:
- 2 syllables (easy to remember)
- Gender-neutral (AI transcends human gender)
- Sci-fi/fantasy themed (fits space conquest)
- Phonetically distinct (no confusion)
