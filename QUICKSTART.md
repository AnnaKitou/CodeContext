# 🚀 CodeContext - Quick Start Guide

Welcome to CodeContext! This guide will get you up and running in minutes.

## Prerequisites

- Python 3.11+
- `uv` package manager
- GitHub account (for MCP integration)
- Anthropic API key

## 1️⃣ Initial Setup (5 minutes)

### Clone and Setup
```bash
cd "C:\Users\Annak\Desktop\AI LLM\Ασκήσεις\CodeContext"
bash scripts/setup.sh
```

### Configure API Keys
```bash
# Copy template
cp .env.example .env

# Edit .env with your keys
# ANTHROPIC_API_KEY=sk-...
# GITHUB_TOKEN=ghp_...
```

## 2️⃣ Start Backend (Terminal 1)

```bash
cd backend
fastapi dev app/main.py
```

Output should show:
```
Uvicorn running on http://127.0.0.1:8000
```

**Test it**: Open http://localhost:8000/docs to see API documentation

## 3️⃣ Start Frontend (Terminal 2)

```bash
cd frontend
uv run app.py
```

Output should show:
```
Running on http://127.0.0.1:7860
```

Open that URL in your browser 🎉

## 4️⃣ Use the System

### Option A: Upload Your Code
1. Go to **"📥 Ingest Repository"** tab
2. Enter GitHub URL: `https://github.com/anthropics/anthropic-sdk-python`
3. Enter name: `anthropic-sdk`
4. Click **"🚀 Start Ingestion"**
5. Wait for indexing to complete

### Option B: Try Sample Questions
In the **"💬 Chat"** tab, try these questions:
- "What's the main function of this codebase?"
- "How is authentication implemented?"
- "What are the key API endpoints?"

You'll see:
- 📝 Answer with explanation
- 📍 Source file citations with line numbers
- 🔗 Relevant code snippets
- 🎯 Confidence score

## 5️⃣ What's Working Now

✅ **Backend Infrastructure**
- FastAPI REST API
- Configuration management
- Service architecture
- API endpoints defined

✅ **Frontend**
- Gradio chat interface
- Citation display
- Ingest form

⏳ **Not Yet Implemented**
- Tree-sitter code chunking
- ChromaDB vector database
- Anthropic embeddings
- Claude API integration
- GitHub MCP integration

## 🛠️ Next Development Steps

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed implementation roadmap.

### Priority Tasks:
1. **Implement tree-sitter chunking** (`backend/app/services/chunking.py`)
   - Parse code AST
   - Extract semantic units (functions, classes)
   
2. **Connect ChromaDB** (`backend/app/services/retriever.py`)
   - Initialize vector database
   - Implement semantic search
   
3. **Integrate Claude API** (`backend/app/services/agent.py`)
   - Build prompts with retrieved context
   - Handle function calling for tools
   
4. **Add GitHub MCP** (`backend/app/services/mcp_server.py`)
   - Implement git blame, issues, PRs lookups

## 📚 Documentation

- **[README.md](README.md)** - Project overview
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Architecture & development guide
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Implementation roadmap
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Reinstall dependencies
cd backend
uv sync
```

### Frontend shows "Cannot connect to backend"
- Ensure backend is running: `http://localhost:8000`
- Check firewall/network settings
- Verify .env is configured correctly

### Missing API keys
```
Error: ANTHROPIC_API_KEY not set
```
- Edit `.env` file in project root
- Add your actual API keys
- Restart backend

## 🔑 Getting API Keys

### Anthropic API
1. Go to https://console.anthropic.com
2. Create an API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-...`

### GitHub Token
1. Go to https://github.com/settings/tokens
2. Create a Personal Access Token
3. Select scopes: `repo`, `read:org`
4. Add to `.env`: `GITHUB_TOKEN=ghp_...`

## 📞 Need Help?

- Check [DEVELOPMENT.md](DEVELOPMENT.md) for architecture questions
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development help
- Open a GitHub issue for bugs
- Email: a.kitou@codehub.gr

## 📈 Next Features to Build

Want to contribute? Here are high-impact areas:

1. **Tree-sitter integration** (Enables code chunking)
2. **ChromaDB setup** (Enables vector search)
3. **Anthropic embeddings** (Enables semantic search)
4. **Claude API agent** (Enables intelligent answers)
5. **GitHub MCP** (Enables live data queries)
6. **Evaluation framework** (Enables research validation)

---

🎉 **Welcome to CodeContext!** Happy coding! 🚀
