from trello_mcp.server import mcp


async def test_tools_are_registered() -> None:
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {"list_boards", "list_lists", "get_cards"}
