# Space Conquest - Quick Start Guide

## Installation

1. Clone the repository
2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install pytest pytest-cov

# For LLM opponent (optional)
pip install boto3
```

## Running the Game

### Start a New Game (Human vs Human)
```bash
python game.py
```

### Play Against AI (Human vs LLM)
```bash
python game.py --mode hvl
```
**Note:** Requires AWS credentials and Bedrock access. See [docs/QUICKSTART_LLM.md](docs/QUICKSTART_LLM.md) for setup.

### Watch AI vs AI
```bash
python game.py --mode lvl
```

### View All Options
```bash
python game.py --help
```

### Run Demo
```bash
python demo.py
```

## How to Play

1. The game starts with Player 1's turn
2. You'll see:
   - Your controlled stars and ship counts
   - Fleets in transit
   - Production capacity
   - ASCII map of the galaxy

3. Enter commands to move ships:
   - `move 5 ships from A to B`
   - `send 3 from C to D`
   - `attack E with 10 from A`
   - `pass` or `done` - end turn
   - `help` - show command help
   - `status` - show current state

4. Win by capturing your opponent's home star!

## Map Legend

- `?X` - Star X with unknown resource units (RU)
- `2A` - Star A with 2 RU (NPC or unowned)
- `*A` - Star A controlled by you
- `!A` - Star A controlled by opponent
- `..` - Empty space

## Game Rules

- **Production:** Each controlled star produces ships equal to its RU value per turn
- **Movement:** Ships travel through hyperspace; distance = Manhattan distance
- **Combat:** Higher ship count wins; winner loses ceil(loser/2) ships
- **Hyperspace Loss:** 2% chance per fleet per turn (d50 roll of 1)
- **Rebellions:** Under-garrisoned conquered stars (ships < RU) have 50% rebellion chance

## Running Tests

Run all tests:
```bash
source venv/bin/activate
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_command_parser.py -v
```

## Project Structure

```
/space-conquest
  ├── game.py                  # Main entry point
  ├── demo.py                  # Demo script
  ├── src/
  │   ├── models/             # Data models (Star, Fleet, Player, Game)
  │   ├── engine/             # Game logic (turn execution, combat, etc.)
  │   ├── interface/          # Human CLI (renderer, parser, display)
  │   └── utils/              # Utilities (RNG, distance, serialization)
  └── tests/                  # Test files
```

## Example Game Session

```
Turn 0 - Player p1
============================================================

Controlled Stars:
  A: Theta (4 RU) - 4 ships [HOME]
  Total: 1 stars, 4 ships

Map:
   0  1  2  3  4  5  6  7  8  9 10 11
0 .. .. .. ?H .. .. .. .. .. .. .. ..
1 .. .. .. .. .. .. *A .. .. .. .. ..
2 .. .. .. ?P .. .. .. .. .. ?G .. ..
...

[p1] > move 2 ships from A to C
Order added: 2 ships from A to C
Add another order? (y/n): n
Ending turn with 1 order(s).
```

## Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'pytest'`
**Solution:** Activate venv and install dependencies:
```bash
source venv/bin/activate
pip install pytest pytest-cov
```

**Issue:** `FileNotFoundError` when loading game
**Solution:** Check that the save file exists in the `state/` directory or provide absolute path

**Issue:** Command not recognized
**Solution:** Type `help` to see valid command formats

## Next Steps

- Play a few games to get familiar with the mechanics
- Experiment with different seeds: `python game.py --seed 123`
- Save interesting games: `python game.py --save mygame.json`
- Load and continue: `python game.py --load mygame.json`

## Need Help?

- Type `help` during gameplay for command syntax
- Check `specs/space_conquest_spec.md` for full game rules
- Check `specs/technical_architecture.md` for implementation details
- See `IMPLEMENTATION_SUMMARY.md` for recent changes
- See `docs/QUICKSTART_LLM.md` for LLM opponent setup
- See `docs/LLM_AGENT_SETUP.md` for detailed AWS configuration
