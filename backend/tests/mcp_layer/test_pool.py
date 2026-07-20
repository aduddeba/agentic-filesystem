"""MCPClientPool.call_tool() round-tripping over real Streamable HTTP, against
actually-running Filesystem + Search servers (not the in-memory session helper
the per-server tests use -- this is what proves the real transport works)."""

import pytest

from mcp_layer.client.errors import ToolError
from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.registry import ServerRegistry


@pytest.fixture
def two_server_registry(running_filesystem_and_search_servers, tmp_path):
    yaml_path = tmp_path / "servers.yaml"
    yaml_path.write_text(
        "servers:\n"
        "  - name: filesystem\n"
        "    url: http://127.0.0.1:8801/mcp\n"
        "    transport: streamable-http\n"
        "    health: /healthz\n"
        "  - name: search\n"
        "    url: http://127.0.0.1:8802/mcp\n"
        "    transport: streamable-http\n"
        "    health: /healthz\n",
        encoding="utf-8",
    )
    return ServerRegistry(yaml_path)


@pytest.mark.anyio
async def test_call_tool_round_trips_across_two_servers(two_server_registry):
    pool = MCPClientPool(two_server_registry)
    await pool.start()
    try:
        write_result = await pool.call_tool(
            "filesystem.write", {"path": "pool_test.txt", "content": "hello pool"}
        )
        assert write_result.server == "filesystem"
        assert write_result.content == {"path": "pool_test.txt", "size_bytes": 10}

        search_result = await pool.call_tool("search.keyword", {"query": "hello"})
        assert search_result.server == "search"
        assert search_result.content["matches"][0]["path"] == "pool_test.txt"
    finally:
        await pool.stop()


@pytest.mark.anyio
async def test_call_tool_raises_tool_error_on_failure(two_server_registry):
    pool = MCPClientPool(two_server_registry)
    await pool.start()
    try:
        with pytest.raises(ToolError) as exc_info:
            await pool.call_tool("filesystem.read", {"path": "does-not-exist.txt"})
        assert exc_info.value.server == "filesystem"
        assert exc_info.value.tool == "filesystem.read"
    finally:
        await pool.stop()


@pytest.mark.anyio
async def test_call_tool_raises_tool_error_for_an_unregistered_tool_name(two_server_registry):
    """A tool name no server exposes (e.g. a `git.*`/`python.*` call before those servers
    exist) must surface as a ToolError, not a bare KeyError from the catalog lookup."""
    pool = MCPClientPool(two_server_registry)
    await pool.start()
    try:
        with pytest.raises(ToolError) as exc_info:
            await pool.call_tool("git.status", {})
        assert exc_info.value.tool == "git.status"
    finally:
        await pool.stop()


@pytest.mark.anyio
async def test_start_stop_are_no_ops_on_an_empty_registry(tmp_path):
    empty_yaml = tmp_path / "servers.yaml"
    empty_yaml.write_text("servers: []\n", encoding="utf-8")

    pool = MCPClientPool(ServerRegistry(empty_yaml))
    await pool.start()
    assert pool.server_names() == []
    await pool.stop()
