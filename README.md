# Space Conquest

A turn-based 4X strategy game where players compete to capture each other's home stars through fleet management and combat.

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

1. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install dependencies and create virtual environment:
   ```bash
   uv sync
   ```

## Running the Game

### Basic Usage

Start a human vs human game in text mode:
```bash
uv run game.py
```

Start a game with the terminal user interface (TUI):
```bash
uv run game.py --tui
```

### Game Modes

- `hvh` - Human vs Human (default)
- `hvl` - Human vs LLM (AI opponent)
- `lvl` - LLM vs LLM (AI vs AI)

Example with human vs AI:
```bash
uv run game.py --tui --mode hvl
```

### LLM Models

When playing against AI (`hvl` or `lvl` modes), you can choose the model:

- `haiku` - Fast and cheap (default)
- `haiku45` - Claude 4.5
- `sonnet` - Balanced performance
- `opus` - Most capable

Example:
```bash
uv run game.py --mode hvl --model sonnet
```

### Additional Options

- `--seed N` - Use specific random seed for map generation (default: 42)
- `--load FILE` - Load a saved game from JSON file
- `--save FILE` - Save game to JSON file after completion
- `--debug` - Enable debug logging (shows verbose LLM tool calls and iterations)

### Examples

```bash
# Human vs human with TUI
uv run game.py --tui

# Human vs AI with TUI
uv run game.py --tui --mode hvl

# Human vs AI with specific seed
uv run game.py --mode hvl --seed 12345

# AI vs AI with debug output
uv run game.py --mode lvl --debug

# Load a saved game
uv run game.py --load savegame.json

# Play and auto-save after
uv run game.py --save mygame.json
```

## Game Objective

Capture your opponent's home star to win!

## Controls

- In text mode: Follow the prompts to issue orders
- In TUI mode: Use the interactive terminal interface to manage your fleets
- Press `Ctrl+C` at any time to quit

## Running Tests

```bash
uv run pytest
```
