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

## 3. Configure your MCP client

The server reads `TRELLO_API_KEY` and `TRELLO_TOKEN` from the environment.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) and add:

```json
{
  "mcpServers": {
    "trello": {
      "command": "/absolute/path/to/trello-mcp/.venv/bin/trello-mcp",
      "env": {
        "TRELLO_API_KEY": "your_key_here",
        "TRELLO_TOKEN": "your_token_here"
      }
    }
  }
}
```

Restart Claude Desktop. The `trello` server should appear in the MCP indicator.

Alternatively, let uv resolve the environment at launch — useful if you don't want to hard-code the venv path:

```json
"command": "uv",
"args": ["--directory", "/absolute/path/to/trello-mcp", "run", "trello-mcp"]
```

### Claude Code

```bash
claude mcp add trello \
  --env TRELLO_API_KEY=your_key_here \
  --env TRELLO_TOKEN=your_token_here \
  -- /absolute/path/to/trello-mcp/.venv/bin/trello-mcp
```

### Any other MCP client

Run the binary directly as a stdio server:

```bash
TRELLO_API_KEY=... TRELLO_TOKEN=... trello-mcp
```

## 4. Try it

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

Install git hooks (optional) so ruff + pyright run on every commit:

```bash
uv run pre-commit install
```

Source: [src/trello_mcp/server.py](src/trello_mcp/server.py). Tests: [tests/test_server.py](tests/test_server.py).
