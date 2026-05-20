# Trello MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets an MCP-aware client (Claude Code, Claude Desktop, Cursor, VS Code, Codex, etc.) read your Trello boards, lists, and cards.

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `list_boards` | — | Open boards the authenticated user can see (`id`, `name`, `url`) |
| `list_lists` | `board_id` | Open lists on a board (`id`, `name`) |
| `get_cards` | `list_id`, optional `since` (ISO 8601 UTC) | Cards on a list (`id`, `name`, `desc`, `due`, `due_complete`, `labels`, `url`, `member_ids`, `date_last_activity`). With `since`, only cards whose `date_last_activity` is at or after that timestamp. |

The model discovers boards and lists by calling `list_boards` → `list_lists` → `get_cards`. Nothing is hard-coded — point it at any board/list you have access to.

## 1. Get Trello credentials

You need an **API key** and a **token**.

1. Sign in to Trello, then visit <https://trello.com/power-ups/admin> and create a Power-Up (any name — it just gives you a key).
2. On the Power-Up's "API key" tab, copy the **API key**.
3. Next to the key, click the **Token** link. Authorize the app — Trello will give you a token. Copy it.

Keep these secret. Treat the token like a password.

## 2. Store credentials in a `.env` file

Save them once at a canonical location so every MCP client can find them:

```bash
mkdir -p ~/.config/trello-mcp
cat > ~/.config/trello-mcp/.env <<EOF
TRELLO_API_KEY=your_api_key_here
TRELLO_TOKEN=your_token_here
EOF
chmod 600 ~/.config/trello-mcp/.env
```

Every snippet below points `--env-file` at this file. Use a different path if you prefer — only the path is in the client config, never the secrets.

## 3. Quick install

`uvx` runs the server straight from GitHub — no clone, no manual virtualenv. You'll need [uv](https://docs.astral.sh/uv/) (`brew install uv` on macOS).

### Claude Code

```bash
claude mcp add trello -- uvx --from git+https://github.com/RPAzevedo/Trello-MCP.git \
  trello-mcp --env-file "$HOME/.config/trello-mcp/.env"
```

No `--env` flags, so the token never lands in shell history. Restart Claude Code or run `/mcp` to confirm.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "trello": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/RPAzevedo/Trello-MCP.git",
        "trello-mcp",
        "--env-file", "/Users/you/.config/trello-mcp/.env"
      ]
    }
  }
}
```

Restart Claude Desktop.

### Cursor

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per-project — `.gitignore` it if per-project):

```json
{
  "mcpServers": {
    "trello": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/RPAzevedo/Trello-MCP.git",
        "trello-mcp",
        "--env-file", "/Users/you/.config/trello-mcp/.env"
      ]
    }
  }
}
```

### VS Code

Edit `.vscode/mcp.json` in the workspace:

```json
{
  "servers": {
    "trello": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/RPAzevedo/Trello-MCP.git",
        "trello-mcp",
        "--env-file", "${userHome}/.config/trello-mcp/.env"
      ]
    }
  }
}
```

### Codex

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.trello]
command = "uvx"
args = [
  "--from", "git+https://github.com/RPAzevedo/Trello-MCP.git",
  "trello-mcp",
  "--env-file", "/Users/you/.config/trello-mcp/.env",
]
```

## 4. Try it

Ask your client something like:

> List my Trello boards, then show me the cards on the "Doing" list of my "Work" board.

The model will call `list_boards`, pick the matching board, call `list_lists` to find "Doing", and then `get_cards` to return the cards.

### Daily summary

Each card carries a `date_last_activity` timestamp, and `get_cards` accepts an ISO 8601 UTC `since` cutoff. That makes "what changed today?" prompts cheap:

> Summarize what changed on my "Work" board since yesterday.

The model picks a `since` (e.g. `2026-05-19T00:00:00Z`), passes it to `get_cards` per list, and only the recently-touched cards come back.

## Alternative install methods

### Install as a uv tool (persistent CLI on PATH)

If you want `trello-mcp` as a real command (for shell scripts, the MCP Inspector, or just shorter client configs):

```bash
uv tool install git+https://github.com/RPAzevedo/Trello-MCP.git
# upgrade later
uv tool upgrade trello-mcp
```

Client configs can then drop `uvx --from ...` and use `"command": "trello-mcp"` directly. Still pass `--env-file`.

### Clone for development

```bash
git clone https://github.com/RPAzevedo/Trello-MCP.git trello-mcp
cd trello-mcp
uv sync
cp .env.example .env  # then fill in your key and token
uv run trello-mcp
```

With no `--env-file`, the server walks up from CWD looking for `.env`, so a repo-local `.env` keeps working. Client configs pointed at a checkout can still use the `uv --directory /path/to/trello-mcp run trello-mcp` form if you'd rather run from a clone than via `uvx`.

## Security notes

- The `.env` file is plaintext; filesystem permissions are the only barrier. Keep it `chmod 600` and out of any synced folder (Dropbox, iCloud Documents).
- Mint a token dedicated to this MCP rather than reusing one tied to other tools. Pass `?expiration=30days` when authorizing so a leak has a fuse, and rotate periodically.
- Revoke tokens at <https://trello.com/your/account> → Applications.
- Trello tokens can't be scoped read-only — they grant full read/write on every board the authorizing user can see. Treat them accordingly.
- If you use a secret manager, prefer `op run --env-file=op.env -- uvx ... trello-mcp` (1Password CLI) or `pass`-piped equivalents over a long-lived plaintext `.env`.

## Troubleshooting

- **`TRELLO_API_KEY and TRELLO_TOKEN environment variables must be set`** — the server can't see the env file. Confirm `--env-file` points at the right path (absolute, not `~`-relative in JSON; expand `$HOME` first if your client doesn't).
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

To poke at the tools without wiring the server into a client:

```bash
# Repo-local .env (created by `cp .env.example .env` above):
uv run mcp dev src/trello_mcp/server.py

# Or point at the centralized file used by your MCP clients:
TRELLO_MCP_ENV_FILE=~/.config/trello-mcp/.env uv run mcp dev src/trello_mcp/server.py
```

`mcp dev` imports the server module instead of running the console script, so the `--env-file` CLI flag doesn't apply — use `TRELLO_MCP_ENV_FILE` or a repo-local `.env` instead. Both `--env-file` and `TRELLO_MCP_ENV_FILE` resolve to the same path; either works.

### Terminal client — `scripts/call.py`

A small stdio client for calling tools straight from a shell, no browser:

```bash
uv run python scripts/call.py --list                          # list available tools
uv run python scripts/call.py list_boards                     # no arguments
uv run python scripts/call.py list_lists board_id=abc123      # one argument
uv run python scripts/call.py get_cards list_id=xyz789        # one argument
uv run python scripts/call.py get_cards list_id=xyz789 since=2026-05-19T00:00:00Z  # recent activity only
```

Output is the tool's JSON response, pretty-printed. Useful for ad-hoc inspection and shell pipelines (`uv run python scripts/call.py list_boards | jq '.[].name'`).

Install git hooks (optional) so ruff + pyright run on every commit:

```bash
uv run pre-commit install
```

Source: [src/trello_mcp/server.py](src/trello_mcp/server.py). Tests: [tests/test_server.py](tests/test_server.py).
