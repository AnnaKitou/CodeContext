from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic API
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_embedding_model: str = "text-embedding-3-small"

    # GitHub (for MCP)
    github_token: str | None = None
    github_repo_url: str | None = None
    github_repo_owner: str | None = None
    github_repo_name: str | None = None

    # FastAPI
    debug: bool = False
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000

    # ChromaDB
    chroma_db_path: str = "./chroma_db"
    chroma_persist: bool = True

    # RAG Configuration
    retriever_top_k: int = 5
    retriever_score_threshold: float = 0.3
    chunk_overlap: int = 100
    min_chunk_size: int = 200
    max_chunk_size: int = 1000

    # Evaluation
    eval_dataset_path: str = "./evaluation/queries.json"
    eval_ground_truth_path: str = "./evaluation/ground_truth.json"

    # Features
    use_mcp: bool = True
    use_semantic_chunking: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
