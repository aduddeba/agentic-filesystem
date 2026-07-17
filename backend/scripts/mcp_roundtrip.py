"""Throwaway smoke test for the M1/M2 MCP servers.

Boots all 5 servers in-process (Streamable HTTP, via `uvicorn.Server` in
background threads on the ports in `mcp_layer/registry/servers.yaml`), then
calls one tool on each through a real `MCPClientPool` -- proving the round
trip end to end exactly the way the design doc's M1 milestone asks for.

Run from `backend/`:
    python -m scripts.mcp_roundtrip

`embeddings`/`vectors` calls need sentence-transformers/torch installed and
(for `vectors`) a reachable Postgres+pgvector -- if either is missing, those
two lines report [FAIL] with the underlying error instead of the whole
script aborting.
"""

import asyncio
import threading
import time

import httpx
import uvicorn

from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.registry import ServerRegistry
from mcp_layer.servers.documents.server import app as documents_app
from mcp_layer.servers.embeddings.server import app as embeddings_app
from mcp_layer.servers.filesystem.server import app as filesystem_app
from mcp_layer.servers.search.server import app as search_app
from mcp_layer.servers.vectors.server import app as vectors_app

APPS = {
    "filesystem": (filesystem_app, 8801),
    "search": (search_app, 8802),
    "documents": (documents_app, 8803),
    "embeddings": (embeddings_app, 8804),
    "vectors": (vectors_app, 8805),
}

# One tool call per server that should succeed against whatever's already in
# `backend/storage/` -- no fixtures, this is meant to run against a real dev setup.
CALLS = [
    ("filesystem.list", {}),
    ("search.keyword", {"query": "the"}),
    ("document.chunk", {"text": "hello there general kenobi", "chunk_size": 2, "overlap": 0}),
    ("embedding.query", {"text": "hello"}),
    ("semantic.search", {"query": "hello"}),
]


def _serve(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


async def _wait_healthy(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                response = await client.get(f"http://127.0.0.1:{port}/healthz")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise TimeoutError(f"server on port {port} never became healthy")


async def main() -> None:
    print("Booting all 5 MCP servers...")
    servers = [_serve(app, port) for app, port in APPS.values()]
    for _name, port in APPS.values():
        await _wait_healthy(port)
    print("All servers healthy.\n")

    pool = MCPClientPool(ServerRegistry())
    await pool.start()

    for tool_name, arguments in CALLS:
        try:
            result = await pool.call_tool(tool_name, arguments)
            print(f"[PASS] {tool_name} -> {result.content}")
        except Exception as exc:  # noqa: BLE001 - smoke test: report and keep going
            print(f"[FAIL] {tool_name} -> {exc!r}")

    await pool.stop()
    for server in servers:
        server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
