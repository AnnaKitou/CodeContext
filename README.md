<!-- Hugging Face Spaces configuration (required at the top of the Space's README). -->
<!-- Harmless on GitHub; remove this block if you don't deploy to HF Spaces.       -->
---
title: CodeContext
emoji: 🔍
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# CodeContext: RAG/MCP System for Codebase Understanding

A hybrid RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol) system designed to accelerate developer onboarding by providing intelligent, source-referenced answers about codebases.

## Overview

**CodeContext** combines:
- **RAG (Retrieval-Augmented Generation)**: Semantic code chunking with tree-sitter and vector search via ChromaDB
- **MCP (Model Context Protocol)**: Live access to GitHub data (issues, PRs, git blame, commit history)
- **LLM Agent**: Claude API with tool use for intelligent synthesis

Ask questions about any GitHub repository and get answers with precise file/line citations.

> New here? See **[QUICKSTART.md](QUICKSTART.md)** to be running in ~5 minutes.
> Full technical write-up: **[DOCUMENTATION.md](DOCUMENTATION.md)**.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Web UI                             │
│   HTML SPA (port 8000, served by FastAPI)               │
│   — or — Gradio (port 7860, optional)                   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼──────────┐          ┌──────▼──────────┐
   │  /ingest      │          │  /query         │
   │  (Index repo) │          │  (Ask question) │
   └────┬──────────┘          └──────┬──────────┘
        │                            │
   ┌────▼──────────────────────────┬─▼────────────────┐
   │      Indexing Pipeline        │   RAG Retriever  │
   │  • git clone                  │   • Vector search│
   │  • tree-sitter chunking       │   • Top-k chunks │
   │  • ChromaDB embeddings        │                  │
   └────┬──────────────────────────┴──────┬───────────┘
        │                                 │
   ┌────▼──────────────────┐     ┌───────▼────────┐
   │    ChromaDB           │     │  LLM Agent     │
   │  (Vector DB)          │     │  (Claude API)  │
   └───────────────────────┘     └───────┬────────┘
                                         │
                              ┌──────────▼────────┐
                              │  MCP Server       │
                              │  (GitHub API)     │
                              └───────────────────┘
```

## Tech Stack

- **Backend**: FastAPI
- **Code Analysis**: tree-sitter (AST-based chunking, per-language grammars)
- **Vector DB**: ChromaDB (persistent, cosine similarity)
- **Embeddings**: ChromaDB default embedder (`all-MiniLM-L6-v2`)
- **LLM**: Claude API (`claude-sonnet-4-6`, with tool use)
- **MCP**: GitHub API via PyGithub
- **Frontend**: HTML/CSS/JS single-page app (primary) · Gradio (optional)
- **Language**: Python 3.11+
- **Package manager**: uv

### Supported languages (semantic chunking)

Python, JavaScript, TypeScript, TSX, Go, Java, C, C++, C#, Rust, Ruby — via dedicated
tree-sitter grammars, with a regex fallback for Python, JS/TS, and C#.

## Project Structure

```
CodeContext/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app — serves API + web UI
│   │   ├── core/
│   │   │   └── config.py           # Pydantic settings (loads .env)
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── ingest.py       # POST/DELETE /api/v1/ingest
│   │   │       └── query.py        # POST /api/v1/query
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response models
│   │   ├── crud/                   # (reserved)
│   │   └── services/
│   │       ├── chunking.py         # tree-sitter semantic chunking
│   │       ├── retriever.py        # ChromaDB RAG retrieval
│   │       ├── agent.py            # Claude agent + MCP tool loop
│   │       └── mcp_server.py       # GitHub MCP integration
│   └── tests/
├── frontend/
│   ├── index.html                  # Primary web UI (served at :8000)
│   └── app.py                      # Optional Gradio interface (:7860)
├── scripts/
│   ├── setup.sh                    # Project setup
│   └── eval.py                     # Evaluation script
├── evaluation/                     # Eval datasets
├── pyproject.toml
├── .env.example
├── QUICKSTART.md
└── README.md
```

## Quick Start

> Full step-by-step walkthrough: **[QUICKSTART.md](QUICKSTART.md)**

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An Anthropic API key
- `git` on your PATH (used to clone repositories during ingest)

### Setup

1. **Install dependencies** (from the project root):
   ```bash
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env — set ANTHROPIC_API_KEY (and optionally GITHUB_TOKEN for MCP)
   ```

3. **Run the backend** (serves both the API and the web UI):
   ```bash
   uv run fastapi dev backend/app/main.py
   ```
   Open **http://localhost:8000** for the web UI.

4. **(Optional) Run the Gradio frontend** in a second terminal:
   ```bash
   uv run python frontend/app.py
   ```
   Open **http://localhost:7860**.

## Usage

### Web UI (recommended)

Open **http://localhost:8000**:
1. Go to **Ingest** → paste a GitHub URL + a name → click **Index repository**.
   Tick **Replace existing index** (or use **Clear Index**) when switching repos so
   old results don't mix in.
2. Go to **Chat** → ask questions and get answers with file/line citations.

### API

Ingest a repository:
```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "repository_url": "https://github.com/tiangolo/fastapi",
        "repository_name": "fastapi",
        "clear_before_ingest": true
      }'
```

Query the indexed codebase:
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{ "query": "How is authentication handled?", "top_k": 5, "use_mcp": true }'
```

Clear the index:
```bash
curl -X DELETE http://localhost:8000/api/v1/ingest
```

Interactive API docs are available at **http://localhost:8000/docs**.

## Configuration

Key `.env` settings (see [.env.example](.env.example) for the full list):

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (**required**) | `changethis` |
| `ANTHROPIC_MODEL` | Claude model used by the agent | `claude-sonnet-4-6` |
| `GITHUB_TOKEN` | Enables MCP GitHub tools (blank = MCP disabled) | — |
| `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME` | Repo the MCP tools target | — |
| `CHROMA_DB_PATH` | ChromaDB persistence directory | `./chroma_db` |
| `RETRIEVER_TOP_K` | Chunks retrieved per query | `5` |
| `RETRIEVER_SCORE_THRESHOLD` | Minimum relevance score | `0.3` |

> **MCP** is only active when `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, and `GITHUB_REPO_NAME`
> are all set. Otherwise the agent answers from RAG context alone.

## Research Questions

**RQ1**: Does semantic AST-based chunking (tree-sitter) improve retrieval quality vs fixed-size chunking?

**RQ2**: How do RAG and MCP patterns complement each other? Which excels at different query types?

**RQ3**: How reliable are the generated citations (file/line references)?

## Evaluation

- **Retrieval Metrics**: Recall@k, Mean Reciprocal Rank (MRR)
- **Answer Quality**: LLM-as-judge + manual evaluation
- **Citation Accuracy**: % of citations pointing to truly relevant code
- **Baseline Comparison**: Naive chunking vs tree-sitter chunking

See `scripts/eval.py` for the evaluation framework.

## License

MIT

## Author

Anna Kitou (kitouanna@gmail.com)
