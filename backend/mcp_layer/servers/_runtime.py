"""Shared boilerplate for running an MCP server standalone.

Every server module does the same two things beyond defining its tools:
exposes a `/healthz` route on its Streamable HTTP app (so `ServerRegistry`
can poll it), and dispatches `__main__` to either stdio (local dev) or
Streamable HTTP (`docker-compose`/`uvicorn`) per the design doc's transport
decision. Centralized here instead of repeated per server.
"""

from __future__ import annotations

import sys

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route


def build_app(mcp) -> Starlette:
    """Return `mcp`'s Streamable HTTP app with a `/healthz` route attached."""
    app = mcp.streamable_http_app()
    app.router.routes.append(Route("/healthz", lambda request: PlainTextResponse("ok")))
    return app


def run_main(mcp) -> None:
    """`python -m mcp_layer.servers.<name>.server [--stdio]` entrypoint."""
    transport = "stdio" if "--stdio" in sys.argv else "streamable-http"
    mcp.run(transport=transport)
