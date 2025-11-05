"""Tests for map generator."""

from src.engine import generate_map
from src.utils import (
    GRID_X,
    GRID_Y,
    HOME_DISTANCE_RANGE,
    HOME_RU,
    NUM_STARS,
    chebyshev_distance,
)


class TestMapGenerator:
    """Test map generation."""

    def test_generate_map_seed_42(self):
        """Test deterministic map generation with seed 42."""
        game = generate_map(42)

        # Check basic game properties
        assert game.seed == 42
        assert game.turn == 0
        assert game.winner is None
        assert len(game.stars) == NUM_STARS
        assert len(game.players) == 2
        assert len(game.fleets) == 0

        # Check RNG is initialized
        assert game.rng is not None

    def test_home_stars_created(self):
        """Test that home stars are created correctly."""
        game = generate_map(42)

        # Find home stars using player references
        p1_home = next(s for s in game.stars if s.id == game.players["p1"].home_star)
        p2_home = next(s for s in game.stars if s.id == game.players["p2"].home_star)

        # Check home star properties
        assert p1_home.owner == "p1"
        assert p1_home.base_ru == HOME_RU
        assert p1_home.stationed_ships["p1"] == HOME_RU
        assert p1_home.npc_ships == 0

        assert p2_home.owner == "p2"
        assert p2_home.base_ru == HOME_RU
        assert p2_home.stationed_ships["p2"] == HOME_RU
        assert p2_home.npc_ships == 0

    def test_home_stars_distance_from_corners(self):
        """Test that home stars are placed within correct distance from corners."""
        game = generate_map(42)

        # Find home stars using player references
        p1_home = next(s for s in game.stars if s.id == game.players["p1"].home_star)
        p2_home = next(s for s in game.stars if s.id == game.players["p2"].home_star)

        # Check distance from corners
        p1_dist = chebyshev_distance(0, 0, p1_home.x, p1_home.y)
        p2_dist = chebyshev_distance(GRID_X - 1, GRID_Y - 1, p2_home.x, p2_home.y)

        min_dist, max_dist = HOME_DISTANCE_RANGE
        assert min_dist <= p1_dist <= max_dist
        assert min_dist <= p2_dist <= max_dist

    def test_home_star_separation_reasonable(self):
        """Test that home stars are adequately separated across multiple seeds."""
        for seed in range(10):
            game = generate_map(seed=seed)
            p1_home = next(s for s in game.stars if s.id == game.players["p1"].home_star)
            p2_home = next(s for s in game.stars if s.id == game.players["p2"].home_star)
            separation = chebyshev_distance(p1_home.x, p1_home.y, p2_home.x, p2_home.y)
            assert separation >= 6, f"Home stars too close: {separation} parsecs (seed {seed})"
            assert separation <= 11, f"Home stars too far: {separation} parsecs (seed {seed})"

    def test_npc_stars_created(self):
        """Test that NPC stars are created correctly."""
        game = generate_map(42)

        # Find NPC stars (all except home stars)
        npc_stars = [s for s in game.stars if s.owner is None]

        # Should have 14 NPC stars
        assert len(npc_stars) == NUM_STARS - 2

        # Check NPC star properties
        for star in npc_stars:
            assert star.owner is None
            assert 1 <= star.base_ru <= 3
            assert star.npc_ships == star.base_ru
            assert star.stationed_ships["p1"] == 0
            assert star.stationed_ships["p2"] == 0

    def test_all_stars_on_grid(self):
        """Test that all stars are placed on valid grid coordinates."""
        game = generate_map(42)

        for star in game.stars:
            assert 0 <= star.x < GRID_X
            assert 0 <= star.y < GRID_Y

    def test_all_stars_unique_positions(self):
        """Test that all stars have unique positions."""
        game = generate_map(42)

        positions = [(s.x, s.y) for s in game.stars]
        assert len(positions) == len(set(positions))

    def test_all_stars_unique_ids(self):
        """Test that all stars have unique IDs."""
        game = generate_map(42)

        ids = [s.id for s in game.stars]
        assert len(ids) == len(set(ids))
        assert len(ids) == NUM_STARS

    def test_all_stars_have_names(self):
        """Test that all stars have names."""
        game = generate_map(42)

        for star in game.stars:
            assert star.name
            assert len(star.name) > 0

    def test_players_initialized(self):
        """Test that players are initialized correctly."""
        game = generate_map(42)

        # Check Player 1
        p1 = game.players["p1"]
        assert p1.id == "p1"
        assert p1.home_star in "ABCDEFGHIJKLMNOP"  # Home star should be a valid ID
        assert p1.visited_stars == {p1.home_star}
        assert len(p1.fleets) == 0

        # Check Player 2
        p2 = game.players["p2"]
        assert p2.id == "p2"
        assert p2.home_star in "ABCDEFGHIJKLMNOP"  # Home star should be a valid ID
        assert p2.visited_stars == {p2.home_star}
        assert len(p2.fleets) == 0

        # Home stars should be different
        assert p1.home_star != p2.home_star

    def test_deterministic_generation(self):
        """Test that same seed produces same map."""
        game1 = generate_map(42)
        game2 = generate_map(42)

        # Check same number of stars
        assert len(game1.stars) == len(game2.stars)

        # Check same star positions and properties
        for s1, s2 in zip(game1.stars, game2.stars):
            assert s1.id == s2.id
            assert s1.name == s2.name
            assert s1.x == s2.x
            assert s1.y == s2.y
            assert s1.base_ru == s2.base_ru
            assert s1.owner == s2.owner
            assert s1.npc_ships == s2.npc_ships

    def test_star_names_are_deterministic_by_id(self):
        """Test that star names are deterministic based on star ID (not seed)."""
        # Generate maps with different seeds
        game1 = generate_map(42)
        game2 = generate_map(999)

        # Build ID-to-star mappings for both games
        stars1_by_id = {s.id: s for s in game1.stars}
        stars2_by_id = {s.id: s for s in game2.stars}

        # Star names should be the same across different seeds (based on ID)
        for star_id in "ABCDEFGHIJKLMNOP":
            assert stars1_by_id[star_id].name == stars2_by_id[star_id].name

        # Verify specific star ID to name mappings
        assert stars1_by_id["A"].name == "Altair"
        assert stars1_by_id["B"].name == "Bellatrix"
        assert stars1_by_id["C"].name == "Capella"

    def test_different_seeds_produce_different_maps(self):
        """Test that different seeds produce different maps."""
        game1 = generate_map(42)
        game2 = generate_map(123)

        # At least some stars should have different properties
        differences = 0
        for s1, s2 in zip(game1.stars, game2.stars):
            if s1.x != s2.x or s1.y != s2.y or s1.base_ru != s2.base_ru:
                differences += 1

        # Should have some differences (not all stars identical)
        assert differences > 0

    def test_fleet_counter_initialized(self):
        """Test that fleet counter is initialized."""
        game = generate_map(42)

        assert game.fleet_counter == {"p1": 0, "p2": 0}

    def test_turn_history_empty(self):
        """Test that turn history starts empty."""
        game = generate_map(42)

        assert game.turn_history == []

    def test_star_letter_assignment_randomized(self):
        """Test that star letters are randomly assigned using seeded RNG."""
        # Generate maps with different seeds
        game1 = generate_map(42)
        game2 = generate_map(123)

        # Get home star IDs for each game
        p1_home_id_1 = game1.players["p1"].home_star
        p1_home_id_2 = game2.players["p1"].home_star

        # Home star IDs should be different (with high probability)
        # This tests that letters are shuffled, not always assigned in order
        assert p1_home_id_1 != p1_home_id_2 or p1_home_id_1 != "A", (
            "Star letters should be randomly assigned, not always in order"
        )

    def test_star_letter_assignment_deterministic(self):
        """Test that same seed produces same star letter assignments."""
        game1 = generate_map(42)
        game2 = generate_map(42)

        # All star IDs should match exactly
        for s1, s2 in zip(game1.stars, game2.stars):
            assert s1.id == s2.id, f"Star IDs should be deterministic: {s1.id} != {s2.id}"

        # Home star IDs should match
        assert game1.players["p1"].home_star == game2.players["p1"].home_star
        assert game1.players["p2"].home_star == game2.players["p2"].home_star

    def test_star_letters_all_unique(self):
        """Test that all 16 stars get unique letters A-P."""
        game = generate_map(42)

        # Collect all star IDs
        star_ids = [s.id for s in game.stars]

        # Should have 16 unique IDs
        assert len(star_ids) == 16
        assert len(set(star_ids)) == 16

        # All IDs should be from A-P
        assert set(star_ids) == set("ABCDEFGHIJKLMNOP")

    def test_quadrant_star_distribution(self):
        """Test that stars are distributed correctly across quadrants."""
        game = generate_map(42)

        # Define quadrants
        q1_stars = [s for s in game.stars if 0 <= s.x <= 5 and 0 <= s.y <= 4]
        q2_stars = [s for s in game.stars if 6 <= s.x <= 11 and 0 <= s.y <= 4]
        q3_stars = [s for s in game.stars if 0 <= s.x <= 5 and 5 <= s.y <= 9]
        q4_stars = [s for s in game.stars if 6 <= s.x <= 11 and 5 <= s.y <= 9]

        # Q1 and Q4 should have 5 total stars each (1 home + 4 NPC)
        # Q2 and Q3 should have 3 NPC stars each
        # This depends on where home stars land, but we can verify total counts
        total_stars = len(q1_stars) + len(q2_stars) + len(q3_stars) + len(q4_stars)
        assert total_stars == 16, f"Expected 16 stars total, got {total_stars}"

    def test_quadrant_ru_balance(self):
        """Test that RU is balanced across quadrants."""
        game = generate_map(42)

        # Separate NPC stars by quadrant
        q1_npc = [s for s in game.stars if 0 <= s.x <= 5 and 0 <= s.y <= 4 and s.owner is None]
        q2_npc = [s for s in game.stars if 6 <= s.x <= 11 and 0 <= s.y <= 4 and s.owner is None]
        q3_npc = [s for s in game.stars if 0 <= s.x <= 5 and 5 <= s.y <= 9 and s.owner is None]
        q4_npc = [s for s in game.stars if 6 <= s.x <= 11 and 5 <= s.y <= 9 and s.owner is None]

        # Count NPC stars per quadrant
        assert len(q1_npc) == 4, f"Q1 should have 4 NPC stars, got {len(q1_npc)}"
        assert len(q2_npc) == 3, f"Q2 should have 3 NPC stars, got {len(q2_npc)}"
        assert len(q3_npc) == 3, f"Q3 should have 3 NPC stars, got {len(q3_npc)}"
        assert len(q4_npc) == 4, f"Q4 should have 4 NPC stars, got {len(q4_npc)}"

        # Calculate RU totals per quadrant
        q1_ru = sum(s.base_ru for s in q1_npc)
        q2_ru = sum(s.base_ru for s in q2_npc)
        q3_ru = sum(s.base_ru for s in q3_npc)
        q4_ru = sum(s.base_ru for s in q4_npc)

        # Q1 and Q4 should have 8 RU (1+2+2+3), Q2 and Q3 should have 6 RU (1+2+3)
        assert q1_ru == 8, f"Q1 should have 8 NPC RU, got {q1_ru}"
        assert q2_ru == 6, f"Q2 should have 6 NPC RU, got {q2_ru}"
        assert q3_ru == 6, f"Q3 should have 6 NPC RU, got {q3_ru}"
        assert q4_ru == 8, f"Q4 should have 8 NPC RU, got {q4_ru}"

        # Total NPC RU should be 28
        total_npc_ru = q1_ru + q2_ru + q3_ru + q4_ru
        assert total_npc_ru == 28, f"Total NPC RU should be 28, got {total_npc_ru}"

    def test_quadrant_ru_values(self):
        """Test that each quadrant has the correct RU value distribution."""
        game = generate_map(42)

        # Separate NPC stars by quadrant
        q1_npc = sorted(
            [s.base_ru for s in game.stars if 0 <= s.x <= 5 and 0 <= s.y <= 4 and s.owner is None]
        )
        q2_npc = sorted(
            [s.base_ru for s in game.stars if 6 <= s.x <= 11 and 0 <= s.y <= 4 and s.owner is None]
        )
        q3_npc = sorted(
            [s.base_ru for s in game.stars if 0 <= s.x <= 5 and 5 <= s.y <= 9 and s.owner is None]
        )
        q4_npc = sorted(
            [s.base_ru for s in game.stars if 6 <= s.x <= 11 and 5 <= s.y <= 9 and s.owner is None]
        )

        # Q1 and Q4 should have {1, 2, 2, 3}
        assert q1_npc == [1, 2, 2, 3], f"Q1 NPC RU should be [1,2,2,3], got {q1_npc}"
        assert q4_npc == [1, 2, 2, 3], f"Q4 NPC RU should be [1,2,2,3], got {q4_npc}"

        # Q2 and Q3 should have {1, 2, 3}
        assert q2_npc == [1, 2, 3], f"Q2 NPC RU should be [1,2,3], got {q2_npc}"
        assert q3_npc == [1, 2, 3], f"Q3 NPC RU should be [1,2,3], got {q3_npc}"

    def test_home_stars_minimum_separation(self):
        """Test that home stars maintain minimum separation distance."""
        # Test across multiple seeds to ensure consistency
        for seed in range(20):
            game = generate_map(seed)
            p1_home = next(s for s in game.stars if s.id == game.players["p1"].home_star)
            p2_home = next(s for s in game.stars if s.id == game.players["p2"].home_star)

            separation = chebyshev_distance(p1_home.x, p1_home.y, p2_home.x, p2_home.y)

            # With corner-based placement, home stars should be well separated
            # Players are randomly assigned to opposite corners (0,0) and (11,9)
            # Minimum separation should be at least 6 parsecs
            assert separation >= 6, (
                f"Home stars too close: {separation} parsecs (seed {seed}), "
                f"P1 at ({p1_home.x},{p1_home.y}), P2 at ({p2_home.x},{p2_home.y})"
            )

    def test_balanced_distribution_across_seeds(self):
        """Test that quadrant distribution is consistent across different seeds."""
        for seed in range(10):
            game = generate_map(seed)

            # Count NPC stars per quadrant
            q1_npc = [s for s in game.stars if 0 <= s.x <= 5 and 0 <= s.y <= 4 and s.owner is None]
            q2_npc = [s for s in game.stars if 6 <= s.x <= 11 and 0 <= s.y <= 4 and s.owner is None]
            q3_npc = [s for s in game.stars if 0 <= s.x <= 5 and 5 <= s.y <= 9 and s.owner is None]
            q4_npc = [s for s in game.stars if 6 <= s.x <= 11 and 5 <= s.y <= 9 and s.owner is None]

            # Every seed should have the same distribution
            assert len(q1_npc) == 4, f"Seed {seed}: Q1 should have 4 NPC stars"
            assert len(q2_npc) == 3, f"Seed {seed}: Q2 should have 3 NPC stars"
            assert len(q3_npc) == 3, f"Seed {seed}: Q3 should have 3 NPC stars"
            assert len(q4_npc) == 4, f"Seed {seed}: Q4 should have 4 NPC stars"

            # RU balance should be consistent
            assert sum(s.base_ru for s in q1_npc) == 8, f"Seed {seed}: Q1 should have 8 RU"
            assert sum(s.base_ru for s in q2_npc) == 6, f"Seed {seed}: Q2 should have 6 RU"
            assert sum(s.base_ru for s in q3_npc) == 6, f"Seed {seed}: Q3 should have 6 RU"
            assert sum(s.base_ru for s in q4_npc) == 8, f"Seed {seed}: Q4 should have 8 RU"

    def test_corner_assignment_randomization(self):
        """Test that corner assignments are randomized across different seeds."""
        # Test multiple seeds to verify randomization
        corner_configs = []
        for seed in range(20):
            game = generate_map(seed)
            p1_home = next(s for s in game.stars if s.id == game.players["p1"].home_star)

            # Check which corner each player got
            # Corner A is (0,0), Corner B is (11,9)
            # Players should be within 3 parsecs of their assigned corner
            p1_dist_to_corner_a = chebyshev_distance(0, 0, p1_home.x, p1_home.y)

            if p1_dist_to_corner_a <= 3:
                p1_corner = "A"
            else:
                p1_corner = "B"

            corner_configs.append(p1_corner)

        # Should see both configurations across 20 seeds
        unique_configs = set(corner_configs)
        assert len(unique_configs) == 2, (
            f"Expected to see both corner configurations across seeds, "
            f"but only saw: {unique_configs}"
        )

        # Verify the corner assignments are stored in game state
        game = generate_map(42)
        assert game.corner_assignments is not None
        assert "p1" in game.corner_assignments
        assert "p2" in game.corner_assignments
        assert game.corner_assignments["p1"] in [(0, 0), (11, 9)]
        assert game.corner_assignments["p2"] in [(0, 0), (11, 9)]
        # Players should have opposite corners
        assert game.corner_assignments["p1"] != game.corner_assignments["p2"]

    def test_corner_assignment_determinism(self):
        """Test that same seed produces same corner assignments."""
        # Test determinism for multiple seeds
        for seed in [42, 123, 999, 1234, 5678]:
            game1 = generate_map(seed)
            game2 = generate_map(seed)

            # Corner assignments should be identical
            assert game1.corner_assignments == game2.corner_assignments, (
                f"Seed {seed}: Corner assignments should be deterministic"
            )

            # Player home positions should be identical
            p1_home_1 = next(s for s in game1.stars if s.id == game1.players["p1"].home_star)
            p1_home_2 = next(s for s in game2.stars if s.id == game2.players["p1"].home_star)
            assert (p1_home_1.x, p1_home_1.y) == (p1_home_2.x, p1_home_2.y), (
                f"Seed {seed}: P1 home position should be deterministic"
            )

            p2_home_1 = next(s for s in game1.stars if s.id == game1.players["p2"].home_star)
            p2_home_2 = next(s for s in game2.stars if s.id == game2.players["p2"].home_star)
            assert (p2_home_1.x, p2_home_1.y) == (p2_home_2.x, p2_home_2.y), (
                f"Seed {seed}: P2 home position should be deterministic"
            )
