import warnings
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AnyUrl, BeforeValidator, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    """Accept CORS origins as a comma-separated string or a list."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """Application settings — loaded from .env, then environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    # ── Project ───────────────────────────────────────────────────────────────
    PROJECT_NAME: str = "CodeContext"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # ── Sentry (optional) ─────────────────────────────────────────────────────
    SENTRY_DSN: str | None = None

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Accepts a comma-separated string or a JSON array.
    # Example:  BACKEND_CORS_ORIGINS="http://localhost:7860,http://localhost:3000"
    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []
    FRONTEND_HOST: str = "http://localhost:7860"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """Return CORS origins including the frontend host."""
        origins = [str(o).rstrip("/") for o in self.BACKEND_CORS_ORIGINS]
        if self.FRONTEND_HOST not in origins:
            origins = [self.FRONTEND_HOST] + origins
        return origins

    # ── FastAPI ───────────────────────────────────────────────────────────────
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Anthropic ─────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = "changethis"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    EMBEDDER_MODEL: str = "all-MiniLM-L6-v2"

    # ── Embeddings (Optional: for non-Anthropic providers) ────────────────────
    OPENAI_API_KEY: str | None = None

    # ── GitHub / MCP ─────────────────────────────────────────────────────────
    GITHUB_TOKEN: str | None = None
    GITHUB_REPO_URL: str | None = None
    GITHUB_REPO_OWNER: str | None = None
    GITHUB_REPO_NAME: str | None = None

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    CHROMA_DB_PATH: str = (
        "/home/user/.codecontext/chroma_db"
        if Path("/home/user").exists()  # HF Spaces
        else str(Path.home() / ".codecontext" / "chroma_db")  # Local (cross-platform)
    )
    CHROMA_PERSIST: bool = True

    # ── RAG ───────────────────────────────────────────────────────────────────
    RETRIEVER_TOP_K: int = 5
    RETRIEVER_SCORE_THRESHOLD: float = 0.3
    CHUNK_OVERLAP: int = 100
    MIN_CHUNK_SIZE: int = 200
    MAX_CHUNK_SIZE: int = 1000

    # ── Features ──────────────────────────────────────────────────────────────
    USE_MCP: bool = True
    USE_SEMANTIC_CHUNKING: bool = True

    # ── Agent V2 Configuration ────────────────────────────────────────────────
    ENABLE_AGENT_V2: bool = True
    AGENT_ENABLE_QUERY_DECOMPOSITION: bool = True
    AGENT_ENABLE_ITERATIVE_RETRIEVAL: bool = True
    AGENT_ENABLE_SELF_CRITIQUE: bool = True
    AGENT_MAX_RETRIEVAL_ROUNDS: int = 3
    AGENT_REASONING_DEPTH: Literal["shallow", "medium", "deep"] = "medium"

    # ── Multi-Turn Configuration ──────────────────────────────────────────────
    ENABLE_CONVERSATION_STATE: bool = False
    CONVERSATION_HISTORY_LIMIT: int = 10

    # ── Evaluation ────────────────────────────────────────────────────────────
    EVAL_DATASET_PATH: str = "./evaluation/queries.json"
    EVAL_GROUND_TRUTH_PATH: str = "./evaluation/ground_truth.json"

    # ── Secret validation (mirrors template) ─────────────────────────────────
    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        if self.ANTHROPIC_API_KEY == "changethis":
            message = (
                'ANTHROPIC_API_KEY is set to "changethis" — '
                "please set a real key in your .env file."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)
        return self


settings = Settings()
