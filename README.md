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
Tool Execution Layer
      │
Filesystem + PostgreSQL + pgvector + Ollama
```

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
├── api/
├── agents/
│   ├── planner/
│   ├── search/
│   ├── organization/
│   ├── editing/
│   ├── analysis/
│   ├── coding/
│   └── memory/
│
├── tools/
│   ├── filesystem/
│   ├── embeddings/
│   ├── database/
│   ├── documents/
│   └── search/
│
├── workers/
├── models/
└── services/

database/
migrations/

storage/
uploads/
cache/

docker/

docs/

tests/
```

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

## Phase 1

- File explorer
- CRUD operations
- PostgreSQL
- REST API

## Phase 2

- File indexing
- Metadata extraction
- Embeddings
- Semantic search

## Phase 3

- Planner
- Agent orchestration
- Tool execution
- Memory

## Phase 4

- Document editing
- Folder organization
- Automation
- Background workers

## Phase 5

- Multi-step reasoning
- Long-term memory
- Workflow automation
- Plugin system

---

# Running Locally

## Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Ollama

```bash
ollama serve

ollama pull llama3.1

ollama pull bge-m3
```

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
