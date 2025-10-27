"""Pydantic models for tool input/output validation.

Provides type-safe validation for all LLM agent tools to ensure
data integrity and catch errors early in the tool execution pipeline.
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ========== Input Models ==========


class GetObservationInput(BaseModel):
    """Input for get_observation tool - no parameters required."""

    pass


class GetAsciiMapInput(BaseModel):
    """Input for get_ascii_map tool."""

    view: str = Field(
        default="current", description="Map view mode (only 'current' supported)"
    )


class QueryStarInput(BaseModel):
    """Input for query_star tool."""

    star_ref: str = Field(description="Star ID or letter to query (e.g., 'A', 'P')")

    @field_validator("star_ref")
    @classmethod
    def uppercase_star_ref(cls, v: str) -> str:
        """Convert star reference to uppercase."""
        return v.upper()


class EstimateRouteInput(BaseModel):
    """Input for estimate_route tool."""

    from_star: str = Field(description="Origin star ID")
    to_star: str = Field(description="Destination star ID")

    @field_validator("from_star", "to_star")
    @classmethod
    def uppercase_star(cls, v: str) -> str:
        """Convert star IDs to uppercase."""
        return v.upper()


class OrderModel(BaseModel):
    """Model for a single order."""

    from_: str = Field(alias="from", description="Origin star ID")
    to: str = Field(description="Destination star ID")
    ships: int = Field(gt=0, description="Number of ships to move (must be > 0)")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("from_", "to")
    @classmethod
    def uppercase_star(cls, v: str) -> str:
        """Convert star IDs to uppercase."""
        return v.upper()


class ProposeOrdersInput(BaseModel):
    """Input for propose_orders tool."""

    draft_orders: List[OrderModel] = Field(
        description="List of draft orders to validate"
    )


class SubmitOrdersInput(BaseModel):
    """Input for submit_orders tool."""

    orders: List[OrderModel] = Field(description="List of orders to submit")


class MemoryQueryInput(BaseModel):
    """Input for memory_query tool."""

    table: Literal["battle_log", "discovery_log"] = Field(
        description="Memory table name"
    )
    filter_dict: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional filter criteria as key-value pairs"
    )




# ========== Output Models ==========


class StarObservation(BaseModel):
    """Model for a star in observation output."""

    id: str
    x: int
    y: int
    letter: str
    name: str
    owner: Optional[str]
    known_ru: Optional[int]
    last_seen_control: str
    is_home: bool
    stationed_ships: Optional[
        int
    ]  # Ships at this star (only for owned stars, fog-of-war)
    distance_from_home: int  # Chebyshev distance from your home star (for quick sorting)


class FleetObservation(BaseModel):
    """Model for a fleet in observation output."""

    id: str
    ships: int
    origin: str
    dest: str
    dist_remaining: int


class ArrivalObservation(BaseModel):
    """Model for fleet arrival."""

    fleet_id: str
    dest: str


class ProductionReport(BaseModel):
    """Model for production report entry."""

    star: str
    ships_produced: int


class RebellionReport(BaseModel):
    """Model for rebellion report entry."""

    star: str
    star_name: str
    ru: int
    garrison_before: int
    rebel_ships: int
    outcome: str
    garrison_after: int
    rebel_survivors: int


class HyperspaceLossReport(BaseModel):
    """Model for hyperspace loss report entry."""

    fleet_id: str
    origin: str
    dest: str
    ships_lost: int


class CombatReport(BaseModel):
    """Model for combat report entry with enhanced attacker/defender schema.

    Fields:
        star: Star letter identifier (e.g., "K")
        attacker: "me", "opp", or "npc" - who initiated the attack (arrived this turn)
        defender: "me", "opp", or "npc" - who was defending (garrison already present)
        attacker_ships_before: Attacker fleet size before combat
        defender_ships_before: Defender fleet size before combat
        attacker_losses: Ships lost by attacker
        defender_losses: Ships lost by defender
        control_before: Star owner before combat ("me", "opp", "npc", or None for uncontrolled)
        control_after: Star owner after combat ("me", "opp", "npc", or None)
    """

    star: str
    attacker: Literal["me", "opp", "npc"]
    defender: Literal["me", "opp", "npc"]
    attacker_ships_before: int
    defender_ships_before: int
    attacker_losses: int
    defender_losses: int
    control_before: Optional[Literal["me", "opp", "npc"]]
    control_after: Optional[Literal["me", "opp", "npc"]]


class StrategicDashboard(BaseModel):
    """Model for strategic at-a-glance metrics."""

    total_ships_stationed: int  # Sum of ships at all controlled stars
    total_ships_in_transit: int  # Sum of ships in all my fleets
    total_ships: int  # Total military power (stationed + in transit)
    total_production_per_turn: int  # Sum of RU from controlled stars
    controlled_stars_count: int  # Number of stars controlled
    stars_by_ru: Dict[int, int]  # Distribution: {1: 2, 2: 1, 3: 0, 4: 1} = 2 one-RU stars, 1 two-RU star, etc.
    fleet_count: int  # Number of fleets in transit
    avg_fleet_size: float  # Average ships per fleet (0 if no fleets)


class GameRules(BaseModel):
    """Model for game rules."""

    hyperspace_loss: float
    rebellion_chance: float
    production_formula: str  # Explicit formula: "ships_per_turn = star_ru"


class ObservationOutput(BaseModel):
    """Output for get_observation tool."""

    turn: int
    seed: int
    grid: Dict[str, int]
    strategic_dashboard: StrategicDashboard
    stars: List[StarObservation]
    my_fleets: List[FleetObservation]
    arrivals_this_turn: List[ArrivalObservation]
    combats_last_turn: List[CombatReport]
    combats_last_5_turns: List[List[CombatReport]]
    rebellions_last_turn: List[RebellionReport]
    hyperspace_losses_last_turn: List[HyperspaceLossReport]
    production_report: List[ProductionReport]
    rules: GameRules


class AsciiMapOutput(BaseModel):
    """Output for get_ascii_map tool."""

    map: str


class StarQueryOutput(BaseModel):
    """Output for query_star tool."""

    id: str
    name: str
    x: int
    y: int
    visited: bool
    known_ru: Optional[int]
    owner: Optional[str]
    last_seen_control: str
    stationed_ships: Optional[
        int
    ]  # Ships at this star (only for owned stars, fog-of-war)
    distances_from_my_stars: Dict[str, int]
    note: Optional[str] = None


class RouteEstimate(BaseModel):
    """Output for estimate_route tool."""

    distance: int = Field(ge=0, description="Chebyshev distance between stars (8-directional movement)")
    risk: float = Field(
        ge=0.0, le=1.0, description="Cumulative hyperspace loss probability"
    )


class GarrisonWarning(BaseModel):
    """Warning about potential garrison risk after orders execute."""

    star_id: str
    star_name: str
    current_garrison: int
    ships_after_orders: int
    required_ru: int
    deficit: int
    rebellion_chance: float = 0.5
    message: str


class ValidationResult(BaseModel):
    """Output for propose_orders tool."""

    ok: bool
    errors: Optional[List[str]] = None
    warnings: List[GarrisonWarning] = []


class SubmitOrdersOutput(BaseModel):
    """Output for submit_orders tool."""

    status: str
    order_count: int
    turn: int


class MemoryQueryOutput(BaseModel):
    """Output for memory_query tool."""

    records: List[Dict[str, Any]]




class BedrockResponse(BaseModel):
    """Model for Bedrock API response.

    The response field can be either:
    - A string (for final text responses)
    - A list of content blocks (for tool_use responses)
    """

    response: Union[str, List[Dict[str, Any]]]
    content_blocks: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    stop_reason: str
    requires_tool_execution: bool


# ========== Tool Registry ==========


TOOL_REGISTRY = {
    "get_observation": {
        "input_model": GetObservationInput,
        "output_model": ObservationOutput,
        "description": "Get current game state observation for Player 2 with fog-of-war filtering. Returns turn number, STRATEGIC DASHBOARD (at-a-glance metrics: total ships, production, fleet distribution), stars (SORTED BY DISTANCE from your home star - closest first, each with distance_from_home field showing Chebyshev distance), fleets, arrivals, combats (current turn + last 5 turns history), rebellions, hyperspace losses (YOUR fleets only), production, and game rules. STARS: Sorted by distance_from_home (closest first) for easy target selection. Each star includes distance_from_home field - use this to identify nearby expansion targets without calling estimate_route. STRATEGIC DASHBOARD: Provides aggregate metrics (total_ships, total_production_per_turn, controlled_stars_count, stars_by_ru distribution) for quick strategic assessment. COMBAT HISTORY: combats_last_5_turns provides up to 5 turns of combat history (oldest to newest) for strategic pattern analysis. PRODUCTION RULE: Each controlled star produces ships equal to its RU value per turn (added to stationed_ships during production phase). HYPERSPACE LOSSES: Each fleet has 2% chance per turn to be destroyed in hyperspace.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    "get_ascii_map": {
        "input_model": GetAsciiMapInput,
        "output_model": AsciiMapOutput,
        "description": "Get ASCII representation of the game map from Player 2's perspective. Shows star positions, ownership, and known RU values. Unknown RU shown as '?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "view": {
                    "type": "string",
                    "description": "Map view mode (only 'current' supported)",
                    "default": "current",
                }
            },
            "required": [],
        },
    },
    "query_star": {
        "input_model": QueryStarInput,
        "output_model": StarQueryOutput,
        "description": "Query detailed information about a specific star. Returns coordinates, distances, and (if visited) RU and ownership. For stars YOU CONTROL, also returns stationed_ships count showing your garrison. Enemy/NPC garrison counts are not visible (fog-of-war) unless revealed through combat reports.",
        "input_schema": {
            "type": "object",
            "properties": {
                "star_ref": {
                    "type": "string",
                    "description": "Star ID or letter to query (e.g., 'A', 'P')",
                }
            },
            "required": ["star_ref"],
        },
    },
    "estimate_route": {
        "input_model": EstimateRouteInput,
        "output_model": RouteEstimate,
        "description": "Calculate Chebyshev distance (8-directional movement, diagonal costs same as orthogonal) and cumulative hyperspace loss risk for a route between two stars. ALWAYS use this tool to calculate distances - do not estimate manually. Risk = 1 - (1-0.02)^distance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_star": {"type": "string", "description": "Origin star ID"},
                "to_star": {"type": "string", "description": "Destination star ID"},
            },
            "required": ["from_star", "to_star"],
        },
    },
    "propose_orders": {
        "input_model": ProposeOrdersInput,
        "output_model": ValidationResult,
        "description": "Validate draft orders before submission. Returns ok=true if orders are valid, errors=[] list of validation failures, warnings=[] list of garrison risks (stars that will have garrison < RU after orders execute, 50% rebellion chance). Use this to check orders AND identify potential rebellions before committing with submit_orders(). WARNING: Multiple orders from the same star are CUMULATIVE. Example: Star B has 10 ships - CORRECT: B->A (6 ships), B->C (4 ships) = 10 total. WRONG: B->A (8 ships), B->C (5 ships) = 13 total (OVER-COMMITTED!).",
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_orders": {
                    "type": "array",
                    "description": "List of order objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string", "description": "Origin star ID"},
                            "to": {
                                "type": "string",
                                "description": "Destination star ID",
                            },
                            "ships": {
                                "type": "integer",
                                "description": "Number of ships to move",
                            },
                        },
                        "required": ["from", "to", "ships"],
                    },
                }
            },
            "required": ["draft_orders"],
        },
    },
    "submit_orders": {
        "input_model": SubmitOrdersInput,
        "output_model": SubmitOrdersOutput,
        "description": "Submit validated orders for this turn. This commits your moves and they will be executed. Can only be called once per turn.",
        "input_schema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "description": "List of order objects",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string", "description": "Origin star ID"},
                            "to": {
                                "type": "string",
                                "description": "Destination star ID",
                            },
                            "ships": {
                                "type": "integer",
                                "description": "Number of ships to move",
                            },
                        },
                        "required": ["from", "to", "ships"],
                    },
                }
            },
            "required": ["orders"],
        },
    },
    "memory_query": {
        "input_model": MemoryQueryInput,
        "output_model": MemoryQueryOutput,
        "description": "Query historical game data automatically recorded each turn. Use to learn from past player-vs-player battles and track star discoveries. Tables: 'battle_log' (PvP combat history with ships/outcome - excludes NPC battles), 'discovery_log' (when stars were first scouted with RU values). Use battle_log to identify opponent attack patterns, typical fleet sizes, and contested stars. Auto-populated each turn - no manual recording needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "Memory table name",
                    "enum": ["battle_log", "discovery_log"],
                },
                "filter_dict": {
                    "type": "object",
                    "description": "Optional filter criteria as key-value pairs",
                    "additionalProperties": True,
                },
            },
            "required": ["table"],
        },
    },
}


# Generate TOOL_DEFINITIONS for Claude API from registry
TOOL_DEFINITIONS = [
    {
        "name": tool_name,
        "description": tool_info["description"],
        "input_schema": tool_info["input_schema"],
    }
    for tool_name, tool_info in TOOL_REGISTRY.items()
]
