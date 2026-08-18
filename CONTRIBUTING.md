# Contributing to CodeContext

Thank you for your interest in contributing to CodeContext! This document provides guidelines and instructions for contributing to the project.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AnnaKitou/CodeContext.git
   cd CodeContext
   ```

### 2. Install dependencies

**With `uv` (recommended):**
```bash
uv sync
```

**With `pip`:**
```bash
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your Anthropic API key (and optionally GitHub token for MCP)
```

## Running Locally

### Backend (API + Web UI)
```bash
uv run fastapi dev backend/app/main.py
# Starts at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Tests
```bash
# Run all tests
uv run pytest backend/tests/ -v

# With coverage report
uv run pytest backend/tests/ --cov=backend/app --cov-report=html

# Specific test file
uv run pytest backend/tests/test_agent_reasoning.py -v
```

## Code Quality

### Style & Linting
```bash
# Format code with ruff
ruff format backend/

# Check and fix linting issues
ruff check --fix backend/

# Type checking (strict mode)
mypy backend/app --strict
```

Run before committing:
```bash
cd backend
ruff format app/
ruff check --fix app/
mypy app/ --strict
pytest tests/ -q
```

## Making Changes

### 1. Branch naming
- Features: `feature/describe-feature`
- Bug fixes: `fix/describe-bug`
- Agent improvements: `agent/describe-improvement`
- Research: `research/describe-investigation`

### 2. Commit messages
Keep commits atomic and descriptive:
```
[component] Brief description

- Longer explanation if needed
- Reference issue or context
```

Examples:
- `[agent] Add query decomposition to handle complex questions`
- `[retriever] Implement adaptive multi-step retrieval`
- `[validator] Add hallucination detection via self-critique`

### 3. Pull request process
1. Create a feature branch from `main`
2. Make your changes (keep commits small & focused)
3. Add tests for new functionality
4. Run full test suite: `pytest backend/tests/ -q`
5. Ensure linting passes: `ruff check --fix && mypy . --strict`
6. Submit PR with clear description and motivation
7. Address review feedback

## Architecture Overview

```
CodeContext/
├── backend/
│   ├── app/
│   │   ├── api/routes/           # FastAPI endpoints
│   │   │   ├── query.py          # /query endpoint (with Agent V2 integration)
│   │   │   └── ingest.py         # /ingest endpoint
│   │   │
│   │   ├── services/             # Business logic & AI services
│   │   │   ├── agent.py          # CodeContextAgent (orchestrator)
│   │   │   ├── query_analyzer.py # Query decomposition
│   │   │   ├── agent_planner.py  # Strategy planning
│   │   │   ├── adaptive_retriever.py  # Multi-step retrieval
│   │   │   ├── answer_validator.py   # Self-critique validation
│   │   │   ├── retriever.py      # RAGRetriever (ChromaDB)
│   │   │   ├── chunking.py       # SemanticChunker (tree-sitter)
│   │   │   └── mcp_server.py     # GitHub MCP tools
│   │   │
│   │   ├── models/schemas.py     # Pydantic request/response models
│   │   ├── core/config.py        # Configuration & settings
│   │   └── main.py               # FastAPI app initialization
│   │
│   └── tests/
│       ├── test_query_analyzer.py          # Unit tests for QueryAnalyzer
│       ├── test_answer_validator.py        # Unit tests for AnswerValidator
│       ├── test_agent_reasoning.py         # Integration tests
│       └── test_main.py                    # API endpoint tests
│
├── frontend/
│   └── index.html                # Primary SPA UI (served by FastAPI)
│
├── AGENT_V2.md                   # Complete Agent V2 documentation
├── QUICKSTART.md                 # Getting started guide
├── DOCUMENTATION.md              # Full technical documentation
└── CONTRIBUTING.md               # This file
```

## Key Components to Understand

### Agent V2 System (ReAct Pattern)
The agentic reasoning system uses the **Reason → Act → Observe → Reflect** pattern:

- **QueryAnalyzer** (`services/query_analyzer.py`) — Analyzes query complexity
- **AgentPlanner** (`services/agent_planner.py`) — Plans strategy before execution
- **AdaptiveRetriever** (`services/adaptive_retriever.py`) — Multi-step retrieval refinement
- **AnswerValidator** (`services/answer_validator.py`) — Self-critique & validation
- **CodeContextAgent** (`services/agent.py`) — Orchestrates the full loop

See [AGENT_V2.md](AGENT_V2.md) for complete details.

### Legacy Components (Still Active)
- **RAGRetriever** — ChromaDB semantic search (unchanged)
- **SemanticChunker** — Tree-sitter AST parsing (unchanged)
- **MCPGithubServer** — GitHub integration via PyGithub (unchanged)

## Areas for Contribution

### High Priority
- [ ] Query refinement using Claude (intelligent iteration)
- [ ] Multi-turn conversation support with persistent history
- [ ] Code-specialized embeddings (replace all-MiniLM-L6-v2)
- [ ] Performance optimization & caching

### Medium Priority
- [ ] Add more language support (currently 11 languages)
- [ ] Batch repository indexing
- [ ] Streaming API responses
- [ ] Docker containerization

### Nice to Have
- [ ] React/Vue frontend alternative
- [ ] Analytics dashboard
- [ ] Cost tracking per query
- [ ] User authentication & rate limiting
- [ ] Webhook support

## Testing Guidelines

### Unit Tests
Test individual services in isolation with mocked dependencies:
```python
# Example: testing QueryAnalyzer
pytest backend/tests/test_query_analyzer.py::test_analyze_complex_query -v
```

### Integration Tests
Test full agent loop with mocked Claude responses:
```python
# Example: testing full reasoning chain
pytest backend/tests/test_agent_reasoning.py::test_thinking_steps_captured -v
```

### End-to-End Tests
Test actual HTTP endpoints:
```python
# Example: testing /query endpoint
pytest backend/tests/test_main.py::TestQueryRouter -v
```

### Coverage Report
```bash
pytest backend/tests/ --cov=backend/app --cov-report=html
# Open htmlcov/index.html in browser
```

## Documentation

When contributing:
- **New services**: Add docstrings and module-level documentation
- **New endpoints**: Document in code and add to [AGENT_V2.md](AGENT_V2.md)
- **Config changes**: Update [QUICKSTART.md](QUICKSTART.md)
- **Architecture changes**: Update [DOCUMENTATION.md](DOCUMENTATION.md)
- **Bug fixes/features**: Update relevant README section

## Questions & Support

- **Architecture questions**: See [DOCUMENTATION.md](DOCUMENTATION.md) & [AGENT_V2.md](AGENT_V2.md)
- **Quick start**: See [QUICKSTART.md](QUICKSTART.md)
- **Agent V2 specifics**: See [AGENT_V2.md](AGENT_V2.md)
- **Contact**: kitouanna@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
