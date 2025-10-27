"""Tests for LLM agent tools and player controller."""

import pytest
from src.agent.langchain_client import MockLangChainClient
from src.agent.bedrock_client import MockBedrockClient
from src.agent.llm_player import LLMPlayer
from src.agent.tools import AgentTools, TOOL_DEFINITIONS
from src.engine.map_generator import generate_map
from src.models.order import Order


class TestAgentTools:
    """Test suite for AgentTools class."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def tools(self, game):
        """Create AgentTools instance."""
        return AgentTools(game, player_id="p2")

    def test_get_observation(self, tools, game):
        """Test get_observation returns proper fog-of-war filtered state."""
        obs = tools.get_observation()

        # Check basic structure
        assert "turn" in obs
        assert "seed" in obs
        assert "grid" in obs
        assert "stars" in obs
        assert "my_fleets" in obs
        assert "rules" in obs

        assert obs["turn"] == game.turn
        assert obs["seed"] == game.seed
        assert obs["grid"] == {"width": 12, "height": 10}

        # Check stars are fog-of-war filtered
        assert len(obs["stars"]) == len(game.stars)
        for star_data in obs["stars"]:
            assert "id" in star_data
            assert "x" in star_data
            assert "y" in star_data
            assert "owner" in star_data
            assert "known_ru" in star_data
            assert "is_home" in star_data
            assert "stationed_ships" in star_data  # New field

        # Check rules
        assert obs["rules"]["hyperspace_loss"] == 0.02
        assert obs["rules"]["rebellion_chance"] == 0.5
        assert obs["rules"]["production_formula"].startswith("ships_per_turn = star_ru")

    def test_get_ascii_map(self, tools):
        """Test ASCII map generation."""
        map_str = tools.get_ascii_map()

        # Check basic structure
        assert isinstance(map_str, str)
        assert len(map_str) > 0

        # Should contain coordinate headers
        lines = map_str.split("\n")
        assert len(lines) > 10  # At least 10 rows

        # First line should have column numbers
        assert "0" in lines[0]

    def test_query_star(self, tools, game):
        """Test querying star information."""
        # Get a star ID
        star = game.stars[0]
        result = tools.query_star(star.id)

        # Check structure
        assert result["id"] == star.id
        assert result["name"] == star.name
        assert result["x"] == star.x
        assert result["y"] == star.y
        assert "known_ru" in result
        assert "last_seen_control" in result
        assert "stationed_ships" in result  # New field
        assert "distances_from_my_stars" in result

    def test_query_star_invalid(self, tools):
        """Test querying invalid star raises error."""
        with pytest.raises(ValueError, match="Invalid star reference"):
            tools.query_star("INVALID_STAR")

    def test_estimate_route(self, tools, game):
        """Test route estimation."""
        star1 = game.stars[0]
        star2 = game.stars[1]

        result = tools.estimate_route(star1.id, star2.id)

        # Check structure
        assert "distance" in result
        assert "risk" in result
        assert isinstance(result["distance"], int)
        assert isinstance(result["risk"], float)
        assert 0.0 <= result["risk"] <= 1.0

    def test_estimate_route_invalid_origin(self, tools, game):
        """Test route estimation with invalid origin."""
        with pytest.raises(ValueError, match="Invalid star reference"):
            tools.estimate_route("INVALID", game.stars[0].id)

    def test_estimate_route_invalid_dest(self, tools, game):
        """Test route estimation with invalid destination."""
        with pytest.raises(ValueError, match="Invalid star reference"):
            tools.estimate_route(game.stars[0].id, "INVALID")

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

    def test_memory_query_empty(self, tools):
        """Test querying empty memory."""
        result = tools.memory_query("discovery_log")
        assert result == []

        result = tools.memory_query("battle_log")
        assert result == []

    def test_memory_query_with_filter(self, tools):
        """Test querying memory with filter."""
        # Manually populate for testing (normally auto-populated)
        records = [
            {"turn": 1, "star_id": "A", "ru": 2},
            {"turn": 1, "star_id": "B", "ru": 3},
            {"turn": 2, "star_id": "C", "ru": 1},
        ]
        tools.memory["discovery_log"].extend(records)

        # Filter by turn
        result = tools.memory_query("discovery_log", {"turn": 1})
        assert len(result) == 2

    def test_reset_turn(self, tools):
        """Test resetting turn state."""
        tools.orders_submitted = True
        tools.pending_orders = [Order("A", "B", 1)]

        tools.reset_turn()

        assert tools.orders_submitted is False
        assert tools.pending_orders is None

    def test_tool_definitions_complete(self):
        """Test that all required tools are defined."""
        tool_names = {td["name"] for td in TOOL_DEFINITIONS}

        required_tools = {
            "get_observation",
            "get_ascii_map",
            "query_star",
            "estimate_route",
            "propose_orders",
            "submit_orders",
            "memory_query",
        }

        assert tool_names == required_tools

    def test_stationed_ships_visible_for_owned_stars(self, tools, game):
        """Test that stationed_ships is visible for player-owned stars."""
        # Find a star owned by p2 and set up garrison
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Set garrison and mark as visited
        p2_star.stationed_ships["p2"] = 7
        tools.player.visited_stars.add(p2_star.id)

        obs = tools.get_observation()

        # Find the star in observation
        star_obs = None
        for s in obs["stars"]:
            if s["id"] == p2_star.id:
                star_obs = s
                break

        assert star_obs is not None
        assert star_obs["stationed_ships"] == 7
        assert star_obs["owner"] == "p2"

    def test_stationed_ships_hidden_for_enemy_stars(self, tools, game):
        """Test that stationed_ships is hidden for enemy stars (fog-of-war)."""
        # Find a star owned by p1 (enemy)
        p1_star = None
        for star in game.stars:
            if star.owner == "p1":
                p1_star = star
                break

        if p1_star is None:
            pytest.skip("No p1 star found in test game")

        # Set enemy garrison and mark as visited (so we know ownership/RU)
        p1_star.stationed_ships["p1"] = 10
        tools.player.visited_stars.add(p1_star.id)

        obs = tools.get_observation()

        # Find the star in observation
        star_obs = None
        for s in obs["stars"]:
            if s["id"] == p1_star.id:
                star_obs = s
                break

        assert star_obs is not None
        assert star_obs["stationed_ships"] is None  # Hidden by fog-of-war
        assert star_obs["owner"] == "p1"
        assert star_obs["known_ru"] is not None  # RU is visible (visited)

    def test_stationed_ships_hidden_for_npc_stars(self, tools, game):
        """Test that stationed_ships is hidden for NPC stars (fog-of-war)."""
        # Find an NPC star
        npc_star = None
        for star in game.stars:
            if star.owner == "npc":
                npc_star = star
                break

        if npc_star is None:
            pytest.skip("No NPC star found in test game")

        # Set NPC garrison and mark as visited
        npc_star.stationed_ships["npc"] = 5
        tools.player.visited_stars.add(npc_star.id)

        obs = tools.get_observation()

        # Find the star in observation
        star_obs = None
        for s in obs["stars"]:
            if s["id"] == npc_star.id:
                star_obs = s
                break

        assert star_obs is not None
        assert star_obs["stationed_ships"] is None  # Hidden by fog-of-war
        assert star_obs["owner"] is None  # NPC shown as None
        assert star_obs["known_ru"] is not None  # RU is visible (visited)

    def test_stationed_ships_hidden_for_unvisited_stars(self, tools, game):
        """Test that stationed_ships is hidden for unvisited stars."""
        # Get any star and ensure it's not visited
        star = game.stars[0]
        tools.player.visited_stars.discard(star.id)

        obs = tools.get_observation()

        # Find the star in observation
        star_obs = None
        for s in obs["stars"]:
            if s["id"] == star.id:
                star_obs = s
                break

        assert star_obs is not None
        assert star_obs["stationed_ships"] is None  # Hidden (unvisited)
        assert star_obs["owner"] is None  # Hidden (unvisited)
        assert star_obs["known_ru"] is None  # Hidden (unvisited)
        assert star_obs["last_seen_control"] == "unknown"

    def test_query_star_stationed_ships_for_owned(self, tools, game):
        """Test query_star returns stationed_ships for owned stars."""
        # Find a star owned by p2
        p2_star = None
        for star in game.stars:
            if star.owner == "p2":
                p2_star = star
                break

        if p2_star is None:
            pytest.skip("No p2 star found in test game")

        # Set garrison and mark as visited
        p2_star.stationed_ships["p2"] = 12
        tools.player.visited_stars.add(p2_star.id)

        result = tools.query_star(p2_star.id)

        assert result["stationed_ships"] == 12
        assert result["owner"] == "p2"

    def test_query_star_stationed_ships_hidden_for_enemy(self, tools, game):
        """Test query_star hides stationed_ships for enemy stars."""
        # Find a star owned by p1
        p1_star = None
        for star in game.stars:
            if star.owner == "p1":
                p1_star = star
                break

        if p1_star is None:
            pytest.skip("No p1 star found in test game")

        # Set enemy garrison and mark as visited
        p1_star.stationed_ships["p1"] = 20
        tools.player.visited_stars.add(p1_star.id)

        result = tools.query_star(p1_star.id)

        assert result["stationed_ships"] is None  # Hidden by fog-of-war
        assert result["owner"] == "p1"

    def test_hyperspace_losses_filtered_by_owner(self, tools, game):
        """Test that hyperspace_losses_last_turn only shows player's own losses."""
        # Set up hyperspace losses in game state (simulate turn executor storing them)
        game.hyperspace_losses_last_turn = [
            {
                "fleet_id": "p2-001",
                "owner": "p2",
                "ships": 5,
                "origin": "A",
                "dest": "B",
            },
            {
                "fleet_id": "p1-003",
                "owner": "p1",
                "ships": 8,
                "origin": "C",
                "dest": "D",
            },
            {
                "fleet_id": "p2-007",
                "owner": "p2",
                "ships": 3,
                "origin": "E",
                "dest": "F",
            },
        ]

        obs = tools.get_observation()

        # Check that hyperspace_losses_last_turn field exists
        assert "hyperspace_losses_last_turn" in obs

        # Check that only p2's losses are visible
        losses = obs["hyperspace_losses_last_turn"]
        assert len(losses) == 2  # Only p2's 2 losses, not p1's loss

        # Verify loss details
        loss_ids = {loss["fleet_id"] for loss in losses}
        assert "p2-001" in loss_ids
        assert "p2-007" in loss_ids
        assert "p1-003" not in loss_ids  # Enemy loss hidden

        # Verify structure
        for loss in losses:
            assert "fleet_id" in loss
            assert "origin" in loss
            assert "dest" in loss
            assert "ships_lost" in loss

    def test_hyperspace_losses_empty_when_none(self, tools, game):
        """Test that hyperspace_losses_last_turn is empty when no losses occurred."""
        # Ensure no losses in game state
        game.hyperspace_losses_last_turn = []

        obs = tools.get_observation()

        assert "hyperspace_losses_last_turn" in obs
        assert obs["hyperspace_losses_last_turn"] == []

    def test_npc_combat_shows_npc_not_opp(self, tools, game):
        """Test that NPC combats correctly show 'npc' instead of 'opp'."""
        # Create NPC combat scenario where p2 attacks NPC
        game.combats_last_turn = [
            {
                "star_id": "K",
                "star_name": "Kappa",
                "combat_type": "npc",
                "attacker": "p2",
                "defender": "npc",
                "attacker_ships": 5,
                "defender_ships": 3,
                "attacker_survivors": 4,
                "defender_survivors": 0,
                "attacker_losses": 1,
                "defender_losses": 3,
                "winner": "attacker",
                "control_before": "npc",
                "control_after": "p2",
                "simultaneous": False,
            }
        ]

        observation = tools.get_observation()
        combats = observation.get("combats_last_turn", [])

        assert len(combats) == 1
        combat = combats[0]
        assert combat["attacker"] == "me"  # p2 from p2's perspective
        assert combat["defender"] == "npc"  # Should be 'npc', not 'opp'
        assert combat["control_before"] == "npc"
        assert combat["control_after"] == "me"

    def test_pvp_combat_shows_opp_not_npc(self, tools, game):
        """Test that PvP combats correctly show 'opp' for real opponents."""
        # Create PvP combat scenario where p1 attacks p2
        game.combats_last_turn = [
            {
                "star_id": "M",
                "star_name": "Mu",
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

        observation = tools.get_observation()
        combats = observation.get("combats_last_turn", [])

        assert len(combats) == 1
        combat = combats[0]
        assert combat["attacker"] == "opp"  # p1 from p2's perspective
        assert combat["defender"] == "me"  # p2 from p2's perspective
        assert combat["control_before"] == "me"
        assert combat["control_after"] == "opp"


class TestLLMPlayer:
    """Test suite for LLMPlayer class."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        return generate_map(seed=42)

    @pytest.fixture
    def llm_player(self):
        """Create LLMPlayer with mock client."""
        return LLMPlayer("p2", use_mock=True, verbose=False)

    def test_initialization(self, llm_player):
        """Test LLMPlayer initializes correctly."""
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

    def test_call_tool_get_observation(self, llm_player, game):
        """Test calling get_observation tool."""
        tools = AgentTools(game, "p2")
        result = llm_player._call_tool("get_observation", {}, tools)

        assert "turn" in result
        assert "stars" in result

    def test_call_tool_get_ascii_map(self, llm_player, game):
        """Test calling get_ascii_map tool."""
        tools = AgentTools(game, "p2")
        result = llm_player._call_tool("get_ascii_map", {"view": "current"}, tools)

        assert "map" in result
        assert isinstance(result["map"], str)

    def test_call_tool_query_star(self, llm_player, game):
        """Test calling query_star tool."""
        tools = AgentTools(game, "p2")
        star_id = game.stars[0].id

        result = llm_player._call_tool("query_star", {"star_ref": star_id}, tools)

        assert "id" in result
        assert result["id"] == star_id

    def test_call_tool_estimate_route(self, llm_player, game):
        """Test calling estimate_route tool."""
        tools = AgentTools(game, "p2")
        star1 = game.stars[0].id
        star2 = game.stars[1].id

        result = llm_player._call_tool(
            "estimate_route", {"from_star": star1, "to_star": star2}, tools
        )

        assert "distance" in result
        assert "risk" in result

    def test_call_tool_invalid(self, llm_player, game):
        """Test calling invalid tool raises error."""
        tools = AgentTools(game, "p2")

        with pytest.raises(ValueError, match="Unknown tool"):
            llm_player._call_tool("invalid_tool", {}, tools)


class TestMockBedrockClient:
    """Test suite for MockBedrockClient."""

    def test_initialization(self):
        """Test mock client initializes."""
        client = MockBedrockClient()
        assert client.call_count == 0

    def test_invoke_increments_counter(self):
        """Test that invoke increments call counter."""
        client = MockBedrockClient()
        client.invoke([], "system prompt")

        assert client.call_count == 1

    def test_invoke_returns_response(self):
        """Test that invoke returns proper response structure."""
        client = MockBedrockClient()
        response = client.invoke([], "system prompt")

        assert "response" in response
        assert "tool_calls" in response
        assert "stop_reason" in response
        assert "requires_tool_execution" in response

    def test_invoke_saves_request(self):
        """Test that invoke saves the last request."""
        client = MockBedrockClient()
        messages = [{"role": "user", "content": "test"}]
        system = "test system"
        tools = [{"name": "test_tool"}]

        client.invoke(messages, system, tools)

        assert client.last_request is not None
        assert client.last_request["messages"] == messages
        assert client.last_request["system"] == system
        assert client.last_request["tools"] == tools


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
