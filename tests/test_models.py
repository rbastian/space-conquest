"""Tests for data models."""

import pytest

from src.models import Fleet, Game, Order, Player, Star
from src.utils import GameRNG


class TestStar:
    """Test Star dataclass."""

    def test_create_star(self):
        """Test basic star creation."""
        star = Star(
            id="A",
            name="Altair",
            x=5,
            y=5,
            base_ru=3,
            owner=None,
            npc_ships=3,
            stationed_ships={"p1": 0, "p2": 0},
        )
        assert star.id == "A"
        assert star.name == "Altair"
        assert star.x == 5
        assert star.y == 5
        assert star.base_ru == 3
        assert star.owner is None
        assert star.npc_ships == 3

    def test_create_home_star(self):
        """Test home star creation."""
        star = Star(
            id="A",
            name="Altair",
            x=2,
            y=3,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 4, "p2": 0},
        )
        assert star.owner == "p1"
        assert star.stationed_ships["p1"] == 4
        assert star.npc_ships == 0

    def test_invalid_coordinates(self):
        """Test star validation for invalid coordinates."""
        with pytest.raises(ValueError, match="Invalid x coordinate"):
            Star(
                id="A",
                name="Altair",
                x=12,
                y=5,
                base_ru=3,
                owner=None,
                npc_ships=3,
                stationed_ships={},
            )

        with pytest.raises(ValueError, match="Invalid y coordinate"):
            Star(
                id="A",
                name="Altair",
                x=5,
                y=10,
                base_ru=3,
                owner=None,
                npc_ships=3,
                stationed_ships={},
            )

    def test_invalid_base_ru(self):
        """Test star validation for invalid base_ru."""
        with pytest.raises(ValueError, match="Invalid base_ru"):
            Star(
                id="A",
                name="Altair",
                x=5,
                y=5,
                base_ru=0,
                owner=None,
                npc_ships=3,
                stationed_ships={},
            )

        with pytest.raises(ValueError, match="Invalid base_ru"):
            Star(
                id="A",
                name="Altair",
                x=5,
                y=5,
                base_ru=5,
                owner=None,
                npc_ships=3,
                stationed_ships={},
            )

    def test_invalid_owner(self):
        """Test star validation for invalid owner."""
        with pytest.raises(ValueError, match="Invalid owner"):
            Star(
                id="A",
                name="Altair",
                x=5,
                y=5,
                base_ru=3,
                owner="p3",
                npc_ships=3,
                stationed_ships={},
            )


class TestFleet:
    """Test Fleet dataclass."""

    def test_create_fleet(self):
        """Test basic fleet creation."""
        fleet = Fleet(
            id="p1-001",
            owner="p1",
            ships=5,
            origin="A",
            dest="B",
            dist_remaining=3,
            rationale="attack",
        )
        assert fleet.id == "p1-001"
        assert fleet.owner == "p1"
        assert fleet.ships == 5
        assert fleet.origin == "A"
        assert fleet.dest == "B"
        assert fleet.dist_remaining == 3

    def test_invalid_owner(self):
        """Test fleet validation for invalid owner."""
        with pytest.raises(ValueError, match="Invalid owner"):
            Fleet(
                id="p3-001",
                owner="p3",
                ships=5,
                origin="A",
                dest="B",
                dist_remaining=3,
                rationale="attack",
            )

    def test_invalid_ships(self):
        """Test fleet validation for invalid ship count."""
        with pytest.raises(ValueError, match="Invalid ships"):
            Fleet(
                id="p1-001",
                owner="p1",
                ships=0,
                origin="A",
                dest="B",
                dist_remaining=3,
                rationale="attack",
            )

        with pytest.raises(ValueError, match="Invalid ships"):
            Fleet(
                id="p1-001",
                owner="p1",
                ships=-1,
                origin="A",
                dest="B",
                dist_remaining=3,
                rationale="attack",
            )

    def test_invalid_distance(self):
        """Test fleet validation for invalid distance."""
        with pytest.raises(ValueError, match="Invalid dist_remaining"):
            Fleet(
                id="p1-001",
                owner="p1",
                ships=5,
                origin="A",
                dest="B",
                dist_remaining=-1,
                rationale="attack",
            )


class TestOrder:
    """Test Order dataclass."""

    def test_create_order(self):
        """Test basic order creation."""
        order = Order(from_star="A", to_star="B", ships=3)
        assert order.from_star == "A"
        assert order.to_star == "B"
        assert order.ships == 3

    def test_invalid_ships(self):
        """Test order validation for invalid ship count."""
        with pytest.raises(ValueError, match="Invalid ships"):
            Order(from_star="A", to_star="B", ships=0)

        with pytest.raises(ValueError, match="Invalid ships"):
            Order(from_star="A", to_star="B", ships=-1)

    def test_same_star(self):
        """Test order validation for same origin and destination."""
        with pytest.raises(ValueError, match="Cannot move ships from star to itself"):
            Order(from_star="A", to_star="A", ships=3)

    def test_empty_star_ids(self):
        """Test order validation for empty star IDs."""
        with pytest.raises(ValueError, match="from_star cannot be empty"):
            Order(from_star="", to_star="B", ships=3)

        with pytest.raises(ValueError, match="to_star cannot be empty"):
            Order(from_star="A", to_star="", ships=3)


class TestPlayer:
    """Test Player dataclass."""

    def test_create_player(self):
        """Test basic player creation."""
        player = Player(
            id="p1",
            home_star="A",
            visited_stars={"A"},
            fleets=[],
        )
        assert player.id == "p1"
        assert player.home_star == "A"
        assert player.visited_stars == {"A"}
        assert len(player.fleets) == 0

    def test_invalid_player_id(self):
        """Test player validation for invalid ID."""
        with pytest.raises(ValueError, match="Invalid player id"):
            Player(
                id="p3",
                home_star="A",
                visited_stars=set(),
                fleets=[],
            )

    def test_empty_home_star(self):
        """Test player validation for empty home star."""
        with pytest.raises(ValueError, match="home_star cannot be empty"):
            Player(
                id="p1",
                home_star="",
                visited_stars=set(),
                fleets=[],
            )


class TestGame:
    """Test Game class."""

    def test_create_game(self):
        """Test basic game creation."""
        game = Game(
            seed=42,
            turn=0,
            stars=[],
            fleets=[],
            players={},
            winner=None,
            turn_history=[],
            fleet_counter={"p1": 0, "p2": 0},
        )
        assert game.seed == 42
        assert game.turn == 0
        assert game.winner is None
        assert game.rng is not None
        assert isinstance(game.rng, GameRNG)

    def test_game_with_rng(self):
        """Test game creation with explicit RNG."""
        rng = GameRNG(42)
        game = Game(
            seed=42,
            turn=0,
            stars=[],
            fleets=[],
            players={},
            rng=rng,
            winner=None,
            turn_history=[],
            fleet_counter={"p1": 0, "p2": 0},
        )
        assert game.rng is rng

    def test_invalid_turn(self):
        """Test game validation for invalid turn."""
        with pytest.raises(ValueError, match="Invalid turn"):
            Game(
                seed=42,
                turn=-1,
                stars=[],
                fleets=[],
                players={},
                winner=None,
                turn_history=[],
                fleet_counter={"p1": 0, "p2": 0},
            )

    def test_invalid_winner(self):
        """Test game validation for invalid winner."""
        with pytest.raises(ValueError, match="Invalid winner"):
            Game(
                seed=42,
                turn=0,
                stars=[],
                fleets=[],
                players={},
                winner="p3",
                turn_history=[],
                fleet_counter={"p1": 0, "p2": 0},
            )

    def test_game_with_stars_and_players(self):
        """Test game with stars and players."""
        star_a = Star(
            id="A",
            name="Altair",
            x=2,
            y=3,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 4, "p2": 0},
        )
        player1 = Player(
            id="p1",
            home_star="A",
            visited_stars={"A"},
            fleets=[],
        )
        game = Game(
            seed=42,
            turn=0,
            stars=[star_a],
            fleets=[],
            players={"p1": player1},
            winner=None,
            turn_history=[],
            fleet_counter={"p1": 0, "p2": 0},
        )
        assert len(game.stars) == 1
        assert len(game.players) == 1
        assert game.players["p1"].home_star == "A"
