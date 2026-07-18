# Agentic AI File System

A fully local, privacy-focused AI-powered file management system capable of understanding, organizing, searching, and editing files using autonomous AI agents.

The project is designed to run **entirely on your own computer** with **no paid APIs or cloud services required**.

---

# Features

- 📁 Semantic file search
- 🤖 Multi-agent architecture
- 🧠 Long-term memory
- 📄 Automatic document indexing
- 🔍 Hybrid keyword + vector search
- 📚 PDF, DOCX, Markdown, TXT support
- 💻 Codebase understanding
- 📂 Intelligent folder organization
- ⚡ Local LLM inference
- 🔒 Privacy-first (everything runs locally)

---

# Architecture

The backend is mid-migration from a plain FastAPI app to an MCP-based
multi-agent system. What's running today (Phases 1–2) is the left-hand side;
the full design for where it's headed (Phases 3+) is written up in
[`backend/docs/mcp_architecture.md`](backend/docs/mcp_architecture.md) and
summarized below.

## Current (Phases 1–2)

```
Next.js
      │
      ▼
 FastAPI Backend (app/)
      │
 Routes call plain functions directly
      │
Indexing + Search (app/indexing.py, app/search.py)
      │
Tools (tools/filesystem, tools/documents, tools/embeddings)
      │
Filesystem + PostgreSQL + pgvector
```

There is no planner, agent, orchestrator, or LLM integration yet — routes in
`app/routes/` call functions in `tools/*` directly.

## Target (Phase 3+, MCP-based)

```
Next.js
      │
      ▼
 FastAPI Backend
      │
Agent Orchestrator
      │
Planner
      │
Specialized Agents
      │
MCP Client → MCP Server Registry
      │
Filesystem / Search / Document / Embedding / Vector / Git / Python / Ollama servers
      │
Filesystem + PostgreSQL + pgvector + Ollama
```

Each tool namespace becomes its own long-lived MCP server process (Streamable
HTTP), and agents/planner/orchestrator are only ever allowed to reach an
implementation through `MCPClient.call_tool()` — never by importing a server
module directly. See the design doc for the full rationale, folder layout,
and milestone-by-milestone rollout.

---

# Tech Stack

## Frontend

- Next.js
- React
- Tailwind CSS
- TypeScript

## Backend

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

## AI

- Ollama
- Llama 3 / Qwen / Gemma
- BAAI BGE Embeddings

## Database

- PostgreSQL
- pgvector

## File Processing

- PyMuPDF
- python-docx
- openpyxl
- Watchdog
- ripgrep

---

# Project Structure

What's actually implemented today (Phases 1–2):

```
agentic-filesystem/

frontend/
│
├── app/
├── components/
├── hooks/
└── lib/

backend/
│
├── app/
│   ├── main.py            # FastAPI app, CORS, lifespan (reconcile on startup)
│   ├── config.py          # env-driven settings, storage root
│   ├── models.py          # FileRecord, Chunk (pgvector)
│   ├── schemas.py
│   ├── paths.py            # storage-root jail (resolve_path)
│   ├── repository.py       # reconcile() DB <-> disk
│   ├── indexing.py         # chunk + embed files, keep index in sync
│   ├── search.py           # hybrid keyword + vector semantic_search()
│   └── routes/
│       ├── files.py
│       └── settings.py
│
├── tools/
│   ├── filesystem/          # read/write/delete/rename/search
│   ├── documents/            # chunk_text, extract_metadata
│   └── embeddings/           # sentence-transformers (BAAI/bge-small-en-v1.5)
│
├── alembic/
├── docs/
│   └── mcp_architecture.md  # design doc for the Phase 3+ MCP migration
├── storage/
└── tests/
```

Phase 3+ introduces `agents/`, `planner/`, `orchestrator/`, `memory/`, and
`mcp/` (client, registry, servers) per the target layout in
[`backend/docs/mcp_architecture.md`](backend/docs/mcp_architecture.md#2-folder-structure) —
`backend/tools/` is deleted once its contents move into each MCP server's
`impl.py`.

---

# Agent Workflow

```
User Request

      │

      ▼

Planner Agent

      │

Break task into steps

      │

Choose specialized agents

      │

Execute tools

      │

Verify results

      │

Return response
```

---

# Agent Types

## Search Agent

- Semantic search
- Keyword search
- Metadata lookup
- Duplicate detection

---

## Organization Agent

- Rename files
- Sort folders
- Archive documents
- Detect duplicates

---

## Analysis Agent

- Summarize documents
- Compare files
- Extract information
- Generate reports

---

## Editing Agent

- Rewrite text
- Translate documents
- Convert formats
- OCR cleanup

---

## Coding Agent

- Understand repositories
- Explain code
- Generate documentation
- Refactor files

---

# Search Pipeline

```
User Query

↓

Embedding Generation

↓

Vector Search

↓

Keyword Search

↓

Ranking

↓

LLM Response
```

---

# File Processing Pipeline

```
New File

↓

Watchdog detects file

↓

Extract text

↓

Generate metadata

↓

Generate embedding

↓

Store in PostgreSQL

↓

Store vector in pgvector

↓

Ready for search
```

---

# Development Roadmap

Phases 3+ follow the MCP migration plan in
[`backend/docs/mcp_architecture.md`](backend/docs/mcp_architecture.md#11-roadmap),
which breaks the old single "agent orchestration" phase into incremental
milestones — each one ships with `docker compose up` and the full test suite
still green, so the app is never left in a broken intermediate state.

## Phase 1 — Done

- File explorer
- CRUD operations
- PostgreSQL
- REST API

## Phase 2 — Done

- File indexing
- Metadata extraction
- Embeddings
- Semantic search

## Phase 3 — MCP Foundation (design doc M0–M2)

- MCP client pool + server registry, zero servers registered (no behavior change)
- Filesystem MCP server (wraps existing `tools/filesystem/*`)
- Search, Document, Embedding, and Vector MCP servers (wrap existing `tools/*`)
- Import-graph lint in CI enforcing agents/planner/orchestrator never import `mcp/servers/**`

## Phase 4 — Planning & Orchestration (M3–M4)

- Ollama MCP server (`llm.chat`, `.generate`, `.embed`, `.summarize`, `.classify`)
- Planner v0: fixed single-tool plans, proving Plan → execute → result end to end
- Real LLM-driven planning (`Planner.plan()` via `llm.chat` + `ToolCatalog`)
- Orchestrator wired to the Planner and a first agent (SearchAgent), `/api/tasks` endpoint

## Phase 5 — Full Agent Suite & Memory (M5)

- OrganizationAgent, EditingAgent, AnalysisAgent, CodingAgent
- `memory/` store (recent tasks, preferences, file history)
- Orchestrator consults Memory before planning, records after

## Phase 6 — Coding Agent & Sandboxing (M6)

- Git MCP server (status/diff/commit/history/branch)
- Python MCP server, sandboxed in its own process/container with resource limits
- CodingAgent goes live against both

## Phase 7 — Cutover & Cleanup (M7)

- Re-point `app/routes/files.py` at the Orchestrator (or retire it in favor of the task endpoint)
- Delete `backend/tools/` once nothing imports it
- Fold the old `app/` package into `api/`, `shared/`, `database/`

---

# Backend API

The REST API (FastAPI, under `/api`) performs CRUD against a sandboxed,
user-configurable storage root, with PostgreSQL tracking file/directory
metadata (kept in sync via `reconcile()` after every mutation and on
startup). Phase 2 adds background indexing: every create/write/rename
triggers `index_file`/`index_pending`, which chunks text and generates
embeddings for semantic search.

| Method | Path                       | Purpose                                       |
| ------ | -------------------------- | ---------------------------------------------- |
| GET    | `/api/health`               | DB connectivity check                          |
| GET    | `/api/files/tree`           | Flattened directory listing (live disk)        |
| GET    | `/api/files/stats`          | File/directory counts, total size (DB)         |
| GET    | `/api/files/content`        | Read a file's contents                         |
| POST   | `/api/files`                | Create a file or directory                     |
| PUT    | `/api/files/content`        | Update a file's contents                       |
| DELETE | `/api/files`                | Delete a file or directory (recursive)         |
| PATCH  | `/api/files`                | Rename/move a file or directory                |
| GET    | `/api/files/search`         | Keyword search under storage root (ripgrep)    |
| GET    | `/api/files/search/semantic`| Hybrid keyword + vector semantic search         |
| POST   | `/api/files/reindex`        | Re-chunk and re-embed every indexed file        |
| GET    | `/api/settings`             | Read the current storage root                   |
| PUT    | `/api/settings`             | Change the storage root (reconciles + reindexes)|

---

# Running Locally

## Postgres

```bash
docker-compose up -d db   # or `docker compose up -d db` if you have the v2 plugin
```

## Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

alembic upgrade head

uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

cp .env.example .env.local

npm run dev
```

---

## Ollama

```bash
ollama serve

ollama pull llama3.2:1b   # chat/planning model -- small and fast for local dev
ollama pull all-minilm    # embedding model
```

Swap in larger models (e.g. `llama3.1`, `bge-m3`) via `OLLAMA_CHAT_MODEL` /
`OLLAMA_EMBED_MODEL` in `.env` if you want better quality over speed.

To exercise the planner/orchestrator end to end, also start the MCP server
cluster and the backend in separate terminals:

```bash
cd backend
python -m scripts.run_mcp_servers   # boots all 6 MCP servers on 8801-8808
uvicorn app.main:app --reload       # in another terminal
```

`POST /api/tasks` only needs the cluster running; the rest of the API
(file browsing, keyword/semantic search) works without it.

---

# Goals

- Fully local
- Zero recurring cost
- Modular architecture
- Easy to extend
- Production-quality codebase
- Strong portfolio project

---

# License

MIT License
