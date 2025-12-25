# Game Analysis Tool

Comprehensive post-game analysis tool for analyzing strategic gameplay metrics from JSONL logs.

## Overview

The game analysis tool provides detailed insights into LLM gameplay performance across six strategic dimensions:

1. **Spatial Awareness** - Discovery and positioning relative to opponent
2. **Expansion Strategy** - Territory growth patterns and efficiency
3. **Resource Control** - Production capacity and economic performance
4. **Fleet Concentration** - Fleet size distribution and offensive capability
5. **Garrison Management** - Home defense and threat response
6. **Territory Control** - Quadrant dominance and strategic positioning

## Quick Start

### Analyze a Single Game

```bash
uv run scripts/analyze_game.py logs/game_abc123_strategic.jsonl
```

This generates a comprehensive report with:
- Overall performance score (0-100) and grade (A-F)
- Individual dimension scores and assessments
- Key insights (strengths and weaknesses)
- Actionable recommendations for improvement
- Detailed metrics summary

### Analyze All Games

```bash
uv run scripts/analyze_game.py --all logs
```

This provides aggregate statistics across all games:
- Average scores per dimension
- Best and worst game performance
- Common weaknesses across games
- Score distribution and trends

## Programmatic Usage

### Basic Analysis

```python
from src.analysis.game_analyzer import GameAnalyzer

# Load and analyze a game
analyzer = GameAnalyzer("logs/game_abc123_strategic.jsonl")
analysis = analyzer.analyze()

# Access results
print(f"Overall Score: {analysis['overall_score']:.1f}/100")
print(f"Grade: {analysis['grade']}")

# Generate human-readable report
report = analyzer.generate_report()
print(report)
```

### Multi-Game Analysis

```python
from src.analysis.game_analyzer import analyze_multiple_games

# Analyze all games in directory
results = analyze_multiple_games("logs")

print(f"Games analyzed: {results['total_games']}")
print(f"Average score: {results['avg_overall_score']:.1f}/100")

# Access dimension averages
for dim, score in results['avg_dimension_scores'].items():
    print(f"{dim}: {score:.1f}/100")
```

### Custom Metric Extraction

```python
analyzer = GameAnalyzer("logs/game_abc123_strategic.jsonl")

# Access raw metrics for custom analysis
for metric in analyzer.metrics:
    turn = metric['turn']
    production = metric['resources']['total_production_ru']
    ratio = metric['resources']['production_ratio']
    print(f"Turn {turn}: {production} RU/turn (ratio: {ratio:.2f})")
```

## Scoring System

### Overall Score Calculation

The overall score is a weighted average of dimension scores:

- **Resource Control**: 25% (most important - economy wins)
- **Expansion Strategy**: 20% (critical for winning)
- **Fleet Concentration**: 20% (critical for offense)
- **Spatial Awareness**: 15% (important early game)
- **Territory Control**: 10% (secondary to production)
- **Garrison Management**: 10% (important but not primary)

### Dimension Scoring Details

#### Spatial Awareness (0-100)
- Early discovery (≤5 turns): 100 points
- Good discovery (6-10 turns): 85 points
- Adequate discovery (11-20 turns): 70 points
- Late discovery (21-30 turns): 55 points
- Very late discovery (31+ turns): 40 points
- Never discovered: 20 points

#### Expansion Strategy (0-100)
- **Rate component (0-60 points)**:
  - Excellent (≥0.5 stars/turn): 60 points
  - Good (≥0.3 stars/turn): 45 points
  - Adequate (≥0.2 stars/turn): 30 points
  - Poor (<0.2 stars/turn): 15 points
- **Pattern component (0-40 points)**:
  - Optimal distance (3-7 from home): 40 points
  - Acceptable distance (2-8 from home): 25 points
  - Too conservative (<2 from home): 10 points

#### Resource Control (0-100)
Based on final production ratio vs opponent:
- Dominant (≥2.0x): 100 points
- Strong (≥1.5x): 85 points
- Good (≥1.2x): 70 points
- Competitive (≥1.0x): 55 points
- Disadvantage (≥0.8x): 40 points
- Poor (<0.8x): 20 points
- Bonus: +10 points if ratio is improving over time

#### Fleet Concentration (0-100)
- **Average fleet size (0-60 points)**:
  - Large fleets (≥50 ships): 60 points
  - Medium fleets (≥30 ships): 45 points
  - Small fleets (≥20 ships): 30 points
  - Tiny fleets (<20 ships): 15 points
- **Large fleet presence (0-40 points)**:
  - Many (≥2 large fleets): 40 points
  - Some (≥1 large fleet): 30 points
  - Few (≥0.5 large fleets): 20 points
  - None: 10 points

#### Garrison Management (0-100)
Score = Appropriateness rate × 100

Garrison is considered appropriate if it meets threat-based thresholds:
- No threat: ≥5% of total ships
- Low threat: ≥10% of total ships
- Medium threat: ≥20% of total ships
- High threat: ≥30% of total ships

#### Territory Control (0-100)
Based on territorial advantage (-1 to +1 scale):
- Base score: (advantage + 1) × 50 (maps -1→0, 0→50, 1→100)
- Bonus: +10 points for 3+ center zone stars
- Bonus: +10 points for 3+ stars in opponent quadrant
- Maximum score capped at 100

### Grading Scale

- **A** (90-100): Excellent performance
- **B** (80-89): Good performance
- **C** (70-79): Adequate performance
- **D** (60-69): Poor performance
- **F** (0-59): Failing performance

## Report Structure

### Overall Performance
- Numerical score (0-100)
- Letter grade (A-F)
- Game metadata (ID, duration)

### Dimension Scores
Each dimension includes:
- Numerical score (0-100)
- Qualitative assessment
- Detailed metrics

### Key Insights
- **Strengths**: Top 2 dimensions with scores ≥70
- **Weaknesses**: Bottom 2 dimensions with scores <70

### Recommendations
Up to 5 actionable recommendations prioritized by:
1. Critical issues (production disadvantage, never discovering opponent)
2. Major weaknesses (scores <50)
3. Moderate issues (scores 50-70)
4. Advanced optimization tips (scores ≥80)

### Detailed Metrics Summary
Raw metrics for each dimension showing:
- Key performance indicators
- Trends over time
- Comparison to opponent

## Integration with LLM Development

### Iterative Improvement Workflow

1. **Run a game** with strategic logging enabled
2. **Analyze the game** immediately after completion
3. **Identify weaknesses** from the dimension scores
4. **Review recommendations** for specific improvements
5. **Update prompts/strategy** based on insights
6. **Run another game** to test improvements
7. **Compare results** using multi-game analysis

### Example: Improving Spatial Awareness

If analysis shows poor spatial awareness (score <60):

1. **Check metrics**: Did opponent get discovered? When?
2. **Read recommendation**: "Implement early scouting strategy..."
3. **Update prompt**: Add explicit instruction to scout all quadrants by turn 5
4. **Test change**: Run new game with updated prompt
5. **Verify improvement**: Check if discovery turn decreased

### Tracking Progress Over Time

Use multi-game analysis to track improvement:

```bash
# Run multiple test games
uv run scripts/analyze_game.py --all logs

# Check if average scores are improving
# Focus on dimensions with lowest scores
# Iterate on weakest areas
```

## Examples

See `/examples/game_analysis_example.py` for comprehensive usage examples:

```bash
uv run python examples/game_analysis_example.py
```

This demonstrates:
- Single game analysis
- Full report generation
- Custom metric extraction
- Multi-game trend analysis

## Technical Details

### Input Format

The analyzer expects JSONL files where each line is a JSON object with strategic metrics from one turn. These files are automatically generated by `StrategicLogger` during gameplay.

Expected structure:
```json
{
  "turn": 5,
  "spatial_awareness": {
    "llm_home_coords": [1, 2],
    "opponent_home_coords": [10, 8],
    "llm_home_quadrant": "upper-left",
    "opponent_home_quadrant": "lower-right",
    "opponent_home_discovered": true
  },
  "expansion": {...},
  "resources": {...},
  "fleets": {...},
  "garrison": {...},
  "territory": {...}
}
```

### Performance Considerations

- **Memory efficient**: Streams JSONL files line-by-line
- **Fast analysis**: Typically <100ms per game
- **Caching**: Analysis results are cached per instance
- **Batch processing**: Multi-game analysis processes files in parallel concepts

### Error Handling

The analyzer gracefully handles:
- Missing or malformed log files
- Incomplete metrics (missing turns)
- Edge cases (infinite ratios, zero fleets)
- Empty or very short games

Errors are reported clearly with actionable messages.

## Future Enhancements

Potential additions:
- Visualization exports (JSON for charts)
- Comparison mode (Game A vs Game B)
- Time-series trend analysis
- Custom scoring weight profiles
- Export to CSV for spreadsheet analysis
- Integration with prompt engineering tools
