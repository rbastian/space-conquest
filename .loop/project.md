# Project

This section gives the facts about this project. The prompt above refers to it as "the Project section". The prompt also uses names that this section defines, for example "the gate", `$PRIMARY` and `$CODER`.

## What the project is

Space Conquest is a turn-based 4X strategy game in Python. Players capture each other's home stars through fleet movement, production and combat on a fog-of-war star map. It runs as a text or Textual TUI game (`game.py`), and as a FastAPI/WebSocket server (`run_server.py`) for the browser frontend. Opponents can be human or LLM players, and LLM-vs-LLM games are used to evaluate agent behavior. The users are the repository owner and the people who play or study the AI opponents.

Out of scope: `.loop/` (the harness, which `update.sh` manages), `.beads/` (bd writes it, change beads only with `bd`), `.claude/`, `.codex/`, `.agents/`, the `CLAUDE.md` and `AGENTS.md` blocks between `BEGIN`/`END` markers, `logs/`, and `uv.lock` except through `uv add`, `uv remove` or `uv lock`.

## Roles

```bash
CODER=Ralph
REVIEWER=Alice
HUMAN=rbastian
CODER_ENGINE=claude
CODER_MODEL=
REVIEWER_ENGINE=codex
REVIEWER_MODEL=
BEAD_PREFIX=space-conquest
```

`$CODER` is the agent that implements beads. `$REVIEWER` is the agent that reviews them. Each name is the bead assignee that the agent's loop polls for. `$HUMAN` is the bd assignee for the human's queues: merge approval, acceptance and escalation. `BEAD_PREFIX` is the prefix of every bead ID in this project, and the watchers match bead IDs with it.

`CODER_ENGINE` is the CLI that the coder's loop runs on: `claude` or `fw`. The coder needs Claude Code, because its prompt uses the `/simplify` skill, and `fw` is a launcher that runs Claude Code on a Fireworks model. `CODER_MODEL` is the coder's model for its engine. `REVIEWER_ENGINE` is the CLI that the reviewer's loop runs on: `claude`, `codex` or `fw`. `REVIEWER_MODEL` is the reviewer's model for its engine. An empty model gives the default of the engine: `claude-opus-5-5` for the coder on `claude`, `claude-sonnet-5-5` for the reviewer on `claude`, and the plan's default model on `codex`. `fw` has no default, so an agent on `fw` must have a model, for example `deepseek-flash-latest[1m]`.

## Ship mode

```bash
SHIP_MODE=pr
GITHUB_ACCOUNT=rbastian
```

`SHIP_MODE` is `pr` or `local`. `pr` is the default. `$CODER` pushes each branch to `origin` and opens a pull request against `main`. `$REVIEWER` reviews the branch and comments on the pull request. `$HUMAN` approves and merges it. `$BASE` is `origin/main`.

`local` is only for a repository with one user and no shared remote. `$REVIEWER` merges the branch into `main` in the primary checkout, and no pull request exists. `$BASE` is `main`.

`GITHUB_ACCOUNT` is the GitHub account that `$CODER` and `$REVIEWER` use in `pr` mode, for every `gh` command and every push. It is usually `$HUMAN`'s own account. The agents do not use separate bot accounts. `run.sh` pins this account at start: it exports the account's token as `GH_TOKEN`, and it checks that an SSH push uses the same account. In `local` mode the field is empty.

### Remote actions in `pr` mode

This list is the only place that says what each role can do on the GitHub remote. An action that is not on the list is not allowed.

- `$CODER` can push its own `feat/` branches to `origin`. After a rebase, it pushes with `git push --force-with-lease`, never with a plain `--force`. It can open a pull request against `main` with `gh pr create`, and it can read pull requests with `gh pr view`.
- `$REVIEWER` can read pull requests with `gh pr view`, and it can post comments with `gh pr comment`. It does not push, approve, merge, close, edit or label a pull request on GitHub, and it does not delete branches. A GitHub account cannot approve its own pull request, so the review result is a comment, not `gh pr review --approve`.
- `$HUMAN` approves and merges pull requests, deletes remote branches, and changes anything else on the remote, for example the settings, the releases and the tags.
- No agent pushes to `main`, creates or deletes tags or releases, changes the repository settings, or closes a pull request that another author opened.

## Paths

```bash
PRIMARY=/Users/rbastian/github.com/rbastian/space-conquest
CODER_WORKTREE=/Users/rbastian/github.com/rbastian/space-conquest-ralph
REVIEWER_WORKTREE=/Users/rbastian/github.com/rbastian/space-conquest-alice
```

`PRIMARY` is the primary checkout, which belongs to `$HUMAN`. `CODER_WORKTREE` is the worktree of `$CODER`. `REVIEWER_WORKTREE` is the worktree of `$REVIEWER`.

There are no exceptions to the rule that agents do not write in the primary checkout.

## Tech stack

- Python 3.10 or later (`requires-python = ">=3.10"`), managed and run only through `uv`. uv is the only way to install packages or run anything: `uv add`, `uv sync`, `uv run python ...`, `uv run pytest`. Never call `pip`, `python` or `pytest` directly, and never create or activate a virtualenv by hand.
- pytest for tests and ruff for formatting and lint, configured in `pyproject.toml` (line length 100). ruff also formats the Python code blocks in Markdown files. ty is installed (`uv run ty check`) but is not in the gate yet, because the codebase still has open ty diagnostics. Do not add new ones in the files that a bead changes.
- Pydantic v2 models, Textual for the TUI, FastAPI, uvicorn and websockets for the server, a plain HTML/CSS/JavaScript frontend in `frontend/` with no build step, tenacity for retries, and LangChain/LangGraph (`langchain-aws`, `langchain-anthropic`, `langchain-openai`, `langchain-ollama`) for the current LLM players.

## Key directories

- `src/`: the package. `src/models/` holds the game state (game, star, fleet, order, player). `src/engine/` holds the rules: map generation, movement, production, combat, turn execution and victory. `src/agent/` holds the LLM players, their prompts and tools. `src/analysis/` holds the decision and strategic logging and metrics. `src/interface/` holds the text and TUI interfaces and the human player. `src/server/` holds the FastAPI app and game sessions. `src/utils/` holds distance, RNG, naming and serialization helpers.
- `game.py`: the CLI entry point (`uv run game.py`). `run_server.py` starts the server. `watch_game.py`, `monitor_game.py`, `monitor_live.py`, `scripts/` and `examples/` are tools around games and logs.
- `frontend/`: the browser client for the server.
- `specs/` and `docs/`: the game specification (`specs/space_conquest_spec.md`), design specs and architecture notes.
- `tests/`: the pytest suite.
- `.loop/`: the loop scripts and prompts.

## Format commands and gate

Format commands:

```bash
uv run ruff format . && uv run ruff check --fix .
```

The gate:

```bash
uv run ruff format --check . && uv run ruff check . && uv run pytest -q
```

## External services

The game, the engine and the test suite use no external services. Only the LLM players call models at run time: AWS Bedrock (the default, AWS credentials from the environment or profile, `AWS_REGION`, default `us-east-1`), Anthropic (`ANTHROPIC_API_KEY`), OpenAI (`OPENAI_API_KEY`) and a local Ollama server. Tests must never call a real model: mock the LLM client, as the existing agent tests do. Do not run `game.py --mode hvl` or `lvl` against a real provider as part of a bead. If a bead needs a service and it is unavailable, follow "When Things Go Wrong".

## Review method (for the reviewer)

The reviewer always runs the default method for its engine. List here only the checks that add to it, chosen by the files that the branch changes.

- `src/engine/` or `src/models/`: check that the change matches the rules in `specs/space_conquest_spec.md`, including the order of turn phases, fog of war and combat. A rule change needs a test that pins the new behavior and a matching update to the spec.
- `src/agent/`: check that no test calls a real LLM or needs credentials. A change to a prompt in `src/agent/prompts*.py` updates the prompt's version header and adds an entry to `PROMPT_CHANGELOG.md`.
- `src/server/` or `frontend/`: check that the request and response schemas in `src/server/schemas/` and the frontend's use of them still agree.
- `pyproject.toml` or `uv.lock`: check that each dependency change was made with `uv` and that `uv.lock` matches.
