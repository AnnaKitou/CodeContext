---
title: CodeContext
emoji: 🔍
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# CodeContext: Agentic RAG/MCP System for Codebase Understanding

An intelligent **agentic reasoning system** built on RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol) that accelerates developer onboarding with multi-step reasoning over source code.

## Overview

**CodeContext** now features **Agent V2** — an advanced agentic reasoning engine implementing the **ReAct pattern** (Reason → Act → Observe → Reflect):

- **Agent V2 Reasoning**: Query decomposition, adaptive retrieval, strategy planning, and self-critique
- **RAG**: Semantic code chunking (tree-sitter AST) + vector search (ChromaDB)
- **MCP**: Live GitHub data (issues, PRs, git blame, commit history)
- **Intelligent Tool Use**: Claude API with optional MCP tool calling

Ask complex questions about any GitHub repository and get comprehensive, citation-grounded answers with visible reasoning steps.

> **New here?** Start with **[QUICKSTART.md](QUICKSTART.md)** (~5 minutes to working).
> **Want details?** See **[AGENT_V2.md](AGENT_V2.md)** (complete agentic reasoning guide) or **[DOCUMENTATION.md](DOCUMENTATION.md)** (full technical docs).
> **Contributing?** Check **[CONTRIBUTING.md](CONTRIBUTING.md)** (development setup).

## Architecture

### With Agent V2 (Agentic Reasoning)

```
┌──────────────────────────────────────────────────────────────────┐
│                         Web UI                                  │
│  HTML SPA (port 8000, served by FastAPI) + API docs (/docs)   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
   ┌────▼──────────┐              ┌──────────▼────────────┐
   │  /ingest      │              │  /query (Agent V2)   │
   │  (Index repo) │              │  (Ask question)      │
   └────┬──────────┘              └──────┬───────────────┘
        │                                │
   ┌────▼────────────┐    ┌──────────────▼──────────────────────┐
   │ Indexing Pipe   │    │  Agent V2 Reasoning Loop (ReAct)    │
   │ • git clone     │    │  [PLAN] QueryAnalyzer              │
   │ • chunking      │    │  ↓                                  │
   │ • embeddings    │    │  [PLAN] AgentPlanner               │
   └────┬────────────┘    │  ↓                                  │
        │                 │  [RETRIEVE] AdaptiveRetriever      │
   ┌────▼──────────────┐  │  ↓ (multi-step, iterative)        │
   │  ChromaDB         │  │  [REASON] Agent + MCP tools        │
   │  (Vector DB)      │  │  ↓                                  │
   └───────────────────┘  │  [CRITIQUE] AnswerValidator        │
                          │  ↓ (optional self-critique)        │
                          │  [REFLECT] Return reasoning steps  │
                          └──────┬──────────────────────────────┘
                                 │
                          ┌──────▼──────────┐
                          │  Response with  │
                          │  thinking_      │
                          │  process        │
                          └─────────────────┘
```

### Legacy RAG Mode (Fallback)

When `ENABLE_AGENT_V2=false`, uses simple RAG pipeline:
```
Query → Retriever → Agent → Response
```

## Tech Stack

- **Backend**: FastAPI (async, Pydantic validation, auto-docs)
- **Code Analysis**: tree-sitter (AST-based chunking, 11+ languages)
- **Vector DB**: ChromaDB (persistent, cosine similarity, local)
- **Embeddings**: all-MiniLM-L6-v2 (384-dim, no API cost)
- **LLM Framework**: LangChain (chains, agents, retrieval patterns)
- **LLM**: Claude API (`claude-sonnet-4-6`, native tool use)
- **MCP**: GitHub API via PyGithub (blame, commits, issues, PRs)
- **Frontend**: HTML/CSS/JS SPA (primary, :8000) + Gradio (optional, :7860)
- **Language**: Python 3.11+
- **Package manager**: uv (fast, lockfile-based)
- **Testing**: pytest + coverage + async fixtures
- **Linting**: ruff (formatter + linter) + mypy (strict type checking)

### Agent V2 Components (New)

- **QueryAnalyzer** — Decomposes complex queries into sub-questions
- **AgentPlanner** — Plans retrieval strategy and tool selection
- **AdaptiveRetriever** — Multi-step retrieval with query refinement
- **AnswerValidator** — Self-critique and hallucination detection
- **Enhanced CodeContextAgent** — Orchestrates ReAct loop

### Supported Languages (Semantic Chunking)

Python, JavaScript, TypeScript, TSX, Go, Java, C, C++, C#, Rust, Ruby — 
via dedicated tree-sitter grammars, with regex fallback for Python/JS/TS/C#.

## Project Structure

```
CodeContext/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app initialization
│   │   ├── core/
│   │   │   └── config.py              # Pydantic settings + Agent V2 config
│   │   ├── api/routes/
│   │   │   ├── ingest.py              # POST/DELETE /api/v1/ingest
│   │   │   └── query.py               # POST /api/v1/query (with Agent V2)
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic models (QueryResponseV2, etc.)
│   │   └── services/
│   │       ├── agent.py               # CodeContextAgent (orchestrator)
│   │       ├── query_analyzer.py      # QueryAnalyzer (Agent V2 NEW)
│   │       ├── agent_planner.py       # AgentPlanner (Agent V2 NEW)
│   │       ├── adaptive_retriever.py  # AdaptiveRetriever (Agent V2 NEW)
│   │       ├── answer_validator.py    # AnswerValidator (Agent V2 NEW)
│   │       ├── retriever.py           # RAGRetriever (ChromaDB)
│   │       ├── chunking.py            # SemanticChunker (tree-sitter)
│   │       ├── mcp_server.py          # MCPGithubServer
│   │       ├── embedder_factory.py    # Embeddings setup
│   │       └── manifest.py            # File repo tracking
│   └── tests/
│       ├── test_query_analyzer.py         # Unit tests (3)
│       ├── test_answer_validator.py       # Unit tests (3)
│       ├── test_agent_reasoning.py        # Integration tests (3)
│       └── test_main.py                   # Endpoint tests
├── frontend/
│   ├── index.html                    # Primary SPA (served at :8000)
│   └── app.py                        # Optional Gradio interface (:7860)
├── scripts/
│   ├── setup.sh                      # Project setup
│   └── eval.py                       # Evaluation framework
├── evaluation/                       # Eval datasets
├── docs/                            # Documentation (README, guides)
├── pyproject.toml                   # Python dependencies + tool config
├── .env.example                     # Config template
├── AGENT_V2.md                      # Agentic reasoning guide (NEW)
├── QUICKSTART.md                    # Getting started (updated)
├── DOCUMENTATION.md                 # Technical docs (updated)
├── CONTRIBUTING.md                  # Dev guide (updated)
└── README.md                        # This file (updated)
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

## Agent V2: Agentic Reasoning (New!)

CodeContext now features **Agent V2** — an intelligent reasoning engine using the **ReAct pattern**:

```
PLAN    → Analyze query complexity, decide strategy
   ↓
RETRIEVE → Adaptive context gathering (1-3 rounds)
   ↓
REASON  → Synthesize answer with optional MCP tools
   ↓
CRITIQUE → Self-validate (optional, catches hallucinations)
   ↓
REFLECT → Return answer with visible thinking steps
```

### Key Capabilities

- **Query Decomposition**: Breaks "How does auth work AND who maintains it?" into sub-questions
- **Adaptive Retrieval**: Iteratively refines queries when initial results insufficient
- **Self-Critique**: Validates answers for grounding and detects hallucinations
- **Visible Reasoning**: Every response includes thinking steps (great for debugging!)
- **Tool Integration**: Automatically decides when to use MCP vs pure RAG
- **Graceful Degradation**: Falls back to simple RAG if Claude returns invalid JSON

### Example Response

When you ask a complex question, you now get:

```json
{
  "answer": "Token expiration is handled by...",
  "citations": [...],
  "confidence": 0.92,
  "thinking_process": [
    {"step_type": "decompose", "content": "Query has 2 parts..."},
    {"step_type": "retrieve", "content": "Retrieved 12 chunks over 2 rounds..."},
    {"step_type": "reason", "content": "Answer generated with citations..."},
    {"step_type": "critique", "content": "Validation: VALID, Risk: low..."}
  ],
  "validation": {
    "is_valid": true,
    "grounded": true,
    "hallucination_risk": "low"
  },
  "retrieval_rounds": 2
}
```

**See [AGENT_V2.md](AGENT_V2.md)** for the complete guide (architecture, configuration, troubleshooting).

## Configuration

### Core Settings

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (**required**) | `changethis` |
| `ANTHROPIC_MODEL` | Claude model to use | `claude-sonnet-4-6` |
| `CHROMA_DB_PATH` | ChromaDB persistence directory | `./chroma_db` |
| `RETRIEVER_TOP_K` | Chunks retrieved per query | `5` |
| `RETRIEVER_SCORE_THRESHOLD` | Minimum relevance score | `0.3` |

### Agent V2 (Agentic Reasoning) Settings

| Variable | Purpose | Default |
|----------|---------|---------|
| `ENABLE_AGENT_V2` | Master switch for agentic reasoning | `true` |
| `AGENT_ENABLE_QUERY_DECOMPOSITION` | Analyze query complexity | `true` |
| `AGENT_ENABLE_ITERATIVE_RETRIEVAL` | Allow multi-round retrieval | `true` |
| `AGENT_ENABLE_SELF_CRITIQUE` | Validate answers via self-critique | `true` |
| `AGENT_MAX_RETRIEVAL_ROUNDS` | Maximum retrieval iterations | `3` |
| `AGENT_REASONING_DEPTH` | `shallow` / `medium` / `deep` | `medium` |

### GitHub MCP Settings

| Variable | Purpose | Default |
|----------|---------|---------|
| `GITHUB_TOKEN` | GitHub personal access token (enables MCP) | — |
| `GITHUB_REPO_OWNER` | Repository owner (for MCP tools) | — |
| `GITHUB_REPO_NAME` | Repository name (for MCP tools) | — |

> **MCP is optional** — if not configured, the agent answers from RAG context alone.
> **Agent V2 can be disabled** — set `ENABLE_AGENT_V2=false` to use simple RAG pipeline.

See [AGENT_V2.md](AGENT_V2.md#configuration) for complete configuration details.

## Testing

All 9 tests passing:
```bash
pytest backend/tests/ -v

# Unit tests (3 each)
✓ test_query_analyzer.py         — QueryAnalyzer decomposition
✓ test_answer_validator.py       — AnswerValidator grounding checks
✓ test_agent_reasoning.py        — Full agentic loop integration

# Endpoint tests
✓ test_main.py                   — /query, /ingest endpoints
```

Run with coverage:
```bash
pytest backend/tests/ --cov=backend/app --cov-report=html
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** — Get started in ~5 minutes
- **[AGENT_V2.md](AGENT_V2.md)** — Complete agentic reasoning guide
- **[DOCUMENTATION.md](DOCUMENTATION.md)** — Full technical documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development setup & contribution guide

## Research Questions

**RQ1**: Does semantic AST-based chunking (tree-sitter) improve retrieval quality vs fixed-size chunking?

**RQ2**: How do RAG and MCP patterns complement each other? Which excels at different query types?

**RQ3**: How reliable are the generated citations (file/line references)?

## Evaluation Framework

- **Retrieval Metrics**: Recall@k, Mean Reciprocal Rank (MRR)
- **Answer Quality**: LLM-as-judge validation
- **Citation Accuracy**: % of citations pointing to truly relevant code
- **Agentic Metrics**: Reasoning depth, retrieval rounds, validation confidence

See `scripts/eval.py` for the evaluation framework and `evaluation/` for datasets.

## What's Next?

Potential enhancements (see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution areas):

- [ ] Query refinement using Claude (intelligent iteration)
- [ ] Multi-turn conversation support with persistent history
- [ ] Code-specialized embeddings (better than all-MiniLM-L6-v2)
- [ ] Streaming API responses
- [ ] Docker containerization
- [ ] React/Vue frontend alternative

## License

MIT

## Author

**Anna Kitou** (kitouanna@gmail.com)

*Built as a portfolio project to demonstrate AI systems engineering:*
- Clean layered architecture (FastAPI + services)
- Production patterns (DI, error handling, testing, logging)
- Advanced LLM techniques (RAG + MCP + agentic reasoning)
- Comprehensive documentation & examples
