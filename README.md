# CodeContext: RAG/MCP System for Codebase Understanding

A hybrid RAG (Retrieval-Augmented Generation) and MCP (Model Context Protocol) system designed to accelerate developer onboarding by providing intelligent, source-referenced answers about codebases.

## Overview

**CodeContext** combines:
- **RAG (Retrieval-Augmented Generation)**: Semantic code chunking with tree-sitter and vector embeddings via ChromaDB
- **MCP (Model Context Protocol)**: Live access to GitHub data (issues, PRs, git blame)
- **LLM Agent**: Claude API with function calling for intelligent synthesis

The system provides a chat interface where developers can ask questions about a codebase and receive answers with precise file/line citations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Gradio Frontend                      │
│              (Chat Interface + Citations)               │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
   ┌────▼──────────┐          ┌──────▼──────────┐
   │  /ingest      │          │  /query         │
   │  (Upload code)│          │  (Ask question) │
   └────┬──────────┘          └──────┬──────────┘
        │                            │
   ┌────▼──────────────────────────┬─▼────────────────┐
   │      Indexing Pipeline        │   RAG Retriever  │
   │  • tree-sitter chunking       │   • Vector search│
   │  • Embedding generation       │   • Top-k chunks │
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
- **Code Analysis**: tree-sitter (AST-based chunking)
- **Vector DB**: ChromaDB
- **Embeddings**: Anthropic Claude API
- **LLM**: Claude API (with tool use)
- **MCP**: Model Context Protocol SDK (GitHub)
- **Frontend**: Gradio
- **Language**: Python 3.11+

## Project Structure

```
CodeContext/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic settings
│   │   │   ├── security.py         # Auth, API keys
│   │   │   └── embeddings.py       # Embedding generation
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── ingest.py       # POST /ingest
│   │   │       └── query.py        # POST /query
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic models
│   │   ├── crud/
│   │   │   └── vector_db.py        # ChromaDB operations
│   │   └── services/
│   │       ├── chunking.py         # tree-sitter chunking
│   │       ├── retriever.py        # RAG retrieval
│   │       ├── agent.py            # LLM agent + MCP
│   │       └── mcp_server.py       # MCP integration
│   └── tests/
├── frontend/
│   └── app.py                      # Gradio interface
├── scripts/
│   ├── setup.sh                    # Project setup
│   └── eval.py                     # Evaluation script
├── pyproject.toml
├── .env.example
├── DEVELOPMENT.md
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.11+
- uv (package manager)
- Anthropic API key

### Setup

1. **Clone and setup**:
   ```bash
   cd backend
   uv sync
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run backend**:
   ```bash
   cd backend
   fastapi dev app/main.py
   ```

4. **Run frontend** (in another terminal):
   ```bash
   cd frontend
   uv run app.py
   ```

## Usage

1. **Ingest Code** (`POST /ingest`):
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingest \
     -F "files=@mycode.py" \
     -F "repository_url=https://github.com/user/repo"
   ```

2. **Query** via Gradio UI at `http://localhost:7860`:
   - Ask questions about the codebase
   - Receive answers with file/line citations
   - View source code highlights

## Research Questions

**RQ1**: Does semantic AST-based chunking (tree-sitter) improve retrieval quality vs fixed-size chunking?

**RQ2**: How do RAG and MCP patterns complement each other? Which excels at different query types?

**RQ3**: How reliable are the generated citations (file/line references)?

## Evaluation

- **Retrieval Metrics**: Recall@k, Mean Reciprocal Rank (MRR)
- **Answer Quality**: LLM-as-judge + manual evaluation
- **Citation Accuracy**: % of citations pointing to truly relevant code
- **Baseline Comparison**: Naive chunking vs tree-sitter chunking

See `scripts/eval.py` for evaluation framework.

## Deliverables

- ✅ Full codebase (public GitHub repository)
- ✅ Technical documentation (README, DEVELOPMENT.md, architecture diagrams)
- ✅ Evaluation dataset and reproducible scripts
- ✅ Written report with results and analysis
- ✅ Demo (Gradio UI)

## License

MIT

## Author

Anna Kitou (kitouanna@gmail.com)
