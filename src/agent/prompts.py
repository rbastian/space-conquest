"""System prompts for the LLM agent.

Defines the decision-making framework and constraints for the AI player.
Based on the LLM Player 2 Agent specification.
"""

SYSTEM_PROMPT_BASE = """You are Player 2 in Space Conquest, a turn-based 4X strategy game.

VICTORY CONDITIONS (OFFENSE WINS GAMES):
- You WIN by capturing Player 1's Home Star FIRST.
- You LOSE if Player 1 captures YOUR Home Star FIRST - INSTANT GAME OVER, no recovery.
- This is a RACE: first to capture enemy home wins immediately.
- CRITICAL INSIGHT: The best defense is a strong offense. If you capture their home first, your home's garrison becomes irrelevant.
- Defense is a TRAP: Playing defensively means letting the opponent build up forces. Attack first, attack hard, attack constantly.
- EXCEPTION: If enemy forces are within striking distance (≤3 parsecs) AND you cannot win the race to their home, you MUST defend. Losing your home = instant defeat.

CORE RULES (IMMUTABLE):
- Production: Each star you control automatically produces ships each turn equal to its RU (Home=4 RU; NPC=1–3 RU). Production is automatic - no garrison required.
- Ships move on an 8-direction grid (Chebyshev metric). Diagonals cost the same as orthogonal.
- Hyperspace risk: each turn of travel has a 2% chance of destroying the entire fleet (binary outcome).
- Fleets in hyperspace CANNOT be recalled: Once a fleet departs, it will arrive at its destination (or be destroyed by hyperspace). You cannot change its destination or return it to origin.
- Combat: (N+1) attackers beats N defenders. Attacker loses ceil(N/2), winner takes the star.
- NPC stars start with defenders equal to RU (1 RU = 1 defender, 2 RU = 2 defenders, 3 RU = 3 defenders).
- Combat is simultaneous: fleets arriving on the same turn fight that turn.
- Rebellion: ONLY captured NPC stars with garrison < RU risk rebellion (50% chance each turn). To prevent rebellion, keep garrison >= RU (1 RU star needs 1+ ships, 2 RU needs 2+, 3 RU needs 3+). Home stars NEVER rebel.
- Fog-of-war: you only know RU for stars you control/captured; unknown stars may show known_ru: null. Never invent hidden info.

TURN EXECUTION PHASES:
1. Fleet movement
2. Combat
3. Rebellion check (50% risk if garrison < RU on captured NPC stars)
4. Victory check
5. Submit orders (players send fleets)
6. Production (controlled stars produce new ships = star's RU)

TOOL USAGE (MANDATORY):
- The game state is provided to you at the start of each turn in the user message.
- YOU MUST CALL the submit_orders tool to submit your moves - this is the ONLY way to play!
- Do NOT just write "submit_orders(...)" as text - you must ACTUALLY USE THE TOOL
- The tool validates your orders (catches errors like over-committing ships) and submits them
- If validation fails, the tool returns errors - FIX YOUR ORDERS and call submit_orders again
- Can only be called once per turn (after successful validation)
- NOTE: You no longer need get_observation() tool - state is in user message

MANDATORY COMBAT CALCULATION:
Before submitting any attack order, you MUST calculate the outcome:
1. Combat formula: (N+1) attackers beats N defenders
2. Winner loses ceil(N/2) ships
3. Calculate expected survivors before attacking
4. Never guess - use the formula to verify success

OVERWHELMING FORCE DOCTRINE (CRITICAL):
When attacking stars with UNKNOWN defenders (fog-of-war), use OVERWHELMING FORCE:
- NPC stars have 1-3 defenders (equal to their RU)
- If you don't know the RU, assume WORST CASE (3 defenders)
- To guarantee victory against 3 defenders: send 4+ ships minimum
- NEVER send 2-3 ships to unknown targets - high risk of total loss
- Example: Unknown star could be 1, 2, or 3 RU
  * 2 ships vs 1 defender: WIN (1 survivor) ✓
  * 2 ships vs 2 defenders: WIN (1 survivor) ✓
  * 2 ships vs 3 defenders: LOSS (0 survivors) ✗ WASTED ATTACK
- Better: Send 4 ships (guaranteed win against any NPC garrison)
- Best: Send 5+ ships (guaranteed win with multiple survivors)

Combat Examples:
- Attack 3 RU star with 4 ships: 4 beats 3, you win with 4 - ceil(3/2) = 2 survivors
- Attack 2 RU star with 3 ships: 3 beats 2, you win with 3 - ceil(2/2) = 2 survivors
- Attack unknown star with 4 ships: Guaranteed win against any NPC garrison (1-3)

AGGRESSIVE FORCE CONSOLIDATION:
Your strategy is ATTACK, not defend:
1. Consolidate ALL available ships into one massive battle fleet
2. Keep only minimum garrisons (RU value) at captured stars to prevent rebellions
3. Home star can safely have 0 garrison early game - opponent is 8+ parsecs away
4. BUILD THE BIGGEST FLEET POSSIBLE and march it toward enemy territory
5. The goal is overwhelming force at the enemy's home star, not distributed defense

OUTPUT / ACTION CONTRACT:
Respond with one of:
1. A tool call (when you need info or to validate/submit).
2. Final orders JSON only, in the form:
   {"turn": <int>, "moves": [{"from":"A","to":"B","ships":3}, ...], "strategy_notes": "<short note>"}

Never exceed available ships at the origin.
Keep garrisons ≥ RU on captured NPC stars to prevent rebellions (home stars never rebel, so you can send all ships from home).
Respect fog-of-war; do not fabricate RU or enemy positions.
If you choose to pass, send {"turn": <int>, "moves": []}.

FLEET CONCENTRATION (CRITICAL):
Combat is winner-take-all deterministic. Always send fleets as single concentrated forces:
- One 10-ship fleet beats 5 defenders, loses 3 ships (ceil(5/2)), nets 7 survivors.
- Two 5-ship fleets arriving separately: first fleet (5 vs 5) ties with mutual destruction, second fleet captures with 5 survivors (less efficient).
- RULE: When attacking the same star on the same turn, send ONE combined fleet, not multiple small fleets.
- Exception: Send multiple fleets only if they target DIFFERENT stars or arrive on DIFFERENT turns.

FORCE CONSOLIDATION FOR ATTACK (CRITICAL):
Create ONE overwhelming battle fleet, not scattered garrisons:

OFFENSIVE FORCE POSITIONING:
1. Captured NPC Stars: ONLY minimum garrison (RU value) to prevent rebellion
   - 1 RU star = 1 ship garrison
   - 2 RU star = 2 ships garrison
   - 3 RU star = 3 ships garrison
   - NEVER leave extra ships sitting idle at these stars
2. Home Star: 0 ships early/mid game - send EVERYTHING to attack fleet
   - Production goes directly into attack fleet
   - Don't hoard ships at home, they do nothing there
   - EXCEPTION: If THREAT ASSESSMENT shows CRITICAL threats (enemy within 3 parsecs with superior force), keep sufficient garrison to defend. Losing your home = instant game over.
3. Attack Fleet Assembly Point: ONE star close to enemy territory
   - Consolidate ALL available forces here
   - Keep building this fleet bigger every turn
   - Goal: 20+ ship doomstack that crushes everything

FORCE CONCENTRATION FOR OFFENSE:
Concentrated attack fleet wins games. Scattered garrisons lose games.
- 30 ships in one fleet conquers enemy home
- 10 ships at 3 different stars accomplishes nothing

GOOD EXAMPLE (Aggressive Offense):
- Attack Fleet Staging (J): 28 ships (YOUR MAIN WEAPON)
- Captured star (E): 3 ships (minimum garrison, RU=3)
- Captured star (K): 2 ships (minimum garrison, RU=2)
- Home (D): 0 ships (empty - all production feeds attack fleet)
→ Total: 33 ships, with 28-ship doomstack ready to crush enemy home

BAD EXAMPLE (Passive Defense):
- Home (D): 15 ships (sitting idle, defending nothing)
- Frontline (E): 8 ships (too weak to attack, too strong for garrison)
- Frontline (J): 7 ships (same problem)
- Deep territory (A): 3 ships (wasted)
→ Total: 33 ships, but scattered and accomplishing nothing

TURN LOOP (CONCISE):
1. get_observation() → inspect stars (nearby first via distance_from_home).
2. Prefer shorter routes to reduce hyperspace loss.
3. Maintain garrisons on captured NPC stars.
4. estimate_route() as needed; propose_orders(); fix any errors.
5. submit_orders() once.

Begin by calling get_observation()."""

# Additional instructions for verbose mode (--debug flag)
VERBOSE_REASONING_INSTRUCTIONS = """

REASONING STYLE (Verbose Mode):
Before calling each tool, briefly explain your reasoning and strategic intent.
Example: "I'll check the game state to see my current resources and nearby targets."
After analyzing data, explain your strategic assessment before taking action.
This helps track your decision-making process."""


def get_system_prompt(
    verbose: bool = False,
    game_phase: str | None = None,
    threat_level: str | None = None,
) -> str:
    """Get the system prompt, dynamically adapted to game state.

    The prompt is context-aware and adjusts based on:
    - Game phase (early/mid/late game strategy emphasis)
    - Threat level (defensive vs aggressive posture)

    Args:
        verbose: If True, include instructions to explain reasoning (uses more tokens)
        game_phase: Current game phase ("early", "mid", "late")
        threat_level: Current threat level ("low", "medium", "high", "critical")

    Returns:
        System prompt string adapted to current game context
    """
    prompt = SYSTEM_PROMPT_BASE

    # Add context-specific instructions
    if game_phase or threat_level:
        prompt += "\n\nCURRENT SITUATION ANALYSIS:\n"

        # Phase-specific guidance (state-based like chess, not turn-based)
        if game_phase == "early":
            prompt += (
                "- EARLY GAME (No Enemy Contact): MAXIMUM AGGRESSION. PRIMARY OBJECTIVE: Conquer as many stars as possible "
                "to maximize RU production. Send ALL ships from home immediately - empty your home completely. "
                "No enemy stars detected yet, so you're safe to expand aggressively. Build production advantage NOW so you can "
                "create a massive attack fleet for when you locate the enemy.\n"
            )
        elif game_phase == "mid":
            prompt += (
                "- MID GAME (Enemy Located, Distant): ASSAULT PHASE. PRIMARY OBJECTIVE: Build one massive 20+ ship fleet and march it "
                "toward the enemy home star. You've found enemy territory - now push toward it aggressively. Keep ONLY minimum RU "
                "garrisons at captured stars. Send EVERYTHING else to your main attack fleet. Create ONE forward staging base, "
                "consolidate all forces there, then attack.\n"
            )
        elif game_phase == "late":
            prompt += (
                "- LATE GAME (Enemy Close, ≤3 Parsecs): DECISIVE STRIKE. Enemy is within striking distance - this is the endgame. "
                "Calculate the race: Can you capture their home before they capture yours? If YES: commit fully to overwhelming assault. "
                "If NO: you MUST defend your home while also attacking theirs. Check THREAT ASSESSMENT section - if it shows CRITICAL threats "
                "that will arrive before you can win, split forces: enough ships to defend home + remaining ships to attack their home.\n"
            )

        # Threat-specific guidance (reframed as opportunity)
        if threat_level == "critical":
            prompt += (
                "- ENEMY CLOSE: Enemy forces detected within 2 parsecs! CRITICAL SITUATION:\n"
                "  1. Check THREAT ASSESSMENT section below - if enemy can capture your home before you capture theirs, you MUST defend\n"
                "  2. If defending: Keep enough ships at home to beat incoming attacks (use N+1 formula)\n"
                "  3. Simultaneously: Send remaining ships to counter-attack their positions\n"
                "  4. Find their HOME STAR and race them - first to capture enemy home wins\n"
                "  5. Remember: Losing your home = INSTANT GAME OVER. Defense is mandatory when you're losing the race.\n"
            )
        elif threat_level == "high":
            prompt += (
                "- ENEMY DETECTED: Enemy stars 3-4 parsecs from home - TARGET ACQUIRED! "
                "Build your attack fleet and strike their positions. Their presence reveals the direction "
                "to their home star. Consolidate forces and push toward them aggressively.\n"
            )
        elif threat_level == "medium":
            prompt += (
                "- ENEMY DISTANT: Enemy presence 5-6 parsecs away. Perfect attack range! "
                "Continue expanding toward them, build up your fleet, and prepare for assault. "
                "Create forward staging base and march toward their territory.\n"
            )
        elif threat_level == "low":
            prompt += (
                "- ENEMY LOCATION UNKNOWN: Enemy distant or undetected (7+ parsecs). "
                "Expand aggressively in all directions to find them. Scout toward opposite corner "
                "of map (their likely home). Build fleet strength for eventual assault.\n"
            )

    if verbose:
        prompt += VERBOSE_REASONING_INSTRUCTIONS

    return prompt


def format_game_state_prompt(game, player_id: str) -> str:
    """Format current game state as a readable text prompt for the LLM.

    This replaces the tool-based observation system with a direct text representation
    of the game state, reducing cognitive load and token usage.

    Args:
        game: Current Game object
        player_id: Player ID ("p1" or "p2")

    Returns:
        Formatted text string with complete game state
    """
    player = game.players[player_id]
    opponent_id = "p1" if player_id == "p2" else "p2"
    opponent = game.players[opponent_id]

    # Find home star
    home_star = next((s for s in game.stars if s.id == player.home_star), None)

    # Categorize stars
    my_stars = [s for s in game.stars if s.owner == player_id]
    enemy_stars = [s for s in game.stars if s.owner == opponent_id and s.id in player.visited_stars]
    npc_stars = [s for s in game.stars if s.owner is None and s.id in player.visited_stars]
    unknown_stars = [s for s in game.stars if s.id not in player.visited_stars]

    # Count total ships
    total_ships = sum(star.stationed_ships.get(player_id, 0) for star in my_stars)
    total_ships += sum(f.ships for f in game.fleets if f.owner == player_id)

    # Build prompt
    lines = [
        f"### CURRENT TURN: {game.turn}",
        "",
        "### 1. MY EMPIRE (Known Data)",
        f"* **Home Star:** {home_star.name} ({home_star.id}) at ({home_star.x}, {home_star.y})",
        f"* **Total Ships:** {total_ships}",
        "* **My Stars:**",
    ]

    # My controlled stars
    for star in sorted(my_stars, key=lambda s: s.id):
        ships = star.stationed_ships.get(player_id, 0)
        danger_tag = (
            " [DANGER: Under-garrisoned!]"
            if ships < star.base_ru and star.id != player.home_star
            else ""
        )
        lines.append(
            f"    - {star.name} ({star.id}): Loc({star.x},{star.y}), RU: {star.base_ru}, Ships: {ships}{danger_tag}"
        )

    lines.extend(["", "### 2. KNOWN UNIVERSE"])

    # Enemy stars
    if enemy_stars:
        lines.append("* **Enemy Stars:**")
        # Sort with enemy home star first, then by star ID
        sorted_enemy_stars = sorted(
            enemy_stars,
            key=lambda s: (
                s.id != opponent.home_star,
                s.id,
            ),  # False sorts before True, so home star comes first
        )

        home_garrison = home_star.stationed_ships.get(player_id, 0) if home_star else 0

        for star in sorted_enemy_stars:
            ships = star.stationed_ships.get(opponent_id, 0)

            # Check if this is the enemy's home star (VICTORY OBJECTIVE!)
            is_enemy_home = star.id == opponent.home_star
            home_tag = " [ENEMY HOME STAR - CAPTURE TO WIN!!!]" if is_enemy_home else ""

            if home_star:
                from ..utils.constants import HYPERSPACE_LOSS_PROB
                from ..utils.distance import chebyshev_distance

                dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)

                # Calculate hyperspace loss probability: 1 - (1 - loss_rate)^distance
                hyperspace_survival_prob = (1 - HYPERSPACE_LOSS_PROB) ** dist
                hyperspace_loss_prob = (1 - hyperspace_survival_prob) * 100  # Convert to percentage

                # Determine threat level based on distance and relative force
                if dist <= 3:
                    threat = "CRITICAL" if ships > home_garrison else "HIGH"
                elif dist <= 5:
                    threat = "HIGH" if ships > home_garrison else "MEDIUM"
                elif dist <= 7:
                    threat = "MEDIUM" if ships > home_garrison else "LOW"
                else:
                    threat = "LOW" if ships > home_garrison else "NO THREAT"

                lines.append(
                    f"    - {star.name} ({star.id}): Ships: {ships}, Game turns from our home: {dist}, "
                    f"Hyperspace loss probability: {hyperspace_loss_prob:.2f}%, Threat: {threat}{home_tag}"
                )
            else:
                lines.append(f"    - {star.name} ({star.id}): Ships: {ships}{home_tag}")

    # NPC stars
    if npc_stars:
        lines.append("* **Neutral/NPC Stars:**")
        for star in sorted(npc_stars, key=lambda s: s.id):
            if home_star:
                from ..utils.distance import chebyshev_distance

                dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
                lines.append(
                    f"    - {star.name} ({star.id}): Loc({star.x},{star.y}), RU: {star.base_ru}, Est. Defenders: {star.base_ru}, Distance from home: {dist} parsecs"
                )
            else:
                lines.append(
                    f"    - {star.name} ({star.id}): Loc({star.x},{star.y}), RU: {star.base_ru}, Est. Defenders: {star.base_ru}"
                )

    # Unknown stars
    if unknown_stars:
        lines.append("* **Unknown Stars (Fog-of-War):**")
        for star in sorted(unknown_stars, key=lambda s: s.id):
            # Calculate distance from home
            if home_star:
                from ..utils.distance import chebyshev_distance

                dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
                lines.append(
                    f"    - {star.name} ({star.id}): Loc({star.x},{star.y}), Distance from home: {dist} parsecs"
                )
            else:
                lines.append(f"    - {star.name} ({star.id}): Loc({star.x},{star.y})")

    # Fleets in transit (only show MY fleets - enemy fleet movements are hidden by fog-of-war)
    lines.extend(["", "### 3. FLEETS IN TRANSIT"])
    my_fleets = [f for f in game.fleets if f.owner == player_id]

    if my_fleets:
        lines.append("* **My Fleets:**")
        for fleet in my_fleets:
            dest_star = next((s for s in game.stars if s.id == fleet.dest), None)
            dest_name = dest_star.name if dest_star else fleet.dest
            lines.append(
                f"    - Fleet {fleet.id}: {fleet.ships} ships heading to {dest_name} ({fleet.dest}), arrives in {fleet.dist_remaining} turns"
            )
    else:
        lines.append("* No fleets currently in transit")

    # Threat Assessment (replaces enemy fleet visibility - fog-of-war compliant)
    lines.extend(["", "### 4. THREAT ASSESSMENT"])
    if home_star and enemy_stars:
        from ..utils.distance import chebyshev_distance

        home_garrison = home_star.stationed_ships.get(player_id, 0)

        # Find enemy stars within 4 parsecs that could threaten home
        threats = []
        for star in enemy_stars:
            dist = chebyshev_distance(home_star.x, home_star.y, star.x, star.y)
            if dist <= 4:
                enemy_ships = star.stationed_ships.get(opponent_id, 0)
                if enemy_ships > home_garrison:
                    threats.append((star, dist, enemy_ships))

        if threats:
            lines.append("* **CRITICAL THREATS:**")
            lines.append(f"    - Your home garrison: {home_garrison} ships")
            for star, dist, ships in sorted(threats, key=lambda t: t[1]):  # Sort by distance
                lines.append(
                    f"    - {star.name} ({star.id}): {ships} ships at {dist} parsecs (can attack in {dist} turns)"
                )
            lines.append(
                "* **WARNING:** Enemy forces within striking distance exceed your home defense!"
            )
        else:
            lines.append("* No immediate threats to home star detected")
    else:
        lines.append("* No enemy forces detected yet")

    # Recent events
    lines.extend(["", "### 5. RECENT EVENTS"])
    has_events = False

    if game.combats_last_turn:
        has_events = True
        lines.append("* **Combat Reports:**")
        for combat in game.combats_last_turn:
            if combat.get("star_id") in player.visited_stars:
                star_name = combat.get("star_name", "Unknown")
                attacker = combat.get("attacker")
                defender = combat.get("defender")
                winner = combat.get("winner")

                # Translate to player perspective
                attacker_label = (
                    "You"
                    if attacker == player_id
                    else ("Enemy" if attacker == opponent_id else "NPC")
                )
                defender_label = (
                    "You"
                    if defender == player_id
                    else ("Enemy" if defender == opponent_id else "NPC")
                )

                if winner == "attacker":
                    winner_label = attacker_label
                elif winner == "defender":
                    winner_label = defender_label
                else:
                    winner_label = "Tie (Mutual Destruction)"

                lines.append(
                    f"    - Combat at {star_name}: {attacker_label} vs {defender_label} - Winner: {winner_label}"
                )

    if game.rebellions_last_turn:
        rebellions = [r for r in game.rebellions_last_turn if r.get("star") in player.visited_stars]
        if rebellions:
            has_events = True
            lines.append("* **Rebellions:**")
            for reb in rebellions:
                star_name = reb.get("star_name", "Unknown")
                outcome = reb.get("outcome", "unknown")
                lines.append(f"    - Rebellion at {star_name}: {outcome}")

    if game.hyperspace_losses_last_turn:
        my_losses = [loss for loss in game.hyperspace_losses_last_turn if loss.get("owner") == player_id]
        if my_losses:
            has_events = True
            lines.append("* **Hyperspace Losses:**")
            for loss in my_losses:
                ships = loss.get("ships", 0)
                origin = loss.get("origin", "Unknown")
                dest = loss.get("dest", "Unknown")
                lines.append(
                    f"    - Lost {ships} ships in hyperspace (en route from {origin} to {dest})"
                )

    if not has_events:
        lines.append("* No significant events this turn")

    # Instructions
    lines.extend(
        [
            "",
            "### 6. INSTRUCTIONS",
            "1. Review the board and plan your moves",
            "2. CALL the submit_orders tool with your orders (required - this is the ONLY way to submit!)",
            "3. If the tool returns errors, fix your orders and call submit_orders again",
            "4. Tool validates and submits in one atomic operation",
            "",
            "IMPORTANT: You must ACTUALLY CALL submit_orders(orders=[...]), not write JSON text!",
        ]
    )

    return "\n".join(lines)
