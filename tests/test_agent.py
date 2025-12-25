"""Tests for LLM agent tools and player controller."""

import pytest

from src.agent.langchain_client import MockLangChainClient
from src.agent.langgraph_player import LangGraphPlayer
from src.agent.tool_models import TOOL_DEFINITIONS
from src.agent.tools import AgentTools
from src.engine.map_generator import generate_map
from src.models.order import Order


class TestAgentTools:
    """Test suite for AgentTools class (simplified architecture)."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def tools(self, game):
        """Create AgentTools instance."""
        return AgentTools(game, player_id="p2")

    def test_propose_orders_valid(self, tools, game):
        """Test validating valid orders."""
        # Find a star controlled by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Ensure it has ships
        if p2_star.stationed_ships.get("p2", 0) == 0:
            p2_star.stationed_ships["p2"] = 5

        # Find a destination
        dest_star = game.stars[0] if game.stars[0] != p2_star else game.stars[1]

        orders = [{"from": p2_star.id, "to": dest_star.id, "ships": 1}]

        result = tools.propose_orders(orders)
        assert result["ok"] is True

    def test_propose_orders_too_many_ships(self, tools, game):
        """Test validating orders with too many ships."""
        # Find a star controlled by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Set ships to known amount
        p2_star.stationed_ships["p2"] = 3

        dest_star = game.stars[0] if game.stars[0] != p2_star else game.stars[1]

        orders = [{"from": p2_star.id, "to": dest_star.id, "ships": 10}]

        result = tools.propose_orders(orders)
        assert result["ok"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_propose_orders_not_controlled(self, tools, game):
        """Test validating orders from non-controlled star."""
        # Find a star NOT controlled by p2
        other_star = None
        for star in game.stars:
            if star.owner != "p2":
                other_star = star
                break

        if other_star is None:
            pytest.skip("All stars controlled by p2 in test game")

        dest_star = game.stars[0]

        orders = [{"from": other_star.id, "to": dest_star.id, "ships": 1}]

        result = tools.propose_orders(orders)
        assert result["ok"] is False
        assert "errors" in result

    def test_submit_orders(self, tools, game):
        """Test submitting validated orders."""
        # Find a star controlled by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Ensure it has ships
        p2_star.stationed_ships["p2"] = 5

        dest_star = game.stars[0] if game.stars[0] != p2_star else game.stars[1]

        orders = [{"from": p2_star.id, "to": dest_star.id, "ships": 2}]

        result = tools.submit_orders(orders)
        assert result["status"] == "submitted"
        assert result["order_count"] == 1
        assert tools.orders_submitted is True

    def test_submit_orders_twice(self, tools, game):
        """Test that submitting orders twice raises error."""
        # Submit once
        orders = []
        tools.submit_orders(orders)

        # Try to submit again
        with pytest.raises(ValueError, match="already submitted"):
            tools.submit_orders(orders)

    def test_reset_turn(self, tools):
        """Test resetting turn state."""
        tools.orders_submitted = True
        tools.pending_orders = [Order("A", "B", 1)]

        tools.reset_turn()

        assert tools.orders_submitted is False
        assert tools.pending_orders is None

    def test_tool_definitions_complete(self):
        """Test that all tools are defined."""
        tool_names = {td["name"] for td in TOOL_DEFINITIONS}

        # Check that both tools exist
        assert "submit_orders" in tool_names
        assert "calculate_distance" in tool_names
        assert len(tool_names) == 2


class TestLLMPlayer:
    """Test suite for LangGraphPlayer class (simplified architecture)."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def llm_player(self):
        """Create LangGraphPlayer with mock client."""
        return LangGraphPlayer("p2", use_mock=True, verbose=False)

    def test_initialization(self, llm_player):
        """Test LangGraphPlayer initializes correctly."""
        assert llm_player.player_id == "p2"
        assert isinstance(llm_player.client, MockLangChainClient)

    def test_get_orders_returns_list(self, llm_player, game):
        """Test that get_orders returns a list."""
        orders = llm_player.get_orders(game)
        assert isinstance(orders, list)

    def test_get_orders_valid_orders(self, llm_player, game):
        """Test that get_orders returns valid Order objects."""
        orders = llm_player.get_orders(game)

        for order in orders:
            assert isinstance(order, Order)
            assert order.ships > 0
            assert order.from_star != order.to_star


class TestMemoryAutopopulation:
    """Test suite for memory auto-population feature."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    def test_auto_populate_memory_battle_log(self, game):
        """Test that battle_log is auto-populated from combats."""
        # Create a PvP combat
        game.combats_last_turn = [
            {
                "star_id": "K",
                "star_name": "Kappa",
                "combat_type": "pvp",
                "attacker": "p1",
                "defender": "p2",
                "attacker_ships": 10,
                "defender_ships": 8,
                "attacker_survivors": 6,
                "defender_survivors": 0,
                "attacker_losses": 4,
                "defender_losses": 8,
                "winner": "attacker",
                "control_before": "p2",
                "control_after": "p1",
                "simultaneous": False,
            }
        ]

        tools = AgentTools(game, "p2")
        tools.reset_turn()

        # Check battle_log populated
        assert len(tools.memory["battle_log"]) == 1
        battle = tools.memory["battle_log"][0]
        assert battle["turn"] == game.turn
        assert battle["star"] == "K"
        assert battle["attacker"] == "opp"  # p1 from p2's perspective
        assert battle["defender"] == "me"  # p2 from p2's perspective
        assert battle["winner"] == "opp"

    def test_auto_populate_skips_npc_battles(self, game):
        """Test that NPC battles are NOT recorded."""
        # Create NPC combat
        game.combats_last_turn = [
            {
                "star_id": "K",
                "star_name": "Kappa",
                "combat_type": "npc",
                "attacker": "p1",
                "defender": "npc",
                "attacker_ships": 10,
                "defender_ships": 5,
                "attacker_survivors": 8,
                "defender_survivors": 0,
                "attacker_losses": 2,
                "defender_losses": 5,
                "winner": "attacker",
                "control_before": "npc",
                "control_after": "p1",
                "simultaneous": False,
            }
        ]

        tools = AgentTools(game, "p2")
        tools.reset_turn()

        # NPC battle should be skipped
        assert len(tools.memory["battle_log"]) == 0

    def test_auto_populate_memory_discovery_log(self, game):
        """Test that discovery_log is auto-populated from visited stars."""
        # Mark a star as visited
        star = game.stars[0]
        game.players["p2"].visited_stars.add(star.id)  # Star has been visited

        tools = AgentTools(game, "p2")
        tools.reset_turn()

        # Check discovery_log populated
        assert len(tools.memory["discovery_log"]) >= 1
        # Find the discovery record for our star
        discoveries = [d for d in tools.memory["discovery_log"] if d["star"] == star.id]
        assert len(discoveries) == 1
        discovery = discoveries[0]
        assert discovery["ru"] == star.base_ru
        assert discovery["turn"] == game.turn

    def test_memory_persistence_across_turns(self, game):
        """Test that memory persists when AgentTools is recreated."""
        # First turn - populate memory
        game.combats_last_turn = [
            {
                "star_id": "K",
                "star_name": "Kappa",
                "combat_type": "pvp",
                "attacker": "p1",
                "defender": "p2",
                "attacker_ships": 10,
                "defender_ships": 8,
                "attacker_survivors": 6,
                "defender_survivors": 0,
                "attacker_losses": 4,
                "defender_losses": 8,
                "winner": "attacker",
                "control_before": "p2",
                "control_after": "p1",
                "simultaneous": False,
            }
        ]

        tools1 = AgentTools(game, "p2")
        tools1.reset_turn()
        game.agent_memory["p2"] = tools1.memory  # Save memory

        assert len(tools1.memory["battle_log"]) == 1

        # Second turn - create new AgentTools and verify memory restored
        tools2 = AgentTools(game, "p2")

        # Memory should be restored from game
        assert len(tools2.memory["battle_log"]) == 1
        assert tools2.memory["battle_log"][0]["star"] == "K"

    def test_no_duplicate_battle_records(self, game):
        """Test that same battle is not recorded twice."""
        game.combats_last_turn = [
            {
                "star_id": "K",
                "star_name": "Kappa",
                "combat_type": "pvp",
                "attacker": "p1",
                "defender": "p2",
                "attacker_ships": 10,
                "defender_ships": 8,
                "attacker_survivors": 6,
                "defender_survivors": 0,
                "attacker_losses": 4,
                "defender_losses": 8,
                "winner": "attacker",
                "control_before": "p2",
                "control_after": "p1",
                "simultaneous": False,
            }
        ]

        tools = AgentTools(game, "p2")
        tools.reset_turn()
        tools.reset_turn()  # Call twice

        # Should only have one record (no duplicates)
        assert len(tools.memory["battle_log"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
