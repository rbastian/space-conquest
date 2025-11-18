# Getting Started with Space Conquest Server

## Installation

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Configure AWS credentials** (for Bedrock LLM):
   ```bash
   # Option 1: AWS CLI
   aws configure

   # Option 2: Environment variables
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

## Running the Server

### Development Mode

```bash
uv run python run_server.py
```

This starts the server with:
- Auto-reload on code changes
- Server at http://localhost:8000
- API docs at http://localhost:8000/docs
- Frontend at http://localhost:8000/

### Production Mode

```bash
uv run uvicorn src.server.main:app --host 0.0.0.0 --port 8000
```

## Playing the Game

1. **Open your browser**: Navigate to http://localhost:8000/

2. **Game creation**: The frontend automatically creates a new game on load
   - You play as Player 1
   - AI plays as Player 2 (using Bedrock)

3. **Issue orders**: Use the terminal commands:
   ```
   MOVE 10 FROM A TO B    # Send 10 ships from star A to star B
   LIST                    # Show queued orders
   STATUS                  # Show game status
   DONE                    # Submit turn (or click "SUBMIT TURN" button)
   ```

4. **Turn execution**:
   - When you submit orders, the server immediately calls the AI player
   - The AI generates its orders (takes 5-30 seconds)
   - Both orders are executed together
   - Results are broadcast via WebSocket

5. **Victory**: Capture the opponent's home star to win!

## API Endpoints

### Create Game
```http
POST /api/games
{
  "humanPlayer": "p1",
  "aiProvider": "bedrock"
}
```

### Get Game State
```http
GET /api/games/{gameId}/state
```

### Submit Orders
```http
POST /api/games/{gameId}/orders
{
  "orders": [
    {"type": "MOVE", "ships": 10, "from": "A", "to": "B"}
  ]
}
```

### WebSocket
```
ws://localhost:8000/ws/games/{gameId}
```

## Troubleshooting

### AI Player Not Responding

**Issue**: Orders submitted but AI doesn't respond

**Solutions**:
1. Check AWS credentials are configured
2. Check server logs for LLM errors
3. Verify Bedrock access in your AWS region
4. Try using mock AI: Edit `src/server/session.py` line ~156:
   ```python
   ai_player = LangGraphPlayer(
       player_id=ai_player_id,
       use_mock=True,  # <- Change to True for testing
   )
   ```

### WebSocket Connection Failed

**Issue**: Frontend can't connect to WebSocket

**Solutions**:
1. Ensure server is running
2. Check browser console for errors
3. Try refreshing the page
4. Clear browser cache

### Port Already in Use

**Issue**: `Address already in use` error

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uv run uvicorn src.server.main:app --port 8001
```

### Game State Not Loading

**Issue**: Blank map or no stars visible

**Solutions**:
1. Check browser console for API errors
2. Verify server is running and accessible
3. Try creating a new game
4. Check server logs for game creation errors

## Development Tips

### Testing Without AI

To test the backend without waiting for LLM responses, use mock AI:

```python
# In src/server/session.py, line ~156:
ai_player = LangGraphPlayer(
    player_id=ai_player_id,
    use_mock=True,  # Mock AI responds instantly
    provider=ai_provider,
    model=ai_model,
)
```

### Viewing API Docs

FastAPI provides interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Debugging

Enable verbose AI logging:

```python
# In src/server/session.py:
ai_player = LangGraphPlayer(
    player_id=ai_player_id,
    verbose=True,  # AI will explain its reasoning
)
```

### Multiple Games

Each game is independent. You can play multiple games simultaneously:
- Game 1: http://localhost:8000/?gameId=game-abc123
- Game 2: http://localhost:8000/?gameId=game-def456

## Next Steps

- Read [docs/server-architecture.md](server-architecture.md) for architecture details
- Explore [frontend/README.md](../frontend/README.md) for UI customization
- Check [src/agent/prompts.py](../src/agent/prompts.py) to understand AI strategy

## Getting Help

- **API Issues**: Check server logs in terminal
- **Frontend Issues**: Check browser console (F12)
- **AI Behavior**: Enable verbose mode and review decision logs
- **Game Rules**: See [docs/server-architecture.md](server-architecture.md)
