# Space Conquest Server Architecture

## Overview

This document describes the architecture for converting Space Conquest from a standalone terminal game into a web-based multiplayer game where **humans play against LLM agents** through a web interface.

## Architecture Model: Hybrid Human vs AI

```
┌─────────────────────────────────────────────────────────────┐
│                      Game Server Process                     │
│                                                               │
│  ┌────────────────────┐         ┌─────────────────────────┐ │
│  │   Web API Layer    │         │   LLM Player (in-proc)  │ │
│  │  (FastAPI/HTTP/WS) │         │  (LangGraphPlayer)      │ │
│  └──────────┬─────────┘         └───────────┬─────────────┘ │
│             │                               │               │
│             └───────────┬───────────────────┘               │
│                         │                                   │
│                ┌────────▼─────────┐                         │
│                │   Game Engine    │                         │
│                │  (TurnExecutor)  │                         │
│                └────────┬─────────┘                         │
│                         │                                   │
│                ┌────────▼─────────┐                         │
│                │   Game State     │                         │
│                │  (Game dataclass)│                         │
│                └──────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
           │                                      ▲
           │  HTTP/WebSocket                     │  LLM API
           │                                      │  (Bedrock/OpenAI)
           ▼                                      │
    ┌──────────────┐                             │
    │ Web Frontend │                             │
    │  (Browser)   │─────────────────────────────┘
    └──────────────┘
```

### Key Design Principles

1. **LLM Player is In-Process**: No API overhead, direct access to game engine
2. **Human Player via Web**: Standard REST + WebSocket API
3. **Single Game Loop**: Both players interact with same `TurnExecutor`
4. **Asynchronous**: Human submits orders async, LLM executes synchronously when needed
5. **Stateful Server**: Game state lives in memory (with optional persistence)

---

## Component Architecture

### 1. Game Engine (Unchanged)

The core game engine remains **exactly as it is** - no refactoring needed:

- `Game` dataclass holds state
- `TurnExecutor` orchestrates turn phases
- `LangGraphPlayer` provides AI decision-making
- All existing game logic preserved

### 2. Web API Layer (New)

FastAPI server that exposes game to human players:

```python
# Simplified structure
from fastapi import FastAPI, WebSocket
from src.models.game import Game
from src.engine.turn_executor import TurnExecutor
from src.agent.langgraph_player import LangGraphPlayer

app = FastAPI()

# In-memory game storage (MVP)
games: dict[str, GameSession] = {}

@dataclass
class GameSession:
    game: Game
    executor: TurnExecutor
    ai_player: LangGraphPlayer
    human_player_id: str  # "p1" or "p2"
    human_orders: list[Order] | None
    connections: list[WebSocket]
```

### 3. Game Session Management

Each game session manages:
- One `Game` instance
- One `TurnExecutor`
- One `LangGraphPlayer` (AI opponent)
- Human player's pending orders
- WebSocket connections for real-time updates

---

## API Design (Simplified for Hybrid Model)

### Core Endpoints

#### 1. Create Game (Human vs AI)
```http
POST /api/games
{
  "humanPlayer": "p1",  // Which side does human play?
  "seed": 42,           // Optional: deterministic seed
  "aiProvider": "bedrock",
  "aiModel": "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
}

Response:
{
  "gameId": "game-abc123",
  "humanPlayer": "p1",
  "aiPlayer": "p2",
  "seed": 42,
  "state": { /* Initial game state */ }
}
```

#### 2. Get Current State
```http
GET /api/games/{gameId}/state

Response:
{
  "gameId": "game-abc123",
  "turn": 5,
  "phase": "AWAITING_HUMAN_ORDERS" | "AI_THINKING" | "EXECUTING_TURN",
  "humanPlayer": "p1",
  "state": {
    "stars": [ /* All stars */ ],
    "fleets": [ /* All fleets */ ],
    "humanControlledStars": [ /* Filtered for human */ ],
    "humanFleets": [ /* Filtered for human */ ],
    "aiFleets": [ /* Only visible ones */ ]
  },
  "events": {
    "lastTurn": {
      "combat": [],
      "rebellions": [],
      "hyperspaceLosses": []
    }
  }
}
```

#### 3. Submit Human Orders
```http
POST /api/games/{gameId}/orders
{
  "orders": [
    {"type": "MOVE", "ships": 10, "from": "A", "to": "B"}
  ]
}

Response:
{
  "accepted": true,
  "errors": [],
  "aiThinking": true  // AI turn started immediately
}
```

**Important**: When human submits orders, server **immediately**:
1. Validates human orders
2. Triggers AI player to get its orders (synchronous call to `LangGraphPlayer.get_orders()`)
3. Executes turn with both players' orders
4. Returns updated state via WebSocket

#### 4. WebSocket Connection
```
ws://localhost:8000/ws/games/{gameId}

Server → Client Messages:
- GAME_STATE: Full state update
- TURN_EXECUTED: Turn completed with events
- AI_THINKING: AI is deciding (show loading indicator)
- GAME_OVER: Game ended
```

---

## Turn Execution Flow (Human vs AI)

### Detailed Flow

```
1. Human views game state
   │
   ├─> GET /api/games/{gameId}/state
   └─> Server returns current state

2. Human issues orders via UI
   │
   ├─> POST /api/games/{gameId}/orders
   │
   └─> Server validates orders
       │
       ├─ If invalid: return errors
       └─ If valid:
          │
          ├─> Broadcast WS: {"type": "AI_THINKING"}
          │
          ├─> Call ai_player.get_orders(game)  // Synchronous!
          │   │
          │   └─> LangGraphPlayer thinks (may take 5-30 seconds)
          │       └─> Returns AI orders
          │
          ├─> Both orders ready, execute turn:
          │   ├─> executor.execute_pre_turn_logic(game)
          │   ├─> game.turn += 1
          │   ├─> executor.execute_post_turn_logic(game, orders)
          │   └─> Collect events
          │
          ├─> Broadcast WS: {"type": "TURN_EXECUTED", events, state}
          │
          └─> Return HTTP response to human
```

### Async Considerations

The AI thinking happens **synchronously** in the request handler:

```python
@app.post("/api/games/{game_id}/orders")
async def submit_orders(game_id: str, orders: OrdersRequest):
    session = games[game_id]

    # Validate human orders
    if not validate_orders(session.game, orders.orders):
        return {"accepted": False, "errors": [...]}

    # Notify clients AI is thinking
    await broadcast(session, {"type": "AI_THINKING"})

    # Get AI orders (this blocks but runs in executor pool)
    ai_orders = await asyncio.to_thread(
        session.ai_player.get_orders,
        session.game
    )

    # Execute turn with both orders
    all_orders = {
        session.human_player_id: orders.orders,
        session.ai_player.player_id: ai_orders
    }

    # Execute turn phases
    game, events = execute_full_turn(session.game, all_orders)

    # Broadcast results
    await broadcast(session, {
        "type": "TURN_EXECUTED",
        "turn": game.turn,
        "events": events,
        "state": serialize_state(game)
    })

    return {"accepted": True, "turn": game.turn}
```

---

## Implementation Plan

### Phase 1: Minimal Backend (MVP)

**Goal**: Human player can play against AI via web interface

**Tasks**:
1. Create FastAPI server with basic structure
2. Implement game session management (in-memory dict)
3. Add endpoints:
   - `POST /api/games` - Create new game
   - `GET /api/games/{id}/state` - Get state
   - `POST /api/games/{id}/orders` - Submit orders
   - `ws://` - WebSocket connection
4. Integrate existing `LangGraphPlayer` for AI
5. Implement turn execution flow
6. Add WebSocket broadcasting

**No changes to existing game engine or agent code!**

### Phase 2: Frontend Integration

**Goal**: Connect web frontend to backend

**Tasks**:
1. Update `game.js` to call real API instead of mock data
2. Implement order submission via POST
3. Connect WebSocket for real-time updates
4. Add "AI is thinking..." loading state
5. Handle game over conditions

### Phase 3: Polish & Features

**Goal**: Production-ready game

**Tasks**:
1. Add persistence (SQLite or PostgreSQL)
2. Implement game history/replay
3. Add matchmaking/lobby system
4. Handle disconnections/reconnections
5. Add spectator mode
6. Implement turn timer/forfeit
7. Add game statistics

---

## File Structure

```
space-conquest/
├── src/
│   ├── models/          # Existing game models (unchanged)
│   ├── engine/          # Existing game engine (unchanged)
│   ├── agent/           # Existing LLM player (unchanged)
│   ├── server/          # NEW: Web server
│   │   ├── __init__.py
│   │   ├── main.py      # FastAPI app
│   │   ├── routes/      # API route handlers
│   │   │   ├── games.py
│   │   │   └── websocket.py
│   │   ├── schemas/     # Pydantic models for API
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   └── session.py   # GameSession management
│   └── ui/              # Existing TUI (unchanged, optional)
├── frontend/            # Web frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── game.js
└── docs/
    ├── api-specification.md      # Detailed API docs
    └── server-architecture.md    # This file
```

---

## Example Server Code (Pseudocode)

### main.py
```python
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from src.models.game import Game
from src.engine.turn_executor import TurnExecutor
from src.agent.langgraph_player import LangGraphPlayer
from .session import GameSession, GameSessionManager
from .schemas import CreateGameRequest, OrdersRequest

# Global session manager
sessions = GameSessionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown logic"""
    # Startup
    print("Server starting...")
    yield
    # Shutdown
    print("Server shutting down...")
    await sessions.cleanup_all()

app = FastAPI(lifespan=lifespan)

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.post("/api/games")
async def create_game(request: CreateGameRequest):
    """Create new Human vs AI game"""
    session = await sessions.create_session(
        human_player=request.humanPlayer,
        seed=request.seed,
        ai_provider=request.aiProvider,
        ai_model=request.aiModel
    )

    return {
        "gameId": session.id,
        "humanPlayer": session.human_player_id,
        "aiPlayer": session.ai_player.player_id,
        "seed": session.game.seed,
        "state": session.get_state_for_human()
    }

@app.get("/api/games/{game_id}/state")
async def get_state(game_id: str):
    """Get current game state"""
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(404, "Game not found")

    return {
        "gameId": game_id,
        "turn": session.game.turn,
        "phase": session.phase,
        "state": session.get_state_for_human(),
        "events": session.get_last_turn_events()
    }

@app.post("/api/games/{game_id}/orders")
async def submit_orders(game_id: str, request: OrdersRequest):
    """Submit human orders and execute turn"""
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(404, "Game not found")

    # Validate orders
    errors = session.validate_orders(request.orders)
    if errors:
        return {"accepted": False, "errors": errors}

    # Notify AI is thinking
    await session.broadcast({"type": "AI_THINKING"})

    # Get AI orders (run in thread pool to not block event loop)
    ai_orders = await asyncio.to_thread(
        session.ai_player.get_orders,
        session.game
    )

    # Execute turn
    events = await session.execute_turn(
        human_orders=request.orders,
        ai_orders=ai_orders
    )

    # Broadcast results
    await session.broadcast({
        "type": "TURN_EXECUTED",
        "turn": session.game.turn,
        "events": events,
        "state": session.get_state_for_human()
    })

    return {
        "accepted": True,
        "turn": session.game.turn,
        "winner": session.game.winner
    }

@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """WebSocket connection for real-time updates"""
    session = sessions.get(game_id)
    if not session:
        await websocket.close(code=404)
        return

    await websocket.accept()
    session.add_connection(websocket)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "CONNECTED",
            "gameId": game_id,
            "state": session.get_state_for_human()
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_json()
            # Handle pings, etc.
            if data.get("type") == "PING":
                await websocket.send_json({"type": "PONG"})

    except WebSocketDisconnect:
        session.remove_connection(websocket)
```

### session.py
```python
from dataclasses import dataclass
from src.models.game import Game
from src.engine.turn_executor import TurnExecutor
from src.agent.langgraph_player import LangGraphPlayer
from src.game_initialization import create_standard_game

@dataclass
class GameSession:
    """Manages one game session (Human vs AI)"""
    id: str
    game: Game
    executor: TurnExecutor
    ai_player: LangGraphPlayer
    human_player_id: str  # "p1" or "p2"
    connections: list[WebSocket]
    phase: str  # "AWAITING_ORDERS" | "AI_THINKING" | "EXECUTING"

    def get_state_for_human(self) -> dict:
        """Serialize game state for human player"""
        return {
            "stars": [star_to_dict(s) for s in self.game.stars],
            "fleets": [fleet_to_dict(f) for f in self.game.fleets],
            # Filter to human's perspective
            "yourStars": [s for s in self.game.stars if s.owner == self.human_player_id],
            "yourFleets": [f for f in self.game.fleets if f.owner == self.human_player_id],
        }

    async def execute_turn(self, human_orders, ai_orders):
        """Execute one turn with both players' orders"""
        self.phase = "EXECUTING"

        orders_dict = {
            self.human_player_id: human_orders,
            self.ai_player.player_id: ai_orders
        }

        # Execute turn phases
        game, combat, losses, rebellions = self.executor.execute_pre_turn_logic(self.game)
        game = self.executor.execute_post_turn_logic(game, orders_dict)

        self.game = game
        self.phase = "AWAITING_ORDERS"

        return {
            "combat": combat,
            "rebellions": rebellions,
            "hyperspaceLosses": losses
        }

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except:
                self.connections.remove(ws)
```

---

## Key Advantages of This Architecture

1. **Minimal Refactoring**: Game engine stays exactly as-is
2. **Performance**: LLM player runs in-process, no network overhead
3. **Simplicity**: Single game loop, no complex synchronization
4. **Scalability**: Each game is independent, easy to scale horizontally
5. **Testing**: Can test game engine independently of web layer
6. **Flexibility**: Easy to add features like replays, spectating, tournaments

---

## Deployment Considerations

### Development
```bash
uv run python -m src.server.main
# Server on http://localhost:8000
# Frontend served from /frontend
```

### Production
- Use Gunicorn/Uvicorn with workers
- Add Redis for session storage (multi-server)
- PostgreSQL for game persistence
- Load balancer for horizontal scaling
- CDN for frontend static assets

### Resource Requirements
- **CPU**: Moderate (LLM inference via API)
- **Memory**: ~100MB per active game
- **Network**: Minimal (only WebSocket + LLM API calls)

---

## Next Steps

1. **Review this architecture** - Does it match your vision?
2. **Create server skeleton** - Basic FastAPI structure
3. **Implement MVP endpoints** - Core game creation + order submission
4. **Test integration** - Human orders → AI response → turn execution
5. **Connect frontend** - Update game.js to use real API
6. **Polish & deploy** - Add persistence, error handling, monitoring

This architecture preserves all your existing game logic while adding a clean web layer for human players. The LLM player continues to work exactly as it does now, just triggered by the server instead of a terminal loop.

Does this match what you had in mind?
