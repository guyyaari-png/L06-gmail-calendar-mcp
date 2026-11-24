"""Smoke test: start the server over stdio, list its tools, call list_events.

list_events takes start/end, so days_ahead is converted to a range from now.
Read-only: nothing is created, sent or deleted.
"""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
GOOGLE_PRIVATE_DIR = str(Path(os.environ.get("GOOGLE_PRIVATE_DIR", "~/my-private")).expanduser())
DAYS_AHEAD = 1


async def main() -> None:
    params = StdioServerParameters(
        command="uv",
        args=["run", "--directory", str(HERE), "server.py"],
        env={**os.environ, "GOOGLE_PRIVATE_DIR": GOOGLE_PRIVATE_DIR},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            print(f"Tools ({len(tools)}):")
            for tool in tools:
                print(f"  - {tool.name}({', '.join(tool.inputSchema['properties'])})")

            now = datetime.now(ZoneInfo("Asia/Jerusalem")).replace(microsecond=0)
            start, end = now.isoformat(), (now + timedelta(days=DAYS_AHEAD)).isoformat()
            print(f"\nlist_events(start={start}, end={end}):")
            result = await session.call_tool("list_events", {"start": start, "end": end})
            if result.isError:
                print("  ERROR:", " ".join(c.text for c in result.content if hasattr(c, "text")))
            elif not result.content:
                print("  (no events)")
            else:
                for c in result.content:
                    print(" ", getattr(c, "text", c))


if __name__ == "__main__":
    asyncio.run(main())
