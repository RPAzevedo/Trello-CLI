# trello-mcp — repo orientation for Claude Code

Python MCP server exposing read-only Trello tools (`list_boards`, `list_lists`, `get_cards`) via FastMCP over stdio.

## Layout

- `src/trello_mcp/server.py` — FastMCP instance, three async tools, `main()` with `--env-file` flag.
- `src/trello_mcp/__main__.py` — `python -m trello_mcp` entry.
- `scripts/call.py` — terminal stdio client for calling tools without a full MCP host.
- `tests/test_server.py` — currently only checks tool registration.
- `src/`-layout package; wheel target configured in `pyproject.toml`.

## Tooling commands

```bash
uv sync                                       # install runtime + dev deps
uv run ruff check . && uv run ruff format --check .
uv run pyright
uv run pytest
```

Pre-commit hooks (ruff + pyright) are configured in `.pre-commit-config.yaml`; install with `uv run pre-commit install`.

## Running the server locally

- `uv run trello-mcp` — walks up from CWD for `.env`.
- `uv run trello-mcp --env-file PATH` — explicit env file (what users put in MCP client configs).
- `TRELLO_MCP_ENV_FILE=PATH uv run mcp dev src/trello_mcp/server.py` — Inspector with an explicit env file (the flag doesn't apply because `mcp dev` imports the module instead of running the console script).
- `uv run python scripts/call.py <tool> arg=value` — one-shot tool call from a shell.

Server needs `TRELLO_API_KEY` and `TRELLO_TOKEN`. They're read lazily inside `_auth_params()` per request, not at import time.

Env precedence (resolved on import): `TRELLO_MCP_ENV_FILE` env var > CWD-walk for `.env`. The console script's `--env-file` flag layers on top in `main()` via `load_dotenv(..., override=True)`.

## Conventions

- Async-first — every tool is `async def`; use `httpx.AsyncClient` for HTTP, never `requests` or sync httpx.
- Ruff config + line length 100 in `pyproject.toml`; pyright in standard mode.
- Tools return plain `list[dict[str, Any]]` shaped for the model, not raw Trello payloads.
- `load_dotenv()` runs at module scope (reading `TRELLO_MCP_ENV_FILE` if set, else CWD-walk) so non-CLI entry points share the same env story as the console script. `main()` re-loads with `override=True` when `--env-file` is passed. Don't remove the module-level call.

## Pitfalls

- Tests must not hit the real Trello API. The current test only inspects `mcp.list_tools()`. If adding coverage, mock `httpx.AsyncClient` or record cassettes — never call the live API in CI.
- `load_dotenv()`'s CWD-walk only finds `.env` when the server is launched from inside the repo. Anything else (client configs, `uvx`, `uv tool install`) must pass `--env-file`.
- Trello tokens can't be scoped read-only — the server is read-only by tool design, not by token capability.
