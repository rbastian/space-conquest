# Space Conquest

A turn-based 4X strategy game where players compete to capture each other's home stars through fleet management and combat.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

## Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

### Basic Usage

Start a human vs human game in text mode:
```bash
python game.py
```

Start a game with the terminal user interface (TUI):
```bash
python game.py --tui
```

### Game Modes

- `hvh` - Human vs Human (default)
- `hvl` - Human vs LLM (AI opponent)
- `lvl` - LLM vs LLM (AI vs AI)

Example with human vs AI:
```bash
python game.py --tui --mode hvl
```

### LLM Models

When playing against AI (`hvl` or `lvl` modes), you can choose the model:

- `haiku` - Fast and cheap (default)
- `haiku45` - Claude 4.5
- `sonnet` - Balanced performance
- `opus` - Most capable

Example:
```bash
python game.py --mode hvl --model sonnet
```

### Additional Options

- `--seed N` - Use specific random seed for map generation (default: 42)
- `--load FILE` - Load a saved game from JSON file
- `--save FILE` - Save game to JSON file after completion
- `--debug` - Enable debug logging (shows verbose LLM tool calls and iterations)

### Examples

```bash
# Human vs human with TUI
python game.py --tui

# Human vs AI with TUI
python game.py --tui --mode hvl

# Human vs AI with specific seed
python game.py --mode hvl --seed 12345

# AI vs AI with debug output
python game.py --mode lvl --debug

# Load a saved game
python game.py --load savegame.json

# Play and auto-save after
python game.py --save mygame.json
```

## Game Objective

Capture your opponent's home star to win!

## Controls

- In text mode: Follow the prompts to issue orders
- In TUI mode: Use the interactive terminal interface to manage your fleets
- Press `Ctrl+C` at any time to quit

## Running Tests

```bash
python -m pytest -v
```
