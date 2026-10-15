"""Search and fetch with Parallel Search MCP, without an API key or LLM.

From the repository root, install and run:
    python -m pip install -e . "mcp>=1.9,<2"
    python examples/parallel_search_mcp.py search "Python asyncio TaskGroup guide"
    python examples/parallel_search_mcp.py fetch https://docs.python.org/3/library/asyncio-task.html

Anonymous search uses Fast mode and has lower rate limits. See:
https://docs.parallel.ai/integrations/mcp/search-mcp
"""

import argparse
import asyncio
from importlib.metadata import version
from uuid import uuid4

from chak.tools.mcp import Server


async def run(args: argparse.Namespace) -> None:
    server = Server(
        url="https://search.parallel.ai/mcp",
        type="streamable-http",
        headers={
            "User-Agent": f"chak-ai/{version('chakpy')} (+https://github.com/zhixiangxue/chak-ai)"
        },
    )
    tool_name = f"web_{args.command}"
    tools = await server.tools([tool_name])
    if not tools:
        raise RuntimeError(f"Parallel Search MCP did not provide {tool_name}")

    session_id = str(uuid4())
    if args.command == "search":
        arguments = {
            "objective": args.query,
            "search_queries": [args.query],
            "session_id": session_id,
        }
    else:
        arguments = {"urls": args.urls, "session_id": session_id}

    # Surface errors immediately, including free-tier rate limits.
    result = await tools[0].call(arguments, retry=False)
    for block in result.content:
        if block.type == "text":
            print(block.text)
    if result.isError:
        raise RuntimeError(f"Parallel Search MCP {tool_name} failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="Search the web with Fast mode")
    search.add_argument("query", help="A focused search query")
    fetch = commands.add_parser("fetch", help="Fetch page excerpts as markdown")
    fetch.add_argument("urls", nargs="+", help="Up to 20 HTTP or HTTPS URLs")
    args = parser.parse_args()
    if args.command == "fetch" and len(args.urls) > 20:
        parser.error("fetch accepts at most 20 URLs")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
