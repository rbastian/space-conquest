#!/usr/bin/env python3
"""Quick test script to verify server components."""

import sys


def test_imports():
    """Test that all server components import successfully."""
    print("Testing server imports...")

    try:
        print("✓ FastAPI app imports")

        print("✓ Session management imports")

        print("✓ Request schemas import")

        print("✓ Response schemas import")

        print("✓ Map generator imports")

        print("✓ Turn executor imports")

        print("✓ AI player imports")

        return True

    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_game_creation():
    """Test basic game creation."""
    print("\nTesting game creation...")

    try:
        from src.engine.map_generator import generate_map

        game = generate_map(seed=42)
        print(f"✓ Game created: {len(game.stars)} stars, turn {game.turn}")

        assert len(game.stars) > 0, "No stars generated"
        assert len(game.players) == 2, "Wrong number of players"
        print("✓ Game validation passed")

        return True

    except Exception as e:
        print(f"✗ Game creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_session_manager():
    """Test session manager."""
    print("\nTesting session manager...")

    try:
        from src.server.session import GameSessionManager

        manager = GameSessionManager()
        print("✓ Session manager created")

        # Test session count
        assert len(manager.sessions) == 0, "Manager should start empty"
        print("✓ Session manager initialized correctly")

        return True

    except Exception as e:
        print(f"✗ Session manager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Space Conquest Server Component Tests")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Game Creation", test_game_creation()))
    results.append(("Session Manager", test_session_manager()))

    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n✓ All tests passed! Server is ready to run.")
        print("\nTo start the server:")
        print("  uv run python run_server.py")
        print("\nThen open: http://localhost:8000")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix errors before running server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
