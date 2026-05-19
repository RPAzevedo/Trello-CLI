import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

TRELLO_API_BASE = "https://api.trello.com/1"

mcp = FastMCP("trello")


def _auth_params() -> dict[str, str]:
    key = os.environ.get("TRELLO_API_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        raise RuntimeError("TRELLO_API_KEY and TRELLO_TOKEN environment variables must be set")
    return {"key": key, "token": token}


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    merged = {**_auth_params(), **(params or {})}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{TRELLO_API_BASE}{path}", params=merged)
        resp.raise_for_status()
        return resp.json()


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
async def get_cards(list_id: str) -> list[dict[str, Any]]:
    """Get the cards on a Trello list.

    Args:
        list_id: The list id returned by list_lists.

    Returns each card's id, name, description, due date, labels, url, and members.
    """
    cards = await _get(
        f"/lists/{list_id}/cards",
        {"fields": "name,desc,due,dueComplete,labels,url,idMembers,shortLink"},
    )
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
        }
        for c in cards
    ]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
