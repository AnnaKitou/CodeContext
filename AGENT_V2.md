# Agent V2: Agentic Reasoning System

CodeContext now features an **advanced agentic reasoning system** that implements the ReAct pattern (Reason → Act → Observe → Reflect) for intelligent, multi-step code analysis.

## Overview

Agent V2 transforms the simple RAG wrapper into a true reasoning agent that:
- **Analyzes** query complexity and decomposes multi-part questions
- **Plans** retrieval strategy and selects appropriate tools
- **Retrieves** context iteratively, refining queries based on results
- **Reasons** over code with Claude, leveraging RAG + MCP tools
- **Critiques** answers through self-validation (optional)
- **Reflects** by returning transparent thinking steps

## Quick Start

### Enable Agent V2

Set in `.env`:
```bash
ENABLE_AGENT_V2=true                      # Master switch (default: true)
AGENT_ENABLE_QUERY_DECOMPOSITION=true     # Analyze query complexity
AGENT_ENABLE_ITERATIVE_RETRIEVAL=true     # Multi-step refinement
AGENT_ENABLE_SELF_CRITIQUE=true           # Validate answers
AGENT_MAX_RETRIEVAL_ROUNDS=3              # Max iterations
AGENT_REASONING_DEPTH=medium              # shallow/medium/deep
```

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does authentication handle token expiration and who maintains that code?",
    "top_k": 10,
    "use_mcp": true,
    "include_code_preview": true
  }'
```

### Example Response

```json
{
  "answer": "Token expiration is handled by...",
  "citations": [...],
  "mcp_calls": ["get_file_blame", "get_commit_history"],
  "confidence": 0.92,
  "processing_time_ms": 3450,
  
  "thinking_process": [
    {
      "step_type": "plan",
      "content": "Received query: How does authentication...",
      "timestamp": "2026-08-18T10:30:45.123Z"
    },
    {
      "step_type": "decompose",
      "content": "Query complexity: COMPLEX. Sub-queries: 2",
      "confidence": 0.95
    },
    {
      "step_type": "plan",
      "content": "Strategy: iterative retrieval, max 3 rounds...",
      "confidence": 0.90
    },
    {
      "step_type": "retrieve",
      "content": "Retrieved 12 chunks over 2 round(s). Queries used: 2",
      "results_found": 12,
      "queries_used": ["token expiration", "JWT validation"]
    },
    {
      "step_type": "reason",
      "content": "Answer generated with 5 citations. MCP calls: 2",
      "confidence": 0.85
    },
    {
      "step_type": "critique",
      "content": "Validation: VALID. Grounding: YES. Risk: low",
      "confidence": 0.92
    },
    {
      "step_type": "reflect",
      "content": "Reasoning complete. Retrieved 12 chunks...",
      "confidence": 0.90
    }
  ],

  "query_decomposition": {
    "original_query": "How does authentication handle token expiration...",
    "is_complex": true,
    "reasoning": "Query asks 2 separate things",
    "sub_queries": [
      {
        "question": "How does authentication handle token expiration?",
        "reasoning": "Technical implementation detail",
        "priority": 1
      },
      {
        "question": "Who maintains the authentication code?",
        "reasoning": "Ownership and responsibility",
        "priority": 2
      }
    ],
    "estimated_depth": 2
  },

  "validation": {
    "is_valid": true,
    "confidence": 0.92,
    "grounded": true,
    "hallucination_risk": "low",
    "missing_aspects": [],
    "suggestions": null
  },

  "retrieval_rounds": 2,
  "num_retrieval_queries": 2
}
```

## Architecture

### Services

1. **QueryAnalyzer** (`query_analyzer.py`)
   - Analyzes query complexity using Claude
   - Decomposes multi-part questions into sub-queries
   - Returns priority-ranked sub-queries
   - Used in PLAN phase

2. **AgentPlanner** (`agent_planner.py`)
   - Plans agent strategy before execution
   - Decides: retrieval type, tools, validation approach
   - Returns structured plan with reasoning
   - Used in PLAN phase

3. **AdaptiveRetriever** (`adaptive_retriever.py`)
   - Orchestrates single-round or iterative retrieval
   - Deduplicates results across rounds
   - Tracks queries used and rounds executed
   - Used in RETRIEVE phase

4. **AnswerValidator** (`answer_validator.py`)
   - Performs self-critique using Claude
   - Checks: grounding, hallucinations, completeness
   - Returns confidence and improvement suggestions
   - Used in CRITIQUE phase

5. **CodeContextAgent** (enhanced `agent.py`)
   - Orchestrates the full ReAct loop
   - Integrates all services
   - Tracks thinking steps for observability
   - Returns QueryResponseV2 with visible reasoning

### Request Flow

```
POST /api/v1/query
    ↓
IF ENABLE_AGENT_V2:
    ↓
    CodeContextAgent.answer_with_reasoning()
        ↓
        PLAN: QueryAnalyzer.analyze_query()
        ↓
        PLAN: AgentPlanner.plan_agent_actions()
        ↓
        RETRIEVE: AdaptiveRetriever.retrieve_with_strategy()
        ↓
        REASON: CodeContextAgent.answer() (existing method, reused)
        ↓
        CRITIQUE: AnswerValidator.validate_answer() [if enabled]
        ↓
        REFLECT: Compile thinking_process
        ↓
        Return QueryResponseV2
ELSE:
    ↓
    Use original simple RAG pipeline
    Return QueryResponseV2 (with empty thinking_process)
```

## Reasoning Phases

### 1. PLAN: Query Analysis
```
Input: "How does auth work and who maintains it?"
↓
QueryAnalyzer:
- Detects complexity: COMPLEX
- Finds sub-questions:
  1. "How does authentication work?"
  2. "Who maintains the auth code?"
- Estimates depth: 2
↓
Output: QueryDecomposition
```

### 2. PLAN: Strategy Planning
```
Input: QueryDecomposition (is_complex=true)
↓
AgentPlanner:
- Decides: iterative retrieval (multiple rounds)
- Tools needed: ["get_file_blame", "get_commit_history"]
- Max rounds: 3
- Top-k per round: 5
↓
Output: QueryPlanResponse
```

### 3. RETRIEVE: Adaptive Context Collection
```
Round 1: Query "token expiration" → 5 chunks
Round 2: Query "JWT validation" → 3 new chunks
         (Agent sees Round 1 wasn't enough)
         Refines query based on results
↓
Output: (12 chunks total, ["token expiration", "JWT validation"], 2 rounds)
```

### 4. REASON: Answer Synthesis
```
Input: Query + 12 chunks + Optional MCP data
↓
Claude:
- Sees all context
- Can call MCP tools: get_file_blame, get_issue, etc.
- Generates answer with citations
↓
Output: (answer_text, citations, mcp_calls)
```

### 5. CRITIQUE: Self-Validation
```
Input: Query + Answer + Citations + Context
↓
AnswerValidator (Claude):
- Is answer grounded in context? YES
- Hallucination risk? LOW
- Missing important aspects? NO
- Confidence: 0.92
↓
Output: ValidationResult
```

### 6. REFLECT: Observability
```
All thinking steps compiled:
[
  ThinkingStep(step_type="plan", ...),
  ThinkingStep(step_type="decompose", ...),
  ThinkingStep(step_type="plan", ...),
  ThinkingStep(step_type="retrieve", ...),
  ThinkingStep(step_type="reason", ...),
  ThinkingStep(step_type="critique", ...),
  ThinkingStep(step_type="reflect", ...),
]
↓
Output: QueryResponseV2 with full transparency
```

## Configuration

All agentic features are independently controllable:

| Config | Default | Effect |
|--------|---------|--------|
| `ENABLE_AGENT_V2` | `true` | Master switch for agentic reasoning |
| `AGENT_ENABLE_QUERY_DECOMPOSITION` | `true` | Analyze query complexity |
| `AGENT_ENABLE_ITERATIVE_RETRIEVAL` | `true` | Allow multi-round retrieval |
| `AGENT_ENABLE_SELF_CRITIQUE` | `true` | Run validation phase |
| `AGENT_MAX_RETRIEVAL_ROUNDS` | `3` | Limit iteration count |
| `AGENT_REASONING_DEPTH` | `"medium"` | `shallow/medium/deep` |
| `ENABLE_CONVERSATION_STATE` | `false` | Multi-turn support (future) |
| `CONVERSATION_HISTORY_LIMIT` | `10` | Max messages per conversation |

### Graceful Degradation

- If `ENABLE_AGENT_V2=false`: Falls back to simple RAG
- If services fail: Returns fallback response with error indication
- If Claude returns invalid JSON: Uses heuristic fallback
- If no chunks found: Returns helpful message
- If MCP tools fail: Continues with RAG data only

## Testing

### Unit Tests

```bash
# Test QueryAnalyzer
pytest backend/tests/test_query_analyzer.py -v

# Test AnswerValidator
pytest backend/tests/test_answer_validator.py -v

# Test full agentic loop
pytest backend/tests/test_agent_reasoning.py -v
```

### Key Test Scenarios

1. **Simple Query**: Single-part question → no decomposition
2. **Complex Query**: Multi-part question → decomposition + iterative retrieval
3. **Hallucination Detection**: Answer with unsupported claims → validation catches it
4. **Error Handling**: Claude API failure → graceful fallback
5. **JSON Parsing**: Invalid JSON response → regex extraction fallback

## Performance Considerations

### Latency

- **Simple queries** (Agent V2): +500-1000ms (analysis + planning overhead)
- **Complex queries** (Agent V2): +1500-3000ms (iterative retrieval + critique)
- **Fallback (RAG)**: Original latency (no overhead)

### Cost Control

```python
# Limit expensive features
AGENT_MAX_RETRIEVAL_ROUNDS=1              # Single round
AGENT_ENABLE_SELF_CRITIQUE=false          # Skip validation
AGENT_ENABLE_QUERY_DECOMPOSITION=false    # Skip analysis
```

### Token Usage

Agent V2 uses more tokens due to:
- Query analysis (planning)
- Iterative retrieval (multiple queries)
- Self-critique (validation call)

Typical budget per query:
- Simple RAG: ~2-3k tokens
- Agent V2 (simple query): ~4-5k tokens
- Agent V2 (complex query): ~8-12k tokens

## Troubleshooting

### Agent returns empty thinking_process

**Cause**: `ENABLE_AGENT_V2=false` or services not initialized

**Fix**: Check `.env` has `ENABLE_AGENT_V2=true`

### Validation always returns medium/high risk

**Cause**: Answer is not well-grounded in retrieved chunks

**Fix**: Increase `RETRIEVER_TOP_K` or improve query decomposition

### Iterative retrieval doesn't refine queries

**Cause**: Fallback mode (no Claude-based query refinement yet)

**Current**: Refinement is planned for future phases

### MCP tools not called

**Cause**: `use_mcp=false` in request or GitHub not configured

**Fix**: Set `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME` + `use_mcp=true`

## Production Notes

✅ **Production Ready For:**
- Single-turn queries
- Structured logging
- Error handling & graceful degradation
- Type safety (Pydantic validation)
- Configuration-driven behavior

⚠️ **Future Considerations:**
- Load testing under high concurrency
- Cost optimization (token usage)
- Rate limiting per user
- Caching of frequently asked questions
- Analytics on reasoning patterns

## Related Files

- Core logic: `backend/app/services/agent.py`
- Services: `backend/app/services/{query_analyzer,agent_planner,adaptive_retriever,answer_validator}.py`
- Retrieval: `backend/app/services/retriever.py` + `backend/app/services/embedder_factory.py` (LangChain-based embeddings)
- API: `backend/app/api/routes/query.py`
- Models: `backend/app/models/schemas.py`
- Config: `backend/app/core/config.py`
- Tests: `backend/tests/test_*.py`

## LangChain Usage in Agent V2

Agent V2 indirectly uses LangChain through the retrieval layer:
- **`embedder_factory.py`** uses `langchain-huggingface` to create embedder instances
- **`retriever.py`** depends on `langchain_core.embeddings.Embeddings` interface
- This design allows swapping embedder backends (HuggingFace local → Anthropic API) without changing agent logic
