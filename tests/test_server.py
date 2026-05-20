from importlib.metadata import version
from typing import Any

import pytest

from trello_mcp import server
from trello_mcp.server import get_cards, mcp, server_info


async def test_tools_are_registered() -> None:
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {"server_info", "list_boards", "list_lists", "get_cards"}


async def test_server_info_returns_package_version() -> None:
    info = await server_info()
    assert info == {"name": "trello-mcp", "version": version("trello-mcp")}


def _patch_get(
    monkeypatch: pytest.MonkeyPatch, cards: list[dict[str, Any]]
) -> list[tuple[str, dict[str, Any] | None]]:
    """Patch server._get to return `cards`; return list captures (path, params) per call."""
    calls: list[tuple[str, dict[str, Any] | None]] = []

    async def fake_get(path: str, params: dict[str, Any] | None = None) -> Any:
        calls.append((path, params))
        return cards

    monkeypatch.setattr(server, "_get", fake_get)
    return calls


def _card(card_id: str, date_last_activity: str | None, name: str = "card") -> dict[str, Any]:
    return {
        "id": card_id,
        "name": name,
        "desc": "",
        "due": None,
        "dueComplete": False,
        "labels": [],
        "url": f"https://trello.com/c/{card_id}",
        "idMembers": [],
        "shortLink": card_id,
        "dateLastActivity": date_last_activity,
    }


async def test_get_cards_maps_date_last_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get(
        monkeypatch,
        [
            _card("a", "2026-05-19T10:00:00.000Z"),
            _card("b", "2026-05-20T09:30:00.000Z"),
        ],
    )

    result = await get_cards("list-1")

    assert [c["id"] for c in result] == ["a", "b"]
    assert result[0]["date_last_activity"] == "2026-05-19T10:00:00.000Z"
    assert result[1]["date_last_activity"] == "2026-05-20T09:30:00.000Z"


async def test_get_cards_requests_date_last_activity_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_get(monkeypatch, [])

    await get_cards("list-1")

    assert len(calls) == 1
    _, params = calls[0]
    assert params is not None
    assert "dateLastActivity" in params["fields"]


async def test_get_cards_since_filters_inclusive_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_get(
        monkeypatch,
        [
            _card("old", "2026-05-18T23:59:59.000Z"),
            _card("boundary", "2026-05-19T00:00:00.000Z"),
            _card("new", "2026-05-19T12:00:00.000Z"),
        ],
    )

    result = await get_cards("list-1", since="2026-05-19T00:00:00.000Z")

    assert [c["id"] for c in result] == ["boundary", "new"]


async def test_get_cards_since_none_returns_all(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get(
        monkeypatch,
        [
            _card("a", "2020-01-01T00:00:00.000Z"),
            _card("b", "2026-05-20T00:00:00.000Z"),
        ],
    )

    result = await get_cards("list-1")

    assert [c["id"] for c in result] == ["a", "b"]


async def test_get_cards_since_handles_precision_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Trello always returns millisecond precision ("...:00.000Z"); callers commonly
    # pass second precision ("...:00Z"). A string compare would put "." before "Z"
    # and wrongly drop the boundary card. Parsing both as datetimes fixes it.
    _patch_get(
        monkeypatch,
        [
            _card("before", "2026-05-18T23:59:59.999Z"),
            _card("boundary", "2026-05-19T00:00:00.000Z"),
            _card("after", "2026-05-19T00:00:00.500Z"),
        ],
    )

    result = await get_cards("list-1", since="2026-05-19T00:00:00Z")

    assert [c["id"] for c in result] == ["boundary", "after"]


async def test_get_cards_since_excludes_missing_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_get(
        monkeypatch,
        [
            _card("missing", None),
            _card("present", "2026-05-20T00:00:00.000Z"),
        ],
    )

    result = await get_cards("list-1", since="2026-05-19T00:00:00.000Z")

    assert [c["id"] for c in result] == ["present"]
