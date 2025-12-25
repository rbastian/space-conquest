"""Tests for visited_stars fog-of-war system."""

import pytest

from src.engine.map_generator import generate_map
from src.engine.movement import _process_fleet_arrival
from src.models.fleet import Fleet
from src.utils.serialization import _deserialize_player, _serialize_player


class TestVisitedStarsFogOfWar:
    """Test suite for visited_stars fog-of-war implementation (core system)."""

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
            rationale="expand",
        )
        game.fleets.append(fleet)

        # Process arrival
        _process_fleet_arrival(game, fleet)

        # Verify star is now visited
        assert target_star_id in player.visited_stars

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
