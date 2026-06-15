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
From the project root:
```bash
uv sync
```
This creates `.venv/` and installs everything, including the per-language tree-sitter
grammars (Python, JS/TS, Go, Java, C/C++, C#, Rust, Ruby).

### Configure API Keys
```bash
# Copy template
cp .env.example .env
```
Edit `.env` and set at least your Anthropic key:
```dotenv
ANTHROPIC_API_KEY=sk-ant-...        # required
ANTHROPIC_MODEL=claude-sonnet-4-6   # default — fine to leave as-is
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

## 3️⃣ (Optional) Start the Gradio Frontend (Terminal 2)

The HTML UI at port 8000 is the primary interface. If you prefer Gradio:
```bash
uv run python frontend/app.py
```
Then open http://localhost:7860 🎉

## 4️⃣ Use the System

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

### Step B: Ask questions
In the **💬 Chat** tab, try:
- "What's the main function of this codebase?"
- "How is authentication implemented?"
- "What are the key API endpoints?"

You'll see:
- 📝 Answer with explanation
- 📍 Source file citations with line numbers
- 🔗 Relevant code snippets
- 🎯 Confidence score

> Terminal equivalent:
> ```bash
> curl -X POST http://localhost:8000/api/v1/query \
>   -H "Content-Type: application/json" \
>   -d '{"query":"How is authentication implemented?","top_k":5,"use_mcp":true}'
> ```

## 5️⃣ What's Working

✅ **Backend Infrastructure**
- FastAPI REST API (serves both API and web UI)
- Pydantic settings / configuration management
- Service-oriented architecture

✅ **Frontend**
- HTML/CSS/JS single-page app (primary, port 8000)
- Optional Gradio chat interface (port 7860)
- Citation display + ingest form

✅ **Core Pipeline (implemented)**
- **Tree-sitter semantic chunking** — Python, JS, TS, TSX, Go, Java, C, C++, C#, Rust, Ruby (regex fallback for Python/JS/TS/C#)
- **ChromaDB vector database** — persistent, cosine similarity
- **Embeddings** — ChromaDB default embedder (`all-MiniLM-L6-v2`)
- **Claude API integration** — agent with tool-use loop (`claude-sonnet-4-6`)
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

### `Git clone failed` / timeout
Ensure the URL is public and `git` is on your PATH. Large repos may exceed the 60s clone timeout.

### "No relevant code context" on every query
Make sure you indexed a repo first (section 4, Step A).

### MCP tools never fire
Set `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, and `GITHUB_REPO_NAME`, and keep `use_mcp: true`.

### Frontend shows "Cannot connect to backend"
Ensure the backend is running at http://localhost:8000.

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

## 📞 Need Help?

- Open a GitHub issue for bugs
- Email: kitouanna@gmail.com

---

🎉 **Welcome to CodeContext!** Happy coding! 🚀
