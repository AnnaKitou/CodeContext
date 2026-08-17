"""Factory for creating embedders based on model configuration."""

import logging
from langchain_core.embeddings import Embeddings
from ..core.config import settings

logger = logging.getLogger(__name__)

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings


def detect_embedder_type(model_name: str) -> str:
    """
    Detect embedder type from model name.

    Returns: "huggingface", "anthropic", "openai", or "huggingface" (default)
    """
    model_lower = model_name.lower()

    # Anthropic models
    if "text-embedding-3" in model_lower:
        return "anthropic"

    # OpenAI models (but not anthropic's text-embedding-3)
    if "text-embedding" in model_lower and "anthropic" not in model_lower:
        return "openai"

    # HuggingFace models (most common patterns)
    if any(pattern in model_lower for pattern in [
        "minilm", "mpnet", "all-", "sentence-transformers",
        "distilbert", "roberta", "bert-base"
    ]):
        return "huggingface"

    # Default to HuggingFace for unknown models
    logger.debug(f"Unknown model '{model_name}', defaulting to HuggingFace")
    return "huggingface"


def create_embedder(model_name: str | None = None) -> Embeddings:
    """
    Create an embedder instance based on model name.

    Args:
        model_name: Model identifier (if None, uses settings.EMBEDDER_MODEL)

    Returns:
        Embeddings instance (HuggingFaceEmbeddings, AnthropicEmbeddings, or OpenAIEmbeddings)
    """
    if model_name is None:
        model_name = settings.EMBEDDER_MODEL

    embedder_type = detect_embedder_type(model_name)
    logger.info(f"Creating {embedder_type} embedder with model: {model_name}")

    try:
        if embedder_type == "anthropic":
            return _create_anthropic_embedder(model_name)
        elif embedder_type == "openai":
            return _create_openai_embedder(model_name)
        else:  # huggingface (default)
            return _create_huggingface_embedder(model_name)
    except Exception as e:
        logger.error(f"Failed to create {embedder_type} embedder: {str(e)}")
        logger.warning("Falling back to HuggingFace embedder")
        return _create_huggingface_embedder("all-MiniLM-L6-v2")


def _create_anthropic_embedder(model_name: str) -> Embeddings:
    """Create Anthropic embedder with graceful degradation."""
    if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "changethis":
        logger.warning(
            "Anthropic API key not configured, falling back to HuggingFace embedder"
        )
        return _create_huggingface_embedder("all-MiniLM-L6-v2")

    try:
        from langchain_anthropic import AnthropicEmbeddings
        return AnthropicEmbeddings(
            model=model_name,
            api_key=settings.ANTHROPIC_API_KEY
        )
    except ImportError:
        logger.warning("langchain-anthropic not installed, using HuggingFace embedder")
        return _create_huggingface_embedder("all-MiniLM-L6-v2")


def _create_openai_embedder(model_name: str) -> Embeddings:
    """Create OpenAI embedder with graceful degradation."""
    if not settings.OPENAI_API_KEY:
        logger.warning(
            "OpenAI API key not configured, falling back to HuggingFace embedder"
        )
        return _create_huggingface_embedder("all-MiniLM-L6-v2")

    try:
        from langchain_community.embeddings import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=model_name,
            api_key=settings.OPENAI_API_KEY
        )
    except ImportError:
        logger.warning("langchain[openai] not installed, using HuggingFace embedder")
        return _create_huggingface_embedder("all-MiniLM-L6-v2")


def _create_huggingface_embedder(model_name: str) -> HuggingFaceEmbeddings:
    """Create HuggingFace embedder (always available, no API key required)."""
    return HuggingFaceEmbeddings(model_name=model_name)
