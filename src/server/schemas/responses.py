"""Pydantic response schemas for API endpoints."""

from pydantic import BaseModel, Field


class GameStateResponse(BaseModel):
    """Response containing current game state."""

    gameId: str  # noqa: N815
    turn: int
    phase: str
    winner: str | None
    state: dict
    events: dict | None = None


class CreateGameResponse(BaseModel):
    """Response after creating a new game."""

    gameId: str  # noqa: N815
    humanPlayer: str  # noqa: N815
    aiPlayer: str  # noqa: N815
    seed: int
    state: dict


class SubmitOrdersResponse(BaseModel):
    """Response after submitting orders."""

    accepted: bool
    turn: int | None = None
    errors: list[str] = Field(default_factory=list)
    winner: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    details: dict | None = None
