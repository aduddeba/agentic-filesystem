"""Lazy, process-wide MCPClientPool + Orchestrator, started on first use.

Unlike Postgres (required for the app to boot at all), the 6-server MCP
cluster + Ollama daemon are only needed for `/api/tasks` -- file browsing and
keyword/semantic search still call `tools/*` directly, untouched by this
layer. Starting the pool from the FastAPI `lifespan` unconditionally would
make the *entire app* fail to boot without 6 extra background processes
running, which would be a regression for everything else. So construction is
deferred to the first `get_orchestrator()` call and cached after that; a
`shutdown()` hook closes it from the `lifespan` shutdown path if it was ever
started.
"""

from __future__ import annotations

import asyncio

from agents.analysis_agent import AnalysisAgent
from agents.editing_agent import EditingAgent
from agents.organization_agent import OrganizationAgent
from agents.search_agent import SearchAgent
from mcp_layer.client.pool import MCPClientPool
from mcp_layer.registry.registry import ServerRegistry
from memory.store import MemoryStore
from orchestrator.orchestrator import Orchestrator
from planner.planner import Planner

from .config import settings
from .database import SessionLocal

_pool: MCPClientPool | None = None
_orchestrator: Orchestrator | None = None
_lock = asyncio.Lock()


async def get_orchestrator() -> Orchestrator:
    """Return the process-wide Orchestrator, starting the MCP client pool on first call."""
    global _pool, _orchestrator
    if _orchestrator is not None:
        return _orchestrator

    async with _lock:
        if _orchestrator is not None:
            return _orchestrator

        pool = MCPClientPool(ServerRegistry())
        try:
            await pool.start()
        except BaseException:
            # start() can fail partway through, after already entering some
            # servers' async context managers via its internal AsyncExitStack.
            # Unwind those here, in the same task, before propagating -- an
            # orphaned AsyncExitStack gets force-closed later from whatever
            # task happens to garbage-collect it, which corrupts that task's
            # async runtime instead of failing this request cleanly.
            await pool.stop()
            raise

        planner = Planner(pool, chat_model=settings.ollama_chat_model)
        memory = MemoryStore(SessionLocal)
        orchestrator = Orchestrator(
            client=pool,
            tool_catalog=pool.catalog,
            planner=planner,
            # CodingAgent is intentionally excluded -- it's defined and tested (agents/
            # coding_agent.py) but its git.*/python.* tools have no MCP server yet
            # ("CodingAgent goes live" is M6, per the README/design doc roadmap).
            agents=[SearchAgent(), OrganizationAgent(), EditingAgent(), AnalysisAgent()],
            max_steps=settings.planner_max_steps,
            max_replans=settings.planner_max_replans,
            memory=memory,
        )
        _pool, _orchestrator = pool, orchestrator
        return orchestrator


async def shutdown() -> None:
    """Close the pool if it was ever started; safe to call unconditionally from lifespan shutdown."""
    global _pool, _orchestrator
    if _pool is not None:
        await _pool.stop()
    _pool = None
    _orchestrator = None
