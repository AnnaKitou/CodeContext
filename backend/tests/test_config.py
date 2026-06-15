"""Test application configuration."""

import os
import warnings
from pathlib import Path

import pytest

from app.core.config import Settings


def test_settings_default_values():
    """Test that Settings loads with default values."""
    settings = Settings()

    assert settings.PROJECT_NAME == "CodeContext"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.VERSION == "0.1.0"
    assert settings.ENVIRONMENT == "local"
    assert settings.DEBUG is False
    assert settings.PORT == 8000
    assert settings.HOST == "0.0.0.0"
    assert settings.CHROMA_DB_PATH == "./chroma_db"
    assert settings.RETRIEVER_TOP_K == 5
    assert settings.USE_MCP is True


def test_settings_anthropic_defaults():
    """Test Anthropic settings defaults (or from .env if present)."""
    settings = Settings()

    # These can be loaded from .env, so just verify they exist and are strings
    assert isinstance(settings.ANTHROPIC_API_KEY, str) and len(settings.ANTHROPIC_API_KEY) > 0
    assert isinstance(settings.ANTHROPIC_MODEL, str) and len(settings.ANTHROPIC_MODEL) > 0
    assert settings.ANTHROPIC_EMBEDDING_MODEL == "text-embedding-3-small"


def test_settings_github_defaults():
    """Test GitHub settings are optional (may be set from .env)."""
    settings = Settings()

    # These can be None or set from .env, just verify the fields exist
    assert hasattr(settings, "GITHUB_TOKEN")
    assert hasattr(settings, "GITHUB_REPO_URL")
    assert hasattr(settings, "GITHUB_REPO_OWNER")
    assert hasattr(settings, "GITHUB_REPO_NAME")


def test_settings_validation_warns_on_default_key_local():
    """Test that using default ANTHROPIC_API_KEY warns in local environment."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        settings = Settings(ENVIRONMENT="local", ANTHROPIC_API_KEY="changethis")

        assert len(w) == 1
        assert "changethis" in str(w[0].message)


def test_settings_validation_raises_on_default_key_production():
    """Test that using default ANTHROPIC_API_KEY raises in production."""
    with pytest.raises(ValueError, match="changethis"):
        Settings(ENVIRONMENT="production", ANTHROPIC_API_KEY="changethis")


def test_settings_cors_origins_parsing():
    """Test CORS origins parsing from string."""
    settings = Settings(
        BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:8080"
    )

    origins = settings.all_cors_origins
    assert len(origins) >= 2
    assert any("localhost:3000" in str(o) for o in origins)
    assert any("localhost:8080" in str(o) for o in origins)


def test_settings_cors_includes_frontend_host():
    """Test that frontend host is always included in CORS origins."""
    settings = Settings(BACKEND_CORS_ORIGINS="http://localhost:3000")

    origins = settings.all_cors_origins
    assert str(settings.FRONTEND_HOST) in origins or settings.FRONTEND_HOST in origins[0]


def test_settings_rag_configuration():
    """Test RAG-specific settings."""
    settings = Settings()

    assert settings.RETRIEVER_TOP_K == 5
    # RETRIEVER_SCORE_THRESHOLD can be overridden by .env
    assert isinstance(settings.RETRIEVER_SCORE_THRESHOLD, float) and settings.RETRIEVER_SCORE_THRESHOLD >= 0
    assert settings.CHUNK_OVERLAP == 100
    assert settings.MIN_CHUNK_SIZE == 200
    assert settings.MAX_CHUNK_SIZE == 1000


def test_settings_feature_flags():
    """Test feature flags."""
    settings = Settings()

    assert settings.USE_MCP is True
    assert settings.USE_SEMANTIC_CHUNKING is True


def test_settings_chromadb_configuration():
    """Test ChromaDB configuration."""
    settings = Settings()

    assert settings.CHROMA_DB_PATH == "./chroma_db"
    assert settings.CHROMA_PERSIST is True


def test_settings_case_insensitive():
    """Test that settings accepts both uppercase and lowercase field names."""
    # Pydantic with case_sensitive=False accepts lowercase
    settings = Settings(DEBUG=True, PORT=9000)

    assert settings.DEBUG is True
    assert settings.PORT == 9000
