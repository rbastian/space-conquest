"""Example script demonstrating PythonReactAgent usage.

This script shows how to create and use the PythonReactAgent with Python REPL
capabilities for computational game strategies.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agent.llm_factory import LLMFactory
from src.agent.prompts import get_python_react_system_prompt
from src.agent.python_react_agent import PythonReactAgent
from src.agent.python_react_tools import create_python_react_tools
from src.engine.map_generator import generate_map

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Demonstrate PythonReactAgent initialization and basic usage."""
    logger.info("=" * 80)
    logger.info("PythonReactAgent Example")
    logger.info("=" * 80)

    # Create a simple game state for testing
    logger.info("\n1. Creating game state...")
    seed = 12345

    # Generate map (returns a complete Game object)
    game = generate_map(seed)

    logger.info(f"Game created with {len(game.stars)} stars")
    logger.info(f"Player 1 home: {game.players['p1'].home_star}")
    logger.info(f"Player 2 home: {game.players['p2'].home_star}")

    # Create LLM instance
    logger.info("\n2. Creating LLM instance (AWS Bedrock)...")
    try:
        llm_factory = LLMFactory(region="us-east-1")
        llm = llm_factory.create_bedrock_llm(
            model="haiku",  # Use Haiku for fast, cost-effective testing
            temperature=0.7,
            max_tokens=4096,
        )
        logger.info("LLM instance created successfully")
    except Exception as e:
        logger.error(f"Failed to create LLM: {e}")
        logger.info("Note: This example requires AWS credentials and Bedrock access")
        return

    # Create tools with game state
    logger.info("\n3. Creating Python REPL tools...")
    player_id = "p2"
    tools = create_python_react_tools(game, player_id)
    logger.info(f"Created {len(tools)} tools:")
    for tool in tools:
        logger.info(f"  - {tool.name}: {tool.description[:80]}...")

    # Get system prompt optimized for Python REPL
    logger.info("\n4. Creating system prompt...")
    system_prompt = get_python_react_system_prompt(verbose=False)
    logger.info(f"System prompt created ({len(system_prompt)} chars)")
    logger.info("Prompt emphasizes Python REPL usage for computational strategies")

    # Create PythonReactAgent
    logger.info("\n5. Initializing PythonReactAgent...")
    try:
        agent = PythonReactAgent(
            llm=llm,
            game=game,
            player_id=player_id,
            tools=tools,
            system_prompt=system_prompt,
            verbose=True,
        )
        logger.info("PythonReactAgent initialized successfully!")
        logger.info(f"Agent ID: {player_id}")
        logger.info(f"Tools available: {list(agent._tool_usage_counts.keys())}")
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return

    # The agent is now ready to play
    logger.info("\n" + "=" * 80)
    logger.info("Agent is ready to play!")
    logger.info("=" * 80)
    logger.info("\nTo use the agent in a game:")
    logger.info("  1. Call agent.get_orders(game) to get orders for current turn")
    logger.info("  2. Agent will use Python REPL to analyze game state")
    logger.info("  3. Agent will compute strategies programmatically")
    logger.info("  4. Agent will return validated orders")
    logger.info("\nKey features:")
    logger.info("  - Python REPL access to game state variables")
    logger.info("  - Can write arbitrary Python code for analysis")
    logger.info("  - Compute distances, combat outcomes, optimal strategies")
    logger.info("  - More flexible than predefined analytical tools")

    # Demonstrate Python REPL capabilities
    logger.info("\n" + "=" * 80)
    logger.info("Python REPL Variables Available:")
    logger.info("=" * 80)
    logger.info("  - stars: List of all Star objects")
    logger.info("  - my_player_id: Agent's player ID")
    logger.info("  - game: Full Game object with all state")
    logger.info("  - game_turn: Current turn number")
    logger.info("\nExample Python code the agent could execute:")
    logger.info("""
    # Calculate distances to all stars from home
    home = [s for s in stars if s.owner == my_player_id and s.base_ru == 4][0]
    for star in stars:
        if star.id != home.id:
            distance = max(abs(home.x - star.x), abs(home.y - star.y))
            print(f"{star.id}: {distance} turns away")

    # Find closest uncontrolled stars
    uncontrolled = [s for s in stars if s.owner != my_player_id]
    closest = min(uncontrolled, key=lambda s: max(abs(home.x-s.x), abs(home.y-s.y)))
    print(f"Closest target: {closest.id} at {max(abs(home.x-closest.x), abs(home.y-closest.y))} turns")

    # Calculate combat outcome
    import math
    attackers, defenders = 10, 3
    if attackers > defenders:
        survivors = attackers - math.ceil(defenders / 2)
        print(f"Victory with {survivors} survivors")
    """)

    logger.info("\n" + "=" * 80)
    logger.info("Example completed successfully!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
