# System Prompt Changelog

This document tracks changes to the AI agent system prompt (`src/agent/prompts.py`).

## Version 2.2.0 - 2025-12-27

### Removed
- **Dynamic Prompt System**: Removed unused dynamic prompt adaptation infrastructure
  - Removed `game_phase` and `threat_level` parameters from `get_system_prompt()`
  - Removed `assess_threat_level()` function from middleware
  - Removed `update_game_context_from_observation()` function from middleware
  - Removed `inject_defensive_urgency()` function from middleware
  - Simplified `GameContext` TypedDict to only track `orders_submitted`
  - Removed CURRENT SITUATION section that was never populated with real data

### Changed
- Prompt is now static (no longer adapts based on game state)
- All game state information comes through the game state JSON in user messages
- Reduced code complexity by removing ~400 lines of unused infrastructure

### Impact
- Cleaner, more maintainable codebase
- No behavioral change (dynamic features were never active due to hardcoded values)
- All 338 tests still passing

---

## Version 2.1.1 - 2025-12-27

### Added
- **Home Defense Priority**: Added explicit guidance in TIMING AND COORDINATION section
  - Emphasized that home defense calculations must ONLY count reinforcements arriving on or before enemy arrival
  - Highlighted with bold formatting to increase visibility
  - Positioned after general timing examples to reinforce the principle for critical home defense scenarios

### Impact
- Should reduce instances where agent miscalculates home defense by counting late reinforcements
- Increases focus on accurate threat assessment for game-ending scenarios

---

## Version 2.1.0 - 2025-12-27

### Added
- **Prompt Versioning**: Added `PROMPT_VERSION` constant and version identifier in prompt text
- **Stronger Tool Requirements**: Enhanced `GAME MECHANICS - TURNS AND MOVEMENT` section
  - Made `calculate_distance` tool usage mandatory with explicit "MUST" language
  - Clarified tool is for NEW moves, not existing in-transit fleets
  - Added explicit instruction: "Do not guess or estimate distances - use the tool"

### Changed
- **TIMING AND COORDINATION Section**: Significantly improved timing guidance
  - Added mandatory "you MUST:" language to emphasize criticality
  - Strengthened "IGNORE" instruction for late-arriving reinforcements
  - Enhanced examples with more detailed explanations
  - Improved specificity for coordinated attacks and expansion planning
  - Better formatting and consistency throughout

### Impact
- Should increase agent's usage of `calculate_distance` tool for planning
- Should improve timing-based decision making and coordination
- Should reduce instances of late reinforcements being counted incorrectly

---

## Version 2.0.0 - 2025-12-20 (estimated)

### Changed
- **Fleet Rationale**: Made rationale field required for all orders
- **Code Quality**: Improved prompt structure and clarity

### From Commit
- `ff4c39f refactor: Make Fleet rationale required and improve code quality`

---

## Version 1.9.0 - 2025-12-19 (estimated)

### Added
- **Garrison Strategy**: Enhanced LLM garrison management guidance
- **Threat Assessment**: Improved threat analysis logic

### Changed
- **Win/Loss Clarity**: Improved victory condition explanations
- **Strategic Reasoning**: Enhanced overall strategic guidance

### From Commit
- `11644f8 feat: Improve LLM garrison strategy and add game configuration UI`
- `985485f feat: Improve LLM strategic reasoning with win/loss clarity and threat analysis`

---

## Version 1.0.0 - Initial Release

### Added
- Core game mechanics documentation
- Victory conditions
- Combat rules (N+1 beats N formula)
- Movement and timing rules
- Tool usage instructions
- Garrison requirements
- Fleet concentration doctrine

### From Commit
- `059b76b feat: Implement LangGraph agent architecture with combat tools`
- Earlier development commits

---

## Changelog Format

Each entry should include:
- **Version Number**: Semantic versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes to prompt structure or fundamental strategy
  - MINOR: New sections, significant enhancements
  - PATCH: Bug fixes, clarifications, minor wording improvements
- **Date**: When the change was committed
- **Categories**: Added, Changed, Deprecated, Removed, Fixed, Impact
- **From Commit**: Git commit hash for reference

## Testing Notes

When updating the prompt:
1. Document the change here with version bump
2. Update `PROMPT_VERSION` constant in `prompts.py`
3. Update version in `SYSTEM_PROMPT_BASE` text
4. Run test games to validate behavioral changes
5. Consider A/B testing for major strategy changes
