# Space Conquest - Technical Architecture

**Version:** 1.0
**Date:** 2025-10-13
**Author:** Architecture Team

---

## 1. High-Level Architecture Overview

Space Conquest is a turn-based 4X strategy game implemented in Python with three major subsystems:

1. **Game Engine Core** - Deterministic game state management, turn phases, combat resolution
2. **Human Player Interface** - ASCII terminal CLI with natural language command parsing
3. **LLM Player Agent** - AWS Bedrock-powered AI opponent using LangChain framework

The architecture emphasizes:
- **Determinism** - Same seed produces same game (for testing/replay)
- **Separation of Concerns** - Clear boundaries between game logic, presentation, and AI
- **Fog-of-War Integrity** - Strict data isolation between players
- **Testability** - All components designed for unit and integration testing

### System Context Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Game Orchestrator                     │
│                      (game.py)                          │
└────┬─────────────────────┬──────────────────────┬──────┘
     │                     │                      │
     ▼                     ▼                      ▼
┌──────────┐      ┌─────────────────┐    ┌──────────────┐
│  Human   │      │   Game Engine   │    │  LLM Agent   │
│   CLI    │◄────►│   (Core Logic)  │◄──►│  (Player 2)  │
│Interface │      │                 │    │              │
└──────────┘      └─────────────────┘    └──────┬───────┘
                           │                     │
                           ▼                     ▼
                  ┌─────────────────┐   ┌──────────────┐
                  │  State Storage  │   │AWS Bedrock + │
                  │  (JSON Files)   │   │  LangChain   │
                  └─────────────────┘   └──────────────┘
```

---

## 2. Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.10+ | Core implementation |
| LLM Provider | AWS Bedrock | Latest | AI reasoning |
| AI Framework | LangChain | Latest | Agent orchestration |
| Testing | pytest | Latest | Unit & integration tests |
| State Storage | JSON Files | - | Game state persistence |
| CLI | Built-in (input/print) | - | Human interaction |

---

## 3. Directory Structure

```
/space-conquest
  ├── game.py                    # Main entry point
  ├── requirements.txt           # Python dependencies
  ├── pytest.ini                 # Test configuration
  │
  ├── /src                       # All source code
  │   ├── __init__.py
  │   │
  │   ├── /models               # Data models
  │   │   ├── __init__.py
  │   │   ├── star.py           # Star class
  │   │   ├── fleet.py          # Fleet class
  │   │   ├── player.py         # Player class with fog-of-war
  │   │   └── game.py           # Game state container
  │   │
  │   ├── /engine               # Game engine
  │   │   ├── __init__.py
  │   │   ├── turn_phases.py    # 5 turn phase implementations
  │   │   ├── combat.py         # Combat resolution logic
  │   │   ├── movement.py       # Fleet movement & hyperspace
  │   │   ├── production.py     # Ship production & rebellions
  │   │   ├── map_generator.py  # Star placement logic
  │   │   └── victory.py        # Victory condition checking
  │   │
  │   ├── /interface            # Human player CLI
  │   │   ├── __init__.py
  │   │   ├── renderer.py       # ASCII map rendering
  │   │   ├── command_parser.py # Natural language command parsing
  │   │   ├── display.py        # Turn info display
  │   │   └── human_player.py   # Human player controller
  │   │
  │   ├── /agent                # LLM Player 2 Agent
  │   │   ├── __init__.py
  │   │   ├── llm_player.py     # Main LLM player controller
  │   │   ├── tools.py          # 7 tools for LLM agent
  │   │   ├── bedrock_client.py # AWS Bedrock integration
  │   │   ├── memory.py         # Agent memory system
  │   │   ├── heuristics.py     # Target scoring, garrison rules
  │   │   └── prompts.py        # System prompts & templates
  │   │
  │   └── /utils                # Utilities
  │       ├── __init__.py
  │       ├── rng.py            # Seedable RNG wrapper
  │       ├── distance.py       # Chebyshev distance (max(|dx|, |dy|))
  │       ├── serialization.py  # JSON save/load
  │       └── validators.py     # Order validation
  │
  ├── /state                    # Game state files (gitignored)
  │   └── game_*.json
  │
  ├── /tests                    # All tests
  │   ├── __init__.py
  │   ├── /unit
  │   │   ├── test_models.py
  │   │   ├── test_combat.py
  │   │   ├── test_movement.py
  │   │   ├── test_production.py
  │   │   └── test_tools.py
  │   ├── /integration
  │   │   ├── test_turn_flow.py
  │   │   ├── test_llm_agent.py
  │   │   └── test_game_orchestration.py
  │   └── /fixtures
  │       └── test_seeds.py
  │
  └── /specs                    # Documentation
      ├── space_conquest_spec.md
      ├── llm_player_2_agent_spec.md
      └── technical_architecture.md (this file)
```

---

## 4. Core Data Models

### 4.1 Star

```python
@dataclass
class Star:
    """Represents a star system on the map."""
    id: str                    # Unique identifier (e.g., "A")
    name: str                  # Human-readable name (generated from seed)
    x: int                     # X coordinate (0-11)
    y: int                     # Y coordinate (0-9)
    base_ru: int              # Resource units (1-4)
    owner: Optional[str]      # "p1", "p2", or None (NPC)
    npc_ships: int            # NPC defender count (initialized to base_ru for NPC stars)
    stationed_ships: Dict[str, int]  # {"p1": 5, "p2": 0}
```

**Initialization Notes:**
- For NPC stars: `npc_ships = base_ru` at game start
- For home stars: `owner = "p1"/"p2"`, `stationed_ships = {"p1": 4}` or `{"p2": 4}`

### 4.2 Fleet

```python
@dataclass
class Fleet:
    """Represents ships in hyperspace transit."""
    id: str                    # Unique identifier (e.g., "p1-003")
    owner: str                 # "p1" or "p2"
    ships: int                 # Ship count
    origin: str                # Origin star ID
    dest: str                  # Destination star ID
    dist_remaining: int        # Turns until arrival
```

### 4.3 Player

```python
@dataclass
class Player:
    """Player state with fog-of-war knowledge."""
    id: str                    # "p1" or "p2"
    home_star: str             # Home star ID
    known_ru: Dict[str, Optional[int]]        # star_id -> RU (None if unknown)
    known_control: Dict[str, str]             # star_id -> "me"|"opp"|"npc"|"none"
    fleets: List[Fleet]        # Player's fleets in transit
```

### 4.4 Order

```python
@dataclass
class Order:
    """Represents a movement order submitted by a player."""
    from_star: str             # Origin star ID
    to_star: str               # Destination star ID
    ships: int                 # Number of ships to move (must be > 0)
```

**Order Format (JSON):**
```json
{
  "moves": [
    {"from": "A", "to": "F", "ships": 3},
    {"from": "A", "to": "D", "ships": 1}
  ]
}
```

### 4.5 Game

```python
class Game:
    """Main game state container."""
    seed: int                  # RNG seed
    turn: int                  # Current turn number
    stars: List[Star]          # All stars
    fleets: List[Fleet]        # All fleets
    players: Dict[str, Player] # "p1" and "p2"
    rng: random.Random         # Seeded RNG instance
    winner: Optional[str]      # "p1", "p2", "draw", or None
    turn_history: List[Dict]   # Event log for replay (format: [{"turn": N, "events": [...]}])
    fleet_counter: Dict[str, int]  # Fleet ID generation: {"p1": 5, "p2": 3}
    order_errors: Dict[str, List[str]]  # Order validation errors by player: {"p1": ["error1", ...], "p2": [...]}
```

### 4.6 Game Constants

```python
# src/utils/constants.py
"""Game configuration constants from specification."""

GRID_X = 12
GRID_Y = 10
NUM_STARS = 16
HOME_RU = 4
NPC_RU_RANGE = (1, 3)
HYPERSPACE_LOSS_PROB = 0.02  # 2% per turn (d50 roll of 1)
REBELLION_PROB = 0.5          # 50% if under-garrisoned (d6 roll of 4-6)
HOME_DISTANCE_RANGE = (0, 2)  # Chebyshev distance from corners (maintains 7-11 parsec separation)
MOVE_RATE = 1                 # Parsecs per turn
RNG_SEED_DEFAULT = 42         # Default seed for testing
```

---

## 5. Game Engine Architecture

The game engine follows a strict 5-phase turn structure:

### 5.1 Turn Phase Pipeline

```python
class TurnExecutor:
    """Orchestrates the 5 turn phases."""

    def execute_turn(self, game: Game, orders: Dict[str, List[Order]]) -> Game:
        """Execute one complete turn."""
        # Phase 1: Fleet Movement
        game = self.phase1_fleet_movement(game)

        # Phase 2: Combat Resolution
        game = self.phase2_combat_resolution(game)

        # Phase 3: Victory Assessment
        if self.phase3_check_victory(game):
            return game

        # Phase 4: Rebellions & Production
        game = self.phase4_rebellions_and_production(game)

        # Phase 5: Process Orders
        game = self.phase5_process_orders(game, orders)

        game.turn += 1
        return game
```

### 5.2 Phase 1: Fleet Movement

```python
def phase1_fleet_movement(game: Game) -> Game:
    """
    1. Apply 2% hyperspace loss to each fleet in transit:
       - Roll d50 for each fleet (once per fleet, not per ship)
       - On roll of 1: entire fleet is destroyed
       - On roll of 2-50: fleet continues with all ships intact
    2. Decrement dist_remaining for surviving fleets
    3. Process arrivals (dist_remaining == 0):
       - Add arriving fleet ships to star.stationed_ships[owner]
    4. Reveal star RU to arriving player (update known_ru)
    """
```

**CRITICAL**: Hyperspace loss is per-fleet, not per-ship. A single d50 roll determines if the entire fleet survives or is destroyed.

### 5.3 Phase 2: Combat Resolution

```python
def phase2_combat_resolution(game: Game) -> Game:
    """
    For each star with potential combat:

    1. Merge arriving fleets: Add all arriving ships to stationed_ships

    2. If star is NPC-owned and has attackers:
       - Combine all attacking forces (both players if present)
       - Resolve attackers vs NPC defenders
       - NPC loses: all attackers survive (minus casualties), star becomes unowned
       - Attackers lose: NPC retains control with surviving ships

    3. If multiple players have ships at star (after NPC combat):
       - Resolve player-vs-player combat
       - Higher ship count wins
       - Loser eliminated completely
       - Winner loses ceil(loser/2) ships
       - Tie: mutual destruction (both eliminated)
       - Winner gains star control if they didn't own it

    4. Update star.owner based on combat results
    """

def resolve_combat(attacker_ships: int, defender_ships: int) -> CombatResult:
    """
    Deterministic combat resolution:
    - attacker_ships > defender_ships: attacker wins, loses ceil(defender/2)
    - attacker_ships < defender_ships: defender wins, loses ceil(attacker/2)
    - attacker_ships == defender_ships: tie, both eliminated
    """
```

### 5.4 Phase 3: Victory Assessment

```python
def check_victory(game: Game) -> Optional[str]:
    """
    Check victory conditions after Phase 2 combat:

    1. Check if Player 1 captured Player 2's home star this turn
    2. Check if Player 2 captured Player 1's home star this turn
    3. Victory logic:
       - Both captured opponent homes → game.winner = "draw"
       - Only P1 captured P2 home → game.winner = "p1"
       - Only P2 captured P1 home → game.winner = "p2"
       - Neither captured → game.winner = None (continue)

    Return: "p1", "p2", "draw", or None
    """
```

### 5.5 Phase 4: Rebellions & Production

```python
def process_rebellions(game: Game) -> Game:
    """
    For each player-controlled star that was originally NPC:
    - If stationed_ships[owner] < base_ru: 50% rebellion chance (d6 roll of 4-6)
    - On rebellion:
      * Spawn base_ru rebel ships
      * Resolve combat: stationed ships vs rebels
      * If rebels win (or tie):
        - star.owner = None (reverts to NPC)
        - star.npc_ships = surviving_rebel_count
      * If player wins:
        - star.stationed_ships[owner] = surviving_player_count
    - No production occurs at rebelling stars this turn
    """

def process_production(game: Game) -> Game:
    """
    For each controlled star (that didn't rebel):
    - Home stars: +4 ships
    - Other stars: +base_ru ships
    """
```

### 5.6 Phase 5: Orders Processing

```python
def process_orders(game: Game, orders: Dict[str, List[Order]]) -> Game:
    """
    Validate and execute player move orders with graceful error handling:

    1. **Strict over-commitment check:**
       - Sum total ships requested from each star across all orders
       - If total exceeds available ships: reject entire order set, log error
       - Check ownership BEFORE counting ships (prevents exploiting unowned stars)

    2. **Individual order execution (lenient):**
       - For each order that passed over-commitment check:
         * Validate star existence, ownership, ship availability
         * If invalid: skip order, log error, continue with next order
         * If valid: create fleet, deduct from stationed ships

    3. **Error logging:**
       - All errors stored in game.order_errors[player_id]
       - Format: "Order {index}: {from_star} -> {to_star} with {ships} ships: {error_message}"
       - Errors persist for player review in next turn

    4. **No crashes:**
       - All ValueError exceptions caught and logged
       - Game continues regardless of order validity
       - Players retain partial agency (valid orders execute)
    """
```

---

## 6. Human Player CLI Interface

### 6.1 ASCII Map Rendering

```python
class MapRenderer:
    """Renders 12x10 ASCII map with fog-of-war."""

    def render(self, player: Player, stars: List[Star]) -> str:
        """
        Output format:
        .. .. ?A .. .. ?B .. .. ?C .. ..
        .. 4D .. .. ?E .. .. .. ?F .. ..

        Legend:
        - '?X' = unknown RU
        - '1A' = known star with 1 RU
        - '4D' = home star (4 RU)
        - '..' = empty space
        """
```

### 6.2 Command Parser

```python
class CommandParser:
    """Parse natural language commands."""

    def parse(self, command: str) -> Order:
        """
        Supported formats:
        - "move 3 ships from A to B"
        - "send 5 from D to F"
        - "attack C with 10 from A"
        - "pass" (no moves)
        - "help"
        - "status"
        """
```

### 6.3 Display System

```python
class DisplayManager:
    """Manages turn information display."""

    def show_turn_summary(self, player: Player, game: Game):
        """Display:
        - Current turn number
        - Controlled stars with ship counts
        - Fleets in transit
        - Recent combat results
        - Production summary
        """
```

---

## 7. LLM Player 2 Agent Architecture

### 7.1 Agent Overview

The LLM agent uses AWS Bedrock (Claude model) via LangChain to play as Player 2. It follows the OODA loop: Observe → Orient → Decide → Act.

```python
class LLMPlayer:
    """LLM-powered Player 2 agent."""

    def __init__(self, bedrock_client: BedrockClient):
        self.bedrock = bedrock_client
        self.tools = AgentTools()
        self.memory = AgentMemory()
        self.chain = self._build_langchain()

    def get_orders(self, game: Game) -> List[Order]:
        """
        Main decision loop:
        1. Build observation from game state
        2. Invoke LangChain agent with tools
        3. Agent calls tools and decides
        4. Parse and validate orders
        5. Return orders
        """
```

### 7.2 Tool Suite (7 Tools)

```python
class AgentTools:
    """Tools exposed to LLM via LangChain function calling."""

    def get_observation(self) -> dict:
        """Return Player 2's current game state JSON."""

    def get_ascii_map(self) -> str:
        """Return Player 2's fog-of-war map."""

    def query_star(self, star_ref: str) -> dict:
        """Return star details and distances."""

    def estimate_route(self, from_star: str, to_star: str) -> dict:
        """Return Chebyshev distance (max(|dx|, |dy|)) and hyperspace risk."""

    def propose_orders(self, draft_orders: dict) -> dict:
        """Validate orders before submission."""

    def submit_orders(self, orders: dict) -> dict:
        """Commit final orders for the turn."""

    def memory_query(self, table: str, filter: dict) -> list:
        """Query agent's auto-populated memory (battle_log, discovery_log)."""
```

### 7.3 AWS Bedrock + LangChain Integration

```python
class BedrockClient:
    """Wrapper for AWS Bedrock API."""

    def __init__(self, model_id="anthropic.claude-3-sonnet", region="us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def invoke(self, messages: list, tools: list) -> dict:
        """
        Invoke Bedrock with tool calling:
        - Converts LangChain tool specs to Bedrock format
        - Handles tool_use and tool_result messages
        - Manages conversation context
        """

class LangChainAgent:
    """LangChain agent wrapping Bedrock."""

    def build_agent(self, tools: List[Tool]) -> AgentExecutor:
        """
        Build LangChain agent:
        - Use Bedrock as LLM
        - Register 7 agent tools
        - Set system prompt from spec
        - Configure memory and callbacks
        """
```

### 7.4 Agent Memory System

```python
class AgentMemory:
    """Private memory for Player 2 agent (in-memory or SQLite)."""

    # Schema:
    # - discovery_log: {turn, star_id, ru}
    # - battle_log: {turn, star_id, my_ships, opp_ships, outcome}
    # - sighting_log: {turn, star_id, opp_presence}
    # - threat_map: {star_id, threat_score, last_update}
    # - plan_journal: {turn, goals, targets, reserves}

    def upsert(self, table: str, records: List[dict]):
        """Insert or update records."""

    def query(self, table: str, filter: dict) -> List[dict]:
        """Query with filters."""
```

### 7.5 Heuristics Module

```python
class AgentHeuristics:
    """Baseline strategy heuristics for LLM agent."""

    def score_targets(self, stars: List[Star], player: Player) -> List[Tuple[str, float]]:
        """
        Target scoring formula:
        score = w_ru * E[RU] - w_dist * min_dist - w_threat * threat
        """

    def compute_garrison_requirement(self, star: Star) -> int:
        """Return recommended garrison (>= base_ru to prevent rebellion)."""

    def assess_hyperspace_risk(self, distance: int) -> float:
        """Return cumulative loss probability: 1 - (0.95^distance)."""
```

### 7.6 System Prompt Template

```python
SYSTEM_PROMPT = """
You are Player 2 in Space Conquest. Your goal is to capture Player 1's Home Star.

You have access to tools that provide game information and allow you to submit orders.
You must respect fog-of-war: you only know what your fleets have observed.

Process:
1. Call get_observation() to see current game state
2. Call get_ascii_map() for spatial context
3. Query stars and routes as needed
4. Decide on moves using your strategic judgment
5. Validate with propose_orders()
6. Submit with submit_orders()
7. Update memory with discoveries and battle results

Constraints:
- Keep garrisons >= star RU to prevent rebellions
- Minimize hyperspace risk (prefer shorter routes)
- Balance expansion, defense, and offense
"""
```

---

## 8. Game Orchestration (game.py)

### 8.1 Main Entry Point

```python
def main():
    """Main game entry point."""
    parser = argparse.ArgumentParser(description="Space Conquest")
    parser.add_argument("--mode", choices=["hvh", "hvl", "lvl"], default="hvl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--load", type=str, help="Load game from JSON")
    parser.add_argument("--save", type=str, help="Save game to JSON")
    args = parser.parse_args()

    # Initialize game
    if args.load:
        game = load_game(args.load)
    else:
        game = initialize_game(args.seed)

    # Create players
    if args.mode == "hvh":
        p1 = HumanPlayer("p1")
        p2 = HumanPlayer("p2")
    elif args.mode == "hvl":
        p1 = HumanPlayer("p1")
        p2 = LLMPlayer("p2")
    else:  # lvl
        p1 = LLMPlayer("p1")
        p2 = LLMPlayer("p2")

    # Game loop
    orchestrator = GameOrchestrator(game, p1, p2)
    orchestrator.run()

    # Save if requested
    if args.save:
        save_game(game, args.save)
```

### 8.2 Game Orchestrator

```python
class GameOrchestrator:
    """Manages turn loop and player coordination."""

    def __init__(self, game: Game, p1: PlayerController, p2: PlayerController):
        self.game = game
        self.players = {" p1": p1, "p2": p2}
        self.turn_executor = TurnExecutor()

    def run(self):
        """Main game loop."""
        while not self.game.winner:
            print(f"\n=== Turn {self.game.turn} ===\n")

            # Get orders from both players simultaneously
            orders = {}
            for pid, player in self.players.items():
                orders[pid] = player.get_orders(self.game)

            # Execute turn
            self.game = self.turn_executor.execute_turn(self.game, orders)

            # Check for victory
            if self.game.winner:
                print(f"\n🎉 {self.game.winner} wins!")
                break

        return self.game
```

---

## 9. State Management & Serialization

### 9.1 JSON Serialization

```python
class GameSerializer:
    """Save/load game state to JSON."""

    def serialize(self, game: Game) -> dict:
        """Convert game to JSON-compatible dict."""
        return {
            "seed": game.seed,
            "turn": game.turn,
            "stars": [asdict(s) for s in game.stars],
            "fleets": [asdict(f) for f in game.fleets],
            "players": {pid: asdict(p) for pid, p in game.players.items()},
            "winner": game.winner,
            "turn_history": game.turn_history
        }

    def deserialize(self, data: dict) -> Game:
        """Reconstruct game from JSON dict."""
```

### 9.2 File Storage

```python
def save_game(game: Game, filepath: str):
    """Save game to /state directory."""
    serializer = GameSerializer()
    with open(f"state/{filepath}", "w") as f:
        json.dump(serializer.serialize(game), f, indent=2)

def load_game(filepath: str) -> Game:
    """Load game from /state directory."""
    serializer = GameSerializer()
    with open(f"state/{filepath}", "r") as f:
        return serializer.deserialize(json.load(f))
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# tests/unit/test_combat.py
def test_combat_player_wins():
    """Player with more ships wins, loses ceil(loser/2)."""
    result = resolve_combat(attacker_ships=5, defender_ships=3)
    assert result.winner == "attacker"
    assert result.attacker_losses == 2  # ceil(3/2)
    assert result.defender_losses == 3

def test_combat_tie():
    """Equal ships = mutual destruction."""
    result = resolve_combat(attacker_ships=5, defender_ships=5)
    assert result.winner is None
    assert result.attacker_losses == 5
    assert result.defender_losses == 5

# tests/unit/test_movement.py
def test_hyperspace_loss():
    """2% loss applied per turn."""
    rng = random.Random(42)
    fleet = Fleet(id="f1", owner="p1", ships=100, origin="A", dest="B", dist_remaining=1)
    # Simulate 1000 fleets to verify ~2% loss rate

def test_fleet_arrival():
    """Fleets arrive when dist_remaining == 0."""
    fleet = Fleet(id="f1", owner="p1", ships=5, origin="A", dest="B", dist_remaining=0)
    arrivals = process_arrivals([fleet])
    assert len(arrivals) == 1
    assert arrivals[0].dest == "B"
```

### 10.2 Integration Tests

```python
# tests/integration/test_turn_flow.py
def test_full_turn_execution():
    """Test complete turn with all 5 phases."""
    game = create_test_game(seed=42)
    orders = {
        "p1": [Order(from_star="A", to_star="B", ships=2)],
        "p2": []
    }
    executor = TurnExecutor()
    game = executor.execute_turn(game, orders)
    assert game.turn == 1
    # Verify fleets created, combat resolved, production applied

# tests/integration/test_llm_agent.py
@pytest.mark.integration
def test_llm_agent_generates_valid_orders():
    """Test LLM agent produces valid orders."""
    game = create_test_game(seed=42)
    agent = LLMPlayer("p2")
    orders = agent.get_orders(game)
    # Validate orders are legal
    validator = OrderValidator()
    assert validator.validate(orders, game, "p2")
```

### 10.3 Test Fixtures

```python
# tests/fixtures/test_seeds.py
DETERMINISTIC_SEEDS = {
    "balanced_start": 42,
    "close_home_stars": 123,
    "distant_home_stars": 456,
    "early_conflict": 789
}

def create_test_game(seed: int, turn: int = 0) -> Game:
    """Create game with specific seed for testing."""
    return initialize_game(seed, turn)
```

### 10.4 Test Coverage Goals

- **Unit tests**: 90%+ coverage of game engine logic
- **Integration tests**: Cover full turn cycles, LLM agent integration
- **End-to-end tests**: Complete games with deterministic seeds
- **Regression tests**: Capture specific bug scenarios

### 10.5 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest -m integration  # Only integration tests

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_combat.py
```

---

## 11. Data Flow Diagrams

### 11.1 Turn Execution Flow

```
┌─────────────────────────────────────────────────┐
│          Game Orchestrator (game.py)            │
└───┬────────────────────────────────────────┬────┘
    │                                        │
    │ 1. Request Orders                      │
    ▼                                        ▼
┌──────────────┐                    ┌──────────────┐
│ HumanPlayer  │                    │  LLMPlayer   │
│   (CLI)      │                    │  (Bedrock)   │
└───┬──────────┘                    └───┬──────────┘
    │                                   │
    │ 2. Submit Orders                  │ 2. Submit Orders
    ▼                                   ▼
┌─────────────────────────────────────────────────┐
│            TurnExecutor.execute_turn()          │
│  ┌──────────────────────────────────────────┐  │
│  │ Phase 1: Fleet Movement                  │  │
│  │  - Apply hyperspace loss                 │  │
│  │  - Process arrivals                      │  │
│  │  - Reveal stars                          │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Phase 2: Combat Resolution               │  │
│  │  - Merge fleets                          │  │
│  │  - Resolve all combats                   │  │
│  │  - Update ownership                      │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Phase 3: Victory Assessment              │  │
│  │  - Check home star capture               │  │
│  │  - Set winner if applicable              │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Phase 4: Rebellions & Production         │  │
│  │  - Roll for rebellions                   │  │
│  │  - Spawn ships at controlled stars       │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ Phase 5: Process Orders                  │  │
│  │  - Validate orders                       │  │
│  │  - Create new fleets                     │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
    │
    │ 3. Updated Game State
    ▼
┌─────────────────────────────────────────────────┐
│         Display Results / Continue Loop         │
└─────────────────────────────────────────────────┘
```

### 11.2 LLM Agent Decision Flow

```
┌─────────────────────────────────────────────────┐
│        LLMPlayer.get_orders(game)               │
└───┬─────────────────────────────────────────────┘
    │
    │ 1. Build Observation
    ▼
┌─────────────────────────────────────────────────┐
│     AgentTools.get_observation()                │
│  - Filter game state for Player 2               │
│  - Apply fog-of-war                             │
│  - Generate observation JSON                    │
└───┬─────────────────────────────────────────────┘
    │
    │ 2. Invoke LangChain Agent
    ▼
┌─────────────────────────────────────────────────┐
│       LangChain AgentExecutor                   │
│  ┌──────────────────────────────────────────┐  │
│  │  System Prompt + Observation             │  │
│  └─────────────┬────────────────────────────┘  │
│                ▼                                │
│  ┌──────────────────────────────────────────┐  │
│  │  AWS Bedrock (Claude Model)              │  │
│  │  - Reason about game state               │  │
│  │  - Call tools via function calling       │  │
│  └─────────────┬────────────────────────────┘  │
│                ▼                                │
│  ┌──────────────────────────────────────────┐  │
│  │  Tool Execution                          │  │
│  │  - query_star()                          │  │
│  │  - estimate_route()                      │  │
│  │  - memory_query()                        │  │
│  │  - propose_orders()                      │  │
│  └─────────────┬────────────────────────────┘  │
│                ▼                                │
│  ┌──────────────────────────────────────────┐  │
│  │  Final Tool Call: submit_orders()        │  │
│  └─────────────┬────────────────────────────┘  │
└────────────────┼────────────────────────────────┘
                 │
                 │ 3. Parse & Validate Orders
                 ▼
┌─────────────────────────────────────────────────┐
│         OrderValidator.validate()               │
│  - Check ship availability                      │
│  - Check origin ownership                       │
│  - Check star existence                         │
└───┬─────────────────────────────────────────────┘
    │
    │ 4. Return Orders
    ▼
┌─────────────────────────────────────────────────┐
│          Game Orchestrator                      │
└─────────────────────────────────────────────────┘
```

---

## 12. Key Design Decisions & Rationale

### 12.1 Determinism via Seeded RNG

**Decision**: Use a single seeded `random.Random` instance passed through all game logic.

**Rationale**:
- Enables deterministic testing (same seed = same game)
- Supports replay and debugging
- Allows verification of game rules
- Critical for validating LLM agent behavior

**Implementation**: `Game` object owns the RNG; all randomness goes through it.

### 12.2 Fog-of-War as Player State

**Decision**: Each `Player` object maintains its own `known_ru` and `known_control` dicts.

**Rationale**:
- Prevents data leaks between players
- Simplifies rendering (just use player's knowledge)
- Easy to test (inspect player knowledge directly)
- LLM agent only receives its player's knowledge

**Trade-off**: Some duplication of information, but worth it for clarity and security.

### 12.3 JSON for State Storage (not SQLite/DuckDB)

**Decision**: Start with JSON files for save/load; avoid database for initial version.

**Rationale**:
- Simpler implementation (no schema management)
- Human-readable for debugging
- Easy to version control test fixtures
- Sufficient for turn-based game (no high-frequency writes)

**Future**: Could migrate to SQLite if we add features like:
- Game statistics/analytics
- Turn history queries
- Multi-game tournament tracking

### 12.4 LangChain + Bedrock for LLM Agent

**Decision**: Use LangChain's `AgentExecutor` with function calling to Bedrock Claude.

**Rationale**:
- LangChain provides robust tool/function calling framework
- Bedrock Claude excels at strategic reasoning
- Function calling enables structured tool use
- LangChain manages conversation context automatically

**Alternative considered**: Direct Bedrock API calls (more control, more boilerplate).

### 12.5 Natural Language CLI (no JSON exposure)

**Decision**: Human players use natural language commands, not JSON.

**Rationale**:
- Better user experience
- Lower barrier to entry
- Matches how humans think ("move 3 ships from A to B")
- Hides implementation details

**Implementation**: Regex-based command parser with forgiving input handling.

### 12.6 Tool-Based LLM Agent Architecture

**Decision**: LLM agent interacts via 7 well-defined tools, not free-form game state access.

**Rationale**:
- Enforces fog-of-war strictly (tools filter data)
- Provides structured, validatable interface
- Easier to test tool behavior independently
- Matches LLM Player 2 spec requirements
- Reduces hallucination risk (tools return facts)

### 12.7 In-Memory Agent Memory (5 Tables)

**Decision**: Agent memory uses simple in-memory dicts (or lightweight SQLite).

**Rationale**:
- Spec requires 5 memory tables (discovery, battle, sighting, threat, plan)
- In-memory is fast and sufficient for single-game context
- Can persist to JSON between games if needed
- SQLite option available if memory queries become complex

### 12.8 Separate Interface Layer

**Decision**: CLI code lives in `/interface`, completely separate from game engine.

**Rationale**:
- Enables headless testing of game logic
- Could add GUI or web interface later
- Simplifies unit testing (no UI mocking)
- Clear separation of concerns

---

## 13. Implementation Phases (Recommended Order)

### Phase 1: Core Game Engine
1. Implement data models (`Star`, `Fleet`, `Player`, `Game`)
2. Implement RNG and map generation
3. Implement 5 turn phases sequentially
4. Write unit tests for each phase
5. Implement serialization (save/load JSON)

**Milestone**: Can run a headless game with programmatic orders.

### Phase 2: Human Player Interface
1. Implement ASCII map renderer
2. Implement command parser
3. Implement turn display
4. Wire up human player to game loop
5. Test human vs human gameplay

**Milestone**: Two humans can play a complete game via CLI.

### Phase 3: LLM Player 2 Agent
1. Implement 7 agent tools
2. Set up AWS Bedrock client
3. Implement LangChain agent with tools
4. Implement agent memory system
5. Implement heuristics module
6. Test human vs LLM gameplay

**Milestone**: Human can play against LLM opponent.

### Phase 4: Integration & Polish
1. Implement game orchestrator with mode selection
2. Add CLI arguments (seed, save/load, mode)
3. Write integration tests
4. Performance tuning (if needed)
5. Documentation and examples

**Milestone**: Production-ready game with all modes working.

---

## 14. AWS Bedrock Integration Details

### 14.1 Bedrock Model Selection

**Recommended Model**: `anthropic.claude-3-sonnet-20240229-v1:0`

**Rationale**:
- Good balance of reasoning capability and cost
- Supports function/tool calling
- 200K context window (sufficient for game state)
- Fast inference time (~1-2s per turn)

**Alternative**: `anthropic.claude-3-haiku` for faster/cheaper inference if reasoning is sufficient.

### 14.2 Bedrock API Call Pattern

```python
import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

response = bedrock.converse(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[
        {
            "role": "user",
            "content": [{"text": "Your game state observation here"}]
        }
    ],
    inferenceConfig={
        "maxTokens": 4096,
        "temperature": 0.7,
        "topP": 0.9
    },
    toolConfig={
        "tools": [
            {
                "toolSpec": {
                    "name": "get_observation",
                    "description": "Get current game state for Player 2",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            }
            # ... other 6 tools
        ]
    }
)
```

### 14.3 Cost Estimation

**Estimated cost per game** (assuming 20 turns, 3 tool calls per turn):
- Input tokens: ~500 tokens/turn × 20 turns = 10K tokens
- Output tokens: ~200 tokens/turn × 20 turns = 4K tokens
- Tool calls: ~100 tokens/call × 3 × 20 = 6K tokens

**Total**: ~20K tokens per game

**Claude 3 Sonnet pricing** (as of 2024):
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

**Cost**: ~$0.006 per game (less than 1 cent)

### 14.4 Error Handling

```python
class BedrockClient:
    def invoke_with_retry(self, messages, tools, max_retries=3):
        """Invoke Bedrock with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return self.bedrock.converse(...)
            except ClientError as e:
                if e.response['Error']['Code'] == 'ThrottlingException':
                    time.sleep(2 ** attempt)
                elif e.response['Error']['Code'] == 'ModelTimeoutException':
                    time.sleep(2 ** attempt)
                else:
                    raise
        raise Exception("Max retries exceeded")
```

---

## 15. Testing AWS Bedrock Integration

### 15.1 Mock Bedrock for Unit Tests

```python
class MockBedrockClient:
    """Mock Bedrock client for testing without API calls."""

    def converse(self, **kwargs):
        """Return canned responses for testing."""
        # Parse tool_use requests and return realistic results
        # Enables testing agent logic without actual API costs
```

### 15.2 Integration Test with Real Bedrock

```python
@pytest.mark.bedrock
@pytest.mark.slow
def test_llm_agent_with_real_bedrock():
    """Integration test with actual Bedrock API (requires AWS credentials)."""
    game = create_test_game(seed=42)
    agent = LLMPlayer("p2", use_mock=False)
    orders = agent.get_orders(game)
    assert orders is not None
    assert validate_orders(orders, game, "p2")
```

Run with: `pytest -m bedrock` (only when needed, to avoid API costs).

---

## 16. Security & Data Integrity

### 16.1 Fog-of-War Enforcement

**Critical**: LLM agent must never receive data outside Player 2's knowledge.

**Enforcement points**:
1. `get_observation()` tool filters game state before returning
2. `known_ru` and `known_control` strictly maintained per player
3. Map renderer only shows player's knowledge
4. Test suite validates no data leaks

### 16.2 Order Validation

**Critical**: All orders must be validated before execution.

**Validation checks**:
- Origin star is controlled by submitting player
- Ship count available at origin
- Destination star exists on map
- No negative ship counts

### 16.3 Agent Prompt Injection Defense

**Risk**: User might try to manipulate LLM agent via star names or game messages.

**Mitigation**:
- Star names are fixed at game start (from seed)
- No user-controlled text passes to LLM
- System prompt explicitly instructs agent to ignore meta-prompts

---

## 17. Performance Considerations

### 17.1 Expected Performance Targets

- **Turn execution** (headless): < 10ms
- **LLM agent decision**: 1-3 seconds (Bedrock latency)
- **Map rendering**: < 1ms
- **Game initialization**: < 50ms

### 17.2 Bottlenecks

- **Bedrock API latency**: Dominates turn time for LLM games
  - Mitigation: Use Claude 3 Haiku for faster inference if needed
  - Alternative: Async mode (submit orders, poll for completion)

- **Combat resolution**: Worst case 16 stars × 2 players = 32 combats/turn
  - Expected: < 1ms total (simple arithmetic)

- **Memory queries**: If agent memory grows large
  - Mitigation: Index by turn, limit query results

### 17.3 Scalability

Current architecture supports:
- ✅ 1-2 player games (designed for)
- ✅ 16 stars on 12×10 grid
- ✅ Hundreds of fleets in transit
- ❌ Massively multiplayer (would need architecture changes)
- ❌ Real-time gameplay (turn-based only)

---

## 18. Future Extensions

### 18.1 Potential Enhancements

1. **Web Interface**: Flask/FastAPI server with HTML/CSS frontend
2. **Replay Viewer**: Visualize game history turn-by-turn
3. **Tournament Mode**: Multiple games with ELO ratings
4. **AI Training**: Fine-tune LLM on game transcripts
5. **Larger Maps**: Configurable grid sizes
6. **More Players**: 3-4 player free-for-all
7. **Advanced Mechanics**: Diplomacy, tech trees, special abilities

### 18.2 Architecture Readiness for Extensions

| Extension | Effort | Notes |
|-----------|--------|-------|
| Web UI | Medium | Interface layer is separate; add Flask routes |
| Replay Viewer | Low | Turn history already captured |
| Tournament Mode | Low | Run multiple games, track stats |
| Larger Maps | Low | Grid size is configurable |
| More Players | Medium | Refactor Player dict to list, update combat |
| Tech Trees | High | Major game logic additions |

---

## 19. Dependencies & Requirements

### 19.1 Python Packages

```txt
# requirements.txt
boto3>=1.28.0              # AWS SDK for Bedrock
langchain>=0.1.0           # LLM agent framework
langchain-aws>=0.1.0       # LangChain Bedrock integration
pytest>=7.4.0              # Testing framework
pytest-cov>=4.1.0          # Coverage reporting
python-dotenv>=1.0.0       # Environment variable management
```

### 19.2 AWS Configuration

**Required**:
- AWS account with Bedrock access
- IAM role/user with `bedrock:InvokeModel` permission
- Model access enabled for Claude 3 Sonnet in Bedrock console

**Environment variables**:
```bash
AWS_REGION=us-east-1
AWS_PROFILE=default  # or use AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### 19.3 Development Environment

- Python 3.10 or higher
- pip or poetry for package management
- AWS CLI configured (for Bedrock access)
- Terminal with UTF-8 support (for ASCII rendering)

---

## 20. Conclusion

This architecture provides a solid foundation for implementing Space Conquest with clear separation of concerns, testability, and extensibility. The modular design allows for incremental development and testing, while the LLM agent integration via AWS Bedrock and LangChain enables sophisticated AI opponent behavior.

**Key Strengths**:
- ✅ Deterministic and testable
- ✅ Clear separation: engine, interface, AI
- ✅ Fog-of-war strictly enforced
- ✅ LLM agent uses constrained tool interface
- ✅ Human-friendly CLI (no JSON)
- ✅ Extensible for future features

**Next Steps**:
1. Review and approve this architecture
2. Set up Python project structure
3. Begin Phase 1: Core game engine implementation
4. Iterate through phases 2-4 with testing at each stage

---

**Document Version**: 1.0
**Last Updated**: 2025-10-13
**Status**: Ready for Implementation
