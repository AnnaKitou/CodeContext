# CodeContext - Project Status & Roadmap

## Current Status: ✅ **Project Scaffolding Complete**

The foundation of CodeContext has been set up with proper architecture, file structure, and placeholder implementations.

### ✅ Completed

- **Project Structure**
  - FastAPI backend with modular architecture
  - Gradio frontend interface
  - Service layer separation
  - Comprehensive configuration system

- **Documentation**
  - README.md with full project overview
  - CLAUDE.md with architecture and development guide
  - CONTRIBUTING.md with contribution guidelines
  - API reference and examples

- **Configuration**
  - Pydantic settings management
  - Environment variable support (.env)
  - Dependency injection setup

- **Models & Schemas**
  - Request/response Pydantic models
  - Ingest and Query APIs defined
  - Citation and metadata schemas

- **Placeholder Services**
  - Chunking service structure (tree-sitter ready)
  - Retriever service structure (ChromaDB ready)
  - LLM agent structure (Claude API ready)
  - MCP GitHub server structure

- **Evaluation Framework**
  - Evaluation dataset structure
  - Ground truth format
  - Metrics computation skeleton
  - Example test queries and ground truth

## 🚀 Next Steps (Implementation Roadmap)

### Phase 1: Core Indexing Pipeline (HIGH PRIORITY)
**Goal**: Enable uploading and chunking of codebases

1. **Implement tree-sitter integration** (`backend/app/services/chunking.py`)
   - Initialize tree-sitter with language parsers
   - Parse code into AST
   - Extract semantic chunks (functions, classes, methods)
   - Add metadata (file, language, start/end lines)
   - Support Python, JavaScript, Go, Java

2. **Implement ChromaDB integration** (`backend/app/crud/vector_db.py`)
   - Initialize ChromaDB client
   - Create collection with proper metadata schema
   - Implement add_chunks operation
   - Implement search operation with filters

3. **Implement Anthropic embeddings** (`backend/app/core/embeddings.py`)
   - Create embeddings service
   - Call Anthropic API for embeddings
   - Cache embeddings (optional)
   - Handle batch embedding

4. **Complete ingest endpoint** (`backend/app/api/routes/ingest.py`)
   - Clone/fetch repository from GitHub
   - Discover code files
   - Chunk all files
   - Generate embeddings
   - Store in ChromaDB
   - Return statistics

### Phase 2: RAG Retrieval (HIGH PRIORITY)
**Goal**: Retrieve relevant code chunks for queries

1. **Implement retriever** (`backend/app/services/retriever.py`)
   - Encode query with embeddings
   - Search ChromaDB with vector similarity
   - Apply score threshold filtering
   - Return top-k results with metadata
   - Add optional BM25 fallback

2. **Complete query endpoint** (`backend/app/api/routes/query.py`)
   - Integrate retriever
   - Format retrieved context
   - Return chunks with metadata

### Phase 3: LLM Agent & Citations (HIGH PRIORITY)
**Goal**: Generate answers with citations using Claude API

1. **Implement LLM agent** (`backend/app/services/agent.py`)
   - Build system prompt with citation instructions
   - Create prompt with retrieved context
   - Call Claude API with tool definitions
   - Handle tool responses (agentic loop if needed)
   - Extract answer and citations from response
   - Format response

2. **Citation extraction**
   - Parse answer for file references
   - Match against retrieved chunks
   - Verify line numbers
   - Generate Citation objects

### Phase 4: MCP GitHub Integration (MEDIUM PRIORITY)
**Goal**: Enable live data queries with MCP tools

1. **Implement MCP GitHub server** (`backend/app/services/mcp_server.py`)
   - Initialize PyGithub client
   - Implement get_file_blame tool
   - Implement get_issue tool
   - Implement get_pull_requests tool
   - Implement get_commit_history tool

2. **Agent MCP tool use**
   - Define MCP tools in agent
   - Handle tool calls from Claude
   - Call appropriate MCP methods
   - Return results to Claude

### Phase 5: Frontend & UX (MEDIUM PRIORITY)
**Goal**: Complete Gradio interface

1. **Fix Gradio app** (`frontend/app.py`)
   - Test chat interface
   - Test citation display
   - Add code preview panel
   - Add metadata display
   - Test with backend integration

2. **Enhanced UI** (optional)
   - Add code syntax highlighting
   - Add source file viewer
   - Add relevance visualization
   - Add performance metrics

### Phase 6: Evaluation & Research (MEDIUM PRIORITY)
**Goal**: Comprehensive evaluation framework

1. **Build evaluation dataset**
   - Create 20-30 diverse test queries
   - Manually create ground truth answers
   - Document relevant files/lines
   - Mark queries requiring MCP

2. **Implement evaluation metrics** (`scripts/eval.py`)
   - Recall@k computation
   - MRR computation
   - Citation accuracy/precision/recall
   - LLM-as-judge answer quality
   - Processing time metrics

3. **Compare chunking strategies**
   - Run with tree-sitter chunking
   - Run with naive fixed-size chunking
   - Compare all metrics
   - Document findings

4. **Answer research questions**
   - RQ1: tree-sitter vs naive chunking
   - RQ2: RAG vs MCP patterns
   - RQ3: Citation reliability
   - Generate report with findings

### Phase 7: Deployment & Optimization (LOW PRIORITY)
**Goal**: Production-ready system

1. **Docker support**
   - Dockerfile for backend
   - Docker Compose setup
   - Environment configuration

2. **Performance optimization**
   - Embedding caching
   - ChromaDB indexing optimization
   - Parallel chunk processing
   - Request batching

3. **Scalability**
   - Multi-repository support
   - Distributed indexing
   - Load balancing

## Implementation Tips

### For Chunking
- Use `tree-sitter-python` for Python, `tree-sitter-javascript` for JS
- Extract function/class definitions from AST nodes
- Preserve line numbers from source (important for citations!)
- Group related methods with their class

### For ChromaDB
- Use cosine similarity ("hnsw:space": "cosine")
- Store metadata: file, language, start_line, end_line, type
- Use collection names scoped by repository
- Implement persistence to disk

### For LLM Agent
- Use `tool_choice="auto"` for automatic tool use
- Define clear tool schemas for Claude
- Parse tool_calls from response
- Build agentic loop for multi-turn tool use

### For Citations
- Parse answer for file:line patterns
- Validate against retrieved chunks
- Include relevance scores
- Show code previews

## Testing Strategy

### Unit Tests
- `test_chunking.py` - Tree-sitter parsing
- `test_retriever.py` - ChromaDB queries
- `test_embeddings.py` - Embedding generation
- `test_mcp_server.py` - Mock MCP calls

### Integration Tests
- `test_ingest_pipeline.py` - Full index flow
- `test_query_pipeline.py` - Full retrieval flow
- `test_citation_extraction.py` - Citation accuracy

### Manual Testing
- Upload a test repository
- Ask 10 sample questions
- Verify answer quality
- Check citation accuracy
- Test MCP tools

## Known Limitations & TODOs

- [ ] Tree-sitter integration not yet implemented
- [ ] ChromaDB integration not yet implemented
- [ ] Anthropic embeddings API not yet called
- [ ] Claude API not yet integrated for agent
- [ ] MCP GitHub integration not yet implemented
- [ ] Citation extraction not yet implemented
- [ ] Gradio frontend not yet tested with backend
- [ ] Evaluation dataset not yet created
- [ ] Docker setup not yet created
- [ ] Production deployment not yet configured

## Timeline Estimate

- **Phase 1** (Chunking): 2-3 weeks
- **Phase 2** (RAG): 1-2 weeks
- **Phase 3** (Agent & Citations): 1-2 weeks
- **Phase 4** (MCP): 1 week
- **Phase 5** (Frontend): 1 week
- **Phase 6** (Evaluation): 2-3 weeks
- **Phase 7** (Deployment): As needed

**Total**: 8-12 weeks for full implementation

## Getting Help

- **Questions**: Check CLAUDE.md for architecture details
- **Contributing**: See CONTRIBUTING.md
- **Issues**: Create GitHub issues for bugs/features
- **Contact**: a.kitou@codehub.gr

---

**Last Updated**: 2024-01-01
**Project Lead**: Anna Kitou
**Status**: Active Development
