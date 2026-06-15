"""Shared pytest fixtures and configuration."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    with TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text(
            "ANTHROPIC_API_KEY=test-key-123\n"
            "ANTHROPIC_MODEL=claude-opus-4-5\n"
            "DEBUG=true\n"
        )
        yield env_file


@pytest.fixture
def test_client():
    """Provide a FastAPI TestClient."""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def chroma_db_path(tmp_path):
    """Create a temporary ChromaDB path."""
    db_path = tmp_path / "test_chroma"
    db_path.mkdir()
    os.environ["CHROMA_DB_PATH"] = str(db_path)
    yield db_path
    # Cleanup
    if "CHROMA_DB_PATH" in os.environ:
        del os.environ["CHROMA_DB_PATH"]
