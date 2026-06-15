"""Test Pydantic data models."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    Citation,
    CodeChunk,
    ClearIndexResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)


class TestIngestRequest:
    """Test IngestRequest validation."""

    def test_valid_ingest_request(self):
        """Test creating a valid IngestRequest."""
        req = IngestRequest(
            repository_url="https://github.com/user/repo",
            repository_name="my-repo",
        )

        assert req.repository_url == "https://github.com/user/repo"
        assert req.repository_name == "my-repo"
        assert req.clear_before_ingest is False

    def test_ingest_with_clear_flag(self):
        """Test IngestRequest with clear flag."""
        req = IngestRequest(
            repository_url="https://github.com/user/repo",
            repository_name="my-repo",
            clear_before_ingest=True,
        )

        assert req.clear_before_ingest is True

    def test_missing_required_fields(self):
        """Test that missing required fields raises ValidationError."""
        with pytest.raises(ValidationError):
            IngestRequest(repository_url="https://github.com/user/repo")


class TestIngestResponse:
    """Test IngestResponse validation."""

    def test_valid_ingest_response(self):
        """Test creating a valid IngestResponse."""
        resp = IngestResponse(
            message="Ingestion complete",
            files_indexed=10,
            chunks_created=50,
            languages=["python", "javascript"],
        )

        assert resp.message == "Ingestion complete"
        assert resp.files_indexed == 10
        assert resp.chunks_created == 50
        assert resp.languages == ["python", "javascript"]

    def test_empty_languages(self):
        """Test IngestResponse with empty language list."""
        resp = IngestResponse(
            message="Done",
            files_indexed=0,
            chunks_created=0,
            languages=[],
        )

        assert resp.languages == []


class TestCitation:
    """Test Citation model."""

    def test_valid_citation(self):
        """Test creating a valid Citation."""
        citation = Citation(
            file="src/main.py",
            lines="42-58",
            relevance=0.95,
            preview="def foo():\n    pass",
        )

        assert citation.file == "src/main.py"
        assert citation.lines == "42-58"
        assert citation.relevance == 0.95
        assert citation.preview == "def foo():\n    pass"

    def test_citation_without_preview(self):
        """Test Citation without optional preview field."""
        citation = Citation(
            file="src/main.py",
            lines="10-20",
            relevance=0.8,
        )

        assert citation.preview is None

    def test_relevance_score_accepts_floats(self):
        """Test that relevance accepts any float (no validation bounds)."""
        # The Citation model doesn't enforce bounds on relevance
        citation = Citation(
            file="src/main.py",
            lines="1-10",
            relevance=1.5,
        )
        assert citation.relevance == 1.5


class TestQueryRequest:
    """Test QueryRequest validation."""

    def test_valid_query_request(self):
        """Test creating a valid QueryRequest."""
        req = QueryRequest(query="How does authentication work?")

        assert req.query == "How does authentication work?"
        assert req.top_k == 5  # default
        assert req.use_mcp is True  # default
        assert req.include_code_preview is True  # default

    def test_query_with_custom_top_k(self):
        """Test QueryRequest with custom top_k."""
        req = QueryRequest(query="test", top_k=10)

        assert req.top_k == 10

    def test_top_k_bounds(self):
        """Test that top_k must be between 1 and 20."""
        with pytest.raises(ValidationError):
            QueryRequest(query="test", top_k=0)

        with pytest.raises(ValidationError):
            QueryRequest(query="test", top_k=21)

    def test_query_flags(self):
        """Test QueryRequest with feature flags."""
        req = QueryRequest(
            query="test",
            use_mcp=False,
            include_code_preview=False,
        )

        assert req.use_mcp is False
        assert req.include_code_preview is False


class TestQueryResponse:
    """Test QueryResponse validation."""

    def test_valid_query_response(self):
        """Test creating a valid QueryResponse."""
        citations = [
            Citation(file="src/main.py", lines="1-10", relevance=0.9),
            Citation(file="src/utils.py", lines="20-30", relevance=0.8),
        ]
        resp = QueryResponse(
            answer="The authentication uses JWT tokens",
            citations=citations,
            confidence=0.92,
            processing_time_ms=150.5,
        )

        assert resp.answer == "The authentication uses JWT tokens"
        assert len(resp.citations) == 2
        assert resp.confidence == 0.92
        assert resp.processing_time_ms == 150.5
        assert resp.mcp_calls == []

    def test_query_response_with_mcp_calls(self):
        """Test QueryResponse with MCP tool calls."""
        resp = QueryResponse(
            answer="test",
            citations=[],
            mcp_calls=["get_issue", "search_code"],
            confidence=0.5,
            processing_time_ms=100,
        )

        assert resp.mcp_calls == ["get_issue", "search_code"]


class TestHealthResponse:
    """Test HealthResponse model."""

    def test_health_check_ok(self):
        """Test HealthResponse when healthy."""
        resp = HealthResponse(status="ok", db_connected=True)

        assert resp.status == "ok"
        assert resp.db_connected is True
        assert resp.version == "0.1.0"

    def test_health_check_db_disconnected(self):
        """Test HealthResponse when database is down."""
        resp = HealthResponse(status="degraded", db_connected=False)

        assert resp.status == "degraded"
        assert resp.db_connected is False


class TestCodeChunk:
    """Test CodeChunk model."""

    def test_valid_chunk(self):
        """Test creating a valid CodeChunk."""
        chunk = CodeChunk(
            id="chunk_123",
            file="src/main.py",
            language="python",
            start_line=10,
            end_line=25,
            type="function",
            content="def hello():\n    print('hello')",
        )

        assert chunk.id == "chunk_123"
        assert chunk.file == "src/main.py"
        assert chunk.language == "python"
        assert chunk.start_line == 10
        assert chunk.end_line == 25
        assert chunk.type == "function"

    def test_chunk_with_embedding(self):
        """Test CodeChunk with embedding vector."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        chunk = CodeChunk(
            id="chunk_456",
            file="src/utils.py",
            language="python",
            start_line=1,
            end_line=5,
            type="class",
            content="class Helper: pass",
            embedding=embedding,
        )

        assert chunk.embedding == embedding

    def test_chunk_with_metadata(self):
        """Test CodeChunk with custom metadata."""
        metadata = {"complexity": "low", "cyclomatic": 1}
        chunk = CodeChunk(
            id="chunk_789",
            file="src/test.py",
            language="python",
            start_line=1,
            end_line=2,
            type="module",
            content="# test",
            metadata=metadata,
        )

        assert chunk.metadata == metadata


class TestClearIndexResponse:
    """Test ClearIndexResponse model."""

    def test_clear_index_response(self):
        """Test ClearIndexResponse."""
        resp = ClearIndexResponse(
            message="Index cleared successfully",
            chunks_removed=100,
        )

        assert resp.message == "Index cleared successfully"
        assert resp.chunks_removed == 100
