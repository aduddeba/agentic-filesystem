"""Import-graph lint (design doc backend/docs/mcp_architecture.md, #12).

Two invariants, checked via `ast` rather than a new `import-linter`
dependency:

1. `agents/`, `planner/`, `orchestrator/` must never import `mcp_layer.servers.*`
   directly -- the only legal path to an implementation is through
   `MCPClientPool.call_tool()`. These packages don't exist yet (that's M4/M5),
   so this rule is vacuously true today and just needs to keep being true.
2. No MCP server's `impl.py` may import from `agents`/`planner`/`orchestrator`
   or from another server's package.

Runs as an ordinary pytest test, so it rides along with `pytest` -- no
separate tool needed. Kept as the first thing CI runs (see
`.github/workflows/ci.yml`), since it's cheap and catches architectural
drift before any slower test does.
"""

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _imported_module_names(path: Path) -> set[str]:
    """Every module referenced by `import x.y` or `from x.y import z` (absolute only)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def _matches_any(name: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)


def _find_violations(py_files: list[Path], forbidden_prefixes: tuple[str, ...]) -> dict[str, list[str]]:
    violations: dict[str, list[str]] = {}
    for path in py_files:
        hits = sorted(name for name in _imported_module_names(path) if _matches_any(name, forbidden_prefixes))
        if hits:
            violations[str(path.relative_to(BACKEND_ROOT))] = hits
    return violations


def test_agents_planner_orchestrator_never_import_mcp_servers_directly():
    targets: list[Path] = []
    for package in ("agents", "planner", "orchestrator"):
        package_dir = BACKEND_ROOT / package
        if package_dir.is_dir():
            targets.extend(package_dir.rglob("*.py"))

    violations = _find_violations(targets, forbidden_prefixes=("mcp_layer.servers",))
    assert not violations, f"agents/planner/orchestrator importing mcp_layer.servers directly: {violations}"


def test_server_impls_never_cross_import_other_servers_or_agent_layer():
    servers_dir = BACKEND_ROOT / "mcp_layer" / "servers"
    server_names = sorted(d.name for d in servers_dir.iterdir() if d.is_dir() and not d.name.startswith("_"))
    assert server_names, "expected at least one MCP server package under mcp_layer/servers"

    violations: dict[str, list[str]] = {}
    for server_name in server_names:
        impl_path = servers_dir / server_name / "impl.py"
        if not impl_path.is_file():
            continue

        other_servers = tuple(f"mcp_layer.servers.{name}" for name in server_names if name != server_name)
        forbidden = ("agents", "planner", "orchestrator", *other_servers)

        hits = sorted(name for name in _imported_module_names(impl_path) if _matches_any(name, forbidden))
        if hits:
            violations[str(impl_path.relative_to(BACKEND_ROOT))] = hits

    assert not violations, f"MCP server impl.py cross-importing forbidden modules: {violations}"
