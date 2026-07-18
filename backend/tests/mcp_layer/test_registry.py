"""ServerRegistry + ToolCatalog, including a real health-check/tools-list round
trip against actually-running servers (Filesystem + Search -- no Postgres/torch
needed) over Streamable HTTP, not the in-memory session helper."""

import textwrap

import pytest

from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.registry import ServerRegistry


def test_empty_registry_has_no_servers(tmp_path):
    empty_yaml = tmp_path / "servers.yaml"
    empty_yaml.write_text("servers: []\n", encoding="utf-8")

    assert ServerRegistry(empty_yaml).servers() == []


def test_missing_yaml_file_is_also_an_empty_registry(tmp_path):
    assert ServerRegistry(tmp_path / "does-not-exist.yaml").servers() == []


def test_registry_loads_the_real_servers_yaml():
    names = {server.name for server in ServerRegistry().servers()}
    assert names == {"filesystem", "search", "documents", "embeddings", "vectors", "ollama"}


def _write_registry_yaml(tmp_path, *, include_unreachable: bool) -> ServerRegistry:
    entries = [
        "  - name: filesystem\n"
        "    url: http://127.0.0.1:8801/mcp\n"
        "    transport: streamable-http\n"
        "    health: /healthz\n"
    ]
    if include_unreachable:
        entries.append(
            "  - name: unreachable\n"
            "    url: http://127.0.0.1:9999/mcp\n"
            "    transport: streamable-http\n"
            "    health: /healthz\n"
        )
    yaml_path = tmp_path / "servers.yaml"
    yaml_path.write_text("servers:\n" + "".join(entries), encoding="utf-8")
    return ServerRegistry(yaml_path)


@pytest.mark.anyio
async def test_health_check_distinguishes_reachable_from_unreachable(
    running_filesystem_and_search_servers, tmp_path
):
    registry = _write_registry_yaml(tmp_path, include_unreachable=True)
    health = await registry.health_check()
    assert health == {"filesystem": True, "unreachable": False}


@pytest.mark.anyio
async def test_catalog_refresh_lists_tools_from_a_real_running_server(
    running_filesystem_and_search_servers, tmp_path
):
    registry = _write_registry_yaml(tmp_path, include_unreachable=False)
    pool = MCPClientPool(registry)
    await pool.start()
    try:
        tools = await pool.list_tools()
        names = {tool.name for tool in tools}
        assert "filesystem.read" in names
        assert all(tool.server == "filesystem" for tool in tools)
        assert pool.catalog.get("filesystem.read").input_schema["required"] == ["path"]
    finally:
        await pool.stop()
