"""Pydantic models for tool input/output validation.

Provides type-safe validation for all LLM agent tools to ensure
data integrity and catch errors early in the tool execution pipeline.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ========== Input Models ==========


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


class SubmitOrdersInput(BaseModel):
    """Input for submit_orders tool."""

    orders: list[OrderModel] = Field(description="List of orders to submit")


# ========== Output Models ==========


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


class FleetSplittingWarning(BaseModel):
    """Warning about inefficient fleet splitting to same destination."""

    type: str = "fleet_splitting"
    destination: str
    destination_name: str
    fleets: list[dict[str, Any]]
    total_ships: int
    message: str


class ValidationResult(BaseModel):
    """Output for propose_orders tool."""

    ok: bool
    errors: list[str] | None = None
    warnings: list[dict[str, Any]] = []


class SubmitOrdersOutput(BaseModel):
    """Output for submit_orders tool."""

    status: str
    order_count: int
    turn: int


class BedrockResponse(BaseModel):
    """Model for Bedrock API response.

    The response field can be either:
    - A string (for final text responses)
    - A list of content blocks (for tool_use responses)
    """

    response: str | list[dict[str, Any]]
    content_blocks: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    stop_reason: str
    requires_tool_execution: bool


# ========== Tool Registry ==========


TOOL_REGISTRY = {
    "submit_orders": {
        "input_model": SubmitOrdersInput,
        "output_model": SubmitOrdersOutput,
        "description": "Validate and submit your orders for this turn. This is the ONLY way to submit orders - you must call this tool. The tool will first validate your orders (check for errors like over-committing ships or invalid destinations) and if validation passes, will submit them for execution. Returns status, order_count, and turn number. WARNING: Multiple orders from the same star are CUMULATIVE. Example: Star B has 10 ships - CORRECT: B->A (6 ships), B->C (4 ships) = 10 total. WRONG: B->A (8 ships), B->C (5 ships) = 13 total (OVER-COMMITTED!). Can only be called once per turn.",
        "input_schema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "description": "List of order objects to validate and submit",
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
