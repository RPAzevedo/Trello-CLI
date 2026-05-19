# Trello MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an MCP-aware client (Claude Desktop, Claude Code, etc.) read your Trello boards, lists, and cards.

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `list_boards` | — | Open boards the authenticated user can see (`id`, `name`, `url`) |
| `list_lists` | `board_id` | Open lists on a board (`id`, `name`) |
| `get_cards` | `list_id` | Cards on a list (`id`, `name`, `desc`, `due`, `due_complete`, `labels`, `url`, `member_ids`) |

The model discovers boards and lists by calling `list_boards` → `list_lists` → `get_cards`. Nothing is hard-coded — point it at any board/list you have access to.

## 1. Get Trello credentials

You need an **API key** and a **token**.

1. Sign in to Trello, then visit <https://trello.com/power-ups/admin> and create a Power-Up (any name — it just gives you a key).
2. On the Power-Up's "API key" tab, copy the **API key**.
3. Next to the key, click the **Token** link. Authorize the app — Trello will give you a token. Copy it.

Keep these secret. Treat the token like a password.

## 2. Install

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS).

```bash
git clone <this-repo> trello-mcp
cd trello-mcp
uv sync
```

`uv sync` creates `.venv/`, installs runtime + dev deps from `pyproject.toml`, and exposes a `trello-mcp` console script. Run the server directly with `uv run trello-mcp`.

## 3. Configure credentials

The server reads `TRELLO_API_KEY` and `TRELLO_TOKEN` from the environment. You have two options.

### Option A — `.env` file (recommended for local use)

Copy the template and fill in your key and token:

```bash
cp .env.example .env
```

`.env` is git-ignored. The server auto-loads it on startup via `python-dotenv`, walking up from the current working directory. As long as your MCP client launches the server with `cwd` set to the project root (or you `cd` there before running), you're done — no need to put secrets in the client config.

### Option B — env vars in the MCP client config

Pass them inline in your client's MCP server config (see next section).

## 4. Configure your MCP client

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add:

```json
{
  "mcpServers": {
    "trello": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/trello-mcp", "run", "trello-mcp"]
    }
  }
}
```

`uv --directory` sets the working directory before launching, so the `.env` file is picked up automatically. Restart Claude Desktop after editing.

If you'd rather keep secrets in the client config instead of `.env`, add an `env` block:

```json
"env": { "TRELLO_API_KEY": "...", "TRELLO_TOKEN": "..." }
```

### Claude Code

```bash
claude mcp add trello -- uv --directory /absolute/path/to/trello-mcp run trello-mcp
```

Or with inline env vars (skips `.env`):

```bash
claude mcp add trello \
  --env TRELLO_API_KEY=your_key_here \
  --env TRELLO_TOKEN=your_token_here \
  -- /absolute/path/to/trello-mcp/.venv/bin/trello-mcp
```

### Any other MCP client

Run the binary as a stdio server from the project directory (so `.env` is found):

```bash
cd /absolute/path/to/trello-mcp && uv run trello-mcp
```

## 5. Try it

In your client, ask something like:

> List my Trello boards, then show me the cards on the "Doing" list of my "Work" board.

The model will call `list_boards`, pick the matching board, call `list_lists` to find "Doing", and then `get_cards` to return the cards.

## Troubleshooting

- **`TRELLO_API_KEY and TRELLO_TOKEN environment variables must be set`** — your MCP client isn't passing them through. Re-check the `env` block in the client config.
- **401 Unauthorized** — the token is wrong, expired, or was generated against a different API key. Re-issue both from the Power-Up admin page.
- **Empty board list** — the token only sees boards the authorizing user can see. If you expected a team board, make sure that user is a member.

## Development

Tooling is managed by `uv` and configured in [pyproject.toml](pyproject.toml).

```bash
uv sync                       # install runtime + dev deps
uv run trello-mcp             # run the server standalone (Ctrl+C to quit)
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pyright                # type check
uv run pytest                 # tests
```

### Interactive testing — MCP Inspector

To poke at the tools without wiring the server into a client, use the MCP Inspector:

```bash
uv run mcp dev src/trello_mcp/server.py
```

This launches the server and opens a browser UI (proxy on a local port) where you can list tools, fill in arguments, and see the JSON responses. Make sure `.env` is set up first or the tools will error on the missing credentials.

### Terminal client — `scripts/call.py`

A small stdio client for calling tools straight from a shell, no browser:

```bash
uv run python scripts/call.py --list                          # list available tools
uv run python scripts/call.py list_boards                     # no arguments
uv run python scripts/call.py list_lists board_id=abc123      # one argument
uv run python scripts/call.py get_cards list_id=xyz789        # one argument
```

Output is the tool's JSON response, pretty-printed. Useful for ad-hoc inspection and shell pipelines (`uv run python scripts/call.py list_boards | jq '.[].name'`).

Install git hooks (optional) so ruff + pyright run on every commit:

```bash
uv run pre-commit install
```

Source: [src/trello_mcp/server.py](src/trello_mcp/server.py). Tests: [tests/test_server.py](tests/test_server.py).
