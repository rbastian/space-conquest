"""Player naming utilities for display layer.

Provides functions to generate admiral names for LLM opponents and
get display names for players in the UI.
"""

from random import Random

# Admiral surname pool (10 names)
ADMIRAL_SURNAMES = [
    "Krios",  # Greek-inspired, commanding
    "Vex",  # Sharp, tactical, ominous
    "Thalion",  # Elvish-inspired, noble
    "Dravin",  # Strong, authoritative
    "Seris",  # Elegant, strategic
    "Korvan",  # Military, disciplined
    "Nexus",  # Sci-fi, interconnected intelligence
    "Rylon",  # Clean, futuristic
    "Thane",  # Noble title, historical gravitas
    "Vorel",  # Mysterious, alien
]


def extract_model_name(model_id: str) -> str:
    """Extract model name from Bedrock model ID.

    Extracts the model family name (Sonnet, Haiku, Opus) from full
    Bedrock model IDs like "us.anthropic.claude-3-5-sonnet-20241022-v1:0".

    Args:
        model_id: Full model ID from Bedrock

    Returns:
        Capitalized model name: "Sonnet", "Haiku", "Opus", or "Claude" as fallback

    Examples:
        >>> extract_model_name("us.anthropic.claude-3-5-sonnet-20241022-v1:0")
        'Sonnet'
        >>> extract_model_name("claude-3-haiku-20240307-v1:0")
        'Haiku'
        >>> extract_model_name("unknown-model-id")
        'Claude'
    """
    model_lower = model_id.lower()
    if "sonnet" in model_lower:
        return "Sonnet"
    elif "haiku" in model_lower:
        return "Haiku"
    elif "opus" in model_lower:
        return "Opus"
    return "Claude"  # Generic fallback for unknown models


def select_admiral_name(game_seed: int, model_id: str) -> str:
    """Generate admiral name from game seed and model ID.

    Uses seed-based selection to deterministically generate a unique admiral
    name for each game. Same seed + same model always produces the same name,
    enabling reproducibility and consistency within a game session.

    Args:
        game_seed: Game seed for reproducibility
        model_id: LLM model ID (used to extract model name)

    Returns:
        Full display name in format: "Admiral [Model] [Surname]"

    Examples:
        >>> select_admiral_name(42, "us.anthropic.claude-3-5-sonnet-20241022-v1:0")
        'Admiral Sonnet Krios'
        >>> select_admiral_name(42, "claude-3-haiku-20240307-v1:0")
        'Admiral Haiku Krios'
        >>> select_admiral_name(123, "claude-3-5-sonnet-20241022-v1:0")
        'Admiral Sonnet Vex'
    """
    model_name = extract_model_name(model_id)
    rng = Random(game_seed)
    surname = rng.choice(ADMIRAL_SURNAMES)

    return f"Admiral {model_name} {surname}"


def get_player_display_name(
    player_id: str, game_seed: int | None = None, model_id: str | None = None
) -> str:
    """Get display name for a player.

    Transforms internal player IDs ("p1", "p2") into user-friendly display names.
    - p1: "Commander" (human player designation)
    - p2: "Admiral [Model] [Surname]" (LLM opponent with personality)

    Args:
        player_id: Internal player ID ("p1" or "p2")
        game_seed: Game seed (required for p2)
        model_id: Model ID (required for p2)

    Returns:
        Display name for UI presentation

    Examples:
        >>> get_player_display_name("p1")
        'Commander'
        >>> get_player_display_name("p2", 42, "claude-3-5-sonnet-20241022-v1:0")
        'Admiral Sonnet Krios'
        >>> get_player_display_name("p2")  # Missing seed/model
        'p2'
    """
    if player_id == "p1":
        return "Commander"
    elif player_id == "p2" and game_seed is not None and model_id is not None:
        return select_admiral_name(game_seed, model_id)
    return player_id  # Fallback to raw ID if parameters missing
