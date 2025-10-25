"""Tests for visited_stars fog-of-war system."""

import pytest
from src.models.fleet import Fleet
from src.agent.tools import AgentTools
from src.engine.map_generator import generate_map
from src.engine.movement import _process_fleet_arrival
from src.utils.serialization import _serialize_player, _deserialize_player


class TestVisitedStarsFogOfWar:
    """Test suite for visited_stars fog-of-war implementation."""

    def test_home_star_initialized_as_visited(self):
        """Test that home stars are marked as visited at game start."""
        game = generate_map(seed=42)

        p1 = game.players["p1"]
        p2 = game.players["p2"]

        # Both players should have their home stars visited
        assert p1.home_star in p1.visited_stars
        assert p2.home_star in p2.visited_stars

        # Should only have 1 visited star each at start
        assert len(p1.visited_stars) == 1
        assert len(p2.visited_stars) == 1

    def test_unvisited_stars_show_no_details(self):
        """Test that unvisited stars show None for RU and owner."""
        game = generate_map(seed=42)
        tools = AgentTools(game, player_id="p2")

        obs = tools.get_observation()

        # Find an unvisited star (not home star)
        home_star = game.players["p2"].home_star
        unvisited_stars = [s for s in obs["stars"] if s["id"] != home_star]

        assert len(unvisited_stars) > 0, "Should have unvisited stars"

        for star in unvisited_stars:
            assert star["known_ru"] is None, f"Star {star['id']} should have unknown RU"
            # Owner should be None for unvisited stars (fog-of-war)
            assert star["owner"] is None, f"Star {star['id']} should have unknown owner"
            assert star["last_seen_control"] == "unknown", (
                f"Star {star['id']} should have unknown control"
            )

    def test_fleet_arrival_marks_star_visited(self):
        """Test that fleet arrival adds star to visited_stars."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Create a fleet arriving at an unvisited star
        target_star_id = None
        for star in game.stars:
            if star.id not in player.visited_stars:
                target_star_id = star.id
                break

        assert target_star_id is not None, "Should have unvisited stars"

        # Create fleet
        fleet = Fleet(
            id="test_fleet",
            owner="p2",
            ships=5,
            origin=player.home_star,
            dest=target_star_id,
            dist_remaining=0,  # Arriving this turn
        )
        game.fleets.append(fleet)

        # Process arrival
        _process_fleet_arrival(game, fleet)

        # Verify star is now visited
        assert target_star_id in player.visited_stars

    def test_visited_star_shows_real_time_ru(self):
        """Test that visited stars show current (real-time) RU values."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Mark a non-home star as visited
        target_star = None
        for star in game.stars:
            if star.id != player.home_star:
                target_star = star
                break

        player.visited_stars.add(target_star.id)

        # Get observation
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Find the star in observation
        obs_star = next((s for s in obs["stars"] if s["id"] == target_star.id), None)
        assert obs_star is not None

        # Should show real-time RU value
        assert obs_star["known_ru"] == target_star.base_ru

    def test_ascii_map_respects_visited_stars(self):
        """Test that ASCII map only shows RU for visited stars."""
        game = generate_map(seed=42)
        player = game.players["p2"]
        tools = AgentTools(game, player_id="p2")

        # Mark only home star as visited (initial state)
        ascii_map = tools.get_ascii_map()

        # Home star should show RU
        home_star = game.players["p2"].home_star
        home_star_obj = next(s for s in game.stars if s.id == home_star)

        # Should contain home star with RU (e.g., "B4")
        assert f"{home_star}{home_star_obj.base_ru}" in ascii_map.replace(" ", "")

        # Unvisited stars should show '?' (e.g., "C?")
        unvisited = [s for s in game.stars if s.id not in player.visited_stars]
        for star in unvisited[:3]:  # Check first 3
            assert f"{star.id}?" in ascii_map.replace(" ", "")

    def test_query_star_unvisited_returns_partial_info(self):
        """Test that query_star returns partial info for unvisited stars."""
        game = generate_map(seed=42)
        player = game.players["p2"]
        tools = AgentTools(game, player_id="p2")

        # Find unvisited star
        unvisited_star = None
        for star in game.stars:
            if star.id not in player.visited_stars:
                unvisited_star = star
                break

        assert unvisited_star is not None

        # Query unvisited star
        result = tools.query_star(unvisited_star.id)

        assert result["visited"] is False
        assert result["known_ru"] is None
        assert result["owner"] is None
        assert "note" in result
        assert "not been visited" in result["note"]

    def test_query_star_visited_returns_full_info(self):
        """Test that query_star returns full info for visited stars."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Visit a star
        target_star = None
        for star in game.stars:
            if star.id != player.home_star:
                target_star = star
                break

        player.visited_stars.add(target_star.id)

        tools = AgentTools(game, player_id="p2")
        result = tools.query_star(target_star.id)

        assert result["visited"] is True
        assert result["known_ru"] == target_star.base_ru
        # Owner should be revealed (could be None if unowned)
        if target_star.owner == "p2":
            assert result["owner"] == "p2"
        elif target_star.owner == "p1":
            assert result["owner"] == "p1"
        else:
            assert result["owner"] is None
        assert "note" not in result or "not been visited" not in result.get("note", "")

    def test_multiple_fleets_same_star_visits_once(self):
        """Test that multiple fleets to same star only visit once (set property)."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        target_star = None
        for star in game.stars:
            if star.id not in player.visited_stars:
                target_star = star
                break

        # Add star 3 times (simulating 3 fleet arrivals)
        player.visited_stars.add(target_star.id)
        player.visited_stars.add(target_star.id)
        player.visited_stars.add(target_star.id)

        # Should only appear once (set property)
        assert len([s for s in player.visited_stars if s == target_star.id]) == 1

    def test_serialization_preserves_visited_stars(self):
        """Test that visited_stars survives serialization round-trip."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Add some visited stars
        for star in game.stars[:5]:
            player.visited_stars.add(star.id)

        # Serialize
        player_data = _serialize_player(player)

        # Deserialize
        restored_player = _deserialize_player(player_data)

        # Should have same visited stars
        assert restored_player.visited_stars == player.visited_stars

    def test_home_star_shows_full_info(self):
        """Test that home star always shows full information."""
        game = generate_map(seed=42)
        tools = AgentTools(game, player_id="p2")

        obs = tools.get_observation()

        # Find home star in observation
        home_star_id = game.players["p2"].home_star
        home_star_obs = next((s for s in obs["stars"] if s["id"] == home_star_id), None)

        assert home_star_obs is not None
        assert home_star_obs["owner"] == "p2"
        assert home_star_obs["known_ru"] is not None
        assert home_star_obs["last_seen_control"] == "controlled"
        assert home_star_obs["is_home"] is True

    def test_visited_star_shows_ownership_changes(self):
        """Test that visited stars show real-time ownership (not stale data)."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Find a neutral star and mark it visited
        neutral_star = None
        for star in game.stars:
            if star.owner is None and star.id != player.home_star:
                neutral_star = star
                break

        assert neutral_star is not None
        player.visited_stars.add(neutral_star.id)

        # Check initial observation
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()
        star_obs = next((s for s in obs["stars"] if s["id"] == neutral_star.id), None)
        assert star_obs["owner"] is None
        assert star_obs["last_seen_control"] == "neutral"

        # Simulate capture by p2
        neutral_star.owner = "p2"
        neutral_star.npc_ships = 0

        # Get new observation - should show real-time ownership
        obs = tools.get_observation()
        star_obs = next((s for s in obs["stars"] if s["id"] == neutral_star.id), None)
        assert star_obs["owner"] == "p2"
        assert star_obs["last_seen_control"] == "controlled"

    def test_visited_star_shows_ru_changes(self):
        """Test that visited stars show real-time RU changes."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Visit a star
        target_star = game.stars[2]  # Pick a non-home star
        player.visited_stars.add(target_star.id)

        # Get initial RU
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()
        star_obs = next((s for s in obs["stars"] if s["id"] == target_star.id), None)
        initial_ru = star_obs["known_ru"]

        # Change star RU
        new_ru = initial_ru + 5
        target_star.base_ru = new_ru

        # Get new observation - should show updated RU
        obs = tools.get_observation()
        star_obs = next((s for s in obs["stars"] if s["id"] == target_star.id), None)
        assert star_obs["known_ru"] == new_ru

    def test_opponent_star_unvisited_hides_details(self):
        """Test that opponent's home star is hidden until visited."""
        game = generate_map(seed=42)
        player = game.players["p2"]

        # Remove opponent's home star from visited set
        opponent_home = game.players["p1"].home_star
        player.visited_stars.discard(opponent_home)

        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Find opponent's home star in observation
        opp_star_obs = next((s for s in obs["stars"] if s["id"] == opponent_home), None)

        assert opp_star_obs is not None
        assert opp_star_obs["owner"] is None  # Hidden due to fog-of-war
        assert opp_star_obs["known_ru"] is None  # Hidden
        assert opp_star_obs["last_seen_control"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
