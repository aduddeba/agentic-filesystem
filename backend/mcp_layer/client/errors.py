"""Typed error surfaced when an MCP tool call fails."""


class ToolError(Exception):
    """Raised when a tool call returns `isError=True` or the transport fails.

    Carries enough structure (`server`, `tool`) for a caller like the Planner
    to decide whether to re-plan around the failure or surface it verbatim,
    instead of pattern-matching a bare exception message.
    """

    def __init__(self, server: str, tool: str, message: str) -> None:
        self.server = server
        self.tool = tool
        self.message = message
        super().__init__(f"{tool} ({server}): {message}")
