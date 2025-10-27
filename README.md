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

### LLM Providers and Models

When playing against AI (`hvl` or `lvl` modes), you can choose from multiple LLM providers:

#### AWS Bedrock (default)
```bash
uv run game.py --mode hvl --provider bedrock --model haiku
uv run game.py --mode hvl --provider bedrock --model sonnet
```

Available models:
- `haiku` - Claude 3.5 Haiku (fast and cheap, default)
- `haiku45` - Claude 4.5 Haiku
- `sonnet` - Claude 3.5 Sonnet (balanced)
- `opus` - Claude 3 Opus (most capable)

**Setup:** Requires AWS credentials configured via `aws configure`

#### OpenAI API
```bash
uv run game.py --mode hvl --provider openai --model gpt-4o
```

Available models:
- `gpt-4o` - GPT-4 Optimized
- `gpt-4o-mini` - GPT-4 Mini (default)
- `gpt-4-turbo` - GPT-4 Turbo
- `gpt-3.5-turbo` - GPT-3.5 Turbo

**Setup:** Set `OPENAI_API_KEY` environment variable:
```bash
export OPENAI_API_KEY="your-api-key"
```

#### Anthropic API
```bash
uv run game.py --mode hvl --provider anthropic --model sonnet
```

Available models:
- `sonnet` - Claude 3.5 Sonnet (default)
- `haiku` - Claude 3.5 Haiku
- `opus` - Claude 3 Opus
- Full model IDs also supported (e.g., `claude-3-5-sonnet-20241022`)

**Setup:** Set `ANTHROPIC_API_KEY` environment variable:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

#### Ollama (Local Models)
```bash
uv run game.py --mode hvl --provider ollama --model llama3
```

Available models (any model installed in Ollama):
- `llama3` - Llama 3 (default)
- `mistral` - Mistral
- `mixtral` - Mixtral
- `gemma` - Gemma
- Any other model you've pulled with `ollama pull`

**Setup:**
1. Install Ollama from https://ollama.com
2. Pull a model: `ollama pull llama3`
3. Optionally specify API base: `--api-base http://localhost:11434` (default)

### Additional Options

- `--seed N` - Use specific random seed for map generation (default: 42)
- `--load FILE` - Load a saved game from JSON file
- `--save FILE` - Save game to JSON file after completion
- `--debug` - Enable verbose AI reasoning and debug logging (shows the AI's thought process)
  - **Note:** This uses more tokens and increases API costs, but helps understand the AI's strategy
  - Without `--debug`: AI makes decisions silently (cheaper, faster)
  - With `--debug`: AI explains its reasoning before each action (more expensive, educational)

### Examples

```bash
# Human vs human with TUI
uv run game.py --tui

# Human vs AI with TUI (default: AWS Bedrock)
uv run game.py --tui --mode hvl

# Human vs AI using OpenAI GPT-4
uv run game.py --mode hvl --provider openai --model gpt-4o

# Human vs AI using local Ollama model
uv run game.py --mode hvl --provider ollama --model llama3

# AI vs AI with debug output (see LLM reasoning - uses more tokens!)
uv run game.py --mode lvl --provider anthropic --debug

# Play without debug to save on API costs (AI still plays, just doesn't explain)
uv run game.py --mode hvl --provider openai --model gpt-4o-mini

# Human vs AI with specific seed
uv run game.py --mode hvl --seed 12345

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
