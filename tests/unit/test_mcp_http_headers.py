"""Configured headers must reach both Streamable HTTP operations."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("mcp")
from mcp.types import CallToolResult, TextContent, Tool

from chak.tools.mcp import Server
from chak.tools.mcp import client

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("configured", [False, True])
async def test_http_headers_reach_discovery_and_execution(monkeypatch, configured):
    monkeypatch.setenv("MCP_TEST_TOKEN", "test-token")
    headers = {
        "User-Agent": "chak-ai/test",
        "Authorization": "Bearer ${MCP_TEST_TOKEN}",
    } if configured else {}
    expected = {
        "User-Agent": "chak-ai/test",
        "Authorization": "Bearer test-token",
    } if configured else {}
    url = "https://example.com/mcp"
    observed = []

    @asynccontextmanager
    async def transport(actual_url, *, headers):
        observed.append((actual_url, headers))
        yield ("read-stream", "write-stream", lambda: None)

    remote_tool = Tool(name="web_search", inputSchema={"type": "object"})
    result = CallToolResult(content=[TextContent(type="text", text="Useful result")])
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[remote_tool]))
    session.call_tool = AsyncMock(return_value=result)
    session_factory = MagicMock(return_value=session)
    monkeypatch.setattr(client, "streamablehttp_client", transport)
    monkeypatch.setattr(client, "ClientSession", session_factory)

    server = Server(url=url, headers=headers)
    tools = await server.tools(["web_search"])
    assert len(tools) == 1
    arguments = {"objective": "Python asyncio", "search_queries": ["Python asyncio guide"]}
    assert await tools[0].call(arguments, retry=False) == result
    assert observed == [(url, expected), (url, expected)]
    assert server.get_config()["headers"] == headers
    assert session_factory.call_count == 2
    session_factory.assert_called_with("read-stream", "write-stream")
    assert session.initialize.await_count == 2
    assert session.__aexit__.await_count == 2
    session.call_tool.assert_awaited_once_with("web_search", arguments=arguments)
