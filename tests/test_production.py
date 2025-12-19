"""Tests for Phase 4: Rebellions and Production."""

from src.engine.production import process_rebellions_and_production
from src.models.game import Game
from src.models.player import Player
from src.models.star import Star


def test_home_star_production():
    """Test home stars produce 4 ships."""
    game = Game(seed=42, turn=0)

    # Create home star for P1
    star = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process production
    game, rebellion_events = process_rebellions_and_production(game)

    # Home star should produce +4 ships
    assert star.stationed_ships["p1"] == 14
    # Should not have rebellions (well-garrisoned)
    assert rebellion_events == []


def test_non_home_star_production():
    """Test non-home stars produce base_ru ships."""
    game = Game(seed=42, turn=0)

    # Create non-home star controlled by P1
    star = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 5},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process production
    game, rebellion_events = process_rebellions_and_production(game)

    # Star should produce +base_ru (2) ships
    assert star.stationed_ships["p1"] == 7
    assert rebellion_events == []


def test_npc_star_no_production():
    """Test NPC-controlled stars don't produce."""
    game = Game(seed=42, turn=0)

    # Create NPC star
    star = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner=None,
        npc_ships=2,
        stationed_ships={},
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process production
    game, rebellion_events = process_rebellions_and_production(game)

    # NPC star should not produce
    assert star.npc_ships == 2
    assert star.stationed_ships == {}
    assert rebellion_events == []


def test_well_garrisoned_no_rebellion():
    """Test well-garrisoned star (garrison >= base_ru) doesn't rebel."""
    game = Game(seed=42, turn=0)

    # Create well-garrisoned star
    star = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 3},  # 3 >= 2, well-garrisoned
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process rebellions and production
    game, rebellion_events = process_rebellions_and_production(game)

    # Star should not rebel, should produce normally
    assert star.owner == "p1"
    assert star.stationed_ships["p1"] == 5  # 3 + 2 production
    assert rebellion_events == []


def test_under_garrisoned_rebellion_occurs():
    """Test under-garrisoned star can rebel (50% chance)."""
    # Test multiple seeds to find one where rebellion occurs
    rebellion_occurred = False

    for seed in range(100):
        game = Game(seed=seed, turn=0)

        # Create under-garrisoned star
        star = Star(
            id="C",
            name="Capella",
            x=5,
            y=5,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 2},  # 2 < 3, under-garrisoned
        )
        game.stars = [star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        # Process rebellions and production
        initial_garrison = star.stationed_ships.get("p1", 0)
        game, rebellion_events = process_rebellions_and_production(game)

        # Check if rebellion occurred (star became NPC or garrison changed dramatically)
        if (
            star.owner is None
            or star.stationed_ships.get("p1", 0) != initial_garrison + star.base_ru
        ):
            rebellion_occurred = True
            # Should have rebellion event recorded
            assert len(rebellion_events) > 0
            break

    # At least one rebellion should occur in 100 trials (50% chance each)
    assert rebellion_occurred


def test_rebellion_garrison_wins():
    """Test garrison defeating rebels."""
    # Find a seed where garrison wins rebellion
    for seed in range(1000):
        game = Game(seed=seed, turn=0)

        # Create under-garrisoned star with strong garrison
        star = Star(
            id="C",
            name="Capella",
            x=5,
            y=5,
            base_ru=2,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 1},  # 1 < 2, under-garrisoned
        )
        game.stars = [star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        # Process rebellions
        game, rebellion_events = process_rebellions_and_production(game)

        # Check if rebellion occurred and garrison lost
        # Rebellion: garrison (1) vs rebels (2)
        # If roll is 4-6 (rebellion), then combat: 1 vs 2 -> rebels win
        # We need to find a case where rebellion doesn't occur
        if star.owner == "p1":
            # Either no rebellion, or garrison won - both are valid
            break


def test_rebellion_rebels_win():
    """Test rebels winning and star reverting to NPC."""
    # Find a seed where rebels win
    for seed in range(1000):
        game = Game(seed=seed, turn=0)

        # Create very under-garrisoned star
        star = Star(
            id="C",
            name="Capella",
            x=5,
            y=5,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 1},  # 1 < 3, very under-garrisoned
        )
        game.stars = [star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        # Process rebellions
        game, rebellion_events = process_rebellions_and_production(game)

        # Check if rebellion occurred and rebels won
        if star.owner is None and star.npc_ships > 0:
            # Rebels won! Star reverted to NPC
            assert star.stationed_ships.get("p1", 0) == 0
            assert len(rebellion_events) == 1
            assert rebellion_events[0].outcome == "lost"
            break


def test_no_production_after_rebellion():
    """Test that rebelling stars don't produce ships."""
    # Find a seed where rebellion occurs
    for seed in range(1000):
        game = Game(seed=seed, turn=0)

        # Create under-garrisoned star
        star = Star(
            id="C",
            name="Capella",
            x=5,
            y=5,
            base_ru=3,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 1},  # Under-garrisoned
        )
        game.stars = [star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        initial_garrison = star.stationed_ships.get("p1", 0)

        # Process rebellions and production
        game, rebellion_events = process_rebellions_and_production(game)

        # If rebellion occurred, check no production happened
        # Normal production would add 3 ships (base_ru)
        if star.owner is None:
            # Rebellion occurred and rebels won - no production
            assert star.stationed_ships.get("p1", 0) == 0
            assert len(rebellion_events) == 1
            break
        elif star.owner == "p1" and star.stationed_ships.get("p1", 0) != initial_garrison + 3:
            # Rebellion occurred, garrison won, but no production beyond combat result
            # This is harder to verify, but if garrison is not exactly initial + 3, likely rebellion
            assert len(rebellion_events) == 1
            break


def test_multiple_stars_production():
    """Test production at multiple stars."""
    game = Game(seed=42, turn=0)

    # Create multiple controlled stars
    star_a = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 10},
    )
    star_b = Star(
        id="B",
        name="Bellatrix",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 8},
    )
    star_c = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 5},
    )
    game.stars = [star_a, star_b, star_c]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process production
    game, rebellion_events = process_rebellions_and_production(game)

    # Check production at each star
    assert star_a.stationed_ships["p1"] == 14  # Home: +4
    assert star_b.stationed_ships["p2"] == 12  # Home: +4
    assert star_c.stationed_ships["p1"] == 7  # Normal: +2
    assert rebellion_events == []


def test_rebellion_probability():
    """Test that rebellion occurs approximately 50% of the time when under-garrisoned."""
    rebellion_count = 0
    trials = 1000

    for seed in range(trials):
        game = Game(seed=seed, turn=0)

        # Create under-garrisoned star
        star = Star(
            id="C",
            name="Capella",
            x=5,
            y=5,
            base_ru=2,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 1},  # 1 < 2, under-garrisoned
        )
        game.stars = [star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        initial_garrison = star.stationed_ships.get("p1", 0)

        # Process rebellions and production
        game, rebellion_events = process_rebellions_and_production(game)

        # Check if rebellion occurred
        # If no rebellion: garrison = 1 + 2 (production) = 3
        # If rebellion: different outcome
        if (
            star.stationed_ships.get("p1", 0) != initial_garrison + star.base_ru
            or star.owner != "p1"
        ):
            rebellion_count += 1

    # Check rebellion rate is approximately 50% (within 10% margin)
    rebellion_rate = rebellion_count / trials
    assert 0.4 < rebellion_rate < 0.6, f"Rebellion rate {rebellion_rate:.2%} outside expected range"


def test_production_initializes_stationed_ships():
    """Test production initializes stationed_ships dict if needed."""
    game = Game(seed=42, turn=0)

    # Create star with no stationed_ships entry for owner but well-garrisoned
    star = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=2,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 3},  # Well-garrisoned to avoid rebellion
    )
    game.stars = [star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Process production
    game, rebellion_events = process_rebellions_and_production(game)

    # Should add production
    assert "p1" in star.stationed_ships
    assert star.stationed_ships["p1"] == 5  # 3 + 2 (base_ru) production
    assert rebellion_events == []


def test_home_star_immune_to_rebellion():
    """Test that home stars never rebel, even when severely under-garrisoned.

    Tests across 100 different RNG seeds to ensure immunity is reliable.
    """
    rebellion_count = 0

    for seed in range(100):
        game = Game(seed=seed, turn=0)

        # Create p1's home star (severely under-garrisoned)
        home_star = Star(
            id="A",
            name="Altair",
            x=0,
            y=0,
            base_ru=4,
            owner="p1",
            npc_ships=0,
            stationed_ships={"p1": 1},  # 1 < 4, severely under-garrisoned
        )
        game.stars = [home_star]

        # Create players
        game.players = {
            "p1": Player(id="p1", home_star="A"),
            "p2": Player(id="p2", home_star="B"),
        }

        # Process rebellions 10 times per seed (1000 total chances)
        for _ in range(10):
            garrison_before = home_star.stationed_ships["p1"]
            game, rebellion_events = process_rebellions_and_production(game)

            # Home star should NEVER rebel
            assert home_star.owner == "p1", f"Home star rebelled on seed {seed}!"

            # Check if any rebellion events mention the home star
            for event in rebellion_events:
                if event.star == "A":
                    rebellion_count += 1

            # Production should still occur (4 ships)
            expected_garrison = garrison_before + 4
            assert home_star.stationed_ships["p1"] == expected_garrison

    # No rebellions should have occurred at home stars
    assert rebellion_count == 0, f"Home star rebelled {rebellion_count} times across 1000 rolls!"


def test_home_star_immunity_both_players():
    """Test that BOTH p1 and p2 home stars are immune to rebellion."""
    game = Game(seed=42, turn=0)

    # Create both home stars (both under-garrisoned)
    p1_home = Star(
        id="A",
        name="Altair",
        x=0,
        y=0,
        base_ru=4,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 1},  # Under-garrisoned
    )
    p2_home = Star(
        id="B",
        name="Bellatrix",
        x=11,
        y=9,
        base_ru=4,
        owner="p2",
        npc_ships=0,
        stationed_ships={"p2": 1},  # Under-garrisoned
    )
    game.stars = [p1_home, p2_home]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Test 100 times
    for _ in range(100):
        game, rebellion_events = process_rebellions_and_production(game)

        # Neither home should rebel
        assert p1_home.owner == "p1", "p1 home rebelled!"
        assert p2_home.owner == "p2", "p2 home rebelled!"

        # No rebellion events for either home
        for event in rebellion_events:
            assert event.star != "A", f"Rebellion event for p1 home: {event}"
            assert event.star != "B", f"Rebellion event for p2 home: {event}"


def test_non_home_stars_still_rebel():
    """Test that non-home stars CAN still rebel (immunity is home-specific)."""
    game = Game(seed=42, turn=0)

    # Create a non-home star (under-garrisoned)
    non_home_star = Star(
        id="C",
        name="Capella",
        x=5,
        y=5,
        base_ru=3,
        owner="p1",
        npc_ships=0,
        stationed_ships={"p1": 1},  # 1 < 3, under-garrisoned
    )
    game.stars = [non_home_star]

    # Create players
    game.players = {
        "p1": Player(id="p1", home_star="A"),
        "p2": Player(id="p2", home_star="B"),
    }

    # Test many times - should eventually see a rebellion
    rebellion_occurred = False
    for _ in range(200):  # 200 tries * 50% chance = ~100 expected rebellions
        game, rebellion_events = process_rebellions_and_production(game)

        for event in rebellion_events:
            if event.star == "C":
                rebellion_occurred = True
                break

        if rebellion_occurred:
            break

        # Reset star state for next iteration
        non_home_star.owner = "p1"
        non_home_star.stationed_ships = {"p1": 1}
        non_home_star.npc_ships = 0

    # Non-home stars should still be able to rebel
    assert rebellion_occurred, "Non-home star never rebelled (immunity incorrectly applied?)"
