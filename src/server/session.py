"""Game session management for Human vs AI gameplay."""

import logging
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket

from ..agent.langgraph_player import LangGraphPlayer
from ..engine.map_generator import generate_map
from ..engine.turn_executor import TurnExecutor
from ..models.game import Game
from ..models.order import Order

logger = logging.getLogger(__name__)


@dataclass
class GameSession:
    """Manages one game session (Human vs AI).

    Coordinates the game state, turn execution, AI player, and WebSocket
    connections for a single human vs AI game.
    """

    id: str
    game: Game
    executor: TurnExecutor
    ai_player: LangGraphPlayer
    human_player_id: str  # "p1" or "p2"
    connections: list[WebSocket] = field(default_factory=list)
    phase: str = "AWAITING_ORDERS"  # "AWAITING_ORDERS" | "AI_THINKING" | "EXECUTING"
    debug_mode: bool = False  # If True, disable fog-of-war for spectator view

    def get_state_for_human(self, debug: bool = False) -> dict:
        """Serialize game state for human player with optional fog-of-war filtering.

        Args:
            debug: If True, return full game state without fog-of-war filtering

        Returns:
            Dictionary with game state filtered to human's perspective (or full state if debug=True)
        """
        if debug:
            # Debug mode: show everything (no fog-of-war)
            all_stars = [self._serialize_star(star, visited=True) for star in self.game.stars]
            all_fleets = [self._serialize_fleet(fleet) for fleet in self.game.fleets]

            human_fleets = [f for f in all_fleets if f.get("owner") == self.human_player_id]
            ai_fleets = [f for f in all_fleets if f.get("owner") != self.human_player_id]

            return {
                "turn": self.game.turn,
                "phase": self.phase,
                "winner": self.game.winner,
                "stars": all_stars,
                "fleets": all_fleets,
                "yourStars": [s for s in all_stars if s.get("owner") == self.human_player_id],
                "yourFleets": human_fleets,
                "aiFleets": ai_fleets,
            }

        # Normal mode: fog-of-war filtering
        human_player = self.game.players[self.human_player_id]

        # Only show stars the human player has visited (fog-of-war)
        visible_stars = [
            self._serialize_star(star, visited=True)
            for star in self.game.stars
            if star.id in human_player.visited_stars
        ]

        # Also include unvisited stars but with limited info (position only)
        unvisited_stars = [
            self._serialize_star(star, visited=False)
            for star in self.game.stars
            if star.id not in human_player.visited_stars
        ]

        human_fleets = [
            self._serialize_fleet(fleet)
            for fleet in self.game.fleets
            if fleet.owner == self.human_player_id
        ]

        # Only show AI fleets that are visible (at stars the human has visited or in transit to/from them)
        visible_ai_fleets = [
            self._serialize_fleet(fleet)
            for fleet in self.game.fleets
            if fleet.owner != self.human_player_id
            and (
                fleet.origin in human_player.visited_stars
                or fleet.dest in human_player.visited_stars
            )
        ]

        return {
            "turn": self.game.turn,
            "phase": self.phase,
            "winner": self.game.winner,
            "stars": visible_stars + unvisited_stars,
            "fleets": human_fleets + visible_ai_fleets,
            "yourStars": [s for s in visible_stars if s.get("owner") == self.human_player_id],
            "yourFleets": human_fleets,
            "aiFleets": visible_ai_fleets,
        }

    def _serialize_star(self, star, visited: bool = True) -> dict:
        """Convert Star to dict for API response with fog-of-war filtering.

        Args:
            star: The Star object to serialize
            visited: Whether the human player has visited this star (fog-of-war)

        Returns:
            Dictionary with star data, limited for unvisited stars
        """
        # For unvisited stars, only reveal position
        if not visited:
            return {
                "id": star.id,
                "name": "???",  # Unknown name
                "x": star.x,
                "y": star.y,
                "owner": None,  # Unknown owner
                "ships": 0,  # Unknown ship count
                "baseRU": 0,  # Unknown RU
                "isHome": False,
                "visited": False,
            }

        # For visited stars, show full information
        # Check if this star is a home star for either player
        is_home = (
            star.id == self.game.players.get("p1").home_star
            or star.id == self.game.players.get("p2").home_star
        )

        return {
            "id": star.id,
            "name": star.name,
            "x": star.x,
            "y": star.y,
            "owner": star.owner,
            "ships": star.stationed_ships.get(star.owner, 0) if star.owner else star.npc_ships,
            "baseRU": star.base_ru,
            "isHome": is_home,
            "visited": True,
        }

    def _serialize_fleet(self, fleet) -> dict:
        """Convert Fleet to dict for API response."""
        return {
            "id": fleet.id,
            "owner": fleet.owner,
            "ships": fleet.ships,
            "origin": fleet.origin,
            "dest": fleet.dest,
            "distRemaining": fleet.dist_remaining,
            "eta": self.game.turn + fleet.dist_remaining,
        }

    def get_last_turn_events(self) -> dict:
        """Get events from the last turn.

        Returns:
            Dictionary with combat, rebellion, and hyperspace loss events
        """
        return {
            "combat": self.game.combats_last_turn,
            "rebellions": self.game.rebellions_last_turn,
            "hyperspaceLosses": self.game.hyperspace_losses_last_turn,
        }

    def validate_orders(self, orders: list[dict]) -> list[str]:
        """Validate human orders before execution.

        Args:
            orders: List of order dictionaries from API

        Returns:
            List of error messages (empty if all valid)
        """
        errors = []

        try:
            # Convert dicts to Order objects
            order_objects = []
            for i, order_dict in enumerate(orders):
                try:
                    order = Order(
                        from_star=order_dict["from"],
                        to_star=order_dict["to"],
                        ships=order_dict["ships"],
                    )
                    order_objects.append(order)
                except (KeyError, ValueError) as e:
                    errors.append(f"Order {i}: Invalid format - {str(e)}")

            if errors:
                return errors

            # Use TurnExecutor validation logic
            star_dict = {star.id: star for star in self.game.stars}
            order_errors = self.executor._check_over_commitment(
                self.game, self.human_player_id, order_objects, star_dict
            )

            if order_errors:
                errors.append(order_errors)

            # Validate individual orders
            for i, order in enumerate(order_objects):
                try:
                    self.executor._validate_single_order(
                        self.game, self.human_player_id, order, star_dict
                    )
                except ValueError as e:
                    errors.append(f"Order {i}: {str(e)}")

        except Exception as e:
            logger.error(f"Order validation error: {e}", exc_info=True)
            errors.append(f"Validation error: {str(e)}")

        return errors

    async def execute_turn(self, human_orders: list[dict], ai_orders: list[Order]) -> dict:
        """Execute one complete turn with both players' orders.

        Args:
            human_orders: List of order dicts from human
            ai_orders: List of Order objects from AI

        Returns:
            Dictionary with turn events
        """
        self.phase = "EXECUTING"

        # Convert human order dicts to Order objects
        human_order_objects = [
            Order(from_star=order["from"], to_star=order["to"], ships=order["ships"])
            for order in human_orders
        ]

        # Build orders dict
        orders_dict = {
            self.human_player_id: human_order_objects,
            self.ai_player.player_id: ai_orders,
        }

        logger.info(
            f"Executing turn {self.game.turn}: "
            f"Human ({self.human_player_id}): {len(human_order_objects)} orders, "
            f"AI ({self.ai_player.player_id}): {len(ai_orders)} orders"
        )

        # Execute turn phases
        self.game, combat_events, hyperspace_losses, rebellion_events = (
            self.executor.execute_pre_turn_logic(self.game)
        )

        # Check if game ended
        if self.game.winner:
            logger.info(f"Game {self.id} ended: winner = {self.game.winner}")
            self.phase = "COMPLETED"
            return self.get_last_turn_events()

        # Process orders and production
        self.game = self.executor.execute_post_turn_logic(self.game, orders_dict)

        self.phase = "AWAITING_ORDERS"

        return self.get_last_turn_events()

    async def broadcast(self, message: dict):
        """Send message to all connected WebSocket clients.

        Args:
            message: Dictionary to send as JSON
        """
        disconnected = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self.connections.remove(ws)

    def add_connection(self, websocket: WebSocket):
        """Add a WebSocket connection to this session."""
        self.connections.append(websocket)
        logger.info(f"WebSocket connected to game {self.id}, total: {len(self.connections)}")

    def remove_connection(self, websocket: WebSocket):
        """Remove a WebSocket connection from this session."""
        if websocket in self.connections:
            self.connections.remove(websocket)
            logger.info(
                f"WebSocket disconnected from game {self.id}, remaining: {len(self.connections)}"
            )


class GameSessionManager:
    """Manages all active game sessions.

    In-memory storage for MVP. Can be replaced with Redis/DB for production.
    """

    def __init__(self):
        self.sessions: dict[str, GameSession] = {}

    async def create_session(
        self,
        human_player: str = "p1",
        seed: int | None = None,
        ai_provider: str = "bedrock",
        ai_model: str | None = None,
    ) -> GameSession:
        """Create a new game session with AI opponent.

        Args:
            human_player: "p1" or "p2" (which side human plays)
            seed: Optional RNG seed for determinism
            ai_provider: LLM provider for AI player
            ai_model: Model name for AI player

        Returns:
            Newly created GameSession
        """
        # Generate unique game ID
        game_id = f"game-{uuid.uuid4().hex[:8]}"

        # Determine AI player ID
        ai_player_id = "p2" if human_player == "p1" else "p1"

        # Create game with deterministic seed
        if seed is None:
            seed = uuid.uuid4().int % (2**32)

        game = generate_map(seed=seed)

        # Initialize AI player
        ai_player = LangGraphPlayer(
            player_id=ai_player_id,
            provider=ai_provider,
            model=ai_model,
            use_mock=False,  # Use real LLM
            verbose=False,  # Can enable for debugging
        )

        # Create session
        session = GameSession(
            id=game_id,
            game=game,
            executor=TurnExecutor(),
            ai_player=ai_player,
            human_player_id=human_player,
        )

        self.sessions[game_id] = session

        logger.info(
            f"Created game {game_id}: Human={human_player}, AI={ai_player_id}, "
            f"seed={seed}, provider={ai_provider}"
        )

        return session

    def get(self, game_id: str) -> GameSession | None:
        """Get a game session by ID.

        Args:
            game_id: Game session ID

        Returns:
            GameSession if found, None otherwise
        """
        return self.sessions.get(game_id)

    def delete(self, game_id: str) -> bool:
        """Delete a game session.

        Args:
            game_id: Game session ID

        Returns:
            True if deleted, False if not found
        """
        if game_id in self.sessions:
            del self.sessions[game_id]
            logger.info(f"Deleted game {game_id}")
            return True
        return False

    async def cleanup_all(self):
        """Clean up all sessions (called on shutdown)."""
        logger.info(f"Cleaning up {len(self.sessions)} game sessions")
        self.sessions.clear()
