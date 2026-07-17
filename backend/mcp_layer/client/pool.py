"""Process-wide pool of MCP client sessions, one per registered server.

Constructed once (FastAPI lifespan, once the Orchestrator exists in M4) and
handed around via dependency injection -- never re-created per request. With
an empty `ServerRegistry` (no servers registered), `start()`/`stop()` are
no-ops, which is exactly the M0 "no behavior change" milestone.
"""

from __future__ import annotations

import json
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ..registry.catalog import ToolCatalog, ToolSpec
from ..registry.registry import ServerRegistry
from .errors import ToolError


@dataclass
class ToolResult:
    tool: str
    server: str
    content: dict[str, Any]
    is_error: bool


class MCPClientPool:
    """Owns one ClientSession per registered MCP server for the process lifetime."""

    def __init__(self, registry: ServerRegistry) -> None:
        self._registry = registry
        self._stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}
        self.catalog = ToolCatalog()

    async def start(self) -> None:
        """Open a streamable-http session to every server in the registry."""
        for server in self._registry.servers():
            read_stream, write_stream, _get_session_id = await self._stack.enter_async_context(
                streamable_http_client(server.url)
            )
            session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            self._sessions[server.name] = session
        await self.catalog.refresh(self)

    async def stop(self) -> None:
        """Close all sessions cleanly (called from FastAPI lifespan shutdown)."""
        await self._stack.aclose()
        self._sessions.clear()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Resolve `tool_name` -> owning server via ToolCatalog, then `session.call_tool()`."""
        spec = self.catalog.get(tool_name)
        session = self._sessions[spec.server]
        result = await session.call_tool(tool_name, arguments or {})

        if result.isError:
            message = result.content[0].text if result.content else "tool call failed"
            raise ToolError(server=spec.server, tool=tool_name, message=message)

        content = result.structuredContent
        if content is None and result.content:
            content = json.loads(result.content[0].text)
        return ToolResult(tool=tool_name, server=spec.server, content=content or {}, is_error=False)

    async def list_tools(self) -> list[ToolSpec]:
        """Delegate to ToolCatalog; used by the Planner for tool discovery."""
        await self.catalog.refresh(self)
        return self.catalog.list()

    def session_for(self, server_name: str) -> ClientSession:
        """Raw session access, used by `ToolCatalog.refresh()` to call `tools/list` per server."""
        return self._sessions[server_name]

    def server_names(self) -> list[str]:
        return list(self._sessions.keys())
