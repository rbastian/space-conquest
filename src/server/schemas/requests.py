"""Pydantic request schemas for API endpoints."""

from pydantic import BaseModel, Field


class CreateGameRequest(BaseModel):
    """Request to create a new game."""

    humanPlayer: str = Field(  # noqa: N815
        default="p1", description="Which player is human: 'p1' or 'p2'"
    )
    seed: int | None = Field(default=None, description="Optional RNG seed for determinism")
    aiProvider: str = Field(  # noqa: N815
        default="bedrock", description="AI LLM provider: 'bedrock', 'openai', 'anthropic'"
    )
    aiModel: str | None = Field(  # noqa: N815
        default=None, description="Optional model name (provider-specific)"
    )


class OrderRequest(BaseModel):
    """Single move order."""

    type: str = Field(default="MOVE", description="Order type (currently only MOVE)")
    ships: int = Field(gt=0, description="Number of ships to move")
    from_star: str = Field(alias="from", description="Origin star ID")
    to_star: str = Field(alias="to", description="Destination star ID")

    class Config:
        populate_by_name = True


class SubmitOrdersRequest(BaseModel):
    """Request to submit player orders."""

    orders: list[dict] = Field(description="List of move orders with keys: ships, from, to")
