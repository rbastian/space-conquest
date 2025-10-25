# Quick Start: Playing Against Claude

Get up and running with the LLM opponent in 5 minutes.

## 1. Install Dependencies

```bash
pip install boto3
```

## 2. Configure AWS (First Time Only)

```bash
# Install AWS CLI
pip install awscli

# Configure your credentials
aws configure
```

You'll need:
- AWS Access Key ID (from AWS IAM)
- AWS Secret Access Key (from AWS IAM)
- Region: `us-east-1`

**Don't have AWS credentials?** See the full [LLM Agent Setup Guide](LLM_AGENT_SETUP.md).

## 3. Enable Bedrock Access (First Time Only)

1. Log into [AWS Console](https://console.aws.amazon.com)
2. Go to **Amazon Bedrock**
3. Click **Model access** in the left sidebar
4. Request access to **Claude 3 Sonnet**
5. Wait for approval (usually instant)

## 4. Play!

```bash
# Start a game against Claude
python game.py --mode hvl

# Use a specific seed
python game.py --mode hvl --seed 42

# Watch two AI players battle
python game.py --mode lvl
```

## Game Modes

- **hvh**: Human vs Human (default)
- **hvl**: Human vs LLM (you play as Player 1)
- **lvl**: LLM vs LLM (watch AI battle)

## Cost

Each game costs approximately **$0.03-0.10** in API fees.

## Testing Without AWS

The game automatically falls back to a mock LLM for testing if AWS credentials are not configured. The mock always passes its turn.

## Need Help?

- **Full Setup Guide**: [docs/LLM_AGENT_SETUP.md](LLM_AGENT_SETUP.md)
- **Architecture Details**: [specs/llm_player_2_agent_spec.md](../specs/llm_player_2_agent_spec.md)
- **Run Tests**: `python -m pytest tests/test_agent.py -v`

## What the LLM Can Do

The Claude agent:
- Analyzes the game state with fog-of-war
- Plans strategic expansions and defenses
- Makes tactical decisions about fleet movements
- Validates moves before submitting
- Remembers discoveries and strategies across turns

It plays competitively and follows game rules strictly!

## Example Game Session

```bash
$ python game.py --mode hvl --seed 42

Generating new map with seed 42...
Map generated successfully!
Initializing Human vs LLM game...
[LLMPlayer] Initialized Bedrock client: anthropic.claude-3-sonnet-20240229-v1:0
LLM player initialized successfully!

============================================================
Space Conquest
============================================================

Goal: Capture your opponent's home star to win!
Press Ctrl+C at any time to quit.

Press Enter to start the game...

============================================================
Turn 1
============================================================

[Player 1's turn - your map and orders]
...

[LLMPlayer] Getting orders for p2 (Turn 1)
[LLMPlayer] Iteration 1/15
[LLMPlayer] Executing tool: get_observation
[LLMPlayer] Executing tool: get_ascii_map
[LLMPlayer] Executing tool: propose_orders
[LLMPlayer] Executing tool: submit_orders
[LLMPlayer] Orders submitted successfully
[LLMPlayer] Returning 2 order(s)
  - 3 ships: P -> F
  - 2 ships: P -> L

[Turn executes...]
```

Enjoy playing against Claude!
