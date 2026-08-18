from pydantic import BaseModel, Field


# Ingest API Models

class IngestRequest(BaseModel):
    """Request to ingest and index a codebase."""

    repository_url: str = Field(..., description="GitHub repository URL")
    repository_name: str = Field(..., description="Name of the repository")
    clear_before_ingest: bool = Field(
        False, description="Wipe the existing index before indexing this repo"
    )



class ClearIndexResponse(BaseModel):
    """Response after clearing the index."""

    message: str
    chunks_removed: int


class IngestResponse(BaseModel):
    """Response after ingestion."""

    message: str
    files_indexed: int
    chunks_created: int
    languages: list[str]


# Query API Models

class Citation(BaseModel):
    """Citation reference to source code."""

    file: str = Field(..., description="File path")
    lines: str = Field(..., description="Line range (e.g., '42-58')")
    relevance: float = Field(..., description="Relevance score 0-1")
    preview: str | None = Field(None, description="Code snippet preview")


class QueryRequest(BaseModel):
    """Request to query the codebase."""

    query: str = Field(..., description="Natural language question")
    top_k: int = Field(5, description="Number of chunks to retrieve", ge=1, le=20)
    use_mcp: bool = Field(True, description="Use MCP for live data")
    include_code_preview: bool = Field(True, description="Include code snippets")


class QueryResponse(BaseModel):
    """Response to a query."""

    answer: str = Field(..., description="Answer to the query")
    citations: list[Citation] = Field(..., description="Source citations")
    mcp_calls: list[str] = Field(default_factory=list, description="MCP tools used")
    confidence: float = Field(..., description="Confidence score 0-1")
    processing_time_ms: float = Field(..., description="Query processing time")


# Health Check

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    db_connected: bool
    version: str = "0.1.0"


# Chunk (internal)

class CodeChunk(BaseModel):
    """Semantic code chunk with metadata."""

    id: str
    file: str
    language: str
    start_line: int
    end_line: int
    type: str  # "function", "class", "method", "module", etc.
    content: str
    relevance_score: float = 0.0
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)


# ── Agent V2: Agentic System Models ───────────────────────────────────────────

class ThinkingStep(BaseModel):
    """Single step in the agent's reasoning process."""

    step_type: str = Field(
        ...,
        description="Type of step: 'plan', 'decompose', 'retrieve', 'reason', 'critique', 'reflect'",
    )
    content: str = Field(..., description="Description of what happened in this step")
    queries_used: list[str] | None = Field(
        None, description="For retrieval steps, the queries used"
    )
    results_found: int | None = Field(None, description="For retrieval steps, results count")
    confidence: float | None = Field(None, description="Agent confidence at this step (0-1)")
    timestamp: str | None = Field(None, description="ISO timestamp when step executed")


class SubQuery(BaseModel):
    """A sub-query resulting from query decomposition."""

    question: str = Field(..., description="The sub-question")
    reasoning: str = Field(..., description="Why this sub-question is needed")
    priority: int = Field(default=1, description="Priority: 1=high, 2=medium, 3=low")


class QueryDecomposition(BaseModel):
    """Result of decomposing a complex query into sub-queries."""

    original_query: str = Field(..., description="The original query")
    is_complex: bool = Field(..., description="Whether the query needs decomposition")
    reasoning: str = Field(..., description="Why/how the query was decomposed")
    sub_queries: list[SubQuery] = Field(default_factory=list, description="Resulting sub-queries")
    estimated_depth: int = Field(
        default=1, description="Estimated reasoning depth needed (1-3)"
    )


class RetrievalStrategy(BaseModel):
    """Strategy for retrieving relevant context."""

    retrieval_type: str = Field(
        default="single_round",
        description="'single_round' or 'iterative'",
    )
    use_mcp_tools: bool = Field(default=False, description="Whether to use MCP tools")
    mcp_tools_needed: list[str] = Field(
        default_factory=list, description="Specific MCP tools to use"
    )
    max_retrieval_rounds: int = Field(default=1, description="Max iterations for adaptive retrieval")
    top_k_per_round: int = Field(default=5, description="Number of results per retrieval")


class QueryPlanResponse(BaseModel):
    """The agent's plan before executing."""

    query: str = Field(..., description="Original query")
    decomposition: QueryDecomposition = Field(..., description="Query decomposition")
    retrieval_strategy: RetrievalStrategy = Field(..., description="How to retrieve context")
    expected_tools: list[str] = Field(
        default_factory=list, description="Tools the agent expects to use"
    )
    reasoning: str = Field(..., description="Agent's reasoning about the plan")


class ValidationResult(BaseModel):
    """Result of validating an answer."""

    is_valid: bool = Field(..., description="Whether answer passes validation")
    confidence: float = Field(..., description="Validation confidence (0-1)")
    grounded: bool = Field(..., description="Is answer grounded in retrieved context?")
    hallucination_risk: str = Field(
        default="low",
        description="Hallucination risk: 'low', 'medium', 'high'",
    )
    missing_aspects: list[str] = Field(
        default_factory=list, description="Important aspects the answer is missing"
    )
    suggestions: str | None = Field(None, description="Suggestions for improving answer")


class QueryResponseV2(QueryResponse):
    """Enhanced query response with agentic reasoning visible."""

    thinking_process: list[ThinkingStep] = Field(
        default_factory=list, description="Agent's reasoning steps"
    )
    query_decomposition: QueryDecomposition | None = Field(
        None, description="How the query was understood"
    )
    validation: ValidationResult | None = Field(None, description="Answer validation results")
    retrieval_rounds: int = Field(default=1, description="Number of retrieval iterations")
    num_retrieval_queries: int = Field(
        default=1, description="Total retrieval queries executed"
    )
