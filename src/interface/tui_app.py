"""Textual TUI application for Space Conquest.

This module provides a modern Terminal User Interface using the Textual framework.
It displays the game map, controlled stars, fleets in transit, and handles player input.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Input, RichLog, Static

from ..models.game import Game
from ..models.order import Order
from .command_parser import CommandParser, ErrorType, OrderParseError
from .display import DisplayManager
from .renderer import MapRenderer


class MapPanel(Static):
    """Widget to display the game map."""

    def __init__(self, *args, **kwargs):
        """Initialize map panel."""
        super().__init__(*args, **kwargs)
        self.renderer = MapRenderer()
        self.border_title = "Map"

    def update_map(self, game: Game, player_id: str) -> None:
        """Update the map display.

        Args:
            game: Current game state
            player_id: Player whose perspective to render
        """
        player = game.players[player_id]
        map_str = self.renderer.render_with_coords(player, game.stars)
        self.update(map_str)


class StarsTable(Static):
    """Widget to display controlled stars."""

    def __init__(self, *args, **kwargs):
        """Initialize stars table."""
        super().__init__(*args, **kwargs)
        self.display_manager = DisplayManager()

    def update_table(self, game: Game, player_id: str) -> None:
        """Update the controlled stars display."""
        player = game.players[player_id]

        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            self.display_manager._show_controlled_stars(player, game)
            output = buffer.getvalue()
        finally:
            sys.stdout = old_stdout

        self.update(output)


class FleetsTable(Static):
    """Widget to display fleets in transit."""

    def __init__(self, *args, **kwargs):
        """Initialize fleets table."""
        super().__init__(*args, **kwargs)
        self.display_manager = DisplayManager()

    def update_table(self, game: Game, player_id: str) -> None:
        """Update the fleets in transit display."""
        player = game.players[player_id]

        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            self.display_manager._show_fleets_in_transit(player, game)
            output = buffer.getvalue()
        finally:
            sys.stdout = old_stdout

        self.update(output)


class TerminalPanel(RichLog):
    """Terminal-style panel with inline command input and responses."""

    def __init__(self, *args, **kwargs):
        """Initialize terminal panel."""
        super().__init__(*args, highlight=True, markup=True, wrap=True, **kwargs)

    def show_command(self, command: str) -> None:
        """Echo the command that was entered.

        Args:
            command: Command string entered by user
        """
        self.write(f"[bold cyan]>[/bold cyan] {command}")

    def show_response(self, message: str, is_error: bool = False) -> None:
        """Show response to a command.

        Args:
            message: Response message to display
            is_error: If True, display in red; otherwise green
        """
        if is_error:
            self.write(f"[red]{message}[/red]")
        else:
            self.write(f"[green]{message}[/green]")
        self.write("")  # Blank line after response

    def show_info(self, message: str) -> None:
        """Show informational message.

        Args:
            message: Info message to display
        """
        self.write(message)

    def add_combat_report(self, event, game, player_id: str) -> None:
        """Add a combat report to the terminal.

        Args:
            event: Combat event to display
            game: Current game state
            player_id: Player ID viewing the report
        """
        display = DisplayManager()
        narrative = display._format_combat_narrative(event, player_id, game)
        self.write(narrative)
        self.write("")

    def add_hyperspace_loss(self, loss, game) -> None:
        """Add a hyperspace loss report to the terminal.

        Args:
            loss: Hyperspace loss event
            game: Current game state
        """
        display = DisplayManager()
        owner_name = display._get_display_name(loss.owner, game)
        message = f"[yellow]Fleet lost in hyperspace: {loss.ships} ships ({owner_name}) from {loss.origin} to {loss.dest}[/yellow]"
        self.write(message)
        self.write("")


class SpaceConquestTUI(App):
    """Space Conquest TUI application."""

    # Disable command palette (Ctrl+P) - we use custom keybindings
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    #map_container {
        height: 13;
        border: solid green;
    }

    #tables_row {
        height: 15;
    }

    #stars_container {
        width: 1fr;
        border: solid blue;
        overflow-y: auto;
    }

    #fleets_container {
        width: 1fr;
        border: solid blue;
        overflow-y: auto;
    }

    StarsTable {
        width: 100%;
        height: auto;
    }

    FleetsTable {
        width: 100%;
        height: auto;
    }

    #terminal_container {
        height: 10;
        border: solid cyan;
    }

    TerminalPanel {
        height: 1fr;
        overflow-y: auto;
        border: none;
    }

    #input_row {
        dock: bottom;
        height: 1;
        background: $surface;
    }

    #prompt_label {
        width: auto;
        background: $surface;
        color: cyan;
        padding: 0;
    }

    #command_input {
        width: 1fr;
        height: 1;
        background: $surface;
        border: none;
        padding: 0;
    }

    Input {
        background: $surface;
        color: white;
    }

    Input:focus {
        background: $surface;
        color: white;
    }

    Input > .input--cursor {
        background: cyan;
        color: black;
        text-style: bold;
    }

    Input > .input--placeholder {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+h", "show_help", "Help", show=True),
    ]

    def __init__(self, game: Game, player_id: str, *args, **kwargs):
        """Initialize the TUI app.

        Args:
            game: Current game state
            player_id: Player ID ("p1" or "p2")
        """
        super().__init__(*args, **kwargs)
        self.game = game
        self.player_id = player_id
        self.map_panel = None
        self.stars_table = None
        self.fleets_table = None
        self.terminal_panel = None
        self.display_manager = DisplayManager()
        self.parser = CommandParser()
        self.orders: list[Order] = []
        self.commitment_tracker: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        self.map_panel = MapPanel(id="map_container")
        yield self.map_panel

        # Two side-by-side containers
        with Horizontal(id="tables_row"):
            # Left: Controlled Stars
            stars_container = Container(id="stars_container")
            stars_container.border_title = "Controlled Stars"
            with stars_container:
                self.stars_table = StarsTable()
                yield self.stars_table

            # Right: Fleets in Hyperspace
            fleets_container = Container(id="fleets_container")
            fleets_container.border_title = "Fleets in Hyperspace"
            with fleets_container:
                self.fleets_table = FleetsTable()
                yield self.fleets_table

        # Terminal with integrated input
        terminal_container = Container(id="terminal_container")
        terminal_container.border_title = "Terminal"
        with terminal_container:
            self.terminal_panel = TerminalPanel()
            yield self.terminal_panel
            with Horizontal(id="input_row"):
                yield Static(f"{self.player_id}> ", id="prompt_label")
                yield Input(placeholder="", id="command_input")

        yield Footer()

    def on_mount(self) -> None:
        """Handle mount event."""
        # Update displays on mount
        self.refresh_display()

        # Show initial welcome and turn info
        if self.terminal_panel:
            player = self.game.players[self.player_id]
            self.terminal_panel.show_info(
                f"[bold cyan]Turn {self.game.turn} - {player.id.upper()}[/bold cyan]"
            )
            self.terminal_panel.write("")

            # Show combat events from last turn if any (filtered by fog of war)
            if hasattr(self.game, "combats_last_turn") and self.game.combats_last_turn:
                for event_dict in self.game.combats_last_turn:
                    # Only show events at stars the player has visited
                    star_id = event_dict.get("star_id")
                    if star_id and star_id in player.visited_stars:
                        # Convert dict to object for display (simple namespace works)
                        from types import SimpleNamespace

                        event = SimpleNamespace(**event_dict)
                        self.terminal_panel.add_combat_report(event, self.game, self.player_id)

            # Show hyperspace losses from last turn if any
            if (
                hasattr(self.game, "hyperspace_losses_last_turn")
                and self.game.hyperspace_losses_last_turn
            ):
                for loss_dict in self.game.hyperspace_losses_last_turn:
                    if loss_dict.get("owner") == self.player_id:
                        from types import SimpleNamespace

                        loss = SimpleNamespace(**loss_dict)
                        self.terminal_panel.add_hyperspace_loss(loss, self.game)

            self.terminal_panel.show_info("Type 'help' for commands or start issuing orders")
            self.terminal_panel.write("")

        # Focus the input field so user can start typing immediately
        self.set_focus_to_input()

    def set_focus_to_input(self) -> None:
        """Set focus to the command input field."""
        try:
            input_widget = self.query_one("#command_input", Input)
            input_widget.focus()
        except Exception:
            pass  # Input might not be ready yet

    def refresh_display(self) -> None:
        """Refresh all display panels."""
        if self.map_panel:
            self.map_panel.update_map(self.game, self.player_id)
        if self.stars_table:
            self.stars_table.update_table(self.game, self.player_id)
        if self.fleets_table:
            self.fleets_table.update_table(self.game, self.player_id)

    def update_game_state(self, new_game: Game) -> None:
        """Update the displayed game state.

        Args:
            new_game: New game state to display
        """
        self.game = new_game

        # Update map
        if self.map_panel:
            self.map_panel.update_map(self.game, self.player_id)

        # Update tables
        if self.stars_table:
            self.stars_table.update_table(self.game, self.player_id)
        if self.fleets_table:
            self.fleets_table.update_table(self.game, self.player_id)

    def show_combat_results(self, events) -> None:
        """Display combat reports in the terminal panel.

        Args:
            events: List of combat events to display
        """
        if not self.terminal_panel:
            return

        for event in events:
            self.terminal_panel.add_combat_report(event, self.game, self.player_id)

    def show_hyperspace_losses(self, losses) -> None:
        """Display hyperspace losses in the terminal panel.

        Args:
            losses: List of hyperspace loss events to display
        """
        if not self.terminal_panel:
            return

        for loss in losses:
            self.terminal_panel.add_hyperspace_loss(loss, self.game)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission.

        Args:
            event: Input submission event
        """
        command = event.value.strip()
        event.input.value = ""  # Clear input

        if not command:
            self.set_focus_to_input()  # Keep focus even on empty submit
            return

        terminal = self.terminal_panel
        if not terminal:
            return

        # Echo command
        terminal.show_command(command)

        cmd_lower = command.lower()

        # Handle special commands
        if cmd_lower in ("done", "end"):
            count = len(self.orders)
            if count == 0:
                terminal.show_response("Submitting 0 orders (passing turn)...")
            else:
                terminal.show_response(f"Submitted {count} order{'s' if count != 1 else ''}")
            terminal.write("")
            # Exit the app and return orders
            self.exit(self.orders)
            return

        if cmd_lower in ("list", "ls"):
            if not self.orders:
                terminal.show_info("No orders queued")
                terminal.write("")
            else:
                terminal.show_info("[bold]Queued orders:[/bold]")
                for i, order in enumerate(self.orders, 1):
                    terminal.show_info(
                        f"  {i}. Move {order.ships} ships: {order.from_star} -> {order.to_star}"
                    )
                terminal.write("")
            self.set_focus_to_input()
            return

        if cmd_lower in ("clear", "reset"):
            count = len(self.orders)
            self.orders.clear()
            self.commitment_tracker.clear()
            if count == 0:
                terminal.show_info("No orders to clear")
            else:
                terminal.show_response(f"Cleared {count} order{'s' if count != 1 else ''}")
            self.set_focus_to_input()
            return

        if cmd_lower in ("help", "h", "?"):
            self._show_help_inline(terminal)
            self.set_focus_to_input()
            return

        if cmd_lower in ("status", "st"):
            self._show_status_inline(terminal)
            self.set_focus_to_input()
            return

        if cmd_lower in ("quit", "exit", "q"):
            # Exit the app with None to signal quit (not just submitting turn)
            terminal.show_info("Exiting game...")
            terminal.write("")
            self.exit(None)  # Return None to indicate quit, not submission
            return

        # Try to parse as order
        try:
            order = self.parser.parse(command)

            if order is None:
                unknown_cmd = cmd_lower.split()[0] if cmd_lower.split() else cmd_lower
                terminal.show_response(f"Unknown command: '{unknown_cmd}'", is_error=True)
                terminal.show_info(
                    "Available commands: move, done, list, clear, help, status, quit"
                )
                terminal.write("")
                self.set_focus_to_input()
                return

            # Validate order
            error = self._validate_order(order)
            if error:
                terminal.show_response(f"Error: {error}", is_error=True)
                self.set_focus_to_input()
                return

            # Queue the order
            self.orders.append(order)

            # Update commitment tracker
            if order.from_star not in self.commitment_tracker:
                self.commitment_tracker[order.from_star] = 0
            self.commitment_tracker[order.from_star] += order.ships

            # Show success feedback
            order_count = len(self.orders)
            terminal.show_response(
                f"Order {order_count} queued: {order.ships} ships from {order.from_star} to {order.to_star}"
            )
            self.set_focus_to_input()

        except OrderParseError as e:
            message = e.message
            terminal.show_response(f"Error: {message}", is_error=True)
            if e.error_type == ErrorType.UNKNOWN_COMMAND:
                terminal.show_info(
                    "Available commands: move, done, list, clear, help, status, quit"
                )
                terminal.show_info("Example: move 5 ships from A to B")
                terminal.write("")
            self.set_focus_to_input()

        except Exception as e:
            terminal.show_response(f"Error: {str(e)}", is_error=True)
            self.set_focus_to_input()

    def _validate_order(self, order: Order) -> str:
        """Validate an order before queuing.

        Args:
            order: Order to validate

        Returns:
            Error message if invalid, empty string if valid
        """
        game = self.game
        player = game.players[self.player_id]

        # Check ships > 0
        if order.ships <= 0:
            return f"Invalid ship count: must be positive (got {order.ships})"

        # Check stars exist
        from_star = None
        to_star = None
        for star in game.stars:
            if star.id == order.from_star:
                from_star = star
            if star.id == order.to_star:
                to_star = star

        if from_star is None and to_star is None:
            return f"Stars '{order.from_star}' and '{order.to_star}' do not exist"
        if from_star is None:
            return f"Origin star '{order.from_star}' does not exist"
        if to_star is None:
            return f"Destination star '{order.to_star}' does not exist"

        # Check not same star
        if order.from_star == order.to_star:
            return f"Cannot send fleet from {order.from_star} to itself"

        # Check ownership
        if from_star.owner != player.id:
            return f"You do not control star '{order.from_star}'"

        # Check sufficient ships
        available = from_star.stationed_ships.get(player.id, 0)
        already_committed = self.commitment_tracker.get(order.from_star, 0)
        remaining = available - already_committed

        if order.ships > remaining:
            return (
                f"Insufficient ships at {order.from_star}\n"
                f"Requested: {order.ships}, Available: {available}, "
                f"Already committed: {already_committed}, Remaining: {remaining}"
            )

        return ""

    def _show_help_inline(self, terminal: TerminalPanel) -> None:
        """Show help in terminal.

        Args:
            terminal: Terminal panel to write to
        """
        terminal.show_info("[bold cyan]=== Space Conquest - Command Help ===[/bold cyan]")
        terminal.write("")
        terminal.show_info("[bold]Core commands:[/bold]")
        terminal.show_info("  [cyan]move <ships> from <star> to <star>[/cyan]  - Queue an order")
        terminal.show_info(
            "  [cyan]done[/cyan]                                 - Submit all queued orders and end turn"
        )
        terminal.show_info(
            "  [cyan]list[/cyan]                                 - Show all queued orders"
        )
        terminal.show_info(
            "  [cyan]clear[/cyan]                                - Remove all queued orders"
        )
        terminal.show_info(
            "  [cyan]help[/cyan]                                 - Show this help message"
        )
        terminal.write("")
        terminal.show_info("[bold]Other commands:[/bold]")
        terminal.show_info(
            "  [cyan]status[/cyan]                               - Show current game status"
        )
        terminal.show_info("  [cyan]quit[/cyan]                                 - Exit the game")
        terminal.write("")
        terminal.show_info("[bold]Examples:[/bold]")
        terminal.show_info("  move 5 ships from A to B")
        terminal.show_info("  move 10 from C to D")
        terminal.show_info("  done")
        terminal.write("")
        terminal.show_info("[bold]Map Legend:[/bold]")
        terminal.show_info("  [dim]?X[/dim]  - Star X with unknown RU")
        terminal.show_info("  [dim]1A[/dim]  - Star A with 1 RU (NPC or unowned)")
        terminal.show_info("  [green]@A[/green]  - Star A controlled by you")
        terminal.show_info("  [red]!A[/red]  - Star A controlled by opponent")
        terminal.show_info("  [dim]..[/dim]  - Empty space")
        terminal.write("")

    def _show_status_inline(self, terminal: TerminalPanel) -> None:
        """Show status in terminal.

        Args:
            terminal: Terminal panel to write to
        """
        player = self.game.players[self.player_id]

        terminal.show_info(f"[bold]Turn {self.game.turn} - {player.id.upper()}[/bold]")
        terminal.write("")

        # Calculate totals
        total_ru = sum(s.base_ru for s in self.game.stars if s.owner == self.player_id)
        total_ships = sum(
            s.stationed_ships.get(self.player_id, 0)
            for s in self.game.stars
            if s.owner == self.player_id
        )
        controlled = len([s for s in self.game.stars if s.owner == self.player_id])

        terminal.show_info(f"Resources: [cyan]{total_ru} RU[/cyan]")
        terminal.show_info(f"Ships: [cyan]{total_ships}[/cyan]")
        terminal.show_info(f"Controlled Stars: [cyan]{controlled}[/cyan]")
        terminal.show_info(f"Queued Orders: [cyan]{len(self.orders)}[/cyan]")
        terminal.write("")

    def action_show_help(self) -> None:
        """Show help information."""
        if self.terminal_panel:
            self._show_help_inline(self.terminal_panel)

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def get_orders(self) -> list[Order]:
        """Get queued orders and clear the queue.

        Returns:
            List of queued orders
        """
        orders = self.orders.copy()
        self.orders.clear()
        self.commitment_tracker.clear()
        return orders


def run_tui_demo():
    """Run a demo of the TUI with a test game state."""
    from ..models.fleet import Fleet
    from ..models.player import Player
    from ..models.star import Star

    # Create a simple test game state
    stars = [
        Star(
            id="A",
            name="Alpha",
            x=0,
            y=0,
            base_ru=3,
            owner="p1",
            stationed_ships={"p1": 10},
            npc_ships=0,
        ),
        Star(
            id="B",
            name="Beta",
            x=3,
            y=2,
            base_ru=2,
            owner="p1",
            stationed_ships={"p1": 5},
            npc_ships=0,
        ),
        Star(
            id="C", name="Gamma", x=6, y=5, base_ru=4, owner=None, stationed_ships={}, npc_ships=8
        ),
        Star(
            id="D",
            name="Delta",
            x=9,
            y=7,
            base_ru=1,
            owner="p2",
            stationed_ships={"p2": 3},
            npc_ships=0,
        ),
        Star(
            id="E",
            name="Epsilon",
            x=11,
            y=9,
            base_ru=2,
            owner="p2",
            stationed_ships={"p2": 6},
            npc_ships=0,
        ),
    ]

    # Create players with some visited stars
    p1 = Player(id="p1", home_star="A")
    p1.visited_stars = {"A", "B", "C"}

    p2 = Player(id="p2", home_star="E")
    p2.visited_stars = {"D", "E", "C"}

    # Create a fleet in transit
    fleets = [
        Fleet(
            id="f1", owner="p1", origin="A", dest="C", ships=3, dist_remaining=2, rationale="expand"
        ),
    ]

    # Create game
    game = Game(
        seed=12345,
        turn=5,
        stars=stars,
        players={"p1": p1, "p2": p2},
        fleets=fleets,
        p2_model_id="test-model",
    )

    # Run the TUI (with mouse disabled - we only need keyboard input)
    app = SpaceConquestTUI(game, "p1")
    app.run(mouse=False)


if __name__ == "__main__":
    run_tui_demo()
