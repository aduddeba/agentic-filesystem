"""Static-ish knowledge of which MCP servers exist and where to reach them.

This is config, not discovery -- a new server has to be added to
`servers.yaml` before anything can call it. What tools each registered
server actually exposes is `ToolCatalog`'s job, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

DEFAULT_SERVERS_YAML = Path(__file__).resolve().parent / "servers.yaml"


@dataclass(frozen=True)
class ServerConfig:
    name: str
    url: str
    transport: str
    health: str


class ServerRegistry:
    def __init__(self, yaml_path: Path | str = DEFAULT_SERVERS_YAML) -> None:
        path = Path(yaml_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
        self._servers = [ServerConfig(**entry) for entry in (data or {}).get("servers", [])]

    def servers(self) -> list[ServerConfig]:
        return list(self._servers)

    async def health_check(self) -> dict[str, bool]:
        """GET each server's health path; True if it responds 200."""
        results: dict[str, bool] = {}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for server in self._servers:
                base = server.url.rsplit("/", 1)[0]
                try:
                    response = await client.get(f"{base}{server.health}")
                    results[server.name] = response.status_code == 200
                except httpx.HTTPError:
                    results[server.name] = False
        return results
