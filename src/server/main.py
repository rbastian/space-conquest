"""FastAPI server for Space Conquest game.

Provides HTTP/WebSocket API for human players to play against AI opponents.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .schemas.requests import CreateGameRequest, SubmitOrdersRequest
from .schemas.responses import (
    CreateGameResponse,
    GameStateResponse,
    SubmitOrdersResponse,
)
from .session import GameSessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global session manager
sessions = GameSessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Space Conquest server starting...")
    yield
    # Shutdown
    logger.info("Space Conquest server shutting down...")
    await sessions.cleanup_all()


# Create FastAPI app
app = FastAPI(
    title="Space Conquest API",
    description="Web API for human vs AI gameplay in Space Conquest",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# API ENDPOINTS
# ============================================


@app.get("/api")
async def api_root():
    """API root endpoint - server health check."""
    return {
        "service": "Space Conquest",
        "status": "operational",
        "activeGames": len(sessions.sessions),
    }


@app.get("/")
async def root():
    """Serve the game frontend."""
    from fastapi.responses import FileResponse

    return FileResponse("frontend/index.html")


@app.post("/api/games", response_model=CreateGameResponse)
async def create_game(request: CreateGameRequest):
    """Create a new Human vs AI game.

    Args:
        request: Game creation parameters

    Returns:
        Game ID and initial state

    Example:
        POST /api/games
        {
          "humanPlayer": "p1",
          "seed": 42,
          "aiProvider": "bedrock",
          "aiModel": "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        }
    """
    try:
        session = await sessions.create_session(
            human_player=request.humanPlayer,
            seed=request.seed,
            ai_provider=request.aiProvider,
            ai_model=request.aiModel,
            reasoning_effort=request.reasoningEffort,
        )

        return CreateGameResponse(
            gameId=session.id,
            humanPlayer=session.human_player_id,
            aiPlayer=session.ai_player.player_id,
            seed=session.game.seed,
            state=session.get_state_for_human(),
        )

    except Exception as e:
        logger.error(f"Failed to create game: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create game: {str(e)}")


@app.get("/api/games/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(game_id: str, debug: bool = False):
    """Get current game state.

    Args:
        game_id: Game session ID
        debug: If True, bypass fog-of-war and show full game state

    Returns:
        Current game state with events

    Example:
        GET /api/games/game-abc123/state
        GET /api/games/game-abc123/state?debug=true  (debug mode)
    """
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    return GameStateResponse(
        gameId=game_id,
        turn=session.game.turn,
        phase=session.phase,
        winner=session.game.winner,
        state=session.get_state_for_human(debug=debug),
        events=session.get_last_turn_events(),
    )


@app.post("/api/games/{game_id}/orders", response_model=SubmitOrdersResponse)
async def submit_orders(game_id: str, request: SubmitOrdersRequest):
    """Submit human orders and execute turn with AI.

    This endpoint:
    1. Validates human orders
    2. Triggers AI to generate its orders (may take 5-30 seconds)
    3. Executes turn with both players' orders
    4. Broadcasts results via WebSocket
    5. Returns updated game state

    Args:
        game_id: Game session ID
        request: Human player's orders

    Returns:
        Order acceptance status and turn results

    Example:
        POST /api/games/game-abc123/orders
        {
          "orders": [
            {"type": "MOVE", "ships": 10, "from": "A", "to": "B"}
          ]
        }
    """
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")

    if session.game.winner:
        raise HTTPException(
            status_code=400,
            detail=f"Game already ended. Winner: {session.game.winner}",
        )

    # Validate human orders
    logger.info(f"Game {game_id}: Validating {len(request.orders)} human orders")
    errors = session.validate_orders(request.orders)
    if errors:
        logger.warning(f"Game {game_id}: Order validation failed: {errors}")
        return SubmitOrdersResponse(accepted=False, errors=errors)

    logger.info(f"Game {game_id}: Orders valid, requesting AI response")

    # Notify WebSocket clients that AI is thinking
    await session.broadcast({"type": "AI_THINKING"})
    session.phase = "AI_THINKING"

    try:
        # Get AI orders (run in thread pool to avoid blocking event loop)
        # This call may take 5-30 seconds depending on LLM provider
        ai_orders = await asyncio.to_thread(session.ai_player.get_orders, session.game)

        logger.info(f"Game {game_id}: AI generated {len(ai_orders)} orders")

        # Execute turn with both players' orders
        events = await session.execute_turn(human_orders=request.orders, ai_orders=ai_orders)

        logger.info(f"Game {game_id}: Turn {session.game.turn} executed successfully")

        # Broadcast results to WebSocket clients
        await session.broadcast(
            {
                "type": "TURN_EXECUTED",
                "turn": session.game.turn,
                "events": events,
                "state": session.get_state_for_human(debug=session.debug_mode),
                "winner": session.game.winner,
            }
        )

        return SubmitOrdersResponse(
            accepted=True, turn=session.game.turn, winner=session.game.winner
        )

    except Exception as e:
        logger.error(f"Game {game_id}: Turn execution failed: {e}", exc_info=True)
        session.phase = "AWAITING_ORDERS"  # Reset phase on error
        raise HTTPException(status_code=500, detail=f"Failed to execute turn: {str(e)}")


@app.delete("/api/games/{game_id}")
async def delete_game(game_id: str):
    """Delete a game session.

    Args:
        game_id: Game session ID

    Returns:
        Success status
    """
    if sessions.delete(game_id):
        return {"message": f"Game {game_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Game not found")


# ============================================
# WEBSOCKET ENDPOINT
# ============================================


@app.websocket("/ws/games/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, debug: bool = False):
    """WebSocket connection for real-time game updates.

    Clients receive:
    - CONNECTED: Initial connection confirmation
    - GAME_STATE: State updates
    - AI_THINKING: AI is generating orders
    - TURN_EXECUTED: Turn completed with events
    - GAME_OVER: Game ended

    Args:
        websocket: WebSocket connection
        game_id: Game session ID
        debug: If True, disable fog-of-war for full game visibility
    """
    session = sessions.get(game_id)
    if not session:
        await websocket.close(code=1008, reason="Game not found")
        return

    await websocket.accept()

    # Store debug mode for this session (affects all subsequent state updates)
    session.debug_mode = debug
    session.add_connection(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "CONNECTED",
                "gameId": game_id,
                "turn": session.game.turn,
                "state": session.get_state_for_human(debug=debug),
            }
        )

        logger.info(f"WebSocket connected to game {game_id} (debug={debug})")

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_json()

            # Handle ping/pong for keepalive
            if data.get("type") == "PING":
                await websocket.send_json({"type": "PONG"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from game {game_id}")
    except Exception as e:
        logger.error(f"WebSocket error in game {game_id}: {e}", exc_info=True)
    finally:
        session.remove_connection(websocket)


# ============================================
# SERVE FRONTEND STATIC FILES
# ============================================

# Mount static assets AFTER all API routes
app.mount("/static", StaticFiles(directory="frontend"), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
