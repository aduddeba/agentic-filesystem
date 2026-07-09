# MCP Architecture — Design Document

Status: **design only** — nothing in this document is wired up yet. It is the
reference the incremental milestones in [§11](#11-roadmap) build toward. Every
milestone must leave `docker compose up` + the existing test suite green.

Baseline this design builds on (as of this write-up): a plain FastAPI app
(`backend/app/`) with SQLAlchemy models (`FileRecord`, `Chunk` + pgvector),
REST routes in `app/routes/files.py` that call plain Python functions in
`backend/tools/{filesystem,documents,embeddings}/` directly, and a hybrid
keyword+vector `semantic_search()` in `app/search.py`. There is **no**
planner, agent, orchestrator, LLM integration, or memory store yet — those are
new. This matters: we are not migrating a working multi-agent system onto
MCP, we're building the agent layer *for the first time*, on top of tool
implementations that mostly already exist as plain functions. That's the
cheap part of this refactor — the existing `tools/*` modules become the
*implementation* called from inside MCP server processes, largely unchanged.

---

## 1. Updated project architecture

```
User
 │
 ▼
Next.js Frontend  (frontend/)
 │  REST + SSE (streaming plan/tool progress)
 ▼
FastAPI Backend  (backend/api/)
 │
 ▼
Agent Orchestrator  (backend/orchestrator/)
 │
 ├──► Memory  (backend/memory/)            [plain Python — never via MCP]
 │
 ▼
Planner  (backend/planner/)
 │  produces a Plan: list[ToolCall] + a verification step
 ▼
Specialized Agents  (backend/agents/{search,organization,editing,analysis,coding})
 │  each agent is only allowed to invoke a subset of tool namespaces
 ▼
MCP Client  (backend/mcp/client/)
 │  one pooled ClientSession per registered server
 ▼
MCP Server Registry  (backend/mcp/registry/)
 │  static config + live tools/list aggregation → ToolCatalog
 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Filesystem │ Search │ Document │ Embedding │ Vector │ Git │ Python │ Ollama │
│   Server   │ Server │  Server  │  Server   │ Server │ Srv │ Server │ Server │
└─────────────────────────────────────────────────────────────────────┘
 │             │          │            │          │       │      │       │
 ▼             ▼          ▼            ▼          ▼       ▼      ▼       ▼
Filesystem   ripgrep   PyMuPDF/    sentence-   pgvector  git   subproc  Ollama
              proc     docx/xlsx   transformers  (Postgres)  CLI   /venv   HTTP API
```

Key invariant, stated as a rule the code must enforce, not just a diagram:
**no agent, planner, or orchestrator module may `import` anything from
`backend/mcp/servers/**`.** The only legal path from an agent to an
implementation is `Agent → MCPClient.call_tool(name, args) → (network/stdio)
→ MCP Server → implementation`. This is enforced in CI by an import-graph
lint (see [§12](#12-testing-strategy)), not just by convention.

### Transport decision

Each MCP server is a **long-lived process** speaking MCP over **Streamable
HTTP** (`mcp.server.fastmcp.FastMCP(..., transport="streamable-http")`),
listening on a fixed localhost port, one container per server in
`docker-compose.yml` — consistent with how `db` already runs today. This is
chosen over stdio because:

- The backend needs **concurrent** tool calls from multiple agents/requests
  against the *same* server (e.g. two search requests in flight). Stdio MCP
  servers are normally spawned 1:1 per client session; HTTP lets one server
  process serve a pooled set of client sessions.
- Servers that hold state worth keeping warm across calls (the Embedding
  server's loaded sentence-transformers model, the Ollama server's HTTP
  keep-alive connection) shouldn't be re-initialized per subprocess spawn.
- It matches the existing `docker-compose.yml` operational model — each
  server is `docker compose up`-able and independently restartable/loggable,
  exactly like `db` is today.

Stdio remains available as a fallback transport per-server (FastMCP supports
both from the same tool definitions) for servers you want to run without
Docker during local development — see `mcp.run(transport=...)` per server's
`__main__`.

---

## 2. Folder structure

Concrete mapping from what exists today to the target tree. Nothing here is
a rename that has to happen in one shot — the roadmap moves one row at a
time.

```
backend/
├── api/                      # was app/routes/ + app/main.py
│   ├── main.py                 # FastAPI app, lifespan, CORS — was app/main.py
│   └── routes/
│       ├── files.py             # thins out as agents take over file ops
│       ├── settings.py
│       └── tasks.py             # NEW — submit a task to the orchestrator, SSE stream back
│
├── orchestrator/             # NEW
│   └── orchestrator.py         # receives a task, calls Memory, calls Planner, dispatches to Agents
│
├── planner/                  # NEW
│   ├── planner.py               # builds a Plan from task + ToolCatalog + memory context
│   ├── plan.py                  # Plan / PlanStep dataclasses (Pydantic)
│   └── prompts.py               # prompt templates sent to llm.chat
│
├── memory/                   # NEW — independent of MCP, see §Memory
│   ├── store.py                 # MemoryStore (SQLAlchemy-backed)
│   ├── models.py                 # TaskRecord, Summary, Preference, FileHistoryEntry
│   └── schemas.py
│
├── agents/                   # NEW
│   ├── base.py                   # Agent Protocol + BaseAgent (shared allow-list enforcement)
│   ├── search_agent.py
│   ├── organization_agent.py
│   ├── editing_agent.py
│   ├── analysis_agent.py
│   └── coding_agent.py
│
├── mcp/                      # NEW — everything MCP-specific lives here
│   ├── client/
│   │   ├── pool.py               # MCPClientPool: one ClientSession per server
│   │   └── errors.py
│   ├── registry/
│   │   ├── servers.yaml          # static: name, url, transport, health path
│   │   ├── registry.py           # ServerRegistry: loads servers.yaml, health-checks
│   │   └── catalog.py            # ToolCatalog: aggregates tools/list across servers
│   └── servers/
│       ├── filesystem/
│       │   ├── server.py          # FastMCP instance + @mcp.tool() defs
│       │   └── impl.py            # was backend/tools/filesystem/*
│       ├── search/
│       │   ├── server.py
│       │   └── impl.py            # was backend/tools/filesystem/search.py (ripgrep wrapper)
│       ├── documents/
│       │   ├── server.py
│       │   └── impl.py            # was backend/tools/documents/*
│       ├── embeddings/
│       │   ├── server.py
│       │   └── impl.py            # was backend/tools/embeddings/*
│       ├── vectors/
│       │   ├── server.py
│       │   └── impl.py            # was app/search.py's vector_search + Chunk CRUD
│       ├── git/
│       │   ├── server.py
│       │   └── impl.py            # NEW — wraps GitPython or `git` CLI
│       ├── python/
│       │   ├── server.py
│       │   └── impl.py            # NEW — subprocess-isolated run/lint/format/tests
│       └── ollama/
│           ├── server.py
│           └── impl.py            # NEW — wraps Ollama's local HTTP API
│
├── shared/                   # cross-cutting, no business logic
│   ├── config.py                # was app/config.py
│   ├── paths.py                  # was app/paths.py
│   └── logging.py
│
├── database/                 # was app/database.py, app/models.py, app/repository.py
│   ├── session.py
│   ├── models.py                 # FileRecord, Chunk (unchanged)
│   └── repository.py
│
├── workers/                  # NEW — background jobs (filesystem watcher, reindex sweeps)
│   └── watcher.py                # Watchdog-based, replaces manual reconcile() polling
│
├── tests/
│   ├── mcp/
│   │   ├── servers/               # one test module per server, in-process, no orchestrator
│   │   └── test_registry.py
│   ├── planner/
│   ├── agents/
│   └── ...                       # existing tests/test_*.py stay, updated for new imports
│
└── docs/
    └── mcp_architecture.md      # this file
```

`backend/tools/` is deleted once its contents are fully absorbed as
`impl.py` modules under each server (Milestone M2 in the roadmap) — the code
mostly moves, it isn't rewritten.

---

## 3. MCP server layout

Every server is a small FastMCP app with **one process, one responsibility,
one port**. None import from each other. None import from `agents/`,
`planner/`, or `orchestrator/`. Ports below are placeholders for
`docker-compose.yml`.

| Server | Port | Tools | Backing implementation |
|---|---|---|---|
| Filesystem | 8801 | `filesystem.read`, `.write`, `.list`, `.move`, `.rename`, `.delete`, `.copy`, `.mkdir`, `.metadata` | stdlib `pathlib`/`shutil`, scoped to `settings.storage_root` |
| Search | 8802 | `search.keyword`, `.regex`, `.filename`, `.extension`, `.todo`, `.content` | `ripgrep` subprocess (existing `tools/filesystem/search.py` logic) |
| Document | 8803 | `document.read_pdf`, `.read_docx`, `.read_excel`, `.extract_text`, `.summary`, `.ocr` | PyMuPDF, python-docx, openpyxl; `.summary` calls `llm.summarize` on the Ollama server via the client pool; `.ocr` optional (pytesseract), degrades to "unsupported" if not installed |
| Embedding | 8804 | `embedding.generate`, `.batch`, `.query` | sentence-transformers, loaded once at server startup and kept warm |
| Vector | 8805 | `semantic.search`, `.similar`, `.related`, `.insert`, `.delete` | pgvector via SQLAlchemy, own DB session, wraps existing `Chunk`/`FileRecord` queries |
| Git | 8806 | `git.status`, `.diff`, `.commit`, `.history`, `.branch` | GitPython or `git` CLI subprocess, scoped to repos under `storage_root` |
| Python | 8807 | `python.run`, `.lint`, `.format`, `.tests` | subprocess, executed in a locked-down venv/container, **never** the backend's own interpreter |
| Ollama | 8808 | `llm.chat`, `.generate`, `.embed`, `.summarize`, `.classify` | HTTP calls to the local Ollama daemon (`http://localhost:11434`) |

Each server directory is independently runnable:

```bash
python -m mcp.servers.filesystem.server         # stdio, for local dev
uvicorn mcp.servers.filesystem.server:app       # streamable-http, for docker-compose
```

### Security boundaries worth calling out now

- **Filesystem / Search / Vector / Document** servers must resolve all paths
  through the existing `paths.resolve_path()` jail (already in
  `app/paths.py`) so a tool call can never escape `storage_root`. This check
  belongs *inside* the server, not the client — the server is the trust
  boundary.
- **Python server** executes arbitrary code by design (`python.run`,
  `.tests`). It must run in a separate, resource-limited process (or
  container) from the FastAPI backend and from every other MCP server, with
  no access to the Postgres credentials or the raw filesystem outside a
  scratch dir. Treat it like a sandboxed code-execution service, not a
  trusted peer.
- **Git server** should only operate on directories under `storage_root`
  that are actual git repos (checked via `git rev-parse --is-inside-work-tree`
  before any mutating tool runs).

---

## 4. Planner architecture

```
Task (natural language, from Orchestrator)
        │
        ▼
 ┌─────────────────────┐
 │ 1. Load context      │  Memory.recent_tasks(), Memory.preferences(),
 │                      │  ToolCatalog.list_tools() (name+desc+schema only)
 └─────────────────────┘
        │
        ▼
 ┌─────────────────────┐
 │ 2. Draft plan        │  llm.chat with a structured-output prompt →
 │    (LLM call)        │  Plan JSON validated against Pydantic schema
 └─────────────────────┘
        │
        ▼
 ┌─────────────────────┐
 │ 3. Execute step N    │  Orchestrator dispatches PlanStep to the Agent
 │    via chosen Agent  │  whose allow-list covers the tool namespace
 └─────────────────────┘
        │
        ▼
 ┌─────────────────────┐
 │ 4. Feed result back  │  ToolResult appended to plan context;
 │    (ReAct loop)       │  Planner may re-plan remaining steps if a
 │                      │  step's result contradicts assumptions
 └─────────────────────┘
        │  (repeat 3-4 until plan exhausted or max_steps hit)
        ▼
 ┌─────────────────────┐
 │ 5. Verify            │  Planner issues a verification step (e.g. a
 │                      │  follow-up filesystem.list / search call) and
 │                      │  asks the LLM to judge goal-satisfaction
 └─────────────────────┘
        │
        ▼
 Final Response (+ what changed, for Memory.record_task())
```

The Planner **never** calls `mcp.servers.*` directly and never imports
`tools/*`. Its only two dependencies are `ToolCatalog` (read-only tool
metadata) and `llm.chat` (itself an MCP tool call routed through the same
client pool everyone else uses) — the Planner is just another MCP client.

Bounded execution: `max_steps` and `max_replans` are config values (not
hardcoded) so a runaway plan can't loop forever; hitting either limit
produces a partial result with an explicit "did not finish" status rather
than silently truncating.

---

## 5. MCP client implementation strategy

One process-wide `MCPClientPool`, constructed once at FastAPI startup
(`api/main.py` lifespan, same place `Base.metadata.create_all` already
happens today) and handed to the Orchestrator via dependency injection —
never re-created per request.

```python
# backend/mcp/client/pool.py
class MCPClientPool:
    """Owns one ClientSession per registered MCP server for the process lifetime."""

    def __init__(self, registry: ServerRegistry) -> None: ...

    async def start(self) -> None:
        """Open a streamable-http session to every server in the registry."""

    async def stop(self) -> None:
        """Close all sessions cleanly (called from FastAPI lifespan shutdown)."""

    async def call_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """Resolve tool_name -> owning server via ToolCatalog, then session.call_tool()."""

    async def list_tools(self) -> list[ToolSpec]:
        """Delegate to ToolCatalog; used by the Planner for tool discovery."""
```

Notes:

- `call_tool` takes a **fully-qualified** tool name (`"filesystem.read"`) so
  the pool can route without agents needing to know which server hosts what
  — that mapping lives entirely in `ToolCatalog`.
- Each `ClientSession` gets its own `asyncio.Lock` if the underlying
  transport isn't safe for concurrent calls on one session; simpler
  alternative (recommended to start): open a small session pool (2-4) per
  server rather than one shared session, sized per server based on expected
  concurrency (Embedding/Ollama benefit most from >1).
- Timeouts and retries are configured per server (Python server needs a much
  longer timeout than Filesystem), not globally.
- Errors from a tool call surface as a typed `ToolError` (not a bare
  exception) carrying `server`, `tool`, and the MCP error payload, so the
  Planner can decide to re-plan vs. surface the failure verbatim.

---

## 6. Tool registry

Two layers, deliberately separate:

1. **`ServerRegistry`** (static-ish) — knows *where* servers are
   (`servers.yaml`: name, base_url, transport, health path). This is
   config, not discovery — you still have to tell the system a new server
   exists and where to find it.
2. **`ToolCatalog`** (dynamic) — knows *what tools exist*. Built by calling
   the standard MCP `tools/list` against every server in `ServerRegistry` at
   startup, cached in memory, and refreshable via
   `POST /api/admin/tools/refresh` or a periodic background refresh. This is
   the piece that satisfies "avoid hardcoding tool lists" — adding a new
   `@mcp.tool()` to an existing server requires *zero* changes outside that
   server's file.

```python
# backend/mcp/registry/catalog.py
@dataclass(frozen=True)
class ToolSpec:
    name: str                 # "filesystem.read"
    server: str               # "filesystem"
    description: str
    input_schema: dict        # JSON Schema, straight from tools/list
    output_schema: dict | None

class ToolCatalog:
    async def refresh(self, pool: MCPClientPool) -> None:
        """Call tools/list on every session in pool, rebuild self._tools."""

    def get(self, name: str) -> ToolSpec: ...
    def list(self, namespace: str | None = None) -> list[ToolSpec]:
        """namespace='filesystem' -> only filesystem.* tools (used for agent allow-lists)."""
    def as_planner_context(self) -> str:
        """Render name+description+schema as compact text for the planning prompt."""
```

`servers.yaml` example:

```yaml
servers:
  - name: filesystem
    url: http://filesystem-mcp:8801/mcp
    transport: streamable-http
    health: /healthz
  - name: search
    url: http://search-mcp:8802/mcp
    transport: streamable-http
    health: /healthz
  - name: ollama
    url: http://ollama-mcp:8808/mcp
    transport: streamable-http
    health: /healthz
```

---

## 7. Example tool schemas

Two representative tools, shown as the JSON Schema an MCP `tools/list` call
returns (this is what the Planner actually sees — no implementation
details).

```json
{
  "name": "filesystem.read",
  "description": "Read a UTF-8 text file's contents given a path relative to the storage root.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "Path relative to storage root" }
    },
    "required": ["path"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "path": { "type": "string" },
      "content": { "type": "string" },
      "size_bytes": { "type": "integer" }
    },
    "required": ["path", "content", "size_bytes"]
  }
}
```

```json
{
  "name": "semantic.search",
  "description": "Rank indexed file chunks by embedding similarity to a query, optionally fused with keyword search.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string" },
      "k": { "type": "integer", "default": 10, "minimum": 1, "maximum": 50 },
      "mode": { "type": "string", "enum": ["hybrid", "vector"], "default": "hybrid" }
    },
    "required": ["query"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "matches": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "path": { "type": "string" },
            "text": { "type": "string" },
            "score": { "type": "number" }
          },
          "required": ["path", "text", "score"]
        }
      }
    },
    "required": ["matches"]
  }
}
```

```json
{
  "name": "llm.classify",
  "description": "Classify text into one of a caller-supplied set of labels using the local LLM.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "text": { "type": "string" },
      "labels": { "type": "array", "items": { "type": "string" }, "minItems": 2 }
    },
    "required": ["text", "labels"]
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "label": { "type": "string" },
      "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
    },
    "required": ["label", "confidence"]
  }
}
```

---

## 8. Sequence diagrams

### 8.1 "Organize my Downloads folder"

```
User → API → Orchestrator: task("organize Downloads")
Orchestrator → Memory: recent_tasks(), preferences()
Orchestrator → Planner: plan(task, memory_context, tool_catalog)
Planner → Ollama MCP (llm.chat): draft plan
Planner ← Ollama MCP: Plan[
  filesystem.list, document.extract_text, llm.classify,
  filesystem.move, filesystem.list (verify)
]

loop for each PlanStep
  Orchestrator → OrganizationAgent (or SearchAgent for the list/extract steps):
      dispatch(step)
  OrganizationAgent → MCPClientPool: call_tool(step.tool, step.args)
  MCPClientPool → Filesystem/Document/Ollama MCP Server: tool call
  MCP Server → Filesystem/Ollama: real work
  MCP Server ← Filesystem/Ollama: result
  MCPClientPool ← MCP Server: ToolResult
  OrganizationAgent ← MCPClientPool: ToolResult
  Orchestrator ← OrganizationAgent: StepResult
  Orchestrator → Planner: record StepResult (context for re-plan/verify)
end

Planner → Ollama MCP (llm.chat): verify(goal, step_results)
Planner ← Ollama MCP: {satisfied: true, notes: "..."}
Orchestrator → Memory: record_task(summary, file_history_deltas)
Orchestrator → API → User: final response
```

### 8.2 "Find all TODOs in the project and summarize them"

```
User → API → Orchestrator: task("find and summarize TODOs")
Orchestrator → Planner: plan(...)
Planner → Ollama MCP: draft plan → [search.todo, llm.summarize]

Orchestrator → SearchAgent: dispatch(search.todo)
SearchAgent → MCPClientPool → Search MCP Server → ripgrep subprocess
SearchAgent ← [{path, line, text}, ...]

Orchestrator → AnalysisAgent: dispatch(llm.summarize, matches)
AnalysisAgent → MCPClientPool → Ollama MCP Server → Ollama HTTP API
AnalysisAgent ← summary text

Orchestrator → Memory: record_task(summary)
Orchestrator → API → User: summary + source locations
```

### 8.3 Semantic search with fallback verification

```
User → API → Orchestrator: task("what did I write about the Q3 budget?")
Orchestrator → Planner: plan(...)
Planner → Ollama MCP: draft plan → [semantic.search]

Orchestrator → SearchAgent: dispatch(semantic.search, {query, k:10})
SearchAgent → MCPClientPool → Vector MCP Server → pgvector query (Postgres)
SearchAgent ← matches[]

alt matches empty
  Planner → Ollama MCP: re-plan → [search.keyword] (fallback to ripgrep)
  Orchestrator → SearchAgent: dispatch(search.keyword)
  SearchAgent → MCPClientPool → Search MCP Server → ripgrep
end

Orchestrator → API → User: matches (+ which strategy found them)
```

---

## 9. Suggested interfaces

Signatures only — no bodies. These are the contracts each milestone
implements against.

```python
# backend/mcp/client/pool.py
from typing import Protocol

class ToolResult(Protocol):
    tool: str
    server: str
    content: dict
    is_error: bool

class MCPClient(Protocol):
    async def call_tool(self, tool_name: str, arguments: dict) -> ToolResult: ...
    async def list_tools(self) -> list["ToolSpec"]: ...


# backend/agents/base.py
class Agent(Protocol):
    name: str
    allowed_namespaces: frozenset[str]        # e.g. {"filesystem", "llm"}

    async def handle(self, step: "PlanStep", client: MCPClient) -> "StepResult": ...
    def can_handle(self, tool_name: str) -> bool: ...   # namespace check


# backend/planner/planner.py
class Planner(Protocol):
    async def plan(
        self,
        task: str,
        memory_context: "MemoryContext",
        tool_catalog: "ToolCatalog",
    ) -> "Plan": ...

    async def replan(self, plan: "Plan", results: list["StepResult"]) -> "Plan": ...
    async def verify(self, task: str, results: list["StepResult"]) -> "VerificationOutcome": ...


# backend/orchestrator/orchestrator.py
class Orchestrator(Protocol):
    async def run_task(self, task: str, user_id: str | None = None) -> "TaskOutcome": ...


# backend/memory/store.py
class MemoryStore(Protocol):
    def recent_tasks(self, limit: int = 10) -> list["TaskRecord"]: ...
    def preferences(self) -> dict[str, str]: ...
    def record_task(self, task: str, summary: str, file_deltas: list[str]) -> None: ...
    def file_history(self, path: str) -> list["FileHistoryEntry"]: ...


# backend/mcp/registry/registry.py
class ServerRegistry(Protocol):
    def servers(self) -> list["ServerConfig"]: ...
    async def health_check(self) -> dict[str, bool]: ...      # name -> healthy


# backend/mcp/registry/catalog.py
class ToolCatalog(Protocol):
    async def refresh(self) -> None: ...
    def get(self, name: str) -> "ToolSpec": ...
    def list(self, namespace: str | None = None) -> list["ToolSpec"]: ...
```

Pydantic dataclasses backing the above (`Plan`, `PlanStep`, `StepResult`,
`TaskOutcome`, `VerificationOutcome`, `ServerConfig`) are plain data — no
methods beyond validation — and live next to the Protocol that consumes
them.

---

## 10. Class diagrams

### 10.1 MCP layer

```
┌────────────────────┐        ┌──────────────────────┐
│   ServerRegistry    │───────▶│    ToolCatalog        │
│ + servers()          │       │ + refresh()            │
│ + health_check()     │       │ + get(name)             │
└────────────────────┘        │ + list(namespace)       │
                                 └──────────┬────────────┘
                                            │ used by
                                            ▼
┌────────────────────┐        ┌──────────────────────┐
│   MCPClientPool      │◀──────│      Planner          │
│ + start()             │      │ + plan()               │
│ + stop()              │      │ + replan()             │
│ + call_tool()         │      │ + verify()             │
│ + list_tools()        │      └──────────┬────────────┘
└──────────┬──────────┘                   │ produces
           │ owns 1 session per            ▼
           │ registered server      ┌──────────────────────┐
           ▼                        │        Plan            │
┌────────────────────┐              │ + steps: list[PlanStep]│
│  ClientSession (×N)  │            └──────────────────────┘
│  (mcp SDK, per server)│
└────────────────────┘
```

### 10.2 Agents

```
              ┌───────────────────┐
              │   <<Protocol>>       │
              │      Agent            │
              │ + name                │
              │ + allowed_namespaces   │
              │ + handle(step, client) │
              │ + can_handle(tool)     │
              └─────────┬─────────┘
                        │ implements
   ┌───────────┬────────┼────────┬───────────┬───────────┐
   ▼           ▼        ▼        ▼           ▼           ▼
SearchAgent  Organiz-  Editing  Analysis   CodingAgent
             ationAgent Agent    Agent
{search,      {filesystem, {filesystem,  {llm,        {python, git,
 semantic,     llm}         document,     document,     filesystem,
 llm.classify}              llm}          embedding}    search}
```

Every agent is intentionally *dumb* — it validates that a step's tool falls
within its `allowed_namespaces`, forwards the call to `MCPClientPool`, and
returns the `ToolResult` wrapped as a `StepResult`. All actual "judgment"
(what to call, in what order, whether the goal was met) lives in the
Planner. This keeps agents trivially unit-testable (mock the client, assert
the namespace check) and keeps the Planner the single place that changes
when you add a new capability.

---

## 11. Roadmap

Each milestone ends with `docker compose up` working and the full test suite
green — no milestone leaves the repo in a broken intermediate state.

| # | Milestone | What ships | Existing code touched |
|---|---|---|---|
| **M0** | MCP scaffolding, no behavior change | `mcp/registry/`, `mcp/client/`, `servers.yaml` with **zero** servers registered yet; import-graph lint added to CI (empty allow-list to start) | none |
| **M1** | First real server: Filesystem | `mcp/servers/filesystem/` wraps existing `tools/filesystem/*`; `docker-compose.yml` gets a `filesystem-mcp` service; a throwaway CLI script proves `call_tool("filesystem.read", ...)` round-trips | `tools/filesystem/*` copied to `impl.py`, not rewritten |
| **M2** | Search + Document + Embedding + Vector servers | Same pattern as M1 for the remaining "wrap what already exists" servers; `app/search.py`'s hybrid logic moves into the Vector server, calling the Search and Embedding servers via the client pool instead of importing them | `tools/documents/*`, `tools/embeddings/*`, `app/search.py` |
| **M3** | Ollama server + Planner v0 | `mcp/servers/ollama/`; minimal `Planner` that takes a fixed single-tool task ("run this exact tool") — no LLM planning yet, just proves the Plan → execute → result pipeline end to end | new |
| **M4** | Real LLM-driven planning + Orchestrator | `Planner.plan()` calls `llm.chat` with `ToolCatalog.as_planner_context()`; `Orchestrator` wires Planner + one Agent (start with SearchAgent only); new `api/routes/tasks.py` endpoint | new |
| **M5** | Remaining agents + Memory | OrganizationAgent, EditingAgent, AnalysisAgent, CodingAgent; `memory/` store backed by new tables; Orchestrator consults Memory before planning and records after | new |
| **M6** | Git + Python servers, CodingAgent goes live | Sandbox the Python server (separate container/venv, resource limits) before enabling `python.run`/`.tests` for real | new |
| **M7** | Cutover + cleanup | `app/routes/files.py` endpoints that now have MCP+Agent equivalents are re-pointed at the Orchestrator (or removed if the frontend moves to the task endpoint); delete `backend/tools/` once nothing imports it; old `app/` package fully absorbed into `api/`, `shared/`, `database/` | `app/routes/files.py`, `app/main.py` deleted after migration |

Do M0–M2 before touching the Planner at all — they carry zero behavioral
risk (pure wrapping of code that already has tests) and prove the transport,
registry, and Docker wiring work before any LLM non-determinism enters the
picture.

---

## 12. Testing strategy

Each MCP server is tested **in isolation**, without the orchestrator,
planner, or other servers running:

- **Per-server unit tests** (`tests/mcp/servers/test_filesystem_server.py`
  etc.) instantiate the server's FastMCP app directly and call tools through
  an in-process MCP client (the `mcp` SDK ships an in-memory transport for
  exactly this) — no subprocess, no Docker, no network. This is the primary
  test tier and should cover the bulk of tool-logic edge cases (the existing
  `tests/test_read.py`, `test_write.py`, etc. patterns move here largely
  unchanged, just invoked through a tool call instead of a bare function
  call).
- **Contract tests** (`tests/mcp/test_registry.py`) start every registered
  server (via `docker compose -f docker-compose.test.yml up`) and assert
  `tools/list` on each returns schemas matching the checked-in JSON Schema
  fixtures in `mcp/servers/*/schemas/` — catches drift between a server's
  actual tool signature and what the Planner thinks it can call.
- **Agent tests** (`tests/agents/`) mock `MCPClientPool` entirely and assert
  only the namespace-allow-list logic and result-wrapping — agents have no
  other logic to test.
- **Planner tests** (`tests/planner/`) mock `llm.chat` responses (fixed JSON
  fixtures) and assert `Plan` parsing, `replan()` triggering conditions, and
  `verify()` outcome handling — no real Ollama call, no real tool execution.
- **End-to-end tests** (`tests/e2e/`, few in number, run in CI nightly not
  per-PR) run the full stack including a real local Ollama model and assert
  on a handful of golden tasks ("organize this fixture Downloads folder")
  producing the expected filesystem end state.
- **Import-graph lint**: a small script (or `import-linter` config) enforces
  that `agents/`, `planner/`, `orchestrator/` never import from
  `mcp/servers/**`, and that `mcp/servers/*/impl.py` never imports from
  `agents/`, `planner/`, or another server's package. Run it in CI as a fast
  first gate — it catches architectural drift before any test does.

This mirrors the existing test layout (`backend/tests/test_*.py` already
tests tools directly today) — the main change is that "call the function"
becomes "call the tool through an in-memory MCP session," which is a small,
mechanical rewrite per test file, not a conceptual one.
