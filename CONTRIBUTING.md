# Contributing to CodeContext

Thank you for your interest in contributing to CodeContext! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/CodeContext.git
   cd CodeContext
   ```

2. **Install dependencies**:
   ```bash
   bash scripts/setup.sh
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Running Locally

### Backend
```bash
cd backend
fastapi dev app/main.py
# Starts at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
uv run app.py
# Opens Gradio at http://localhost:7860
```

## Code Style

### Python
- **Formatter**: `ruff format`
- **Linter**: `ruff check --fix`
- **Type checking**: `mypy --strict`

Run before committing:
```bash
cd backend
ruff format .
ruff check --fix .
mypy . --strict
```

## Testing

```bash
cd backend
pytest tests/ -xvs
pytest tests/ --cov=app --cov-report=html
```

## Making Changes

### 1. Branch naming
- Features: `feature/describe-feature`
- Bug fixes: `fix/describe-bug`
- Research: `research/describe-investigation`

### 2. Commit messages
Keep commits atomic and use clear messages:
```
[component] Brief description

Longer explanation if needed.
```

Examples:
- `[retriever] Implement ChromaDB semantic search`
- `[agent] Add MCP GitHub integration for blame queries`
- `[frontend] Add citations panel to chat UI`

### 3. Pull request process
1. Create a feature branch
2. Make your changes
3. Add tests if applicable
4. Ensure all tests pass
5. Submit PR with description of changes
6. Address review feedback

## Key Areas to Contribute

### High Priority
- [ ] Complete tree-sitter AST-based chunking
- [ ] Implement ChromaDB vector search
- [ ] Integrate Anthropic embeddings API
- [ ] Build LLM agent with MCP tool use
- [ ] Create evaluation framework

### Medium Priority
- [ ] Improve citation extraction from LLM responses
- [ ] Add more code languages support (Java, Go, Rust)
- [ ] Implement batch ingestion for large repositories
- [ ] Optimize embedding caching

### Nice to Have
- [ ] Web UI improvements (React/Vue instead of Gradio)
- [ ] Docker support for easy deployment
- [ ] Multi-repository support
- [ ] Analytics dashboard

## Project Structure

```
CodeContext/
├── backend/                    # FastAPI REST API
│   ├── app/
│   │   ├── api/routes/        # API endpoints
│   │   ├── services/          # Business logic
│   │   ├── core/              # Configuration, security
│   │   ├── models/            # Pydantic schemas
│   │   ├── crud/              # Database operations
│   │   └── main.py            # FastAPI app
│   ├── tests/                 # Pytest test suite
│   └── pyproject.toml         # Python dependencies
├── frontend/                   # Gradio chat interface
│   └── app.py                 # Gradio interface
├── scripts/                    # Utility scripts
│   ├── setup.sh               # Project setup
│   └── eval.py                # Evaluation framework
├── evaluation/                 # Evaluation datasets
│   ├── queries_example.json    # Test questions
│   └── ground_truth_example.json # Ground truth
└── docs/                      # Documentation (planned)
```

## Research Tasks

If you're working on research aspects:

1. **Chunking improvement** (`RQ1`):
   - Implement tree-sitter AST parsing
   - Compare with naive fixed-size chunking
   - Measure Recall@k, MRR improvements

2. **RAG vs MCP patterns** (`RQ2`):
   - Identify query types that benefit from RAG vs MCP
   - Create test cases for each pattern
   - Measure performance trade-offs

3. **Citation reliability** (`RQ3`):
   - Evaluate citation accuracy on test set
   - Compare with ground truth file/line references
   - Document edge cases

## Documentation

- Update README.md with new features
- Add docstrings to new functions
- Update DEVELOPMENT.md with architecture changes
- Document evaluation results

## Questions?

- Check DEVELOPMENT.md for architecture details
- Open an issue for questions/discussions
- Email: a.kitou@codehub.gr

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
