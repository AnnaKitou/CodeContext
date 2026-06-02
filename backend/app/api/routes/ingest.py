import logging
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path
from typing import Set

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.models.schemas import IngestRequest, IngestResponse
from app.services.chunking import SemanticChunker, is_code_file
from app.services.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Global retriever instance for ingestion
_ingest_retriever = None


def get_ingest_retriever() -> RAGRetriever:
    """Get or create retriever instance for ingestion."""
    global _ingest_retriever
    if _ingest_retriever is None:
        _ingest_retriever = RAGRetriever(
            top_k=settings.RETRIEVER_TOP_K,
            db_path=settings.CHROMA_DB_PATH,
        )
    return _ingest_retriever


@router.post("/ingest", response_model=IngestResponse)
async def ingest_codebase(request: IngestRequest) -> IngestResponse:
    """
    Ingest and index a codebase for semantic search.

    This endpoint:
    1. Clones/fetches the repository
    2. Discovers all code files
    3. Chunks code with tree-sitter (semantic units)
    4. Stores chunks in ChromaDB with embeddings

    Args:
        request: Repository URL and name

    Returns:
        IngestResponse with indexing statistics
    """
    logger.info(f"Starting ingest for {request.repository_name}")

    repo_path = None
    try:
        # 1. Clone repository
        repo_path = await clone_repository(request.repository_url, request.repository_name)
        logger.info(f"Repository cloned to {repo_path}")

        # 2. Discover code files
        code_files = discover_code_files(repo_path)
        logger.info(f"Found {len(code_files)} code files")

        if not code_files:
            return IngestResponse(
                message=f"No code files found in {request.repository_name}",
                files_indexed=0,
                chunks_created=0,
                languages=[],
            )

        # 3. Chunk code files
        chunker = SemanticChunker()
        all_chunks = chunker.chunk_repository(repo_path, code_files)
        logger.info(f"Created {len(all_chunks)} semantic chunks")

        # 4. Store chunks in ChromaDB
        retriever = get_ingest_retriever()
        chunks_added = retriever.add_chunks(all_chunks)

        # Get languages used
        languages = set(chunk.language for chunk in all_chunks)

        return IngestResponse(
            message=f"Successfully indexed {request.repository_name}",
            files_indexed=len(code_files),
            chunks_created=chunks_added,
            languages=sorted(list(languages)),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingest failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")
    finally:
        # Cleanup: remove cloned repository
        if repo_path and os.path.exists(repo_path):
            try:
                # On Windows, use onerror to handle permission issues
                def handle_remove_error(func, path, exc_info):
                    if not os.access(path, os.W_OK):
                        os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
                        time.sleep(0.1)
                        func(path)

                shutil.rmtree(repo_path, onerror=handle_remove_error)
                logger.info(f"Cleaned up temporary repository at {repo_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {repo_path}: {str(e)}")


async def clone_repository(repo_url: str, repo_name: str) -> str:
    """
    Clone a GitHub repository to a temporary directory.

    Args:
        repo_url: GitHub repository URL
        repo_name: Repository name

    Returns:
        Path to cloned repository

    Raises:
        HTTPException: If cloning fails
    """
    import asyncio

    temp_dir = Path("./temp_repos")
    temp_dir.mkdir(exist_ok=True)
    repo_path = temp_dir / repo_name

    # Remove existing clone if present
    if repo_path.exists():
        shutil.rmtree(repo_path)

    try:
        # Run git clone in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    "--single-branch",
                    repo_url,
                    str(repo_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            ),
        )

        if result.returncode != 0:
            raise Exception(f"Git clone failed: {result.stderr}")

        return str(repo_path)

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500, detail="Repository clone timed out (> 60 seconds)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clone repository: {str(e)}")


def discover_code_files(repo_path: str) -> list[str]:
    """
    Discover all code files in a repository.

    Args:
        repo_path: Path to repository root

    Returns:
        List of absolute file paths to code files
    """
    code_files = []

    # Directories to skip
    skip_dirs = {
        ".git",
        ".github",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        "env",
        "build",
        "dist",
        ".venv",
    }

    for root, dirs, files in os.walk(repo_path):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        # Check for .gitignore-style exclusions
        for file in files:
            file_path = os.path.join(root, file)

            # Check if it's a code file
            if is_code_file(file_path):
                code_files.append(file_path)

    return code_files
