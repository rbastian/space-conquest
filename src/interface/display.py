"""Turn information display for human players.

This module displays game state information including controlled stars,
fleets in transit, and combat results.
"""

from typing import List, Optional, TYPE_CHECKING

from ..models.game import Game
from ..models.player import Player
from ..models.star import Star
from ..utils.naming import get_player_display_name

if TYPE_CHECKING:
    from ..engine.combat import CombatEvent, RebellionEvent
    from ..engine.movement import HyperspaceLoss
else:
    # Import for runtime
    from ..engine.combat import CombatEvent, RebellionEvent
    from ..engine.movement import HyperspaceLoss


# Event report emoji prefixes for visual differentiation
REPORT_EMOJIS = {
    "combat": "⚔️",
    "rebellion": "🔥",
    "hyperspace_loss": "⚡",
    "arrival": "📍",
    "production": "⚙️",
}


class DisplayManager:
    """Manages turn information display."""

    def _player_participated_in_combat(
        self, event: "CombatEvent", player_id: str
    ) -> bool:
        """Check if player participated in combat (fog-of-war filter).

        Args:
            event: Combat event to check
            player_id: Player ID to check participation for

        Returns:
            True if player participated (as attacker or defender)
        """
        if event.combat_type == "npc":
            # NPC combat: player participated if they were attacker
            # or if it was a combined attack (both players vs NPC)
            return event.attacker == player_id or event.attacker == "combined"
        elif event.combat_type == "pvp":
            # PvP combat: player participated if attacker or defender
            return event.attacker == player_id or event.defender == player_id
        return False

    def _get_display_name(self, player_id: str, game: Game) -> str:
        """Get display name for a player ID.

        Args:
            player_id: Internal player ID ("p1" or "p2")
            game: Current game state (for seed and model ID)

        Returns:
            Display name for UI presentation
        """
        return get_player_display_name(player_id, game.seed, game.p2_model_id)

    def show_turn_summary(
        self,
        player: Player,
        game: Game,
        combat_events: Optional[List["CombatEvent"]] = None,
        hyperspace_losses: Optional[List["HyperspaceLoss"]] = None,
        rebellion_events: Optional[List["RebellionEvent"]] = None,
    ) -> None:
        """Display comprehensive turn summary.

        Shows:
        - Current turn number with player name
        - Combat reports (if provided)
        - Hyperspace losses (if provided)
        - Rebellion reports (if provided)
        - Controlled stars with ship counts
        - Fleets in transit

        Args:
            player: Player whose perspective to show
            game: Current game state
            combat_events: Optional list of combat events from last turn
            hyperspace_losses: Optional list of hyperspace losses from last turn
            rebellion_events: Optional list of rebellion events from last turn
        """
        display_name = self._get_display_name(player.id, game)
        print(f"\n{'=' * 60}")
        print(f"Turn {game.turn} - {display_name}")
        print(f"{'=' * 60}\n")

        # Display reports (if provided)
        if combat_events:
            self.display_combat_results(combat_events, game, player.id)
        if hyperspace_losses:
            self.display_hyperspace_losses(hyperspace_losses, game)
        if rebellion_events:
            self.display_rebellion_results(rebellion_events, player.id, game)

        self._show_controlled_stars(player, game)
        self._show_fleets_in_transit(player, game)

    def _show_controlled_stars(self, player: Player, game: Game) -> None:
        """Display stars controlled by player with ship counts in table format.

        Args:
            player: Player whose stars to show
            game: Current game state
        """
        controlled_stars = [star for star in game.stars if star.owner == player.id]

        if not controlled_stars:
            print("Your Controlled Stars: None\n")
            return

        print("Your Controlled Stars:")

        # Table header (4 columns: Code, Star Name, Resources, Ships)
        print("┌──────┬─────────────────────┬───────────┬───────┐")
        print("│ Code │ Star Name           │ Resources │ Ships │")
        print("├──────┼─────────────────────┼───────────┼───────┤")

        # Table rows
        total_ships = 0
        total_resources = 0
        for star in controlled_stars:
            ships = star.stationed_ships.get(player.id, 0)
            total_ships += ships
            total_resources += star.base_ru

            # Format code column (6 chars, centered)
            code_col = self._format_centered(star.id, 6)

            # Format star name column with home indicator (21 chars, left-aligned)
            star_name = star.name
            if star.id == player.home_star:
                try:
                    # Try to use the house emoji (U+1F3E0)
                    star_name = f"\U0001F3E0 {star.name}"
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Fallback to simple star character if emoji fails
                    star_name = f"* {star.name}"
            star_name_col = self._format_left(star_name, 21)

            # Format resources column (11 chars, right-aligned)
            resources_col = self._format_right(f"{star.base_ru} RU", 11)

            # Format ships column (7 chars, right-aligned)
            ships_col = self._format_right(str(ships), 7)

            print(f"│{code_col}│{star_name_col}│{resources_col}│{ships_col}│")

        # Add footer separator (after all data rows)
        print("├──────┼─────────────────────┼───────────┼───────┤")

        # Add footer row with column-aligned totals
        code_cell = " " * 6
        name_cell = "TOTAL" + " " * 16  # "TOTAL" left-aligned in 21-char field
        ru_cell = f"{total_resources} RU".rjust(11)
        ships_cell = str(total_ships).rjust(7)

        print(f"│{code_cell}│{name_cell}│{ru_cell}│{ships_cell}│")

        # Table footer
        print("└──────┴─────────────────────┴───────────┴───────┘")
        print()

    def _format_centered(self, text: str, width: int) -> str:
        """Center text within specified width.

        Args:
            text: Text to center
            width: Total width including text

        Returns:
            Centered text padded to width
        """
        text_str = str(text)
        # Calculate display width accounting for emojis (they take 2 columns each)
        display_width = self._calculate_display_width(text_str)

        if display_width >= width:
            # Truncate if too long - need to be careful with emojis
            return self._truncate_to_width(text_str, width)

        total_padding = width - display_width
        left_padding = total_padding // 2
        right_padding = total_padding - left_padding

        return " " * left_padding + text_str + " " * right_padding

    def _format_left(self, text: str, width: int) -> str:
        """Left-align text within specified width.

        Args:
            text: Text to align
            width: Total width including text

        Returns:
            Left-aligned text padded to width
        """
        text_str = str(text)
        # Calculate display width accounting for emojis (they take 2 columns each)
        display_width = self._calculate_display_width(text_str)

        if display_width >= width:
            # Truncate if too long - need to be careful with emojis
            return self._truncate_to_width(text_str, width)

        return text_str + " " * (width - display_width)

    def _format_right(self, text: str, width: int) -> str:
        """Right-align text within specified width.

        Args:
            text: Text to align
            width: Total width including text

        Returns:
            Right-aligned text padded to width
        """
        text_str = str(text)
        # Calculate display width accounting for emojis (they take 2 columns each)
        display_width = self._calculate_display_width(text_str)

        if display_width >= width:
            # Truncate if too long - need to be careful with emojis
            return self._truncate_to_width(text_str, width)

        return " " * (width - display_width) + text_str

    def _calculate_display_width(self, text: str) -> int:
        """Calculate the display width of text accounting for wide characters.

        Emojis and some Unicode characters take 2 terminal columns instead of 1.
        This method counts the actual display width.

        Args:
            text: Text to measure

        Returns:
            Display width in terminal columns
        """
        width = 0
        for char in text:
            code_point = ord(char)
            # Check if character is a wide emoji or symbol
            # Common emoji ranges:
            # - 0x2600-0x26FF: Miscellaneous Symbols (⚠️, etc.)
            # - 0x2700-0x27BF: Dingbats
            # - 0x2B50: Star emoji (⭐)
            # - 0x1F300-0x1F9FF: Emoji blocks
            # - 0xFE00-0xFE0F: Variation selectors (don't add width)
            if code_point >= 0xFE00 and code_point <= 0xFE0F:
                # Variation selectors don't add display width
                continue
            elif (
                (code_point >= 0x2600 and code_point <= 0x27BF)
                or code_point == 0x2B50  # Star emoji
                or (code_point >= 0x1F300 and code_point <= 0x1F9FF)
            ):
                # Wide emoji - takes 2 columns
                width += 2
            else:
                # Regular character - takes 1 column
                width += 1
        return width

    def _truncate_to_width(self, text: str, max_width: int) -> str:
        """Truncate text to fit within specified display width.

        Accounts for emoji widths when truncating.

        Args:
            text: Text to truncate
            max_width: Maximum display width

        Returns:
            Truncated text that fits within max_width
        """
        result = []
        current_width = 0

        for char in text:
            code_point = ord(char)
            # Calculate width this character will add
            if code_point >= 0xFE00 and code_point <= 0xFE0F:
                # Variation selectors don't add width
                char_width = 0
            elif (
                (code_point >= 0x2600 and code_point <= 0x27BF)
                or code_point == 0x2B50  # Star emoji
                or (code_point >= 0x1F300 and code_point <= 0x1F9FF)
            ):
                # Wide emoji
                char_width = 2
            else:
                # Regular character
                char_width = 1

            if current_width + char_width > max_width:
                break

            result.append(char)
            current_width += char_width

        return "".join(result)

    def _show_fleets_in_transit(self, player: Player, game: Game) -> None:
        """Display player's fleets currently in hyperspace in table format.

        Args:
            player: Player whose fleets to show
            game: Current game state
        """
        player_fleets = [f for f in game.fleets if f.owner == player.id]

        if not player_fleets:
            print("Fleets in Hyperspace: (none)\n")
            return

        # Sort fleets by arrival turn (ascending), then by fleet ID
        sorted_fleets = sorted(
            player_fleets, key=lambda f: (f.dist_remaining, f.id)
        )

        print("Fleets in Hyperspace:")

        # Table header
        print("┌──────────┬───────┬────────┬──────┬─────────┐")
        print("│ Fleet ID │ Ships │ Origin │ Dest │ Arrives │")
        print("├──────────┼───────┼────────┼──────┼─────────┤")

        # Table rows
        for fleet in sorted_fleets:
            fleet_id_col = self._format_left(fleet.id, 10)
            ships_col = self._format_right(str(fleet.ships), 7)
            origin_col = self._format_centered(fleet.origin, 8)
            dest_col = self._format_centered(fleet.dest, 6)

            # Calculate absolute turn number
            # Note: We display the state AFTER Phases 1-3 have run. The turn counter has
            # already incremented. A fleet with dist_remaining=1 will arrive NEXT turn (in Phase 1).
            # Formula: current_turn + dist_remaining
            arrival_turn = game.turn + fleet.dist_remaining

            # Make it clearer whether fleet arrives NEXT turn or a FUTURE turn
            # Use arrow symbol to indicate "arriving next turn"
            if arrival_turn == game.turn + 1:
                arrives_text = f"Turn {arrival_turn} →"
            else:
                arrives_text = f"Turn {arrival_turn}"
            arrives_col = self._format_left(arrives_text, 9)

            print(f"│{fleet_id_col}│{ships_col}│{origin_col}│{dest_col}│{arrives_col}│")

        # Table footer
        print("└──────────┴───────┴────────┴──────┴─────────┘")
        print()

    # NOTE: _show_production_summary removed as redundant (2025-10-18)
    # Production information is already displayed in the Controlled Stars table footer
    # as "Total: X stars, Y RU/turn, Z ships stationed"
    # Keeping this commented out for reference in case we need to restore it.
    #
    # def _show_production_summary(self, player: Player, game: Game) -> None:
    #     """Display production capacity summary.
    #
    #     Args:
    #         player: Player whose production to show
    #         game: Current game state
    #     """
    #     controlled_stars = [star for star in game.stars if star.owner == player.id]
    #
    #     if not controlled_stars:
    #         print("Production: 0 ships/turn\n")
    #         return
    #
    #     total_production = sum(star.base_ru for star in controlled_stars)
    #     print(f"Production: {total_production} ships/turn")
    #     print(f"  (from {len(controlled_stars)} controlled star(s))\n")

    def show_help(self) -> None:
        """Display help information for human players."""
        print("\n=== Space Conquest - Command Help ===\n")
        print("Commands:")
        print(
            "  move <ships> from <star> to <star>  - Send ships from one star to another"
        )
        print("  pass                                 - End turn without moving")
        print("  help                                 - Show this help message")
        print("  status                               - Show current game state")
        print("  quit                                 - Exit the game")
        print()
        print("Examples:")
        print("  move 5 ships from A to B")
        print("  move 10 from C to D")
        print("  move 3 from A to C")
        print()
        print("Map Legend:")
        print("  ?X  - Star X with unknown RU")
        print("  1A  - Star A with 1 RU (NPC or unowned)")
        print("  @A  - Star A controlled by you")
        print("  !A  - Star A controlled by opponent")
        print("  ..  - Empty space")
        print()

    def show_victory(self, game: Game) -> None:
        """Display victory message.

        Args:
            game: Game state with winner set
        """
        print(f"\n{'=' * 60}")
        print("GAME OVER")
        print(f"{'=' * 60}\n")

        if game.winner == "draw":
            print("The game ended in a DRAW!")
            print("Both players captured each other's home stars simultaneously.")
        elif game.winner in ("p1", "p2"):
            winner_name = self._get_display_name(game.winner, game)
            loser = "p2" if game.winner == "p1" else "p1"
            loser_name = self._get_display_name(loser, game)
            print(f"{winner_name} WINS!")
            print(f"Victory achieved by capturing {loser_name}'s home star!")
        else:
            print("Game ended with unknown result.")

        print(f"\nGame lasted {game.turn} turns.")
        print()

    def show_enhanced_victory(
        self,
        game: Game,
        combat_events: List["CombatEvent"],
        hyperspace_losses: List["HyperspaceLoss"],
        rebellion_events: List["RebellionEvent"],
    ) -> None:
        """Display enhanced victory screen with final turn events and statistics.

        Shows:
        1. Dramatic victory header
        2. Final turn events (home star battles, other combats, arrivals, production)
        3. Final map state with no fog-of-war
        4. Comparative statistics table
        5. Game metadata

        Args:
            game: Final game state with winner set
            combat_events: Combat events from final turn
            hyperspace_losses: Hyperspace losses from final turn
            rebellion_events: Rebellion events from final turn
        """
        # Import here to avoid circular dependency

        print("\n" + "=" * 60)
        print("CONQUEST COMPLETE")
        print("=" * 60 + "\n")

        # Display dramatic victory message
        self._show_victory_message(game)

        # Display final turn events
        self._show_final_turn_events(
            game, combat_events, hyperspace_losses, rebellion_events
        )

        # Display final map state (no fog-of-war)
        self._show_final_map(game)

        # Display comparative statistics
        self._show_statistics_table(game)

        # Display game metadata
        print(f"\nGame Duration: {game.turn} turns")
        print(f"Seed: {game.seed}")
        print()

    def _show_victory_message(self, game: Game) -> None:
        """Display dramatic victory-specific message.

        Args:
            game: Final game state with winner set
        """
        if game.winner == "draw":
            print("MUTUAL CONQUEST ACHIEVED!")
            p1_name = self._get_display_name("p1", game)
            p2_name = self._get_display_name("p2", game)
            print(
                f"{p1_name} and {p2_name} captured their opponent's home star in a simultaneous strike."
            )
            print("History will remember this as a legendary stalemate.\n")
        elif game.winner in ("p1", "p2"):
            winner_name = self._get_display_name(game.winner, game)
            loser = "p2" if game.winner == "p1" else "p1"
            loser_name = self._get_display_name(loser, game)

            # Find the captured home star
            loser_home = game.players[loser].home_star
            captured_star = None
            for star in game.stars:
                if star.id == loser_home:
                    captured_star = star
                    break

            print(f"{winner_name} achieves DECISIVE VICTORY over {loser_name}!")
            if captured_star:
                print(f"The assault on {captured_star.name} ({loser_home}) succeeded—")
                print("the enemy empire has fallen.\n")
            else:
                print("The enemy empire has fallen!\n")
        else:
            print("Game ended with unknown result.\n")

    def _show_final_turn_events(
        self,
        game: Game,
        combat_events: List["CombatEvent"],
        hyperspace_losses: List["HyperspaceLoss"],
        rebellion_events: List["RebellionEvent"],
    ) -> None:
        """Display events from the final turn.

        Priority order:
        1. Home star battles (with special formatting)
        2. Other combats
        3. Fleet arrivals
        4. Rebellions
        5. Production summary

        Args:
            game: Final game state
            combat_events: Combat events from final turn
            hyperspace_losses: Hyperspace losses from final turn
            rebellion_events: Rebellion events from final turn
        """
        print("--- THE CLIMACTIC FINAL TURN ---\n")

        # Identify home stars
        p1_home = game.players["p1"].home_star
        p2_home = game.players["p2"].home_star
        home_stars = {p1_home, p2_home}

        # Separate home star battles from other combats
        home_battles = [e for e in combat_events if e.star_id in home_stars]
        other_combats = [e for e in combat_events if e.star_id not in home_stars]

        # Display home star battles with special formatting
        if home_battles:
            for event in home_battles:
                self._display_home_star_battle(event, game)

        # Display other combats briefly
        if other_combats:
            print("Other Battles:")
            for event in other_combats:
                if event.combat_type == "pvp":
                    attacker_name = self._get_display_name(event.attacker, game)
                    defender_name = self._get_display_name(event.defender, game)
                    print(
                        f"  {REPORT_EMOJIS['combat']} {event.star_id} ({event.star_name}): "
                        f"{attacker_name} {event.attacker_ships} vs "
                        f"{defender_name} {event.defender_ships} "
                        f"-> {attacker_name if event.winner == 'attacker' else (defender_name if event.winner == 'defender' else 'tie')} wins"
                    )
                else:
                    attacker_label = (
                        "Combined forces"
                        if event.attacker == "combined"
                        else self._get_display_name(event.attacker, game)
                    )
                    print(
                        f"  {REPORT_EMOJIS['combat']} {event.star_id} ({event.star_name}): "
                        f"{attacker_label} {event.attacker_ships} vs "
                        f"NPC {event.defender_ships} "
                        f"-> {attacker_label if event.winner == 'attacker' else 'NPC'} wins"
                    )
            print()

        # Display fleet arrivals
        self._show_fleet_arrivals(game)

        # Display rebellions
        if rebellion_events:
            print("Rebellions:")
            for event in rebellion_events:
                owner_name = self._get_display_name(event.owner, game)
                outcome_str = (
                    "lost to rebels" if event.outcome == "lost" else "crushed rebellion"
                )
                print(
                    f"  {REPORT_EMOJIS['rebellion']} {event.star} ({event.star_name}): "
                    f"{owner_name} {outcome_str} "
                    f"({event.garrison_before} vs {event.rebel_ships} rebels)"
                )
            print()

        # Display production summary
        self._show_final_production_summary(game)

    def _display_home_star_battle(self, event: "CombatEvent", game: Game) -> None:
        """Display a home star battle with enhanced formatting.

        Args:
            event: Combat event at a home star
            game: Current game state
        """
        combat_emoji = REPORT_EMOJIS["combat"]
        print(
            f"{combat_emoji} HOME STAR BATTLE at {event.star_id} ({event.star_name}) {combat_emoji}"
        )

        if event.combat_type == "pvp":
            attacker_name = self._get_display_name(event.attacker, game)
            defender_name = self._get_display_name(event.defender, game)
            print(f"  Attacker: {attacker_name} with {event.attacker_ships} ships")
            print(f"  Defender: {defender_name} with {event.defender_ships} ships")
            print(
                f"  Result: {attacker_name} {event.attacker_losses} casualties, "
                f"{defender_name} {event.defender_losses} casualties"
            )

            if event.winner == "attacker":
                print(
                    f"  {attacker_name} VICTORIOUS with {event.attacker_survivors} ships remaining!"
                )
            elif event.winner == "defender":
                print(
                    f"  {defender_name} HOLDS THE LINE with {event.defender_survivors} ships remaining!"
                )
            else:
                print("  MUTUAL DESTRUCTION - Both forces eliminated!")

            # Check if this resulted in game over
            p1_home = game.players["p1"].home_star

            # Determine if this battle captured a home star
            home_owner = "p1" if event.star_id == p1_home else "p2"
            captured = (
                event.winner == "attacker" and event.attacker != home_owner
            ) or (event.winner == "defender" and event.defender != home_owner)
            if captured:
                print("  >>> HOME STAR CAPTURED - GAME OVER <<<")
        else:
            # NPC combat at home star (shouldn't happen, but handle it)
            attacker_label = (
                "Combined forces" if event.attacker == "combined" else event.attacker
            )
            print(f"  Attacker: {attacker_label} with {event.attacker_ships} ships")
            print(f"  Defender: NPC with {event.defender_ships} ships")
            print(f"  Result: {event.winner or 'tie'} wins")

        print()

    def _show_fleet_arrivals(self, game: Game) -> None:
        """Display which fleets would have arrived next turn.

        Since the game ended, we show fleets that are 1 turn away from arrival.

        Args:
            game: Final game state
        """
        arriving_soon = [f for f in game.fleets if f.dist_remaining == 1]

        if arriving_soon:
            print("Fleets Arriving Next Turn (never made it):")
            for fleet in arriving_soon:
                owner_name = self._get_display_name(fleet.owner, game)
                print(
                    f"  {REPORT_EMOJIS['arrival']} {owner_name}: {fleet.ships} ships "
                    f"from {fleet.origin} to {fleet.dest}"
                )
            print()

    def _show_final_production_summary(self, game: Game) -> None:
        """Display production summary by player for final turn.

        Args:
            game: Final game state
        """
        p1_stars = [s for s in game.stars if s.owner == "p1"]
        p2_stars = [s for s in game.stars if s.owner == "p2"]

        p1_production = sum(
            4 if s.id == game.players["p1"].home_star else s.base_ru for s in p1_stars
        )
        p2_production = sum(
            4 if s.id == game.players["p2"].home_star else s.base_ru for s in p2_stars
        )

        if p1_production > 0 or p2_production > 0:
            print("Final Turn Production:")
            if p1_production > 0:
                p1_name = self._get_display_name("p1", game)
                print(
                    f"  {REPORT_EMOJIS['production']} {p1_name}: {p1_production} ships produced"
                )
            if p2_production > 0:
                p2_name = self._get_display_name("p2", game)
                print(
                    f"  {REPORT_EMOJIS['production']} {p2_name}: {p2_production} ships produced"
                )
            print()

    def _show_final_map(self, game: Game) -> None:
        """Display final map state with NO fog-of-war.

        Shows all stars with their true ownership.

        Args:
            game: Final game state
        """
        print("--- FINAL MAP STATE ---")
        print("(All territories revealed)\n")

        # Create a grid to show all stars without fog-of-war
        grid = [[".."] * 12 for _ in range(10)]

        for star in game.stars:
            if star.owner == "p1":
                cell = f"@{star.id}"
            elif star.owner == "p2":
                cell = f"#{star.id}"
            elif star.npc_ships > 0:
                cell = f"{star.base_ru}{star.id}"
            else:
                cell = f"{star.base_ru}{star.id}"
            grid[star.y][star.x] = cell

        # Print grid
        for row in grid:
            print(" ".join(row))

        # Print legend
        p1_name = self._get_display_name("p1", game)
        p2_name = self._get_display_name("p2", game)
        print("\nLegend:")
        print(f"  @X = {p1_name} controlled star")
        print(f"  #X = {p2_name} controlled star")
        print("  NX = NPC/unowned star (N = RU value)")
        print("  .. = empty space")

        # Print star control summary
        p1_stars = [s for s in game.stars if s.owner == "p1"]
        p2_stars = [s for s in game.stars if s.owner == "p2"]

        print(f"\n{p1_name} controls: {', '.join(s.id for s in p1_stars) or 'none'}")
        print(f"{p2_name} controls: {', '.join(s.id for s in p2_stars) or 'none'}")
        print()

    def _show_statistics_table(self, game: Game) -> None:
        """Display comparative statistics table.

        Shows side-by-side comparison of final game state for both players.

        Args:
            game: Final game state
        """
        print("--- FINAL STATISTICS ---\n")

        # Calculate statistics for each player
        stats = {}
        for pid in ["p1", "p2"]:
            controlled_stars = [s for s in game.stars if s.owner == pid]
            stationed_ships = sum(s.stationed_ships.get(pid, 0) for s in game.stars)
            in_transit_ships = sum(f.ships for f in game.fleets if f.owner == pid)
            total_ru = sum(s.base_ru for s in controlled_stars)

            # Add home star bonus to production
            home_star = game.players[pid].home_star
            home_controlled = any(
                s.id == home_star and s.owner == pid for s in controlled_stars
            )
            if home_controlled:
                # Home star produces 4 instead of base_ru
                home_base_ru = next(s.base_ru for s in game.stars if s.id == home_star)
                production = total_ru - home_base_ru + 4
            else:
                production = total_ru

            stats[pid] = {
                "stars": len(controlled_stars),
                "production": production,
                "stationed": stationed_ships,
                "in_transit": in_transit_ships,
                "total_fleet": stationed_ships + in_transit_ships,
            }

        # Print table
        p1_name = self._get_display_name("p1", game)
        p2_name = self._get_display_name("p2", game)
        # Truncate names to fit in columns (max 18 chars for display)
        p1_display = p1_name[:18] if len(p1_name) > 18 else p1_name
        p2_display = p2_name[:18] if len(p2_name) > 18 else p2_name

        col_width = max(len(p1_display), len(p2_display), 10) + 2
        print(f"{'Metric':<25} {p1_display:>{col_width}} {p2_display:>{col_width}}")
        print("-" * (27 + 2 * col_width))
        print(
            f"{'Stars Controlled':<25} {stats['p1']['stars']:>{col_width}} {stats['p2']['stars']:>{col_width}}"
        )
        print(
            f"{'Economic Output (RU/turn)':<25} {stats['p1']['production']:>{col_width}} {stats['p2']['production']:>{col_width}}"
        )
        print(
            f"{'Stationed Ships':<25} {stats['p1']['stationed']:>{col_width}} {stats['p2']['stationed']:>{col_width}}"
        )
        print(
            f"{'Ships in Transit':<25} {stats['p1']['in_transit']:>{col_width}} {stats['p2']['in_transit']:>{col_width}}"
        )
        print(
            f"{'Total Fleet Strength':<25} {stats['p1']['total_fleet']:>{col_width}} {stats['p2']['total_fleet']:>{col_width}}"
        )
        print()

    def show_star_details(self, star: Star, player: Player) -> None:
        """Display detailed information about a star.

        Args:
            star: Star to show details for
            player: Player requesting the information (for fog-of-war)
        """
        print(f"\n--- Star {star.id}: {star.name} ---")

        # Show RU if known
        if star.id in player.known_ru and player.known_ru[star.id] is not None:
            print(f"Resource Units: {player.known_ru[star.id]}")
        else:
            print("Resource Units: Unknown")

        # Show control
        control = player.known_control.get(star.id, "unknown")
        if control == "me":
            print("Control: You")
            ships = star.stationed_ships.get(player.id, 0)
            print(f"Stationed Ships: {ships}")
        elif control == "opp":
            print("Control: Opponent")
        elif control == "npc":
            print("Control: NPC")
        elif control == "none":
            print("Control: Unowned")
        else:
            print("Control: Unknown")

        # Show coordinates
        print(f"Location: ({star.x}, {star.y})")
        print()

    def _format_casualties(
        self,
        winner_losses: int,
        is_player_winner: bool,
        mutual_destruction: bool = False,
    ) -> str:
        """Format casualty text for combat reports (NEW FORMAT: winner's losses only).

        Args:
            winner_losses: Ships lost by the winner
            is_player_winner: True if player won, False if opponent/NPC won
            mutual_destruction: True for mutual destruction scenario

        Returns:
            Formatted casualty string like "(You lost 3 ships)" or "(They lost 2 ships)"
        """
        if mutual_destruction:
            return "(Both fleets destroyed)"

        # Singular vs plural
        ship_word = "ship" if winner_losses == 1 else "ships"

        if is_player_winner:
            return f"(You lost {winner_losses} {ship_word})"
        else:
            return f"(They lost {winner_losses} {ship_word})"

    def _format_combat_narrative(
        self, event: "CombatEvent", observing_player: str, game: Game
    ) -> str:
        """Generate narrative combat report for human display.

        Implements 8 scenario templates according to combat_report_display_spec.md:
        1. Attacker wins & takes control (player attacking)
        2. Attacker wins & takes control (opponent attacking)
        3. Defender repels attacker (player defending)
        4. Defender repels attacker (player attacking fails)
        5. Mutual destruction
        6. Simultaneous arrival (fleet clash)
        7. NPC combat (player wins)
        8. NPC combat (player loses)

        Args:
            event: Combat event to format
            observing_player: Player ID viewing the report ("p1" or "p2")
            game: Game state for opponent name resolution

        Returns:
            Formatted narrative string with emoji prefix
        """
        emoji = REPORT_EMOJIS["combat"]
        star_display = f"{event.star_id} ({event.star_name})"

        # Determine roles based on control_before
        # The attacker is whoever didn't own the star before combat
        # If control_before is None and simultaneous=False, then arriving fleet is attacker
        is_npc_defender = event.defender == "npc"
        opponent_id = "p1" if observing_player == "p2" else "p2"
        opponent_name = self._get_display_name(opponent_id, game)

        # Determine who attacked and who defended from observing player's perspective
        # The key insight: attacker = whoever arrived, defender = whoever was there
        # For PvP: event.attacker and event.defender tell us who is who
        is_me_attacker = event.attacker == observing_player
        is_me_defender = event.defender == observing_player

        # Calculate if all ships were lost
        attacker_all_lost = event.attacker_losses == event.attacker_ships
        defender_all_lost = event.defender_losses == event.defender_ships
        mutual_destruction = (
            attacker_all_lost and defender_all_lost and event.control_after is None
        )

        # Scenario 5: Mutual Destruction
        if mutual_destruction:
            casualties = self._format_casualties(0, True, mutual_destruction=True)
            return f"{emoji} Battle at {star_display} resulted in mutual destruction ({event.attacker_ships} vs {event.defender_ships} ships). The star is now uncontrolled. {casualties}"

        # Scenario 6: Simultaneous Arrival
        if event.simultaneous:
            # Both fleets arrived at same time - use "clashed" language
            if event.winner == "attacker":
                # Attacker (p1, alphabetically first) won
                if is_me_attacker:
                    casualties = self._format_casualties(event.attacker_losses, True)
                    return f"{emoji} Your fleet ({event.attacker_ships} ships) clashed with {opponent_name}'s fleet ({event.defender_ships} ships) arriving simultaneously at {star_display}. You emerged victorious and now control {event.star_id}! {casualties}"
                else:
                    casualties = self._format_casualties(event.attacker_losses, False)
                    return f"{emoji} Your fleet ({event.defender_ships} ships) clashed with {opponent_name}'s fleet ({event.attacker_ships} ships) arriving simultaneously at {star_display}. {opponent_name} emerged victorious and now controls {event.star_id}! {casualties}"
            elif event.winner == "defender":
                # Defender (p2, alphabetically second) won
                if is_me_defender:
                    casualties = self._format_casualties(event.defender_losses, True)
                    return f"{emoji} Your fleet ({event.defender_ships} ships) clashed with {opponent_name}'s fleet ({event.attacker_ships} ships) arriving simultaneously at {star_display}. You emerged victorious and now control {event.star_id}! {casualties}"
                else:
                    casualties = self._format_casualties(event.defender_losses, False)
                    return f"{emoji} Your fleet ({event.attacker_ships} ships) clashed with {opponent_name}'s fleet ({event.defender_ships} ships) arriving simultaneously at {star_display}. {opponent_name} emerged victorious and now controls {event.star_id}! {casualties}"

        # Scenario 7 & 8: NPC Combat
        if is_npc_defender:
            if event.winner == "attacker" and is_me_attacker:
                # Scenario 7: Player conquers NPC
                casualties = self._format_casualties(event.attacker_losses, True)
                return f"{emoji} Your fleet ({event.attacker_ships} ships) emerged from hyperspace and defeated the NPC garrison ({event.defender_ships} ships) at {star_display}. You now control {event.star_id}! {casualties}"
            elif event.winner == "defender" and is_me_attacker:
                # Scenario 8: Player loses to NPC
                casualties = self._format_casualties(event.defender_losses, False)
                return f"{emoji} Your attacking fleet ({event.attacker_ships} ships) at {star_display} was repelled by the NPC garrison ({event.defender_ships} ships). {casualties}"
            elif event.winner == "attacker":
                # Opponent conquers NPC
                casualties = self._format_casualties(event.attacker_losses, False)
                return f"{emoji} {opponent_name}'s fleet ({event.attacker_ships} ships) emerged from hyperspace and captured {star_display}. {opponent_name} now controls {event.star_id}! {casualties}"
            else:
                # Opponent loses to NPC
                casualties = self._format_casualties(event.defender_losses, False)
                return f"{emoji} {opponent_name}'s attacking fleet ({event.attacker_ships} ships) at {star_display} was repelled by the NPC garrison ({event.defender_ships} ships). {casualties}"

        # PvP Scenarios (player vs player)
        # Scenario 1: Attacker wins & takes control (player attacking)
        if event.winner == "attacker" and is_me_attacker and defender_all_lost:
            casualties = self._format_casualties(event.attacker_losses, True)
            # Use "defending forces" instead of "garrison" (spec requirement)
            defender_type = "defending forces"
            return f"{emoji} Your fleet ({event.attacker_ships} ships) emerged from hyperspace and defeated the {defender_type} ({event.defender_ships} ships) at {star_display}. You now control {event.star_id}! {casualties}"

        # Scenario 2: Attacker wins & takes control (opponent attacking)
        if event.winner == "attacker" and not is_me_attacker and defender_all_lost:
            casualties = self._format_casualties(event.attacker_losses, False)
            return f"{emoji} {opponent_name}'s fleet ({event.attacker_ships} ships) emerged from hyperspace and captured {star_display}. {opponent_name} now controls {event.star_id}! {casualties}"

        # Scenario 3: Defender repels attacker (player defending)
        if event.winner == "defender" and is_me_defender and attacker_all_lost:
            casualties = self._format_casualties(event.defender_losses, True)
            return f"{emoji} Your defending forces ({event.defender_ships} ships) at {star_display} repelled {opponent_name}'s attacking fleet ({event.attacker_ships} ships). {casualties}"

        # Scenario 4: Defender repels attacker (player attacking fails)
        if event.winner == "defender" and is_me_attacker and attacker_all_lost:
            casualties = self._format_casualties(event.defender_losses, False)
            return f"{emoji} Your attacking fleet ({event.attacker_ships} ships) at {star_display} was repelled by the defending forces ({event.defender_ships} ships). {casualties}"

        # Fallback: generic report (shouldn't happen but defensive coding)
        is_player_winner = (
            event.winner == "attacker"
            and is_me_attacker
            or event.winner == "defender"
            and is_me_defender
        )
        winner_losses = (
            event.attacker_losses
            if event.winner == "attacker"
            else event.defender_losses
        )
        casualties = self._format_casualties(winner_losses, is_player_winner)
        winner_name = "You" if is_player_winner else opponent_name
        return f"{emoji} Battle at {star_display}: {winner_name} won. {casualties}"

    def display_combat_results(
        self,
        combat_events: List[CombatEvent],
        game: Game = None,
        player_id: Optional[str] = None,
    ) -> None:
        """Display combat results from the turn.

        Args:
            combat_events: List of combat events that occurred
            game: Optional game state for display name resolution
            player_id: If provided, filter to only combats this player participated in (fog-of-war)
                      If None, show all combats (debug/spectator mode)
        """
        if not combat_events:
            return

        # Apply fog-of-war filter if player_id specified
        if player_id:
            filtered_events = [
                event
                for event in combat_events
                if self._player_participated_in_combat(event, player_id)
            ]
        else:
            # No filter - show all events (for victory screen or debug mode)
            filtered_events = combat_events

        if not filtered_events:
            return  # No combats visible to this player

        print("\n--- Combat Reports ---")
        for event in filtered_events:
            # Use enhanced narrative format
            if game and player_id:
                narrative = self._format_combat_narrative(event, player_id, game)
                print(narrative)
            else:
                # Fallback to old format if game or player_id not provided
                if event.combat_type == "npc":
                    self._display_npc_combat(event, game)
                else:
                    self._display_pvp_combat(event, game)
        print()

    def _display_npc_combat(self, event: CombatEvent, game: Game = None) -> None:
        """Display NPC combat result.

        Args:
            event: Combat event to display
            game: Optional game state for display name resolution
        """
        if event.attacker == "combined":
            attacker_label = "Players (combined)"
        elif game:
            attacker_label = self._get_display_name(event.attacker, game)
        else:
            attacker_label = event.attacker

        if event.winner == "attacker":
            print(
                f"{REPORT_EMOJIS['combat']} Combat at Star {event.star_id} ({event.star_name}): "
                f"{attacker_label} {event.attacker_ships} ships vs NPC {event.defender_ships} defenders "
                f"-> {attacker_label} wins with {event.attacker_survivors} ships remaining "
                f"({event.attacker_losses} casualties)"
            )
        elif event.winner == "defender":
            print(
                f"{REPORT_EMOJIS['combat']} Combat at Star {event.star_id} ({event.star_name}): "
                f"{attacker_label} {event.attacker_ships} ships vs NPC {event.defender_ships} defenders "
                f"-> NPC wins with {event.defender_survivors} ships remaining "
                f"({event.defender_losses} NPC casualties)"
            )
        else:
            print(
                f"{REPORT_EMOJIS['combat']} Combat at Star {event.star_id} ({event.star_name}): "
                f"{attacker_label} {event.attacker_ships} ships vs NPC {event.defender_ships} defenders "
                f"-> Mutual destruction (tie)"
            )

    def _display_pvp_combat(self, event: CombatEvent, game: Game = None) -> None:
        """Display PvP combat result.

        Args:
            event: Combat event to display
            game: Optional game state for display name resolution
        """
        # Get display names
        if game:
            attacker_name = self._get_display_name(event.attacker, game)
            defender_name = self._get_display_name(event.defender, game)
        else:
            attacker_name = event.attacker
            defender_name = event.defender

        if event.winner == "attacker":
            winner_name = attacker_name
            survivors = event.attacker_survivors
            casualties = event.attacker_losses
        elif event.winner == "defender":
            winner_name = defender_name
            survivors = event.defender_survivors
            casualties = event.defender_losses
        else:
            print(
                f"{REPORT_EMOJIS['combat']} Combat at Star {event.star_id} ({event.star_name}): "
                f"{attacker_name} {event.attacker_ships} ships vs {defender_name} {event.defender_ships} ships "
                f"-> Mutual destruction (tie)"
            )
            return

        print(
            f"{REPORT_EMOJIS['combat']} Combat at Star {event.star_id} ({event.star_name}): "
            f"{attacker_name} {event.attacker_ships} ships vs {defender_name} {event.defender_ships} ships "
            f"-> {winner_name} wins with {survivors} ships remaining ({casualties} casualties)"
        )

    def display_hyperspace_losses(
        self, losses: List[HyperspaceLoss], game: Game = None
    ) -> None:
        """Display hyperspace losses from the turn.

        Args:
            losses: List of hyperspace losses that occurred
            game: Optional game state for display name resolution
        """
        if not losses:
            return

        print("\n--- Hyperspace Losses ---")
        for loss in losses:
            owner_name = (
                self._get_display_name(loss.owner, game) if game else loss.owner
            )
            print(
                f"{REPORT_EMOJIS['hyperspace_loss']} Fleet lost in hyperspace: {loss.ships} ships ({owner_name}) from {loss.origin} to {loss.dest}"
            )
        print()

    def display_rebellion_results(
        self, rebellion_events: List[RebellionEvent], player_id: str, game: Game
    ) -> None:
        """Display rebellion results from the turn.

        Args:
            rebellion_events: List of rebellion events that occurred
            player_id: Player ID to filter rebellions for
            game: Current game state (to check if explanation should be shown)
        """
        # Filter events for this player
        player_rebellions = [e for e in rebellion_events if e.owner == player_id]

        if not player_rebellions:
            return

        # Show one-time explanation banner if this is player's first rebellion
        if not game.rebellion_explanation_shown.get(player_id, False):
            print("\n" + "=" * 60)
            print("REBELLION MECHANIC EXPLAINED")
            print("=" * 60)
            print("Stars can rebel if garrison < RU value (50% chance per turn)")
            print("Rebels spawn equal to the star's RU value")
            print("If rebels win, the star reverts to NPC control")
            print("Keep garrisons >= RU to prevent rebellions!")
            print("=" * 60)
            # Mark as shown
            game.rebellion_explanation_shown[player_id] = True

        print("\n=== REBELLIONS LAST TURN ===")
        for event in player_rebellions:
            if event.outcome == "lost":
                print(
                    f"{REPORT_EMOJIS['rebellion']} Star {event.star} ({event.star_name}, RU:{event.ru}) - LOST TO REBELS"
                )
                print(f"  Your garrison: {event.garrison_before} ships")
                print(f"  Rebel forces:  {event.rebel_ships} ships")
                if event.rebel_survivors > 0:
                    print(
                        f"  Result: Star reverted to NPC control ({event.rebel_survivors} rebel survivor{'s' if event.rebel_survivors != 1 else ''})"
                    )
                else:
                    print("  Result: Mutual destruction - star is now unowned")
            else:  # defended
                print(
                    f"{REPORT_EMOJIS['rebellion']} Star {event.star} ({event.star_name}, RU:{event.ru}) - REBELLION DEFEATED"
                )
                print(f"  Your garrison: {event.garrison_before} ships")
                print(f"  Rebel forces:  {event.rebel_ships} ships")
                print(
                    f"  Result: Rebellion crushed! {event.garrison_after} ship{'s' if event.garrison_after != 1 else ''} remaining"
                )
        print()
