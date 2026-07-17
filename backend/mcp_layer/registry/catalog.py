"""Aggregates `tools/list` across every registered MCP server into a queryable catalog.

This is the piece that avoids hardcoding tool lists anywhere: adding a new
`@mcp.tool()` to an existing server requires zero changes outside that
server's own file. Callers (Planner, Agent allow-lists) only ever see
`ToolSpec`s, never a server's implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client.pool import MCPClientPool


@dataclass(frozen=True)
class ToolSpec:
    name: str                 # "filesystem.read"
    server: str                # "filesystem"
    description: str
    input_schema: dict
    output_schema: dict | None


class ToolCatalog:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    async def refresh(self, pool: "MCPClientPool") -> None:
        """Call tools/list on every session in `pool`, rebuild `self._tools`."""
        tools: dict[str, ToolSpec] = {}
        for server_name in pool.server_names():
            result = await pool.session_for(server_name).list_tools()
            for tool in result.tools:
                tools[tool.name] = ToolSpec(
                    name=tool.name,
                    server=server_name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema,
                    output_schema=tool.outputSchema,
                )
        self._tools = tools

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def list(self, namespace: str | None = None) -> list[ToolSpec]:
        """namespace='filesystem' -> only filesystem.* tools (used for agent allow-lists)."""
        specs = list(self._tools.values())
        if namespace is None:
            return specs
        prefix = f"{namespace}."
        return [spec for spec in specs if spec.name.startswith(prefix)]

    def as_planner_context(self) -> str:
        """Render name+description+schema as compact text for the planning prompt."""
        return "\n".join(
            f"{spec.name}: {spec.description}\n  input: {spec.input_schema}"
            for spec in self._tools.values()
        )
