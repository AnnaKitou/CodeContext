# CLAUDE.md - CodeContext Development Guide

## Project Overview

**CodeContext** is a RAG/MCP system for codebase understanding, combining:
- **Semantic code chunking** (tree-sitter AST analysis)
- **Vector embeddings** (ChromaDB with Anthropic embeddings)
- **LLM agent** (Claude API with tool use)
- **MCP integration** (GitHub API for live data)
- **Chat interface** (Gradio)

This file guides Claude Code when working on this repository.

---

## Architecture

### Backend (`/backend`)
**FastAPI-based REST API**

- **Entry point**: `backend/app/main.py`
- **API routes**: 
  - `backend/app/api/routes/ingest.py` — `POST /api/v1/ingest` (upload code)
  - `backend/app/api/routes/query.py` — `POST /api/v1/query` (ask questions)
- **Core services**:
  - `backend/app/services/chunking.py` — tree-sitter semantic chunking
  - `backend/app/services/retriever.py` — RAG retrieval from ChromaDB
  - `backend/app/services/agent.py` — LLM agent orchestration
  - `backend/app/services/mcp_server.py` — MCP integration (GitHub)
- **Configuration**: `backend/app/core/config.py` (Pydantic settings)
- **Security**: `backend/app/core/security.py` (API keys, auth)
- **Embeddings**: `backend/app/core/embeddings.py` (Claude embeddings via API)
- **Database**: `backend/app/crud/vector_db.py` (ChromaDB operations)
- **Models**: `backend/app/models/schemas.py` (Pydantic request/response)
- **Tests**: `backend/tests/` (pytest)

### Frontend (`/frontend`)
**Gradio-based chat interface**

- **Entry point**: `frontend/app.py`
- **Features**:
  - Chat interface for code questions
  - Source code citations (file/line references)
  - Code highlighting panel
  - Metadata display (relevance scores, chunks used)

### Key Services Breakdown

#### 1. **Chunking Service** (`backend/app/services/chunking.py`)
Semantic code splitting using tree-sitter AST:
- Parses code into functions, classes, methods
- Extracts metadata: file, language, start/end lines
- Each chunk represents a coherent semantic unit
- Supports Python, JavaScript, Go, etc.

#### 2. **Retriever Service** (`backend/app/services/retriever.py`)
RAG pipeline:
- Encodes user query via Anthropic embeddings API
- Searches ChromaDB for top-k similar chunks
- Returns chunks with metadata (file, lines, relevance score)
- Fallback to BM25 if semantic search insufficient

#### 3. **LLM Agent** (`backend/app/services/agent.py`)
Claude API with function calling:
- Takes user query + retrieved chunks
- Calls MCP tools (GitHub) if needed (e.g., "who last modified this?")
- Synthesizes answer with citations
- Returns answer + cited file/line references

#### 4. **MCP Server** (`backend/app/services/mcp_server.py`)
GitHub API integration via MCP:
- **Tools available**:
  - `get_issue` — Fetch GitHub issue details
  - `get_pull_requests` — List/filter PRs
  - `get_file_blame` — Git blame for a file
  - `get_commit_history` — Commit log for a file
- Called on-demand by the LLM agent

---

## Key Patterns

### CQRS (Query/Ingest Separation)
- `POST /ingest` — One-time indexing of codebase
- `GET /query` — Stateless retrieval + synthesis

### RAG Pipeline
```
User Query
    ↓
Embed Query (Anthropic API)
    ↓
Search ChromaDB (top-k chunks)
    ↓
Retrieve Context + Metadata
    ↓
LLM Agent (with MCP tools)
    ↓
Answer + Citations
```

### MCP Tool Use
```
LLM Agent receives:
  - User query
  - Retrieved code chunks
  - Available MCP tools
    ↓
Agent decides: "Do I need live data?"
    ↓
If yes → Call MCP tool (e.g., get_file_blame)
    ↓
Incorporate result into final answer
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.100+ |
| Code Analysis | tree-sitter (Python bindings) |
| Vector DB | ChromaDB |
| Embeddings | Anthropic Claude API (`text-embedding-3-small`) |
| LLM | Anthropic Claude API (`claude-3-5-sonnet`) |
| MCP | Model Context Protocol SDK |
| Frontend | Gradio |
| Language | Python 3.11+ |
| Package Mgr | uv |

---

## Development Workflow

### Local Setup (First Time)
```bash
cd backend
uv sync
```

### Run Backend
```bash
cd backend
fastapi dev app/main.py
```
Starts at `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Run Frontend
```bash
cd frontend
uv run app.py
```
Opens Gradio at `http://localhost:7860`

### Run Tests
```bash
cd backend
pytest tests/ -xvs
```

### Format & Lint
```bash
cd backend
ruff format .
ruff check --fix .
mypy . --strict
```

---

## Data Flow Example

**User**: "What does the `calculate_revenue` function do?"

1. **Ingest Phase** (happens once):
   - User uploads codebase via `/ingest`
   - Chunking service parses all `.py` files with tree-sitter
   - Chunks stored in ChromaDB with metadata
   - Example chunk:
     ```
     File: billing/revenue.py
     Lines: 42-58
     Type: function
     Content: def calculate_revenue(orders, tax_rate):
              ...
     ```

2. **Query Phase**:
   - User asks question via Gradio
   - Frontend sends to `POST /query`
   - Retriever embeds question, searches ChromaDB
   - Top-3 chunks returned:
     ```
     [
       {file: "billing/revenue.py", lines: 42-58, score: 0.92},
       {file: "tests/test_revenue.py", lines: 120-135, score: 0.85},
       {file: "docs/api.md", lines: 30-40, score: 0.78}
     ]
     ```
   - Agent receives query + chunks
   - Agent calls `get_file_blame("billing/revenue.py", 42)` via MCP (who last touched this?)
   - Agent synthesizes answer with citations
   - Frontend displays answer + highlighted source code

---

## API Reference

### POST /api/v1/ingest
Upload and index a codebase.

**Request**:
```json
{
  "files": [binary file list],
  "repository_url": "https://github.com/user/repo",
  "repository_name": "my-repo"
}
```

**Response**:
```json
{
  "message": "Indexed 150 files",
  "chunks_created": 1245,
  "languages": ["python", "javascript"]
}
```

### POST /api/v1/query
Ask a question about the indexed codebase.

**Request**:
```json
{
  "query": "What does the calculate_revenue function do?",
  "top_k": 5,
  "use_mcp": true
}
```

**Response**:
```json
{
  "answer": "The calculate_revenue function computes total revenue...",
  "citations": [
    {"file": "billing/revenue.py", "lines": "42-58", "relevance": 0.92},
    {"file": "tests/test_revenue.py", "lines": "120-135", "relevance": 0.85}
  ],
  "mcp_calls": ["get_file_blame"],
  "confidence": 0.88
}
```

---

## Environment Variables (.env)

```
# Anthropic API
ANTHROPIC_API_KEY=sk-...

# GitHub (for MCP)
GITHUB_TOKEN=ghp_...
GITHUB_REPO_URL=https://github.com/user/repo

# ChromaDB
CHROMA_DB_PATH=./chroma_db

# FastAPI
DEBUG=False
LOG_LEVEL=INFO
```

---

## Testing Strategy

### Unit Tests
- `test_chunking.py` — tree-sitter AST parsing
- `test_retriever.py` — ChromaDB queries
- `test_mcp_server.py` — Mock MCP calls

### Integration Tests
- `test_ingest_pipeline.py` — Full indexing flow
- `test_query_pipeline.py` — Full retrieval + synthesis
- `test_citations.py` — Citation accuracy

### Evaluation Dataset
- `evaluation/queries.json` — 20-30 test questions
- `evaluation/ground_truth.json` — Expected answers + citations
- `scripts/eval.py` — Run evaluation (Recall@k, MRR, citation accuracy)

---

## Common Issues & Fixes

### ChromaDB Errors
- **Error**: "Collection already exists"
  - **Fix**: Delete `./chroma_db` and reindex

### API Key Not Found
- **Error**: "ANTHROPIC_API_KEY not set"
  - **Fix**: Create `.env` file and add key

### tree-sitter Parser Missing
- **Error**: "Language parser not found"
  - **Fix**: `pip install tree-sitter` and download language parsers

### MCP Tool Call Fails
- **Error**: "GitHub API rate limit exceeded"
  - **Fix**: Implement exponential backoff or increase wait time

---

## File Navigation

| Purpose | File |
|---------|------|
| FastAPI app setup | `backend/app/main.py` |
| Ingest endpoint | `backend/app/api/routes/ingest.py` |
| Query endpoint | `backend/app/api/routes/query.py` |
| Chunking logic | `backend/app/services/chunking.py` |
| RAG retrieval | `backend/app/services/retriever.py` |
| LLM agent | `backend/app/services/agent.py` |
| MCP integration | `backend/app/services/mcp_server.py` |
| Gradio UI | `frontend/app.py` |
| Evaluation | `scripts/eval.py` |

---

## Notes for Contributors

1. **Always use tree-sitter for chunking** — avoid regex-based splitting
2. **Citations are critical** — every answer must cite source files/lines
3. **Test MCP calls** — mock GitHub API in unit tests
4. **Keep chunks semantic** — each chunk = one logical unit (function, class, etc.)
5. **Type hints required** — Python 3.11+ with mypy strict mode
6. **No print() debugging** — use logging module
7. **Gradio is for demo only** — production would use React/Vue

---

## Research Evaluation Checklist

- [ ] Retrieve 20-30 diverse test queries
- [ ] Manually create ground truth answers + citations
- [ ] Run Recall@k, MRR metrics
- [ ] Compare naive chunking vs tree-sitter chunking
- [ ] Evaluate citation accuracy (% correct file/line)
- [ ] LLM-as-judge evaluation on answer quality
- [ ] Document findings in written report

---

## Next Steps

1. **Implement backend** (chunking, retriever, agent)
2. **Set up ChromaDB** and test indexing
3. **Integrate MCP server** for GitHub API
4. **Build Gradio frontend**
5. **Create evaluation dataset**
6. **Run evaluation and document results**
