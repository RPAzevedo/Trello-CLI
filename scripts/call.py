"""Terminal client for the Trello MCP server.

Examples:
    uv run python scripts/call.py --list
    uv run python scripts/call.py list_boards
    uv run python scripts/call.py list_lists board_id=abc123
    uv run python scripts/call.py get_cards list_id=xyz789
"""

import argparse
import asyncio
import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def parse_kv_args(raw: list[str]) -> dict[str, str]:
    args: dict[str, str] = {}
    for item in raw:
        if "=" not in item:
            sys.exit(f"argument {item!r} must be in key=value form")
        key, value = item.split("=", 1)
        args[key] = value
    return args


async def run(tool: str | None, arguments: dict[str, str], list_only: bool) -> None:
    server = StdioServerParameters(command="uv", args=["run", "trello-mcp"])

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(server))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        if list_only or tool is None:
            tools = await session.list_tools()
            for t in tools.tools:
                first_line = (t.description or "").splitlines()[0]
                print(f"{t.name:<14} {first_line}")
            return

        result = await session.call_tool(tool, arguments)
        for block in result.content:
            text = getattr(block, "text", None)
            if text is None:
                print(block)
                continue
            try:
                print(json.dumps(json.loads(text), indent=2))
            except json.JSONDecodeError:
                print(text)

        if result.isError:
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tool", nargs="?", help="Tool to call (omit with --list)")
    parser.add_argument("args", nargs="*", help="Tool arguments as key=value pairs")
    parser.add_argument("--list", action="store_true", help="List available tools and exit")
    parsed = parser.parse_args()

    asyncio.run(run(parsed.tool, parse_kv_args(parsed.args), parsed.list))


if __name__ == "__main__":
    main()
