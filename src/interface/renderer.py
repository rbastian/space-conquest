"""ASCII map rendering with fog-of-war.

This module renders the 12x10 game grid as ASCII art, showing stars
with their RU values based on the player's fog-of-war knowledge.
"""

from typing import List

from ..models.player import Player
from ..models.star import Star


class MapRenderer:
    """Renders 12x10 ASCII map with fog-of-war."""

    def render(self, player: Player, stars: List[Star]) -> str:
        """Render ASCII map from player's perspective.

        Output format (12x10 grid, 2 chars per cell):
        .. .. ?A .. .. ?B .. .. ?C .. ..
        .. 4D .. .. ?E .. .. .. ?F .. ..
        ...

        Legend:
        - '?X' = star with unknown RU (ID is X)
        - '1A' = known star with 1 RU (ID is A)
        - '4D' = star with 4 RU (ID is D)
        - '..' = empty space
        - '*X' = your controlled star (ID is X) with known RU
        - '!X' = opponent controlled star (ID is X)

        Args:
            player: Player whose perspective to render
            stars: List of all stars in the game

        Returns:
            Multi-line ASCII art string representing the map
        """
        # Create a 12x10 grid initialized with empty spaces
        grid = [[".."] * 12 for _ in range(10)]

        # Fill in stars
        for star in stars:
            cell = self._render_star_cell(player, star)
            grid[star.y][star.x] = cell

        # Convert grid to string
        lines = []
        for row in grid:
            lines.append(" ".join(row))

        return "\n".join(lines)

    def _render_star_cell(self, player: Player, star: Star) -> str:
        """Render a single star cell based on player's knowledge.

        Args:
            player: Player whose perspective to render
            star: Star to render

        Returns:
            2-character string representing the star
        """
        star_id = star.id

        # Check if player has visited this star
        visited = star_id in player.visited_stars

        # If not visited, show ?X
        if not visited:
            return f"?{star_id}"

        # Star has been visited - show real-time info
        if star.owner == player.id:
            # Player controls this star - show with @ marker
            return f"@{star_id}"
        elif star.owner is not None:
            # Opponent controls - show with ! marker
            return f"!{star_id}"
        elif star.npc_ships > 0:
            # NPC controlled - show RU value
            return f"{star.base_ru}{star_id}"
        else:
            # Unowned - show RU value
            return f"{star.base_ru}{star_id}"

    def render_with_coords(self, player: Player, stars: List[Star]) -> str:
        """Render map with coordinate labels.

        Args:
            player: Player whose perspective to render
            stars: List of all stars in the game

        Returns:
            Map with coordinate labels on edges
        """
        map_str = self.render(player, stars)

        # Add column numbers at top
        header = "   " + " ".join(f"{i:2d}" for i in range(12))

        # Add row numbers
        lines = map_str.split("\n")
        numbered_lines = [f"{i:2d} {line}" for i, line in enumerate(lines)]

        return header + "\n" + "\n".join(numbered_lines)
