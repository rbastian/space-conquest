"""Test combat reporting in LLM agent observations."""

import pytest
from src.agent.tools import AgentTools
from src.engine.map_generator import generate_map
from src.engine.turn_executor import TurnExecutor


class TestCombatReporting:
    """Test suite for combat reporting to LLM agents."""

    @pytest.fixture
    def game(self):
        """Create a test game state."""
        game = generate_map(seed=42)
        # Initialize combats_last_turn if not present
        if not hasattr(game, "combats_last_turn"):
            game.combats_last_turn = []
        return game

    def test_pvp_combat_reporting_attacker_wins(self, game):
        """Test that PvP combat is reported correctly when player is attacker."""
        # Setup: Create a combat scenario
        # Find star for combat
        star_b = game.stars[1]

        # Set up combat: p2 attacks star owned by p1
        star_b.owner = "p1"
        star_b.stationed_ships = {"p1": 3, "p2": 5}

        # Execute turn to trigger combat
        executor = TurnExecutor()
        game, combat_events, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

        # Verify combat was stored in game state
        assert len(game.combats_last_turn) > 0

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify combat report is included
        assert "combats_last_turn" in obs
        combats = obs["combats_last_turn"]

        # Should have at least one combat
        assert len(combats) > 0

        # Find the combat at star_b
        combat = None
        for c in combats:
            if c["star"] == star_b.id:
                combat = c
                break

        assert combat is not None, "Combat at star_b should be in report"

        # Verify new enhanced combat structure
        assert "star" in combat
        assert "attacker" in combat
        assert "defender" in combat
        assert "attacker_ships_before" in combat
        assert "defender_ships_before" in combat
        assert "attacker_losses" in combat
        assert "defender_losses" in combat
        assert "control_before" in combat
        assert "control_after" in combat

        # Setup: P1 owned star, P2 arrived with 5 ships (P2 is attacker)
        # P1 defended with 3 ships, P2 won and took control
        assert combat["attacker"] == "me"   # P2 is attacker from P2's perspective
        assert combat["defender"] == "opp"  # P1 is defender from P2's perspective
        assert combat["attacker_ships_before"] == 5  # P2 had 5
        assert combat["defender_ships_before"] == 3  # P1 had 3

        # Verify losses follow combat rules (defender eliminated, attacker loses ceil(loser/2))
        assert combat["attacker_losses"] == 2  # P2 loses ceil(3/2)
        assert combat["defender_losses"] == 3  # P1 eliminated

        # Control should change from opp to me (P2 conquered P1's star)
        assert combat["control_before"] == "opp"  # P1 controlled before
        assert combat["control_after"] == "me"    # P2 controls after

    def test_pvp_combat_reporting_defender_wins(self, game):
        """Test that PvP combat is reported correctly when player is defender."""
        # Setup: Create a combat scenario where p2 defends
        star_b = game.stars[1]

        # Set up combat: p1 attacks star owned by p2
        star_b.owner = "p2"
        star_b.stationed_ships = {"p1": 3, "p2": 5}

        # Execute turn to trigger combat
        executor = TurnExecutor()
        game, combat_events, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify combat report
        combats = obs["combats_last_turn"]

        # Find the combat at star_b
        combat = None
        for c in combats:
            if c["star"] == star_b.id:
                combat = c
                break

        assert combat is not None, "Combat at star_b should be in report"

        # P2 defended with 5 ships against 3 attackers
        # P1 attacks P2's star, so P1=attacker, P2=defender
        assert combat["attacker"] == "opp"  # P1 from P2's perspective
        assert combat["defender"] == "me"   # P2 from P2's perspective
        assert combat["attacker_ships_before"] == 3  # P1 had 3
        assert combat["defender_ships_before"] == 5  # P2 had 5

        # P2 should win (defender wins)
        assert combat["attacker_losses"] == 3  # P1 eliminated
        assert combat["defender_losses"] == 2  # P2 loses ceil(3/2)

        # Control remains with P2 (defender won)
        assert combat["control_before"] == "me"
        assert combat["control_after"] == "me"

    def test_npc_combat_reporting(self, game):
        """Test that NPC combat is reported correctly."""
        # Find an NPC star
        npc_star = None
        for star in game.stars:
            if star.owner is None and star.npc_ships > 0:
                npc_star = star
                break

        if npc_star is None:
            pytest.skip("No NPC star found in test game")

        # Setup: p2 attacks NPC star
        npc_star.stationed_ships = {"p2": 10, "p1": 0}

        # Execute turn to trigger combat
        executor = TurnExecutor()
        game, combat_events, _, _ = executor.execute_turn(game, {"p1": [], "p2": []})

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify combat report
        combats = obs["combats_last_turn"]

        # Find the combat at npc_star
        combat = None
        for c in combats:
            if c["star"] == npc_star.id:
                combat = c
                break

        assert combat is not None, "Combat at NPC star should be in report"

        # Verify p2 participated as attacker
        assert combat["attacker"] == "me"  # P2 is attacker
        assert combat["defender"] == "npc"  # NPC kept distinct from real opponents
        assert combat["attacker_ships_before"] > 0

        # Control before should be None (was NPC)
        assert combat["control_before"] is None

        # Control after NPC combat should be "me" (P2 gains control)
        # When a single player defeats NPC, they immediately gain control
        assert combat["control_after"] == "me"

    def test_no_combat_participation_filtered(self, game):
        """Test that combats where player didn't participate are filtered out."""
        # Setup: Create a combat between p1 and NPC that p2 doesn't participate in
        # This requires manually adding a combat event
        game.combats_last_turn = [
            {
                "star_id": "X",
                "star_name": "Test Star",
                "combat_type": "npc",
                "attacker": "p1",  # p1 attacks, not p2
                "defender": "npc",
                "attacker_ships": 5,
                "defender_ships": 3,
                "winner": "attacker",
                "attacker_survivors": 3,
                "defender_survivors": 0,
                "attacker_losses": 2,
                "defender_losses": 3,
                "control_before": None,
                "control_after": None,
                "simultaneous": False,
            }
        ]

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify p2 doesn't see this combat
        combats = obs["combats_last_turn"]

        # Should be empty since p2 didn't participate
        assert len(combats) == 0

    def test_combat_tie_reporting(self, game):
        """Test that combat ties are reported correctly."""
        # Manually add a tie combat to game state
        game.combats_last_turn = [
            {
                "star_id": "B",
                "star_name": "Beta",
                "combat_type": "pvp",
                "attacker": "p1",
                "defender": "p2",
                "attacker_ships": 5,
                "defender_ships": 5,
                "winner": None,  # Tie
                "attacker_survivors": 0,
                "defender_survivors": 0,
                "attacker_losses": 5,
                "defender_losses": 5,
                "control_before": "p2",
                "control_after": None,  # Becomes uncontrolled after tie
                "simultaneous": False,
            }
        ]

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify combat report
        combats = obs["combats_last_turn"]

        # Should have the tie combat
        assert len(combats) == 1
        combat = combats[0]

        # Verify tie - both sides eliminated
        assert combat["attacker"] == "opp"  # P1 attacked
        assert combat["defender"] == "me"   # P2 defended
        assert combat["attacker_losses"] == 5
        assert combat["defender_losses"] == 5

        # Control becomes uncontrolled after tie
        assert combat["control_after"] is None

    def test_combined_attack_victory(self, game):
        """Test combat reporting when both players defeat NPC together."""
        # Setup: NPC star with both players attacking
        npc_star = game.stars[2]  # Use star C
        npc_star.owner = "npc"
        npc_star.base_ru = 2
        npc_star.stationed_ships = {"npc": 3, "p1": 5, "p2": 8}

        # Mark star as visited by p2
        game.players["p2"].visited_stars.add(npc_star.id)

        # Simulate combined attack combat
        # Both p1 and p2 attacked NPC together and won
        game.combats_last_turn = [
            {
                "star_id": "C",
                "star_name": "Gamma",
                "combat_type": "npc",
                "attacker": "combined",  # Both players
                "defender": "npc",
                "attacker_ships": 13,  # 5 + 8
                "defender_ships": 3,
                "winner": "attacker",
                "attacker_survivors": 10,
                "defender_survivors": 0,
                "attacker_losses": 3,
                "defender_losses": 3,
                "control_before": None,  # Was NPC
                "control_after": None,   # Becomes uncontrolled (both players present)
                "simultaneous": False,
            }
        ]

        # Create agent tools for p2
        tools = AgentTools(game, player_id="p2")
        obs = tools.get_observation()

        # Verify combat report
        combats = obs["combats_last_turn"]

        # Should have the combined attack combat
        assert len(combats) == 1
        combat = combats[0]

        # Verify p2 participated and sees the combat
        assert combat["star"] == "C"

        # For combined attack, p2 sees themselves as attacker
        assert combat["attacker"] == "me"  # Combined treated as "me"
        assert combat["defender"] == "npc"  # NPC kept distinct from real opponents
        assert combat["attacker_ships_before"] == 13  # Combined fleet
        assert combat["defender_ships_before"] == 3  # NPC defenders

        # Verify control changed (NPC defeated)
        assert combat["control_before"] is None  # Was NPC
        assert combat["control_after"] is None   # Becomes uncontrolled

    def test_combined_attack_p1_perspective(self, game):
        """Test that p1 also sees combined attack from their perspective."""
        # Same setup as above but verify p1's view
        npc_star = game.stars[2]
        npc_star.owner = "npc"
        npc_star.stationed_ships = {"npc": 3, "p1": 5, "p2": 8}

        # Mark star as visited by p1
        game.players["p1"].visited_stars.add(npc_star.id)

        game.combats_last_turn = [
            {
                "star_id": "C",
                "star_name": "Gamma",
                "combat_type": "npc",
                "attacker": "combined",
                "defender": "npc",
                "attacker_ships": 13,
                "defender_ships": 3,
                "winner": "attacker",
                "attacker_survivors": 10,
                "defender_survivors": 0,
                "attacker_losses": 3,
                "defender_losses": 3,
                "control_before": None,
                "control_after": None,
                "simultaneous": False,
            }
        ]

        # Create agent tools for p1
        tools = AgentTools(game, player_id="p1")
        obs = tools.get_observation()

        # Verify p1 also sees the combat
        combats = obs["combats_last_turn"]
        assert len(combats) == 1
        combat = combats[0]

        # p1 sees themselves as attacker too (combined attack)
        assert combat["attacker"] == "me"
        assert combat["defender"] == "npc"  # NPC kept distinct from real opponents
        assert combat["control_before"] is None
        assert combat["control_after"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
