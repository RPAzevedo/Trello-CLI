import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from trello_mcp import __version__

# Resolved on import so non-CLI entry points (e.g. `mcp dev src/trello_mcp/server.py`,
# programmatic imports) share the same env story as the console script.
# Precedence: TRELLO_MCP_ENV_FILE env var > CWD-walk for `.env`. The console script's
# --env-file flag layers on top via load_dotenv(..., override=True) inside main().
_explicit_env_file = os.environ.get("TRELLO_MCP_ENV_FILE")
if _explicit_env_file:
    load_dotenv(_explicit_env_file, override=True)
else:
    load_dotenv()

# httpx emits a per-request INFO line containing the full URL. Auth now travels in a
# header so URLs are no longer sensitive, but silencing the line removes a future
# footgun if any Trello path ever embeds identifying data in the URL itself.
logging.getLogger("httpx").setLevel(logging.WARNING)

TRELLO_API_BASE = "https://api.trello.com/1"

mcp = FastMCP("trello")


def _auth_header() -> dict[str, str]:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError("TRELLO_API_KEY and TRELLO_TOKEN environment variables must be set")
    return {"Authorization": f'OAuth oauth_consumer_key="{key}", oauth_token="{token}"'}


def _parse_iso8601(value: str) -> datetime:
    # datetime.fromisoformat in 3.10 doesn't accept the trailing "Z" Trello uses,
    # and we must compare datetimes — not strings — because Trello returns
    # millisecond precision (".000Z") while callers may pass second precision ("Z"),
    # and lexicographic compare flips the boundary case.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{TRELLO_API_BASE}{path}",
            params=params or {},
            headers=_auth_header(),
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def server_info() -> dict[str, str]:
    """Return the running server's name and version.

    Use this to confirm which build of trello-mcp is responding and whether an
    upgrade is needed.
    """
    return {"name": "trello-mcp", "version": __version__}


@mcp.tool()
async def list_boards() -> list[dict[str, Any]]:
    """List open Trello boards the authenticated user can access.

    Returns each board's id, name, and url. Use the id with list_lists.
    """
    boards = await _get("/members/me/boards", {"fields": "name,url,closed"})
    return [
        {"id": b["id"], "name": b["name"], "url": b.get("url")}
        for b in boards
        if not b.get("closed")
    ]


@mcp.tool()
async def list_lists(board_id: str) -> list[dict[str, Any]]:
    """List the open lists on a Trello board.

    Args:
        board_id: The board id returned by list_boards.

    Returns each list's id and name. Use the id with get_cards.
    """
    lists = await _get(f"/boards/{board_id}/lists", {"fields": "name,closed"})
    return [{"id": lst["id"], "name": lst["name"]} for lst in lists if not lst.get("closed")]


@mcp.tool()
async def get_cards(list_id: str, since: str | None = None) -> list[dict[str, Any]]:
    """Get the cards on a Trello list.

    Args:
        list_id: The list id returned by list_lists.
        since: Optional ISO 8601 UTC timestamp (e.g. "2026-05-19T00:00:00Z").
            Only cards whose date_last_activity is at or after this time are
            returned. Use this to build daily/recent-activity summaries.

    Returns each card's id, name, description, due date, labels, url, members,
    and date_last_activity (UTC ISO 8601, when Trello last recorded a change).
    """
    cards = await _get(
        f"/lists/{list_id}/cards",
        {"fields": "name,desc,due,dueComplete,labels,url,idMembers,shortLink,dateLastActivity"},
    )
    if since is not None:
        since_dt = _parse_iso8601(since)
        cards = [
            c
            for c in cards
            if c.get("dateLastActivity") and _parse_iso8601(c["dateLastActivity"]) >= since_dt
        ]
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "desc": c.get("desc"),
            "due": c.get("due"),
            "due_complete": c.get("dueComplete"),
            "labels": [
                {"name": lbl.get("name"), "color": lbl.get("color")} for lbl in c.get("labels", [])
            ],
            "url": c.get("url"),
            "member_ids": c.get("idMembers", []),
            "date_last_activity": c.get("dateLastActivity"),
        }
        for c in cards
    ]


def main() -> None:
    parser = argparse.ArgumentParser(prog="trello-mcp")
    parser.add_argument(
        "--version",
        action="version",
        version=f"trello-mcp {__version__}",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to .env file with TRELLO_API_KEY and TRELLO_TOKEN. "
        "Equivalent to setting TRELLO_MCP_ENV_FILE. "
        "If neither is given, walks up from the current directory looking for .env.",
    )
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    mcp.run()


if __name__ == "__main__":
    main()
