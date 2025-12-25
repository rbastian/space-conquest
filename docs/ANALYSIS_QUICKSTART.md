# Game Analysis - Quick Start Guide

## 5-Minute Quick Start

### 1. Analyze a Single Game

```bash
# Analyze the most recent game
uv run scripts/analyze_game.py logs/game_LATEST_strategic.jsonl
```

You'll get:
- Overall score (0-100) and grade (A-F)
- Scores for 6 strategic dimensions
- Top 5 actionable recommendations
- Detailed metrics breakdown

### 2. Analyze All Games

```bash
# See aggregate statistics across all games
uv run scripts/analyze_game.py --all
```

You'll get:
- Average scores across all dimensions
- Best and worst game comparison
- Common weaknesses to address
- Score ranges and trends

### 3. Run the Interactive Example

```bash
# See all features in action
uv run python examples/game_analysis_example.py
```

## Common Use Cases

### "I just ran a game - how did my LLM do?"

```bash
uv run scripts/analyze_game.py logs/game_abc123_strategic.jsonl
```

Look at:
1. **Overall Score** - Quick health check (aim for 70+)
2. **Weaknesses** - What needs improvement most
3. **Recommendations** - Specific actions to take

### "Which strategic dimension needs the most work?"

```bash
uv run scripts/analyze_game.py --all
```

Check the **Average Dimension Scores** section. Dimensions below 60 need attention.

### "How do I improve [specific dimension]?"

1. Run single game analysis
2. Look at that dimension's detailed metrics
3. Read the specific recommendations
4. Update your LLM prompt accordingly
5. Run another game to verify improvement

### "I want to compare two strategies"

```bash
# Run games with strategy A
# Run games with strategy B
uv run scripts/analyze_game.py --all
```

Compare average scores to see which strategy performs better.

## Understanding Your Score

### Overall Score
- **90-100 (A)**: Excellent - LLM is playing at high level
- **80-89 (B)**: Good - Competitive gameplay with minor issues
- **70-79 (C)**: Adequate - Playable but needs improvement
- **60-69 (D)**: Poor - Major strategic flaws
- **0-59 (F)**: Failing - Fundamental issues need addressing

### Critical Dimensions (High Weight)

1. **Resource Control (25%)** - Most important
   - Target: Production ratio > 1.2x opponent
   - Fix: Conquer high-RU stars, maintain expansion

2. **Expansion Strategy (20%)** - Very important
   - Target: 0.5-0.8 stars per turn
   - Fix: Add aggressive expansion to prompts

3. **Fleet Concentration (20%)** - Very important
   - Target: 30+ ships average, 1-2 large fleets
   - Fix: Stop sending tiny fleets, concentrate forces

### Secondary Dimensions (Medium Weight)

4. **Spatial Awareness (15%)** - Important early game
   - Target: Discover opponent by turn 10
   - Fix: Add scouting instructions to prompt

5. **Territory Control (10%)** - Strategic advantage
   - Target: Positive territorial advantage
   - Fix: Push toward center and opponent quadrant

6. **Garrison Management (10%)** - Defense basics
   - Target: 80%+ appropriateness rate
   - Fix: Scale garrison with threat level

## Quick Fixes for Common Issues

### Low Spatial Awareness (<60)
**Problem**: Not discovering opponent or discovering too late

**Quick Fix**: Add to prompt:
```
"On the first turn, send small scout fleets (5-10 ships) to explore
all unexplored quadrants. Discovering the opponent's home star early
is critical for strategic planning."
```

### Low Expansion (<60)
**Problem**: Not conquering enough stars

**Quick Fix**: Add to prompt:
```
"Maintain aggressive expansion. Target conquering 1 new star every
2-3 turns. Prioritize nearby stars with high RU production (3+ RU)."
```

### Low Resources (<60)
**Problem**: Losing economic race to opponent

**Quick Fix**: Add to prompt:
```
"Economic dominance is critical. Always prioritize conquering stars
with high RU production. Maintain at least 1.2x production ratio
versus opponent."
```

### Low Fleet Concentration (<60)
**Problem**: Sending too many small, weak fleets

**Quick Fix**: Add to prompt:
```
"Concentrate forces into large fleets (40-60 ships). Never send
fleets smaller than 30 ships for offensive operations. Merge small
forces at staging points before attacking."
```

### Low Garrison (<60)
**Problem**: Wrong garrison sizes for threat level

**Quick Fix**: Add to prompt:
```
"Scale home garrison with threat:
- No/low threat: 5-10% of total ships
- Medium threat: 15-20% of total ships
- High threat (enemy fleet nearby): 25-30% of total ships"
```

### Low Territory (<60)
**Problem**: Not controlling strategic positions

**Quick Fix**: Add to prompt:
```
"Push aggressively toward center zone and opponent's quadrant.
Controlling enemy territory provides both strategic and economic
advantages."
```

## Integration with Development Workflow

### Recommended Process

1. **Baseline**: Run 3-5 games with current prompt
2. **Analyze**: Use `--all` to see average performance
3. **Identify**: Focus on lowest-scoring dimension
4. **Improve**: Update prompt based on recommendations
5. **Test**: Run 3-5 games with updated prompt
6. **Compare**: Did the target dimension improve?
7. **Iterate**: Move to next lowest dimension

### Tracking Progress

Keep a simple log:

```
Week 1 Baseline:
- Overall: 45/100 (F)
- Lowest: Spatial (20), Expansion (25), Fleets (30)
- Action: Added early scouting to prompt

Week 2 After Fix:
- Overall: 58/100 (F) [+13]
- Lowest: Expansion (25), Fleets (35), Resources (40)
- Spatial improved to 65! [+45]
- Action: Adding aggressive expansion instructions

Week 3 After Fix:
- Overall: 72/100 (C) [+14]
- All dimensions > 60 now
- Action: Fine-tuning fleet concentration
```

## Next Steps

1. **Read the full documentation**: `docs/game_analysis.md`
2. **Explore examples**: `examples/game_analysis_example.py`
3. **Run your first analysis**: `uv run scripts/analyze_game.py --all`
4. **Start iterating**: Use recommendations to improve prompts

## Need Help?

Check these files:
- **Full documentation**: `docs/game_analysis.md`
- **Scoring details**: See "Scoring System" section in full docs
- **Code examples**: `examples/game_analysis_example.py`
- **Tests**: `tests/test_game_analyzer.py` (shows all features)
