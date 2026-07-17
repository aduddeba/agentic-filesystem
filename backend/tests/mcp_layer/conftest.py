"""Shared fixtures for the MCP layer's tests."""

import threading
import time

import httpx
import pytest
import uvicorn


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _serve_in_thread(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    return server


def _wait_healthy(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"server on port {port} never became healthy")


@pytest.fixture(scope="session")
def running_filesystem_and_search_servers(tmp_path_factory):
    """Boot real Filesystem + Search servers over Streamable HTTP (no Postgres/torch
    needed) so `MCPClientPool`/`ServerRegistry` tests exercise the real wire transport
    instead of the in-memory session helper the per-server tests use."""
    from app.config import settings

    settings.storage_root = str(tmp_path_factory.mktemp("mcp_pool_storage"))

    from mcp_layer.servers.filesystem.server import app as filesystem_app
    from mcp_layer.servers.search.server import app as search_app

    servers = [
        _serve_in_thread(filesystem_app, 8801),
        _serve_in_thread(search_app, 8802),
    ]
    _wait_healthy(8801)
    _wait_healthy(8802)
    yield
    for server in servers:
        server.should_exit = True
