# LLM Agent Setup Guide

This guide explains how to set up and use the LLM-powered AI opponent in Space Conquest. The agent supports multiple LLM providers (AWS Bedrock, OpenAI, Anthropic API, Ollama) via LangChain to play strategically against human players.

## Overview

The LLM agent implementation consists of:

- **Agent Tools** (`src/agent/tools.py`) - 7 tools for observing game state and submitting orders
- **LangChain Client** (`src/agent/langchain_client.py`) - Unified multi-provider LLM client with prompt caching support
- **LLM Player** (`src/agent/llm_player.py`) - Player controller that orchestrates tool use
- **System Prompt** (`src/agent/prompts.py`) - Strategic decision-making framework

**Supported Providers:**
- AWS Bedrock (Claude models) - Supports prompt caching
- Anthropic API (Claude models) - Supports prompt caching
- OpenAI (GPT-4, GPT-4o, etc.)
- Ollama (Local models)

## Prerequisites

### 1. Install Dependencies

The project uses `uv` for dependency management:

```bash
uv sync
```

This installs LangChain and all required provider packages.

### 2. AWS Account Setup

You need an AWS account with access to Amazon Bedrock. Follow these steps:

#### A. Create AWS Account
1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the registration process

#### B. Enable Bedrock Model Access
1. Log into AWS Console
2. Navigate to Amazon Bedrock
3. Go to "Model access" in the left sidebar
4. Request access to **Claude 3 Sonnet** (anthropic.claude-3-sonnet-20240229-v1:0)
5. Wait for approval (usually instant for base models)

#### C. Create IAM User with Bedrock Access
1. Navigate to IAM in AWS Console
2. Create a new user with programmatic access
3. Attach the policy `AmazonBedrockFullAccess` (or create custom policy with `bedrock:InvokeModel` permission)
4. Save the Access Key ID and Secret Access Key

### 3. Configure AWS Credentials

Install and configure the AWS CLI:

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

When prompted, enter:
- **AWS Access Key ID**: Your access key from IAM
- **AWS Secret Access Key**: Your secret key from IAM
- **Default region name**: `us-east-1` (or your preferred region)
- **Default output format**: `json`

Alternatively, you can set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
```

Or create `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your_access_key_here
aws_secret_access_key = your_secret_key_here
```

And `~/.aws/config`:

```ini
[default]
region = us-east-1
```

## Usage

### Playing Against the LLM Agent

#### Human vs LLM (hvl mode)

```bash
python game.py --mode hvl
```

This starts a game where:
- **Player 1 (you)**: Human player using CLI interface
- **Player 2 (AI)**: LLM agent powered by Claude

#### LLM vs LLM (lvl mode)

```bash
python game.py --mode lvl
```

Watch two LLM agents battle each other! This is useful for:
- Testing agent behavior
- Generating training data
- Evaluating strategies

### Command-Line Options

```bash
# Specify random seed
python game.py --mode hvl --seed 42

# Load saved game
python game.py --mode hvl --load savegame.json

# Save game after completion
python game.py --mode hvl --save results.json
```

## How the LLM Agent Works

### Decision Process

Each turn, the agent follows this process:

1. **Observe**: Calls `get_observation()` to see current game state (fog-of-war filtered)
2. **Analyze**: Uses `get_ascii_map()` and `query_star()` to understand the situation
3. **Plan**: Decides on expansion targets, defense needs, and offensive moves
4. **Validate**: Uses `propose_orders()` to check order validity
5. **Submit**: Calls `submit_orders()` to commit moves (only once per turn)
6. **Record**: Stores strategic notes in memory for future turns

### Available Tools

The LLM has access to 7 tools:

1. **get_observation()** - Get full game state with fog-of-war filtering
2. **get_ascii_map()** - View ASCII map visualization
3. **query_star(star_ref)** - Get details about a specific star
4. **estimate_route(from, to)** - Calculate distance and hyperspace risk
5. **propose_orders(draft_orders)** - Validate orders before submitting
6. **submit_orders(orders)** - Commit orders for this turn
7. **memory_query(table, filter)** - Query auto-populated battle/discovery history

### Strategic Behavior

The agent is guided by strategic principles:

- **Early Game**: Expand to high-RU stars while maintaining garrisons
- **Mid Game**: Build fleets and deny opponent expansion
- **Late Game**: Strike at opponent's home star
- **Always**: Maintain home defense and avoid hyperspace losses

The agent respects fog-of-war and only uses information visible to Player 2.

## Testing Without AWS

For development and testing without AWS credentials or API costs:

```python
from src.agent.llm_player import LLMPlayer

# Create player with mock client
llm_player = LLMPlayer("p2", use_mock=True)
```

The mock client simulates Bedrock responses for unit testing. The game will automatically fall back to mock mode if Bedrock initialization fails.

## Running Tests

Test the agent implementation:

```bash
# Run all agent tests
python -m pytest tests/test_agent.py -v

# Run specific test class
python -m pytest tests/test_agent.py::TestAgentTools -v

# Run with coverage
python -m pytest tests/test_agent.py --cov=src/agent
```

All 29 tests should pass.

## Cost Considerations

### AWS Bedrock Pricing

Claude 3 Sonnet pricing (as of 2024):
- Input tokens: ~$3 per million tokens
- Output tokens: ~$15 per million tokens

### Typical Game Costs

A typical 20-turn game:
- ~500-1000 input tokens per turn (game state + system prompt)
- ~200-500 output tokens per turn (thinking + orders)
- Total: ~10,000-30,000 tokens per game
- **Cost: $0.03-0.10 per game**

Tips to reduce costs:
- Use mock mode for development/testing
- Set conservative turn limits
- Use Claude 3 Haiku (cheaper) if available
- **Use Anthropic or Bedrock with prompt caching (see below)**

### Prompt Caching (Anthropic/Bedrock Only)

**Automatic token savings of 85-90% on cached content!**

As of the latest update, the LangChain client automatically enables prompt caching for Anthropic and Bedrock providers. This dramatically reduces token usage within a single turn's reasoning loop.

#### How It Works

1. **First LLM call in a turn**: System prompt + tools written to cache (~1500 tokens)
2. **Subsequent calls (iterations 2-15)**: Cached content read instead of re-sent (~0 tokens, 90% cheaper)
3. **Cache lifetime**: ~5 minutes (sufficient for entire turn)

#### Expected Savings

Without caching (typical turn with 8 LLM calls):
- System prompt: 1500 tokens × 8 = **12,000 tokens**
- Tool definitions: 500 tokens × 8 = **4,000 tokens**
- Game state responses: ~10,000 tokens
- **Total: ~26,000 input tokens per turn**

With caching:
- First call: 2000 tokens (system + tools cached)
- Calls 2-8: 200 tokens each (cache hits) = 1,400 tokens
- Game state responses: ~10,000 tokens
- **Total: ~13,400 input tokens per turn**
- **Savings: ~12,600 tokens per turn (48% reduction)**

Over a 20-turn game:
- **Without caching**: ~520,000 input tokens = **$1.56**
- **With caching**: ~268,000 input tokens = **$0.80**
- **You save: ~$0.76 per game (49% cost reduction)**

#### Monitoring Cache Usage

Cache hits/misses are automatically logged:

```
INFO: Cache HIT: 1847 tokens read from cache (saved ~90% cost)
INFO: Cache MISS: 1847 tokens written to cache
DEBUG: Token usage - Input: 412, Cache read: 1847, Cache write: 0
```

#### Provider Support

- ✅ **Anthropic API** (claude-3-5-sonnet, haiku) - Full support
- ✅ **AWS Bedrock** (Claude models) - Full support
- ❌ **OpenAI** - Not supported (no native caching)
- ❌ **Ollama** - Not supported (local models)

**Recommendation**: Use `--provider anthropic` or `--provider bedrock` for maximum cost savings.

## Troubleshooting

### Error: "boto3 is required"

```bash
pip install boto3
```

### Error: "Failed to initialize Bedrock client"

Check:
1. AWS credentials are configured: `aws sts get-caller-identity`
2. Bedrock is available in your region: Use `us-east-1` or `us-west-2`
3. Model access is enabled in Bedrock console

### Error: "Could not connect to the endpoint URL"

The region might not support Bedrock. Try:

```bash
export AWS_DEFAULT_REGION=us-east-1
```

### Agent makes invalid moves

This shouldn't happen as orders are validated with `propose_orders()` before submission. If you see this:
1. Check the verbose output: `python game.py --mode hvl` (verbose is on by default)
2. Report the issue with the full tool call trace

### Agent is too slow

Each turn requires 2-5 Bedrock API calls. To speed up:
- Reduce temperature (faster sampling)
- Use a faster model if available
- Use mock mode for testing

## Advanced Configuration

### Customizing the Agent

Edit `src/agent/prompts.py` to modify:
- Strategic priorities
- Decision-making process
- Constraints and guidelines

Edit `src/agent/llm_player.py` to adjust:
- Model ID (try different Claude versions)
- Temperature (creativity vs. consistency)
- Max tokens (response length)
- Max iterations (tool use limit)

### Using Different Models

```python
from src.agent.llm_player import LLMPlayer

# Use Claude 3 Opus (more powerful, more expensive)
player = LLMPlayer(
    "p2",
    model_id="anthropic.claude-3-opus-20240229-v1:0",
    region="us-east-1"
)

# Use Claude 3 Haiku (faster, cheaper)
player = LLMPlayer(
    "p2",
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region="us-east-1"
)
```

### Verbose Logging

Enable detailed logging to see tool calls:

```python
player = LLMPlayer("p2", verbose=True)
```

This prints:
- Each tool call and its inputs
- Tool execution results
- Order validation details

## Architecture Reference

See the full specification at:
- **LLM Spec**: `specs/llm_player_2_agent_spec.md`
- **Architecture**: Main README section 7

## Support

For issues or questions:
1. Check existing tests: `tests/test_agent.py`
2. Review tool implementations: `src/agent/tools.py`
3. Examine verbose output for debugging
4. Verify AWS credentials and Bedrock access

## Future Enhancements

Planned improvements:
- Persistent memory across games
- Rollout simulator for lookahead
- Fine-tuned models on game data
- Multi-agent coordination (if team modes are added)
- Opponent modeling and deception strategies
