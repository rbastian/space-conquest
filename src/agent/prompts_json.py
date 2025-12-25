"""JSON-formatted prompts for the LLM agent.

This module provides JSON-structured game state prompts for better LLM parsing.
"""

import json


def format_game_state_prompt_json(game, player_id: str) -> str:
    """Format current game state as JSON for the LLM.

    Args:
        game: Current Game object
        player_id: Player ID ("p1" or "p2")

    Returns:
        JSON string with complete game state
    """
    from ..utils.constants import HYPERSPACE_LOSS_PROB
    from ..utils.distance import chebyshev_distance

    player = game.players[player_id]
    opponent_id = "p1" if player_id == "p2" else "p2"
    opponent = game.players[opponent_id]

    # Get my home star
    home_star = next((s for s in game.stars if s.id == player.home_star), None)
    if not home_star:
        return json.dumps({"error": "Home star not found"}, indent=2)

    # Calculate total ships
    total_ships = sum(star.stationed_ships.get(player_id, 0) for star in game.stars)
    total_ships += sum(fleet.ships for fleet in game.fleets if fleet.owner == player_id)

    # Categorize stars
    my_stars = [s for s in game.stars if s.owner == player_id]
    enemy_stars = [s for s in game.stars if s.owner == opponent_id and s.id in player.visited_stars]
    npc_stars = [s for s in game.stars if s.owner == "npc" and s.id in player.visited_stars]
    unknown_stars = [s for s in game.stars if s.id not in player.visited_stars]

    # === SPATIAL AWARENESS ===
    opponent_home_found = opponent.home_star in player.visited_stars
    spatial_awareness = {
        "your_home": {
            "name": home_star.name,
            "id": home_star.id,
            "location": [home_star.x, home_star.y],
        }
    }

    if opponent_home_found:
        opponent_home = next(s for s in game.stars if s.id == opponent.home_star)
        spatial_awareness["opponent_home_discovered"] = True
        spatial_awareness["opponent_home"] = {
            "name": opponent_home.name,
            "id": opponent_home.id,
            "location": [opponent_home.x, opponent_home.y],
            "victory_objective": "CAPTURE THIS STAR TO WIN!",
        }
    else:
        # Determine opponent home candidates
        home_x, home_y = home_star.x, home_star.y

        # Players are always placed in diagonal corners (0,0) and (11,9)
        # Home stars are within Chebyshev distance 3 of corners
        # Corner (0,0): box [0-3, 0-3]
        # Corner (11,9): box [8-11, 6-9]

        if home_x <= 3 and home_y <= 3:
            # Player is in upper-left corner (0,0)
            # Opponent must be in lower-right corner (11,9)
            opponent_x_range, opponent_y_range = "8-11", "6-9"
        else:
            # Player is in lower-right corner (11,9)
            # Opponent must be in upper-left corner (0,0)
            opponent_x_range, opponent_y_range = "0-3", "0-3"

        x_parts = opponent_x_range.split("-")
        x_min, x_max = int(x_parts[0]), int(x_parts[1])
        y_parts = opponent_y_range.split("-")
        y_min, y_max = int(y_parts[0]), int(y_parts[1])

        # Find candidate stars
        possible_opponent_homes = []
        for star in game.stars:
            if x_min <= star.x <= x_max and y_min <= star.y <= y_max:
                if star.id in player.visited_stars:
                    if star.owner == opponent_id and star.id == opponent.home_star:
                        possible_opponent_homes.append(
                            {
                                "name": star.name,
                                "id": star.id,
                                "location": [star.x, star.y],
                                "status": "LIKELY_HOME",
                            }
                        )
                    elif star.owner == opponent_id:
                        possible_opponent_homes.append(
                            {
                                "name": star.name,
                                "id": star.id,
                                "location": [star.x, star.y],
                                "status": "ENEMY_CONTROLLED",
                            }
                        )
                    # else: NPC or our star - don't show
                else:
                    possible_opponent_homes.append(
                        {
                            "name": star.name,
                            "id": star.id,
                            "location": [star.x, star.y],
                            "status": "UNKNOWN",
                        }
                    )

        spatial_awareness["opponent_home_discovered"] = False
        spatial_awareness["opponent_home_candidates"] = possible_opponent_homes
        spatial_awareness["opponent_home_rule"] = (
            "By game rules, opponent's home must be one of the candidate stars listed above"
        )

    # === MY EMPIRE ===
    my_empire_stars = []

    for star in sorted(my_stars, key=lambda s: s.id):
        ships = star.stationed_ships.get(player_id, 0)
        distance_from_home = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)

        star_data = {
            "name": star.name,
            "id": star.id,
            "ru": star.base_ru,
            "ships": ships,
            "distance_from_home": distance_from_home,
            "is_home_star": star.id == player.home_star,
        }

        if ships < star.base_ru and star.id != player.home_star:
            star_data["warning"] = "UNDER_GARRISONED"
            star_data["min_garrison_required"] = star.base_ru

        my_empire_stars.append(star_data)

    # === KNOWN UNIVERSE ===
    known_universe = {}

    # Enemy stars
    if enemy_stars:
        enemy_list = []
        home_garrison = home_star.stationed_ships.get(player_id, 0)

        sorted_enemy_stars = sorted(enemy_stars, key=lambda s: (s.id != opponent.home_star, s.id))

        for star in sorted_enemy_stars:
            ships = star.stationed_ships.get(opponent_id, 0)
            dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)

            hyperspace_survival_prob = (1 - HYPERSPACE_LOSS_PROB) ** dist
            hyperspace_loss_prob = (1 - hyperspace_survival_prob) * 100

            # Determine threat level
            if dist <= 3:
                threat = "CRITICAL" if ships > home_garrison else "HIGH"
            elif dist <= 5:
                threat = "HIGH" if ships > home_garrison else "MEDIUM"
            elif dist <= 7:
                threat = "MEDIUM" if ships > home_garrison else "LOW"
            else:
                threat = "LOW" if ships > home_garrison else "NO_THREAT"

            star_data = {
                "name": star.name,
                "id": star.id,
                "distance_from_home": dist,
                "hyperspace_loss_probability_percent": round(hyperspace_loss_prob, 2),
                "threat_level": threat,
            }

            if star.id == opponent.home_star:
                star_data["is_enemy_home"] = True
                star_data["victory_objective"] = "CAPTURE TO WIN"

            enemy_list.append(star_data)

        known_universe["enemy_stars"] = enemy_list

    # NPC stars
    if npc_stars:
        npc_list = []
        for star in sorted(npc_stars, key=lambda s: s.id):
            dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
            npc_list.append(
                {
                    "name": star.name,
                    "id": star.id,
                    "location": [star.x, star.y],
                    "ru": star.base_ru,
                    "estimated_defenders": star.base_ru,
                    "distance_from_home": dist,
                }
            )
        known_universe["neutral_npc_stars"] = npc_list

    # Unknown stars
    if unknown_stars:
        unknown_list = []
        for star in sorted(unknown_stars, key=lambda s: s.id):
            dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
            unknown_list.append(
                {
                    "name": star.name,
                    "id": star.id,
                    "location": [star.x, star.y],
                    "distance_from_home": dist,
                    "fog_of_war": True,
                }
            )
        known_universe["unknown_stars"] = unknown_list

    # === FLEETS IN TRANSIT ===
    my_fleets = [f for f in game.fleets if f.owner == player_id]
    fleets_data = {"my_fleets": []}

    if my_fleets:
        for fleet in my_fleets:
            origin_star = next((s for s in game.stars if s.id == fleet.origin), None)
            origin_name = origin_star.name if origin_star else fleet.origin
            dest_star = next((s for s in game.stars if s.id == fleet.dest), None)
            dest_name = dest_star.name if dest_star else fleet.dest

            # Calculate when this fleet was ordered by finding original distance
            if origin_star and dest_star:
                original_distance = chebyshev_distance(
                    origin_star.x, origin_star.y, dest_star.x, dest_star.y
                )
                turns_traveled = original_distance - fleet.dist_remaining
                ordered_turn = game.turn - turns_traveled
            else:
                # Fallback if star not found
                ordered_turn = game.turn - 1

            fleet_data = {
                "fleet_id": fleet.id,
                "ships": fleet.ships,
                "origin": {"name": origin_name, "id": fleet.origin},
                "destination": {"name": dest_name, "id": fleet.dest},
                "ordered_turn": ordered_turn,
                "turns_until_arrival": fleet.dist_remaining,
                "arrival_turn": game.turn + fleet.dist_remaining,
                "rationale": fleet.rationale,
            }
            fleets_data["my_fleets"].append(fleet_data)

    # === ENEMY INTELLIGENCE ===
    enemy_intelligence = {"last_known_positions": []}

    if home_star and game.combats_history:
        enemy_positions = {}

        for turn_offset, combat_list in enumerate(reversed(game.combats_history)):
            turn_number = game.turn - 1 - turn_offset

            for combat in combat_list:
                if combat.get("combat_type") != "pvp":
                    continue
                if combat.get("star_id") not in player.visited_stars:
                    continue

                star_id = combat.get("star_id")
                attacker = combat.get("attacker")
                defender = combat.get("defender")
                winner = combat.get("winner")

                enemy_ships = None
                if attacker == opponent_id and winner == "attacker":
                    enemy_ships = combat.get("attacker_survivors", 0)
                elif defender == opponent_id and winner == "defender":
                    enemy_ships = combat.get("defender_survivors", 0)
                elif attacker == opponent_id or defender == opponent_id:
                    enemy_ships = 0

                if enemy_ships is not None and (
                    star_id not in enemy_positions or turn_number > enemy_positions[star_id][1]
                ):
                    star = next((s for s in game.stars if s.id == star_id), None)
                    if star:
                        distance = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
                        enemy_positions[star_id] = (star.name, enemy_ships, turn_number, distance)

        if enemy_positions:
            sorted_positions = sorted(enemy_positions.values(), key=lambda x: x[3])
            for star_name, ships, turn_seen, distance in sorted_positions:
                enemy_intelligence["last_known_positions"].append(
                    {
                        "star_name": star_name,
                        "enemy_ships": ships,
                        "distance_from_home": distance,
                        "turn_observed": turn_seen,
                        "turns_ago": game.turn - turn_seen,
                    }
                )

    # === RECENT EVENTS ===
    recent_events = {}

    # Combat reports (PvP only)
    pvp_combats = [
        c
        for c in game.combats_last_turn
        if c.get("combat_type") == "pvp" and c.get("star_id") in player.visited_stars
    ]

    if pvp_combats:
        combat_reports = []
        for combat in pvp_combats:
            star_name = combat.get("star_name", "Unknown")
            attacker = combat.get("attacker")
            defender = combat.get("defender")
            winner = combat.get("winner")
            attacker_ships = combat.get("attacker_ships", 0)
            defender_ships = combat.get("defender_ships", 0)

            if winner == "attacker":
                survivors = combat.get("attacker_survivors", 0)
            elif winner == "defender":
                survivors = combat.get("defender_survivors", 0)
            else:
                survivors = 0

            report = {
                "location": star_name,
                "you_were": "attacker" if attacker == player_id else "defender",
                "your_ships": attacker_ships if attacker == player_id else defender_ships,
                "enemy_ships": defender_ships if attacker == player_id else attacker_ships,
                "outcome": "victory"
                if (winner == "attacker" and attacker == player_id)
                or (winner == "defender" and defender == player_id)
                else ("defeat" if winner else "tie"),
                "survivors": survivors,
            }
            combat_reports.append(report)
        recent_events["combat_reports"] = combat_reports

    # Rebellions
    if game.rebellions_last_turn:
        rebellions = [r for r in game.rebellions_last_turn if r.get("star") in player.visited_stars]
        if rebellions:
            rebellion_list = []
            for reb in rebellions:
                rebellion_list.append(
                    {
                        "star_name": reb.get("star_name", "Unknown"),
                        "outcome": reb.get("outcome", "unknown"),
                    }
                )
            recent_events["rebellions"] = rebellion_list

    # Hyperspace losses
    if game.hyperspace_losses_last_turn:
        my_losses = [
            loss for loss in game.hyperspace_losses_last_turn if loss.get("owner") == player_id
        ]
        if my_losses:
            loss_list = []
            for loss in my_losses:
                loss_list.append(
                    {
                        "ships_lost": loss.get("ships", 0),
                        "origin": loss.get("origin", "Unknown"),
                        "destination": loss.get("dest", "Unknown"),
                    }
                )
            recent_events["hyperspace_losses"] = loss_list

    # Calculate totals for my empire
    total_production = sum(star.base_ru for star in my_stars)
    num_stars = len(my_stars)

    # === BUILD FINAL JSON ===
    game_state = {
        "turn": game.turn,
        "my_empire": {
            "controlled_stars": my_empire_stars,
            "fleets_in_transit": fleets_data["my_fleets"],
            "totals": {"stars": num_stars, "ships": total_ships, "production_ru": total_production},
        },
        "opponent": {
            "visible_stars": known_universe.get("enemy_stars", []),
            "last_known_positions": enemy_intelligence.get("last_known_positions", []),
        },
        "neutral_territory": {
            "npc_stars": known_universe.get("neutral_npc_stars", []),
            "unexplored_stars": known_universe.get("unknown_stars", []),
        },
        "map_awareness": spatial_awareness,
        "recent_events": recent_events
        if recent_events
        else {"message": "No significant events this turn"},
        "instructions": [
            "Review the game state data above, focusing on my_empire, opponent, and recent_events",
            "If enemy positions are detected in opponent intelligence, assess their threat level before planning",
            "Plan your strategic moves based on the data",
            "CALL the submit_orders tool with your orders array",
            "Each order must have: from (star ID), to (star ID), ships (integer), rationale (optional: attack, reinforce, expand, probe, retreat, consolidate)",
            "If tool returns errors, fix your orders and call submit_orders again",
            "IMPORTANT: You must ACTUALLY CALL the submit_orders tool - do not write JSON text as a response",
        ],
    }

    return json.dumps(game_state, indent=2)
