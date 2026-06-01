from pydantic import BaseModel, Field


# Ingest API Models

class IngestRequest(BaseModel):
    """Request to ingest and index a codebase."""

    repository_url: str = Field(..., description="GitHub repository URL")
    repository_name: str = Field(..., description="Name of the repository")


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
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)
