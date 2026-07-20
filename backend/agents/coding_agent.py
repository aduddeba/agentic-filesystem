"""CodingAgent -- runs/lints code and inspects git history, via the Python/Git MCP servers.

Allow-list per `mcp_architecture.md` #10.2: `python`, `git`, `filesystem`,
`search`. Defined and tested here (M5), but **not** registered in
`app/mcp_runtime.py`'s live agent list yet -- the Python/Git MCP servers
don't exist until M6 ("CodingAgent goes live against both", per the
README/design doc roadmap). Calling a `git.*`/`python.*` tool today still
fails gracefully (a clean `ToolError` via `MCPClientPool.call_tool`, not a
crash) since nothing routes to this agent until it's wired in.
"""

from .base import BaseAgent


class CodingAgent(BaseAgent):
    name = "coding"
    allowed_namespaces = frozenset({"python", "git", "filesystem", "search"})
    allowed_tools = frozenset()
