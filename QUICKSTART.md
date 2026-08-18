# 🚀 CodeContext - Quick Start Guide

Welcome to CodeContext! This guide gets you from zero to your first answer in ~5 minutes.

## Prerequisites

- Python 3.11+
- `uv` package manager
- `git` on your PATH (used to clone repositories during ingest)
- Anthropic API key
- *(optional)* GitHub personal access token — for live MCP data (issues, PRs, blame)

## 1️⃣ Initial Setup (5 minutes)

### Install dependencies

**Option A: Using `uv` (recommended)**
```bash
uv sync
```
This creates `.venv/` and installs everything, including the per-language tree-sitter
grammars (Python, JS/TS, Go, Java, C/C++, C#, Rust, Ruby).

**Option B: Using `pip` (if `uv` not installed)**
```bash
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure API Keys
```bash
# Copy template
cp .env.example .env
```
Edit `.env` and set at least your Anthropic key:
```dotenv
ANTHROPIC_API_KEY=sk-ant-...        # required
ANTHROPIC_MODEL=claude-sonnet-4-6   # default
ENABLE_AGENT_V2=true                # Enable agentic reasoning (default: true)
```
*(Optional)* enable MCP by setting **all three**:
```dotenv
GITHUB_TOKEN=ghp_...
GITHUB_REPO_OWNER=tiangolo
GITHUB_REPO_NAME=fastapi
```

## 2️⃣ Start the Backend (serves the web UI too)

```bash
uv run fastapi dev backend/app/main.py
```

Output should show:
```
Uvicorn running on http://127.0.0.1:8000
```

Then open:
- **Web UI** → http://localhost:8000
- **API docs** → http://localhost:8000/docs
- **Health** → http://localhost:8000/health

## 3️⃣ Use the System

### Step A: Index a repository
1. Go to the **📥 Ingest** tab
2. Enter GitHub URL: `https://github.com/anthropics/anthropic-sdk-python`
3. Enter name: `anthropic-sdk`
4. Tick **🔄 Replace existing index** (recommended when switching repos)
5. Click **🚀 Index repository** and wait for the success summary
   (files indexed, chunks created, languages detected)

> Terminal equivalent:
> ```bash
> curl -X POST http://localhost:8000/api/v1/ingest \
>   -H "Content-Type: application/json" \
>   -d '{"repository_url":"https://github.com/anthropics/anthropic-sdk-python","repository_name":"anthropic-sdk","clear_before_ingest":true}'
> ```

### Step B: Ask questions (now with agentic reasoning!)
In the **💬 Chat** tab, try:
- "What's the main function of this codebase?"
- "How is authentication implemented and who maintains it?"
- "What are the key API endpoints and how do they work?"

You'll see:
- 📝 Answer with explanation
- 📍 Source file citations with line numbers
- 🔗 Relevant code snippets
- 🎯 Confidence score
- **NEW:** 🧠 Thinking process (query decomposition, retrieval strategy, validation)

> Terminal equivalent with visible reasoning:
> ```bash
> curl -X POST http://localhost:8000/api/v1/query \
>   -H "Content-Type: application/json" \
>   -d '{"query":"How is authentication implemented?","top_k":5,"use_mcp":true}' | jq '.thinking_process'
> ```

## 4️⃣ What's New: Agent V2 (Agentic Reasoning)

CodeContext now features **intelligent agentic reasoning** that handles complex questions better:

### ReAct Loop (Reason → Act → Observe → Reflect)
1. **PLAN** — Analyzes query complexity, decomposes multi-part questions
2. **PLAN** — Decides retrieval strategy (single-round or iterative)
3. **RETRIEVE** — Adaptive context gathering (1-3 rounds, refines queries)
4. **REASON** — Synthesizes answer with Claude + optional MCP tools
5. **CRITIQUE** — Self-validates answer against context (optional)
6. **REFLECT** — Returns answer with visible thinking steps

### Visible Reasoning
Every response includes `thinking_process` field showing:
- Query decomposition (if complex)
- Retrieval rounds and queries used
- Reasoning steps with confidence scores
- Validation results (hallucination risk, grounding)

### Configuration
All agentic features are toggleable:
```dotenv
ENABLE_AGENT_V2=true                          # Master switch
AGENT_ENABLE_QUERY_DECOMPOSITION=true         # Analyze complexity
AGENT_ENABLE_ITERATIVE_RETRIEVAL=true         # Multi-round retrieval
AGENT_ENABLE_SELF_CRITIQUE=true               # Validate answers
AGENT_MAX_RETRIEVAL_ROUNDS=3                  # Limit iterations
AGENT_REASONING_DEPTH=medium                  # shallow/medium/deep
```

## 5️⃣ What's Working

✅ **Backend Infrastructure**
- FastAPI REST API (serves both API and web UI)
- Pydantic settings / configuration management
- Service-oriented architecture
- Agentic reasoning engine (ReAct pattern)

✅ **Agent Services**
- QueryAnalyzer — Query complexity detection & decomposition
- AgentPlanner — Strategy planning before execution
- AdaptiveRetriever — Multi-step retrieval refinement
- AnswerValidator — Self-critique & hallucination detection

✅ **Frontend**
- HTML/CSS/JS single-page app (primary, port 8000)
- Citation display + thinking steps
- Ingest form

✅ **Core Pipeline**
- **Tree-sitter semantic chunking** — 11+ languages with AST-based parsing
- **ChromaDB vector database** — persistent, cosine similarity
- **Embeddings** — all-MiniLM-L6-v2 (384-dim)
- **Claude API integration** — agentic reasoning with tool-use
- **GitHub MCP integration** — git blame, issues, PRs, commit history

## 6️⃣ Switching repositories

ChromaDB **accumulates** chunks across ingestions. When moving to a new repo, clear the
old index first or answers will mix codebases:
- In the UI: tick **Replace existing index** before indexing, or click **🗑 Clear Index**
- Via API:
  ```bash
  curl -X DELETE http://localhost:8000/api/v1/ingest
  ```

## 🐛 Troubleshooting

### Backend won't start
```bash
python --version   # Should be 3.11+
uv sync            # Reinstall dependencies
```

### `ANTHROPIC_API_KEY is set to "changethis"` warning
Put a real key in `.env`, then restart the backend.

### Answers reference an old/wrong repo
Clear the index (section 6) before re-indexing.

### Agent returns empty thinking_process
Check `.env` has `ENABLE_AGENT_V2=true` and restart backend.

### Iterative retrieval doesn't seem to happen
Verify `AGENT_ENABLE_ITERATIVE_RETRIEVAL=true` for complex queries.

### "No relevant code context" on every query
Make sure you indexed a repo first (section 3, Step A).

### MCP tools never fire
Set `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, and `GITHUB_REPO_NAME`, and keep `use_mcp: true`.

### Windows: permission error cleaning up `temp_repos`
Handled automatically — read-only `.git` files are chmod'd before removal.

## 🔑 Getting API Keys

### Anthropic API
1. Go to https://console.anthropic.com
2. Create an API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### GitHub Token (optional, for MCP)
1. Go to https://github.com/settings/tokens
2. Create a Personal Access Token
3. Select scopes: `repo`, `read:org`
4. Add to `.env`: `GITHUB_TOKEN=ghp_...` (plus `GITHUB_REPO_OWNER` / `GITHUB_REPO_NAME`)

## 📚 Documentation

- **[README.md](README.md)** — Project overview & architecture
- **[AGENT_V2.md](AGENT_V2.md)** — Complete agentic reasoning guide
- **[DOCUMENTATION.md](DOCUMENTATION.md)** — Technical documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development guide

## 📞 Need Help?

- See [AGENT_V2.md](AGENT_V2.md) for troubleshooting agentic features
- Email: kitouanna@gmail.com

---

🎉 **Welcome to CodeContext!** Now with AI-powered reasoning 🧠✨
