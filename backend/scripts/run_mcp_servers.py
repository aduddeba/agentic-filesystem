"""Long-running dev helper: boots all 6 MCP servers and blocks until Ctrl+C.

Unlike `scripts/mcp_roundtrip.py` (a one-shot smoke test that starts, calls
one tool per server, and exits), this is meant to be left running in its own
terminal while you exercise `POST /api/tasks` against a separately-running
`uvicorn app.main:app`, mirroring how `ollama serve` is its own long-lived
process.

Run from `backend/`:
    python -m scripts.run_mcp_servers
"""

import asyncio
import signal
import threading

import httpx
import uvicorn

from mcp_layer.servers.documents.server import app as documents_app
from mcp_layer.servers.embeddings.server import app as embeddings_app
from mcp_layer.servers.filesystem.server import app as filesystem_app
from mcp_layer.servers.ollama.server import app as ollama_app
from mcp_layer.servers.search.server import app as search_app
from mcp_layer.servers.vectors.server import app as vectors_app

APPS = {
    "filesystem": (filesystem_app, 8801),
    "search": (search_app, 8802),
    "documents": (documents_app, 8803),
    "embeddings": (embeddings_app, 8804),
    "vectors": (vectors_app, 8805),
    "ollama": (ollama_app, 8808),
}


def _serve(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


async def _wait_healthy(port: int, timeout: float = 10.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                response = await client.get(f"http://127.0.0.1:{port}/healthz")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.1)
    raise TimeoutError(f"server on port {port} never became healthy")


async def main() -> None:
    servers = {name: _serve(app, port) for name, (app, port) in APPS.items()}
    for name, (_app, port) in APPS.items():
        await _wait_healthy(port)
        print(f"[ready] {name} on :{port}")
    print("\nAll 6 MCP servers running. Ctrl+C to stop.\n")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    await stop_event.wait()

    print("\nStopping...")
    for server in servers.values():
        server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
